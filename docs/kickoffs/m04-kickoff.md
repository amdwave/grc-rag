# M4 kickoff: the eval set through Gate B, then the query path

Session roots at `D:\` (house convention); the repo is
`D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules load
automatically from `D:\AGENTS.md`; the repo's rules do **not** auto-load
from here — **read `D:\projects\grc-rag\AGENTS.md` first**, then
`docs/decisions.md` (D0–D6) before questioning any design choice. The
full architecture brief is `D:\.staging\grc-rag-kickoff.md` — read its
**Query** section and **Phase 1 steps 5–7**; those are this session's
scope. `D:\` itself is not a git repo — every git command takes
`-C D:\projects\grc-rag`.

**Model plan (decided 2026-08-17):** this milestone runs on **Fable 5**.
M2 and M3 ran on Opus 5 at high effort. Carry this note into the next
milestone's kickoff so the reminder survives.

## What is already on disk (M2 + M3 done, Gate A signed off)

- `corpus/raw/eu/ai-act/` — consolidated `02024R1689-20260727` and the
  original OJ `32024R1689`, each with a fetch manifest. Committed (D0/D5).
- `corpus/eu/ai-act.md` (119 articles, 14 annexes) and
  `corpus/eu/ai-act.recitals.md` (180 recitals) — two documents, two
  provenances, on purpose (**D4**). Reports beside them.
- `corpus/chunks/*.chunks.jsonl` — 871 chunks (633 + 238), each with
  `id` (`ai-act#art_15(4)`), `citation`, `parent_path`, `celex`,
  `source_url`, `version_date`, `date_basis`, `body` (verbatim) and
  `text` (embedded). A readable `.chunks.txt` dump sits beside each.
  `date_basis` is load-bearing for citation rendering: the enacting text
  is current **as of** its consolidation (2026-07-27), the recitals are
  the act **as published** (2024-07-12), and a citation that shows a date
  without saying which claims a currency the recitals do not have.
- `index/` — LanceDB, 871 rows: BGE-M3 dense (1024-dim) + BM25 full-text
  on `text`. Gitignored, Class C, ~1 minute to rebuild.
- Four checks, all green, all expected to stay green:
  `tests/check-imports.py`, `probe-check.sh`, `rerun-identical.sh`,
  `seqcheck-corpus.py`.

**Goal — M4 only:** draft the eval set and stop at ⛔ Gate B; then, after
sign-off, wire the query path and report the eval. Nothing is tuned
before Gate B.

## Steps

1. **Read the reference implementation, do not fork it:**
   `D:\projects\book2rag\rag_query.py` and
   `docs/yogananda-rag-blueprint.md` §5–§7. Different stack, same
   guarantees. The traps listed there (smart punctuation folded before
   quote extraction, markers stripped from both sides, segment-wise quote
   extraction) are already paid for — do not re-earn them.
2. **Draft a 20-question eval set, stored as data** (`eval/`, Class A,
   git-tracked). Each question carries the expected article or recital,
   the expected chunk id(s), and its kind. Cover at least:
   - direct questions with one clearly correct article;
   - **neighbouring-article adversaries** — questions that read like
     Article 14 but are answered by 15, which is what the lexical leg
     exists for;
   - **recital-answered questions**, because those chunks carry the 2024
     document while their neighbours carry the 2026 consolidation, and
     that is the first real test of provenance-honest citation;
   - **questions about provisions the 2026 amendment repealed** (Article
     10(5), Annex I item 1) — the corpus is the current law, so the
     honest answer is a refusal, not a stale quote;
   - **unanswerable questions**, where refusal is the correct output.
3. **⛔ Gate B: I review and approve the eval set before anything is
   tuned against it.** Otherwise the same model authors the answer key
   and grades itself. Stop here and wait.
4. **Wire the query path** (after sign-off), per the brief:
   hybrid retrieval rank-fused with RRF (dense + BM25, always both) →
   rerank top ~20 to ~5 with `bge-reranker-v2-m3` → **relevance gate
   before any model call**, reading the **dense score alone**, never the
   fused or BM25 score → generate at temperature 0, every claim cited to
   a chunk id → mechanical verify that every quoted span ≥ ~20 chars
   appears verbatim in a **retrieved** chunk → anchor-honest citation
   rendering (`Article 15(4)` only when the chunk is anchored at
   paragraph level; the chunk's own `citation` field already encodes
   this — use it, do not re-derive it).
5. **Tune the gate floor from evidence:** score the eval's in-corpus and
   out-of-corpus questions, look at where the two distributions separate,
   choose the floor, and record it in `docs/decisions.md` with the
   numbers that justified it. An untuned floor is decoration.
6. **Sentinel test:** plant a distinctive nonsense string in one chunk,
   ask a question that retrieves it, confirm it comes back in the answer.
   Context overflow truncates silently and the answers still look fine.
   Re-run it after any backend or model change.
7. **Eval report:** retrieval hit rate at k=5, citation correctness
   (right article), refusal correctness on the unanswerable questions.
   Then iterate on chunking/retrieval only if the eval says to — with
   the reason recorded, not the vibe.

## Constraints and gotchas

- **Python is WSL-only.** Export `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/grc-rag`
  in every shell, or `uv` will silently build a second 5 GB venv in the
  repo on `/mnt/d`. WSL `/tmp` does not persist between commands.
- **Import buckets are enforced.** A new module fails
  `tests/check-imports.py` until it is named in `FETCH`, `CONVERT` or
  `QUERY`. Retrieval, generation and eval code is `query`. `convert` stays
  stdlib-only, network-free and clock-free — do not put eval code there
  because it happens to be offline.
- **Dependencies need my OK.** Approved: LanceDB, BGE-M3 +
  bge-reranker-v2-m3, sentence-transformers, `openai` client,
  python-dotenv, Docling, uv. The reranker should run through
  sentence-transformers' `CrossEncoder` — no new dependency — but verify
  that at build time rather than assuming it, the way D6 verified the
  lexical leg. Anything else: ask, with a one-line reason.
- **Generation backend is DeepSeek** via the plain `openai` client
  (`base_url` + model from config, D3). `.env` holds `DEEPSEEK_API_KEY` —
  never echoed, never committed. Gemini's free tier is the named
  zero-cost alternate; verify its endpoint at build time if you reach for
  it.
- **D1 shape:** an importable core, `answer(question) -> Answer` returning
  a structured object; argparse and terminal rendering strictly outside
  it; no global state; REPL mode so BGE-M3 and the reranker load once per
  session.
- **Never glob the corpus.** Consumers name files explicitly —
  `*.md` matches `*.report.md`, and the import check fails on that
  pattern as a literal.
- **No frameworks.** No LlamaIndex, no LangChain. The point is the
  internals.
- Public repo, manual commits only: before every push, check nothing
  secret, licensed or personal is staged.
- Session close: commit + push, verify `status -sb` shows no `[ahead]`.
  **Ending at Gate B is success, not shortfall.**

Start with step 1.
