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
