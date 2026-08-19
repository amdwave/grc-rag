# M5 kickoff: the README an interviewer reads, one diagram, and the filing

Session roots at `D:\` (house convention); the repo is
`D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules load
automatically from `D:\AGENTS.md`; the repo's rules do **not** auto-load
from here — **read `D:\projects\grc-rag\AGENTS.md` first**, then
`docs/decisions.md` (D0–D7). `D:\` itself is not a git repo — every git
command takes `-C D:\projects\grc-rag`.

**Model plan (decided 2026-08-17): this milestone runs on Sonnet 5 at
high effort.** M2/M3 ran on Opus 5, M4 on Fable 5; M5 is
documentation-shaped — well-specified, no gates, no tuning — which is
exactly the cheaper-capable-tier case. Escalate mid-session only if the
writing genuinely fights back. Carry this note into any M6 kickoff.

## What is on disk (M1–M4 done, both gates signed off)

The raw material for the README, all of it already written down once —
link to it, do not restate it (one-owner rule):

- `docs/decisions.md` **D0–D7** — the register an interviewer should be
  pointed at. D4 (two documents, two provenances) and D7 (floor 0.62,
  tuned from measured distributions) are the strongest entries.
- `corpus/` — 871 chunks over two provenance-distinct documents;
  per-document verification reports beside the markdown.
- `src/grc_rag/` — fetch / convert / query buckets, enforced by
  `tests/check-imports.py`. Query path: hybrid RRF → bge-reranker-v2-m3
  → dense-score gate → DeepSeek at temp 0 → mechanical quote verifier →
  provenance-honest citations. `python -m grc_rag.query.cli` has
  ask / show / repl / floor / eval / sentinel / selftest.
- `eval/` — 20-question set (six kinds), README with schema and the two
  recorded run properties (DeepSeek temp-0 nondeterminism; a
  `verified False` row can be a true positive), and the committed
  report: **hit@5 14/14, citation 14/14, refusal 6/6**.
- The story worth telling: drafting eval q01 — before any tuning
  existed — caught the converter silently turning the 10^25 FLOP
  threshold into "10". Gate B's order of operations, vindicated on the
  first day it was tested. q01 is the standing regression canary.

**Goal — M5 only:** the public face. `README.md` for two readers (an
interviewer with five minutes; a practitioner who wants to run it), one
Mermaid pipeline diagram, and the deferred filing of the original brief.
No tuning, no features, no new dependencies.

## Steps

1. **README.md.** Structure that has to survive a skim: what this is
   and why no frameworks (the point is the internals); the pipeline
   diagram; the three mechanical guarantees (gate before any model
   call, verbatim-quote verifier against retrieved chunks, anchor- and
   provenance-honest citations) — each with one sentence on the failure
   it prevents; the eval and its numbers, dated, with the 10^25 catch
   as the worked example; the decision register as the map (link D0–D7,
   restate nothing); quickstart; limitations and the Phase 2 roadmap
   (GDPR, NIS2, DORA — same code, different identifiers).
2. **Quickstart that is actually true.** Every command in it gets run
   before it is written down: WSL, `UV_PROJECT_ENVIRONMENT`, `uv sync`,
   `.env` from `.env.example`, index build, one `ask`, `selftest`.
   A README command that was never executed is a claim, not a
   quickstart — and this repo's checks exist because claims drift.
3. **One Mermaid pipeline diagram** in the README: ingest (fetch →
   convert → chunk → index) and query (retrieve → rerank → gate →
   generate → verify → cite) with the guarantee points marked. Keep it
   one diagram; two small ones only if one becomes unreadable.
   I archive diagrams as PNG/SVG in Obsidian myself — flag when it is
   ready, do not export on my behalf.
4. **File the original brief.** `D:\.staging\grc-rag-kickoff.md` →
   `docs/original-brief.md`, sanitized: drop the "Who I am" section and
   anything personal beyond what a portfolio carries; keep the
   architecture, corpus targets, phase plan, and milestones — they are
   the historical record the decision register grew out of. Add a
   one-line header saying what it is and that decisions.md supersedes
   it where they disagree.
5. **Close-out checks.** All four standing checks green plus
   `cli selftest`; do **not** re-run `cli eval` (temp-0 nondeterminism
   churns the committed report for nothing — its numbers are quoted
   with their date). README read once end-to-end against the disk:
   every path, count and command in it verified.

## Constraints and gotchas

- **Python is WSL-only.** Export
  `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/grc-rag` in every shell. WSL
  `/tmp` does not persist between commands.
- **Public repo, manual commits.** The README is the public face —
  before the push, check nothing personal, no secrets, and that
  `.env` is untracked. `DEEPSEEK_API_KEY` is never echoed.
- **One owner per fact.** The README links to decisions.md, the eval
  README and the reports; it does not duplicate their content. Where
  the README needs a number (871 chunks, 14/14), it carries the number
  and the date it was true.
- **No new work smuggled in as documentation.** A gap the README
  exposes (missing command, awkward CLI ergonomics) is a finding to
  record for M6, not a thing to fix in this session — unless it is a
  one-line defect, in which case fix it, say so, and keep moving.
- Session close: commit + push, verify `status -sb` shows no `[ahead]`.

Start with step 1.
