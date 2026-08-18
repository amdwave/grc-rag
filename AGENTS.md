# AGENTS.md — grc-rag

Read directly by Cline. **Claude Code does not read `AGENTS.md`** — it reads
`CLAUDE.md`, and the `CLAUDE.md` beside this file is a one-line shim whose only
job is to import this one. Delete the shim as a duplicate and everything below
silently stops loading in Claude Code, with no warning.

House rules (bluntness, push-back, verification, secrets, session close) load
from `D:\AGENTS.md`; this file is only what is specific to this repo.

RAG over regulatory primary sources (EU AI Act, GDPR, NIS2, DORA, NIST, CIS,
ENISA) for GRC work and content. Portfolio project: every design decision
should be explainable in an interview. The decision register is
[docs/decisions.md](docs/decisions.md) — **read the entry before re-litigating
anything recorded there.**

## Rules

- **One instrument end to end, then generalize.** No scaffolding the whole
  system up front. Phase 1 is the AI Act only.
- **No LlamaIndex, LangChain, or similar frameworks.** Plain Python; small
  focused libraries are fine. The point is understanding the internals.
- **Ask before adding any dependency, service, or infrastructure** that was
  not already agreed. Approved so far: LanceDB, BGE-M3 + bge-reranker-v2-m3
  (HF cache on WSL ext4, never in this repo) run through
  **sentence-transformers**, openai client, python-dotenv, Docling (ENISA
  PDFs only), uv. The lexical leg is LanceDB's own BM25, not BGE-M3's
  sparse output (decisions.md D6). Fetch and convert remain stdlib-only —
  every dependency here belongs to the query bucket.
- **Everything executes in WSL2/Ubuntu** (`/mnt/d/projects/grc-rag`). Python
  on this machine is WSL-only. Package management: uv.
- **Three import buckets, enforced by a check that runs before anything
  else:** `fetch` may use the network; `convert`/`chunk` is deterministic and
  offline (no network imports, byte-identical reruns); `query` may use the
  network. A module that fits no bucket fails the check — classify it, don't
  widen the allowlist.
- **Corpus conventions:** markdown is the canonical corpus, versioned and
  diffed. Raw fetched source + manifest (URL, timestamp, checksum) are
  committed. Per-document verification reports (`*.report.md`) must never be
  matchable by corpus globs — consumers name or filter explicitly. CIS
  Controls text stays under gitignored `corpus/local/` — manifest committed,
  content never (licensing; decisions.md D2).
- **Two hard gates — stop and wait for sign-off:** Gate A, conversion samples
  before any chunking; Gate B, the eval set before anything is tuned against
  it.
- **Public repo, manual commits only** — no `git-autocommit.ps1` line, same
  reasoning as `portfolio-public`: a human looks before anything becomes
  public. Before every push: no secrets, no licensed corpus text, nothing
  personal beyond what a portfolio should carry.
- `.env` holds `DEEPSEEK_API_KEY` — gitignored, never echoed, never
  committed. `.env.example` carries names only.

## Session close

1. `git -C D:\projects\grc-rag add -A`
2. Commit, push.
3. Verify: `git -C D:\projects\grc-rag status -sb` shows no `[ahead]`.
