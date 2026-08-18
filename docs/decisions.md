# Decision register — grc-rag

Short ADR-style entries. One per decision, newest last. Pre-kickoff decisions
are recorded here for completeness and marked as such.

## D0 — Location, backup classes, model weights (pre-kickoff)

**Status:** decided pre-kickoff, recorded 2026-08-17.

- Repo at `D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules
  from `D:\AGENTS.md` apply, including session close (commit + push).
- Backup classes per storage-strategy §3.3: code, docs, markdown corpus, eval
  set = Class A, git-tracked. `index/` (LanceDB, embeddings) = Class C —
  gitignored, rebuildable from corpus.
- Raw fetched source + fetch manifest are **committed**: a consolidated
  EUR-Lex version fetched today is not re-downloadable once the Commission
  consolidates again, so it fails the cheap-rebuild test.
- Model weights (BGE-M3, reranker, any local LLM) live in the Hugging Face
  cache on WSL ext4 — never in the repo, never on `D:\`.
- Storage-strategy bookkeeping for this folder done in v6.23 (2026-08-17).

## D1 — CLI, not HTTP service (for now)

**Status:** decided 2026-08-17.

**Context.** Day-to-day use is a terminal question→answer loop. A separate
voice-in/voice-out RAG project may eventually consume this system, which
argued for an HTTP service (OpenAI-compatible or custom). A service adds a
process lifecycle, port, wire schema, and client — none of which improve
retrieval, and a wire schema designed with zero consumers is how APIs end up
wrong.

**Decision.** CLI, built as a thin shell over an importable library core.
No HTTP service until the voice project is actually ready to consume one.

Two constraints are part of the decision, because they are what keep the
service option cheap later:

1. **Importable core:** `answer(question) -> Answer` returns a structured
   object (answer text, chunks, citations, scores). argparse and terminal
   rendering stay strictly outside the core. No global state.
2. **REPL mode:** the CLI gets an interactive loop so BGE-M3 and the reranker
   load once per session, not once per question. This removes the only real
   latency argument for a persistent service.

**Trigger to revisit:** the voice project (or any second consumer) is ready to
integrate. At that point wrap the core in a thin HTTP adapter shaped by what
that consumer actually needs.

## D2 — One public repo; CIS text in no repo

**Status:** decided 2026-08-17.

**Context.** The markdown corpus is a first-class, diffable artifact. The code
repo must be public from day one (portfolio). EUR-Lex and NIST content is
redistributable; CIS Controls text likely is not. Options were one repo, or a
separate versioned content repo (`D:\projects\grc-corpus\`).

**Decision.** Single public repo. No `grc-corpus` repo.

- **Atomicity is the load-bearing reason:** the corpus is a build artifact of
  the converter, so a converter fix and the regenerated markdown diff land in
  one commit, reviewable together. Split repos make that two commits in two
  repos with nothing enforcing sync.
- Size is a non-issue (tens of MB of well-diffing text). If that ever changes,
  splitting later via `git filter-repo` preserves corpus history; merging
  repos back is the painful direction.
- **CIS Controls text stays out of every repo:** raw + markdown live under a
  gitignored `corpus/local/` path; only its fetch manifest (URL, version,
  checksum) is committed. "Local-only source" is a first-class pipeline
  concept, not a special case.
- Consumers (voice project, content work) read the corpus by path; no repo
  boundary needed.

**Cost accepted:** the CIS copy exists only on this disk, behind CIS's
registration wall — not guaranteed re-fetchable. It needs a backup home per
storage-strategy, decided when the CIS source is actually built (not before).

**Consequence:** no `grc-corpus` folder, so no additional storage-strategy
edit — the pre-kickoff v6.23 bookkeeping already covers everything.

## D3 — Local embeddings, cloud generation via DeepSeek

**Status:** decided 2026-08-17.

**Context.** Two layers with opposite reversibility. Constraints from
storage-strategy: zero-recurring-spend (register #17), DeepSeek BYO-key
pay-per-token is the established inference lane (register #19, third-party
egress accepted in #20 for client content — stricter than this 100%-public
corpus). The Claude subscription ends ~2026-08-31 and is not renewed; an
earlier draft of this decision recommended Anthropic as the cloud backend and
was corrected against these constraints.

**Decision.**

- **Embeddings: local, pinned BGE-M3** (+ bge-reranker-v2-m3), HF cache on
  WSL ext4. Vectors are only comparable within one model and cloud embedding
  models get deprecated on someone else's schedule; a pinned local file
  cannot be. Multilingual fits the EN/ES roadmap. Backend-independent
  argument — this half survives any generation-layer change.
- **Generation: cloud, DeepSeek default** — the existing key, pay-per-token
  (pennies per query at RAG scale), no new vendor, no new subscription.
  Local Qwen3 14B Q4 via llama-server is the fallback backend.
- **Interface: one plain `openai`-client adapter**, `base_url` + `model` +
  key from config. DeepSeek, llama-server, and the Gemini API all speak the
  OpenAI wire protocol, so one adapter covers every backend in play. If a
  non-OpenAI-compatible provider ever matters, that is the day a small
  internal Protocol appears — not before.
- **Named zero-cost alternate: Gemini API free tier** via its
  OpenAI-compatible endpoint (base_url + key swap). Deliberately decoupled
  from the Google AI Pro subscription, whose justification lives entirely in
  the backup layer (register #18) — the API free tier exists independently.
  Verify endpoint/terms at build time; do not trust this entry's vendor
  trivia.
- Temperature 0 at generation stands — DeepSeek and llama-server accept it.
  The real groundedness guarantee is the verify step + citation contract,
  not sampling determinism.
- **Keys:** `DEEPSEEK_API_KEY` in gitignored `.env`; `.env.example`
  committed with names only; never echoed, never committed. python-dotenv
  approved as a dependency for loading it.

**Trigger to revisit:** DeepSeek pricing/terms change materially (same
trigger as register #19), or eval quality shows generation is the
bottleneck — then swap backends through the adapter and re-run the eval.

## D4 — The corpus is two documents, because the recitals are

**Status:** decided 2026-08-17, during M2.

**Context.** The plan said "fetch the AI Act, consolidated, English". At
fetch time the consolidated representation
(`02024R1689-20260727`, current after Regulation (EU) 2026/1744) turned
out to contain **no recitals at all** — EUR-Lex consolidations carry the
enacting terms and the annexes only. Measured, not assumed: zero `rct_`
ids and zero occurrences of "whereas" in the consolidated HTML, against
180 recitals in the original OJ publication. The recitals matter for this
system: they are what an AI Act question about intent or scope is
usually answered from.

Three options: drop the recitals; take everything from the original OJ
text and lose the amendments; or carry both.

**Decision.** Both, as two files with two provenances.

    corpus/eu/ai-act.md            enacting terms + annexes  02024R1689-20260727
    corpus/eu/ai-act.recitals.md   recitals                  32024R1689

- **One file per source document, never a merged file.** The two have
  different CELEX ids, different dates and different legal status; a
  single file would have to carry per-section provenance, and the first
  time it was wrong a chunk would cite the current law for text that was
  superseded. Front matter carries `celex`, `source_url`, `source_sha256`
  and `version_date` per file, so every M3 chunk inherits a provenance
  that is true for all of it.
- **Paths are stable across consolidations.** The version lives in the
  front matter, not the filename, so the next consolidation rewrites
  `ai-act.md` in place and `git diff` shows exactly what the Commission
  changed. That is the whole reason the markdown is versioned.
- Recitals are not amended by amending acts — they belong to the act as
  adopted — so the recitals file does not go stale when the enacting
  terms are re-consolidated. The amending act's own recitals are a
  separate document, and out of scope until there is a reason.

**Cost accepted:** an M3 chunk from the recitals file is dated 2024-07-12
while its neighbours in the enacting file are dated 2026-07-27. Citation
rendering has to say which — that is a feature, not a wart.

## D5 — The raw file is committed as served; the manifest carries two hashes

**Status:** decided 2026-08-17, during M2.

**Context.** Two fetches of the same unchanged act produce different
bytes. Measured: EUR-Lex stamps a per-response Dynatrace RUM id into one
`<script data-dtconfig="…">` attribute in the head, and nothing else in
the document differs. A hash that changes on every fetch cannot answer
the only question a fetch manifest exists to answer — has the source
changed?

**Decision.** The raw file is committed **exactly as served** — a
normalised "raw" file is not raw, and provenance is the reason it is in
git at all (D0). The manifest carries `sha256` of the bytes as served
**and** `sha256_normalized` of those bytes with the telemetry attribute
removed, plus a `normalization` field stating the rule in words.

Comparing consolidations means comparing `sha256_normalized`. The
verification that this is the right pair of numbers is in the fetch
itself: two consecutive fetches differ in `sha256` and agree in
`sha256_normalized`.

## D6 — Embedding runtime, and the lexical leg verified rather than assumed

**Status:** decided 2026-08-17, during M3.

**Context.** D3 settled *which* embedding model (pinned local BGE-M3) but
not what runs it, and the architecture brief left one thing explicitly
open: whether LanceDB can index BGE-M3's sparse output, with instructions
to **verify at build time** and fall back to LanceDB's own BM25 rather
than hand-roll a sparse index either way.

**Decision.**

- **sentence-transformers** as the BGE-M3 runtime. FlagEmbedding would
  add dense + sparse + ColBERT in one call, but the sparse half has
  nowhere to live (below), so it would buy a heavier dependency tree for
  an output nothing consumes. Writing pooling and normalisation by hand
  against `transformers` is exactly the kind of detail that silently
  produces slightly-wrong vectors.
- **The lexical leg is LanceDB's native BM25 full-text index**, built
  over the chunk's `text` column at index time. Verified, not assumed:
  `python -m grc_rag.query.index --smoke-only` runs an identifier query
  through the FTS leg and fails if Article 15 does not come back. It
  does: `Article 15 accuracy robustness cybersecurity` returns
  `art_15(1)`, `art_15(3)`, `art_15(2)`. A dense-only index would look
  perfectly healthy at that moment, which is why the check is in the
  build and not in a README.
- **Measured at build:** 871 chunks, 1024-dim vectors on `cuda:0`
  (RTX 3500 Ada, torch 2.13+cu130), `index/` 4.5 MB — Class C, gitignored,
  rebuilt in about a minute once the weights are cached.
- **The virtualenv lives on WSL ext4** (`~/.venvs/grc-rag`, 5.1 GB) via
  `UV_PROJECT_ENVIRONMENT`, not in the repo on `/mnt/d`. Same reasoning
  D0 applied to the model weights: thousands of small files behind the
  NTFS boundary are slow to import and belong to no backup class. The
  repo stays on D:; only the environment moves.

**Not decided here:** rank fusion weights, the reranker's cut-off, and
the relevance-gate floor. All three are tuned against the eval set in M4,
after Gate B — tuning them now would be tuning against nothing.

## D7 — Relevance-gate floor: 0.62 on the dense cosine alone

**Status:** decided 2026-08-17, during M4, after Gate B sign-off.

**Context.** The gate refuses before any model call when retrieval says
the corpus is not about the question. It reads the best dense cosine
alone — never the fused rank and never BM25, which scores high on any
question sharing common words (brief; book2rag's earned rule). The floor
is only meaningful against the model that produced the vectors (BGE-M3,
D6), tuned from the approved eval set's distributions, measured by
`python -m grc_rag.query.cli floor`.

**Measured** (20 questions, best dense cosine per question):

| cluster | n | range |
|---|---|---|
| out-of-corpus (`gate_expectation: refuse`) | 4 | 0.4918 – 0.6151 |
| in-corpus (`gate_expectation: pass`) | 16 | 0.6264 – 0.8020 |

Clean gap 0.6151 → 0.6264; **floor 0.62**, the midpoint.

- The hardest out-of-corpus case was ISO/IEC 42001 (0.6151), not the
  GDPR question the eval README predicted (0.5669) — management-system
  vocabulary sits closer to Article 17's than GDPR's does to anything.
- q15/q16 (repealed provisions) score 0.6379 and 0.6967 — above the
  floor **by design**: their refusal belongs to the generator, and a
  floor high enough to catch them would be mistuned (eval README).

**Cost accepted.** The gap is real but narrow (0.011) and rests on four
out-of-corpus samples. The floor is permissive at the margin: a
near-domain out-of-corpus question can score above 0.62 and reach the
generator, whose grounding prompt is the second line of defence.

**Trigger to revisit:** any change to the corpus, chunking, or embedding
model shifts both distributions — re-run `cli.py floor` and re-record.
Adding Phase 2 instruments (GDPR, NIS2, DORA) converts today's
out-of-corpus questions into in-corpus ones; the eval set needs new
out-of-corpus rows at that point, not just a re-run.
