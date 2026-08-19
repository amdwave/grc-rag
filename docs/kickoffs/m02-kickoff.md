# M2 kickoff: AI Act fetch → markdown, through Gate A

Session roots at `D:\` (house convention); the repo is
`D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules load
automatically from `D:\AGENTS.md`; the repo's rules do **not** auto-load
from here — **read `D:\projects\grc-rag\AGENTS.md` first**, then
`docs/decisions.md` in the repo before questioning any design choice.
Phase 0 (D0–D3) and M1 are done: repo is public at
`github.com/amdwave/grc-rag`, scaffold committed. The full architecture
brief is `D:\.staging\grc-rag-kickoff.md` — read its Corpus and
Architecture sections (ingest steps 1–2) before starting; Phase 1 steps 1–2
are this session's entire scope. `D:\` itself is not a git repo — every git
command takes `-C D:\projects\grc-rag`.

**Goal — M2 only:** fetch the EU AI Act from EUR-Lex and convert it to
markdown, ending at ⛔ Gate A. Chunking, embedding, and query are out of
scope; do not scaffold them.

## Steps

1. **Bootstrap the package with uv** (in WSL). Before any pipeline code,
   port the import-bucket check from
   `D:\projects\book2rag\tests\check-imports.py` (read it, don't fork):
   `fetch` may use the network; `convert` is deterministic and offline
   (byte-identical reruns); `query` may use the network (not built yet). The
   check must fail on an unclassified module — verify that with a probe
   module, not by assertion.
2. **Fetch:** EU AI Act — Regulation (EU) 2024/1689, CELEX `32024R1689`.
   EUR-Lex **consolidated** HTML/XHTML representation, **English**. Verify
   the URL and CELEX identifier at fetch time — do not trust remembered
   URLs. Save the raw source plus a fetch manifest (URL, timestamp, SHA-256)
   under the corpus tree and **commit both** (D0: a consolidated version
   fetched today is not re-downloadable once the Commission consolidates
   again).
3. **Convert:** custom parser for EUR-Lex HTML → clean markdown, preserving
   chapter / article / recital / annex structure (parent paths matter for
   M3's chunking, but chunking itself is not this session). Write the
   per-document verification report beside the markdown — counts, structure
   checks, anomalies; `*.report.md` must never be matchable by corpus
   globs. Then run an **order-sensitive** comparison against an independent
   extraction using `D:\ai\extractors\seqcheck.py` — bag-of-words totals
   are blind to content shredded into the wrong order; book2rag passed
   three such checks on a corrupted book.
4. **⛔ Gate A:** show me representative samples — an article with numbered
   paragraphs, a recital, an annex section — and stop for my sign-off.
   Do not chunk.

## Constraints and gotchas

- Python is WSL-only. WSL `/tmp` does not persist between commands — use a
  repo-local or `/mnt/d` scratch path.
- Dependencies need my OK (`AGENTS.md` lists what's approved). Fetch and
  convert should lean stdlib-first; if you want `requests`/`httpx`/`lxml`/
  `beautifulsoup4`, ask with a one-line reason before adding.
- EUR-Lex can be hostile to naive scripted fetches (user-agent checks,
  redirects). If it is, surface exactly what you see — do not silently
  substitute a different source or representation.
- This repo is public and manual-commit-only: before every push, check
  nothing secret, licensed, or personal is staged.
- Session close: commit + push, verify `status -sb` shows no `[ahead]`.
  Ending at Gate A is success, not shortfall.
- Model plan (decided 2026-08-17): this session and M3 run on Opus 5 at
  high effort; **M4 switches to Fable 5**. Carry this note into the next
  milestone's kickoff prompt so the reminder survives to M4.

Start with step 1.
