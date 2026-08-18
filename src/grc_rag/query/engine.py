"""The query core: `Engine.answer(question) -> Answer`, importable, no CLI.

Everything argparse-shaped lives in `cli.py`; this module returns
structured objects and prints nothing (decisions.md D1). One Engine
instance loads BGE-M3, the reranker and the LanceDB table once, so a
REPL or a future HTTP adapter pays the model load once per process, not
once per question.

THE PIPELINE, and where each guarantee lives

  retrieve   dense (BGE-M3 cosine) + lexical (LanceDB BM25), always
             both, rank-fused with RRF. Pure vector search fails on
             exact identifiers - "Article 15" embeds next to 14 and 16.
  rerank     bge-reranker-v2-m3 cross-encoder over the fused top ~20,
             keeping ~5. Run through sentence-transformers'
             CrossEncoder - verified at build time, per the brief,
             by `cli.py selftest --with-models`.
  gate       BEFORE any model call, on the best DENSE cosine alone -
             never the fused rank and never BM25, which scores high on
             any question sharing common words (the opposite of what a
             refusal test needs). Below the floor: fixed refusal string,
             no request made. An untuned floor is decoration; the tuned
             value and its evidence live in docs/decisions.md.
  generate   temperature 0, via the plain `openai` client against an
             OpenAI-compatible endpoint (DeepSeek default, D3). The
             grounding prompt orders the model to prefer the documents
             over its training data - this corpus is a 2026
             consolidation and parametric memory predates it.
  verify     mechanical, post-generation: every quoted span >= 20 chars
             must appear verbatim in a chunk that was RETRIEVED - not
             merely somewhere in the corpus - so the citation is checked
             for free. Traps inherited from book2rag, already paid for:
             smart punctuation folds to ASCII BEFORE extraction; our
             own [chunk-id] markers strip from both sides; quotes
             extract segment-wise, never by naive left-to-right pairing
             (legal text nests quotes).
  cite       anchor honesty: the rendered citation is the chunk's own
             `citation` field plus its date basis. The chunker decided
             the precision; nothing here re-derives it. A recital cites
             the act as published (2024), an enacting chunk the
             consolidation (2026) - saying which is the point (D4).
"""
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field

import lancedb
from openai import OpenAI
from sentence_transformers import CrossEncoder, SentenceTransformer

EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
TABLE = "chunks"

REFUSAL = "The corpus does not address this."

# Tuned against the eval set's in-corpus vs out-of-corpus dense-score
# distributions (docs/decisions.md D7): out-of-corpus max 0.6151,
# in-corpus min 0.6264, midpoint 0.62. The gap is real but narrow -
# re-run `cli.py floor` after ANY corpus, chunking or embedder change.
DEFAULT_FLOOR = 0.62

GROUNDING_PROMPT = """\
You are a compliance research assistant answering questions from an
indexed corpus of EU regulatory texts. Answer ONLY from the numbered
documents provided below. No outside knowledge, no training-data recall.

1. Cite every claim to the document supporting it by its chunk id in
   square brackets, e.g. [ai-act#art_15(4)].
2. Quote the decisive language verbatim in double quotes, followed by
   its chunk id.
3. If the documents do not contain the answer, say exactly:
   "The corpus does not address this." You may add one sentence saying
   what the retrieved documents do contain, cited. Do not guess.
4. The documents are the law as currently consolidated (recitals: the
   act as published). Where a document contradicts what you believe you
   know, THE DOCUMENT WINS - your training data may predate amendments.
   Never state a number, threshold, date or article content that does
   not appear in a provided document.
5. Answer the question that was asked; do not survey the corpus."""


# -- structured results (D1: the core returns objects, never prints) ---------

@dataclass
class Source:
    """One retrieved chunk plus the scores that put it there."""
    id: str
    citation: str
    parent_path: str
    date_basis: str
    version_date: str
    body: str
    text: str
    dense: float          # cosine similarity; 0.0 if only BM25 found it
    rerank: float = 0.0


@dataclass
class Answer:
    question: str
    mode: str             # "answered" | "refused-gate" | "refused-generation"
    text: str
    sources: list = field(default_factory=list)   # the Sources given to the model
    best_dense: float = 0.0
    floor: float = None
    quotes: list = field(default_factory=list)    # (span, Source-or-None) pairs
    verified: bool = True                          # False if any quote unmatched

    @property
    def refused(self):
        return self.mode != "answered"


# -- text normalisation for the verifier (book2rag §6 lineage) ---------------

# Our own apparatus that a model may copy into a quote: the [chunk-id]
# citation markers the grounding prompt mandates. Stripped from both
# sides before matching - a false verifier failure trains people to
# ignore the verifier, which defeats it.
MARKER_RE = re.compile(r"\[[a-z0-9-]+#[^\]]*\]")


def fold_punct(s):
    """Smart punctuation to ASCII, BEFORE quote extraction - EUR-Lex text
    is full of curly quotes and a model quotes them faithfully; extraction
    that only sees straight quotes would pass them through unchecked."""
    return (s.replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"')
             .replace("—", "-").replace("–", "-")
             .replace("…", "..."))


def normalize(s):
    s = unicodedata.normalize("NFKC", fold_punct(s))
    s = MARKER_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


SEGMENT_RE = re.compile(r"\n+")


def extract_quotes(answer, min_len=20):
    """One quoted span per line-segment: first quote mark to last.

    Not `"([^\"]{20,})"` over the whole answer: legal text nests quoted
    definitions inside quoted provisions, and naive pairing closes on the
    wrong mark and silently re-pairs everything after it (observed in
    book2rag - an invented quote was eaten as a delimiter). Two separate
    quotes on one line merge into one unmatchable span: a false alarm,
    which is the safe direction. The verifier fails loudly or not at all.
    """
    out = []
    for seg in SEGMENT_RE.split(fold_punct(answer)):
        first, last = seg.find('"'), seg.rfind('"')
        if first >= 0 and last > first:
            span = seg[first + 1:last].strip()
            if len(span) >= min_len:
                out.append(span)
    return out


def verify(answer_text, sources):
    """Every quoted span must appear verbatim in a RETRIEVED chunk's
    `body` - the act's words with nothing this pipeline added (the
    parent-path lives in `text`, deliberately not checked against)."""
    haystacks = [(s, normalize(s.body)) for s in sources]
    results = []
    for q in extract_quotes(answer_text):
        needle = normalize(q)
        hit = next((s for s, h in haystacks if needle and needle in h), None)
        results.append((q, hit))
    return results


# -- citation rendering ------------------------------------------------------

def cite(source):
    """The chunk's own citation string plus the date claim it can honestly
    make. `date_basis` decides the wording: the enacting text is current
    AS OF its consolidation; a recital is the act AS PUBLISHED, and
    rendering it with the consolidation's date would claim a currency the
    recitals do not have (D4)."""
    if source.date_basis == "consolidation":
        return f"{source.citation} (consolidated text as of {source.version_date})"
    return f"{source.citation} (act as published, {source.version_date})"


# -- the engine --------------------------------------------------------------

class Engine:
    """Loads once, answers many. No module-level state (D1)."""

    def __init__(self, index_dir="index", floor=DEFAULT_FLOOR, k=20, keep=5,
                 base_url="https://api.deepseek.com",
                 chat_model="deepseek-chat", api_key=None):
        self.floor, self.k, self.keep = floor, k, keep
        self.chat_model = chat_model
        db = lancedb.connect(index_dir)
        self.table = db.open_table(TABLE)
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.reranker = CrossEncoder(RERANK_MODEL)
        key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.client = OpenAI(base_url=base_url, api_key=key or "unset")

    # -- retrieval ----------------------------------------------------------

    def _source(self, row, dense=0.0):
        return Source(id=row["id"], citation=row["citation"],
                      parent_path=row["parent_path"],
                      date_basis=row["date_basis"],
                      version_date=row["version_date"],
                      body=row["body"], text=row["text"], dense=dense)

    def retrieve(self, question):
        """Hybrid RRF over both legs, rerank the fused top k, keep `keep`.

        Returns (kept sources, best dense cosine). The best cosine comes
        from the dense leg alone and travels with the result because the
        gate reads it - fused rank and BM25 say nothing about whether the
        corpus is actually about the question.
        """
        qvec = self.embedder.encode([question],
                                    normalize_embeddings=True)[0].tolist()
        dense = (self.table.search(qvec, vector_column_name="vector")
                 .distance_type("cosine").limit(self.k * 2).to_list())
        # LanceDB cosine _distance = 1 - cosine similarity.
        cos_by_id = {r["id"]: 1.0 - r["_distance"] for r in dense}
        best = max(cos_by_id.values(), default=0.0)

        try:
            lexical = (self.table.search(question, query_type="fts")
                       .limit(self.k * 2).to_list())
        except Exception:
            lexical = []       # an FTS syntax miss must not kill retrieval

        fused, rows = {}, {}
        for rank, r in enumerate(dense):
            fused[r["id"]] = fused.get(r["id"], 0.0) + 1.0 / (60.0 + rank)
            rows[r["id"]] = r
        for rank, r in enumerate(lexical):
            fused[r["id"]] = fused.get(r["id"], 0.0) + 1.0 / (60.0 + rank)
            rows.setdefault(r["id"], r)

        top = sorted(fused, key=lambda i: -fused[i])[:self.k]
        sources = [self._source(rows[i], cos_by_id.get(i, 0.0)) for i in top]

        pairs = [(question, s.text) for s in sources]
        for s, score in zip(sources, self.reranker.predict(pairs)):
            s.rerank = float(score)
        sources.sort(key=lambda s: -s.rerank)
        return sources[:self.keep], best

    # -- generation ---------------------------------------------------------

    def _generate(self, question, sources):
        docs = "\n\n".join(
            f"[{s.id}] {cite(s)}\n{s.body}" for s in sources)
        r = self.client.chat.completions.create(
            model=self.chat_model, temperature=0,
            messages=[
                {"role": "system", "content": GROUNDING_PROMPT},
                {"role": "user",
                 "content": f"Documents:\n\n{docs}\n\n---\n\n"
                            f"Question: {question}"}])
        return r.choices[0].message.content

    def answer(self, question):
        sources, best = self.retrieve(question)
        if self.floor is not None and best < self.floor:
            return Answer(question=question, mode="refused-gate",
                          text=REFUSAL, sources=sources, best_dense=best,
                          floor=self.floor)
        text = self._generate(question, sources)
        quotes = verify(text, sources)
        mode = ("refused-generation" if REFUSAL.lower() in text.lower()
                else "answered")
        return Answer(question=question, mode=mode, text=text,
                      sources=sources, best_dense=best, floor=self.floor,
                      quotes=quotes,
                      verified=all(hit is not None for _, hit in quotes))

    def dense_score(self, question):
        """Best dense cosine only - what the gate would see. Used by the
        floor-tuning command, which must measure exactly the gate's input."""
        qvec = self.embedder.encode([question],
                                    normalize_embeddings=True)[0].tolist()
        hits = (self.table.search(qvec, vector_column_name="vector")
                .distance_type("cosine").limit(1).to_list())
        return 1.0 - hits[0]["_distance"] if hits else 0.0


def cited_ids(answer_text):
    """Chunk ids the model actually cited, in order of first appearance."""
    seen, out = set(), []
    for m in MARKER_RE.finditer(answer_text):
        cid = m.group(0)[1:-1]
        if cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def load_eval(path):
    """The eval set, one dict per question. Named file, never a glob."""
    return [json.loads(line)
            for line in open(path, encoding="utf-8") if line.strip()]
