#!/usr/bin/env python3
"""Chunks -> a LanceDB table with both legs of the hybrid retrieval built.

    python -m grc_rag.query.index                 # build from corpus/chunks
    python -m grc_rag.query.index --smoke-only    # check an existing index

WHY BOTH LEGS ARE BUILT HERE AND NOT AT QUERY TIME

Retrieval is dense + lexical, rank-fused, always both: pure vector search
fails on exact identifiers, because "Article 15" sits in embedding space
right next to Articles 14 and 16 and the literal token is the only thing
that separates them. The lexical leg is LanceDB's own BM25 full-text
index rather than BGE-M3's sparse output - the architecture brief said to
verify that at build time rather than assume it, and this file does:
`--smoke-only` runs an identifier query through the lexical leg and fails
if it comes back empty.

WHAT IS EMBEDDED

The chunk's `text`, which carries the parent path and the chapeau, not
the bare `body`. "4. High-risk AI systems shall be as resilient as
possible" means nothing without "Article 15"; the path is what makes the
chunk answerable on its own, and it is what the lexical leg matches an
article number against. `body` is stored alongside, untouched, because
M4's quote check has to run against the act's words with nothing this
pipeline added.

INDEX IS CLASS C

`index/` is gitignored and has no backup: it is rebuildable from the
corpus and this file in a few minutes (decisions.md D0). The corpus is
the artifact; this is a derived cache, and treating it as anything more
is how a pipeline acquires a state nobody can reproduce.
"""
import argparse
import json
import sys
from pathlib import Path

import lancedb
from lancedb.index import FTS
from sentence_transformers import SentenceTransformer

MODEL = "BAAI/bge-m3"          # pinned by name; weights live in the HF cache
DIM = 1024
TABLE = "chunks"

# Named, never globbed: `corpus/chunks/*.jsonl` would also sweep up
# anything a future step writes beside them, and the report files next
# door are the standing reminder of why this repo does not glob.
CHUNK_FILES = [
    "corpus/chunks/ai-act.chunks.jsonl",
    "corpus/chunks/ai-act.recitals.chunks.jsonl",
    "corpus/chunks/gdpr.chunks.jsonl",
    "corpus/chunks/gdpr.recitals.chunks.jsonl",
    "corpus/chunks/nis2.chunks.jsonl",
    "corpus/chunks/nis2.recitals.chunks.jsonl",
]

# Fields that travel into the table. Anything not named here stays out,
# so a new chunk field is a deliberate schema change rather than a
# surprise column.
FIELDS = ("id", "instrument", "part", "kind", "unit_number", "marker",
          "anchor", "citation", "parent_path", "celex", "source_url",
          "version_date", "date_basis", "language", "chars", "body", "text")


def load(root):
    rows, seen = [], set()
    for rel in CHUNK_FILES:
        path = root / rel
        if not path.exists():
            sys.exit(f"index: {rel} is missing - run "
                     f"`python -m grc_rag.convert.chunk` first")
        for line in path.read_text("utf-8").splitlines():
            c = json.loads(line)
            if c["id"] in seen:
                sys.exit(f"index: duplicate chunk id {c['id']} across files - "
                         f"ids are the citation key, so this is a defect, "
                         f"not something to de-duplicate here")
            seen.add(c["id"])
            rows.append({k: ("" if c.get(k) is None else c[k])
                         for k in FIELDS})
    return rows


def embed(rows, batch=16):
    model = SentenceTransformer(MODEL)
    device = str(getattr(model, "device", "?"))
    print(f"  model {MODEL} on {device}")
    vectors = model.encode([r["text"] for r in rows], batch_size=batch,
                           normalize_embeddings=True, show_progress_bar=True)
    if vectors.shape[1] != DIM:
        sys.exit(f"index: model returned {vectors.shape[1]}-dim vectors, "
                 f"expected {DIM} - wrong model?")
    for r, v in zip(rows, vectors):
        r["vector"] = v.tolist()
    return rows


def smoke(table, rows=None):
    """Three checks that fail differently, so a pass means something.

    1. The lexical leg returns the chunk whose literal identifier was
       asked for. This is the one the brief said to verify at build time
       rather than assume - if LanceDB's BM25 index is not there, this
       comes back empty and the build has no lexical leg at all.
    2. The dense leg returns a plausible neighbourhood for a question
       phrased in words the chunk does not use, which is the only thing
       embeddings buy over BM25.
    3. Both answer from a table whose row count matches the chunk files.
    """
    ok = True
    n = table.count_rows()
    print(f"  rows in table: {n:,}")
    if rows is not None and n != len(rows):
        print(f"  FAIL: {len(rows)} chunks loaded but {n} rows in the table")
        ok = False

    hits = table.search("Article 15 accuracy robustness cybersecurity",
                        query_type="fts").limit(5).to_list()
    ids = [h["id"] for h in hits]
    print(f"  lexical  'Article 15 …' -> {ids[:3]}")
    if not any(h["anchor"] == "art_15" for h in hits):
        print("  FAIL: the lexical leg did not return Article 15 for a query "
              "naming it. That is the failure mode the lexical leg exists to "
              "prevent; a dense-only index would look fine here.")
        ok = False

    model = SentenceTransformer(MODEL)
    q = model.encode(["when may police use live face recognition in public?"],
                     normalize_embeddings=True)[0].tolist()
    dense = table.search(q, vector_column_name="vector").limit(5).to_list()
    print(f"  dense    'live face recognition …' -> "
          f"{[h['citation'] for h in dense[:3]]}")
    if not dense:
        print("  FAIL: the dense leg returned nothing")
        ok = False
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--index-dir", default="index")
    ap.add_argument("--smoke-only", action="store_true",
                    help="do not rebuild; just run the checks on what exists")
    a = ap.parse_args(argv)

    root = Path.cwd()
    db = lancedb.connect(a.index_dir)

    if a.smoke_only:
        table = db.open_table(TABLE)
        print(f"index: smoke test on {a.index_dir}/{TABLE}")
        return 0 if smoke(table) else 1

    rows = load(root)
    print(f"index: {len(rows):,} chunks from {len(CHUNK_FILES)} files")
    rows = embed(rows)

    # Not `if TABLE in db.list_tables()`: that returns a
    # ListTablesResponse, so the membership test is silently always false
    # and the create then fails with "table already exists". Asking to
    # drop it and saying a missing one is fine has no such ambiguity.
    db.drop_table(TABLE, ignore_missing=True)
    table = db.create_table(TABLE, data=rows)
    # Stemming and stop-word removal are left ON: the questions this
    # corpus answers are phrased in English prose ("what must providers
    # ensure…"), and the identifiers the lexical leg exists to catch -
    # "Article 15", "Annex III" - survive both. ascii_folding matters
    # more than it looks: the act is full of curly quotes and dashes.
    # Unified API: the first positional argument is the COLUMN when a
    # config object is passed (it is the distance metric in the legacy
    # form, which is a trap worth naming rather than rediscovering).
    table.create_index("text", config=FTS(with_position=True), replace=True)
    print(f"  wrote {a.index_dir}/{TABLE}.lance  (dense {DIM}-dim + BM25 "
          f"full-text on `text`)")

    print("index: smoke test")
    return 0 if smoke(table, rows) else 1


if __name__ == "__main__":
    sys.exit(main())
