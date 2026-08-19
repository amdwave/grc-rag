# Audit kickoff: is the refusal architecture load-bearing, and what do the checks not see?

Session roots at `D:\` (house convention); the repo is
`D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules load
automatically from `D:\AGENTS.md`; the repo's rules do **not** auto-load
from here — **read `D:\projects\grc-rag\AGENTS.md` first**, then
`docs/decisions.md` (D0–D13). `D:\` itself is not a git repo — every git
command takes `-C D:\projects\grc-rag`.

**Model plan: Opus 5 at high effort, escalate rather than drop.** This is
open-ended, judgment-heavy and adversarial; there is no mechanical half
to hand to a cheaper tier. Budget note per D3: the Claude subscription
ends ~2026-08-31 and is not renewed, so there are roughly two weeks of
sessions left. This audit is deliberately scheduled ahead of any fourth
instrument, because adding one compounds a property D13 records as
broken.

## This is an audit, and the thing under audit is a previous Claude's work

M6–M10 were built by prior sessions of this assistant, in one long run,
with the user signing off at each gate. **Everything those sessions
concluded is a claim to test, not a finding to inherit.** The register is
well-written and internally consistent, which is exactly the failure mode
to watch for: a document that argues fluently for its own decisions is
not evidence they were right.

The user's own summary of why this session exists: four decision entries
(D7, D10, D13, plus the M10 experiment) record the same mechanism
degrading, and no session ever asked the prior question — *should there
be a pre-generation relevance gate at all?*

**Do not open by agreeing.** The named claims below are the ones a
previous session was most confident about, which makes them the ones
worth attacking first.

## The claims to falsify, in priority order

1. **"A relevance-based gate cannot work in principle."** M10 measured
   the reranker as a gate and found it no better than the dense cosine
   (5/10 caught at zero false refusals), and *confidently wrong* on the
   worst case — q50 scored +0.9947 because NIS2 Article 24 genuinely is
   about European cybersecurity certification schemes. The conclusion
   drawn was that both scores measure topical relevance while the gate
   needs answerability. **The sample is ten negatives.** That is the
   identical weakness this project criticised in D7, which rested on
   four. Re-run it, widen it, or show the conclusion does not survive.
   The reproduction is `/mnt/d/.staging/m10-gate.json` plus the scripts
   noted in "Reproducing what M10 did" below.
2. **The control experiment nobody ran: remove the gate entirely.** Every
   entry from D7 onward assumes a pre-generation gate should exist and
   argues only about its threshold. Nobody has measured the system with
   `floor=None` against the 51-question set. If generation-side refusal
   alone scores the same, the gate is a cost optimisation with no
   correctness claim, and four decision entries have been defending a
   number that buys nothing. **This is the single highest-value
   measurement available and it is cheap.** `Engine(floor=None)` already
   works; the CLI prints "floor UNTUNED - the gate is decoration" for it,
   which is either an accurate description or an accidentally honest one.
3. **The eval set is authored by the system's own builder.**
   `eval/README.md` names this as a limitation. Four sessions in it is
   doing more work than that: 51 questions, one author, and in M7 four
   `unanswerable` rows were relabelled `refusal_source: generation`
   *after* their scores were seen (D10 records the ordering as its own
   weak point; M9's two later rows were pre-registered instead, which is
   the standard to hold everything to). Ask whether the answer key has
   drifted toward what the system does. A concrete probe: write ten
   questions **without** looking at the corpus, from the instruments'
   tables of contents alone, and see whether scores hold up.
4. **The OR-gate, measured but deliberately not shipped.** Refusing when
   *either* the dense or rerank score falls below its own floor catches
   6/10 instead of 5/10 with 0/41 false refusals, at zero extra compute
   (the rerank already runs before the gate fires). It was parked
   because it adds a second threshold tuned on the same 51 questions
   with no holdout. Decide it properly: ship, reject, or fold into
   whatever replaces the gate.
5. **D12's call that no third standing check is needed.** Coverage sees
   a character multiset, seqcheck sees their order, and a `rowspan`
   misalignment is neither — it reached the corpus and was caught only
   by a human reading the table at Gate A. D12 accepted that hole
   explicitly and sketched a cheap check without building it. One
   instrument later, M9 exposed a *fourth* class: cross-regime answers
   that are `verified True` with correct citations and still wrong.
   **Two of the four real defects found in M6–M10 passed every
   mechanical check.** The README sells "three mechanical checks
   standing between the model and a plausible fabrication"; audit
   whether that sentence is still honest.

## Goal — this session only

A written diagnosis, not a rebuild. Specifically:

- a defensible answer to whether the pre-generation gate stays, changes
  mechanism, or is demoted to a cost optimisation with its correctness
  claim moved to generation; and
- a **defect-class inventory**: enumerate what can go wrong in this
  pipeline, mark which check sees each class, and leave the gaps
  explicit rather than discovered one instrument at a time.

⛔ **Stop after the diagnosis and recommendation. Do not implement a gate
redesign in this session.** A measurement that changes the gate's
behaviour needs the eval re-run and a decision entry, and both belong to
whatever milestone acts on this.

## Steps

1. **Read before measuring.** `AGENTS.md`, then `docs/decisions.md` D7,
   D10, D11, D12, D13 in that order — they are one argument in five
   parts. Then `eval/README.md`. Note where a later entry contradicts an
   earlier one rather than superseding it cleanly; that is where the
   reasoning is weakest.
2. **Run the control experiment (claim 2).** Score the 51 questions with
   the gate disabled and compare refusal correctness against the
   committed run. This costs one eval pass; see the gotcha about
   `cli eval` below before running anything.
3. **Re-examine claim 1 with more negatives.** The eval has ten. Adding
   out-of-corpus questions for this measurement is legitimate — it is a
   diagnostic, not the graded set — provided anything added is kept
   separate from `eval/corpus.eval.jsonl` and not quietly folded in.
4. **Probe the answer key (claim 3)** by the table-of-contents method
   above, or a better one. Report what you find even if it is "the set
   is fine"; a negative result here is worth as much as a positive.
5. **Build the defect-class inventory.** Start from the four defects
   these sessions actually found — the 10^25 superscript (M4), the
   Cellar-route provenance loss (D9), the rowspan misalignment (D12),
   the cross-regime answers (D13) — and generalise. Which check caught
   each? Which caught none?
6. **Write it up** as a decision entry (D14) plus, if the inventory
   warrants it, a document of its own. If the audit concludes the prior
   sessions were right, say so plainly and record why — a confirmed
   design is a finding.

## Reproducing what M10 did

The gate experiment was run from a scratchpad, not committed; if its
result matters to the audit, it should become a repo command rather than
be re-derived from a chat transcript. Its raw output is at
`/mnt/d/.staging/m10-gate.json` (51 rows: question id, kind, whether it
is a negative, best dense cosine, best rerank score). Ground truth used
all ten `kind: unanswerable` rows as negatives and the other 41 as
positives, **deliberately ignoring `refusal_source`**, because six of
those labels exist only to accommodate the incumbent gate's failure.
Reproducing it needs `Engine.retrieve()`, which returns the kept sources
with `.rerank` already populated alongside the best dense cosine.

## Constraints and gotchas

- **Python is WSL-only.** Export `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/grc-rag`
  in every shell. Claude Code's own Bash tool is **Git Bash (MINGW), not
  WSL**: `/mnt/d` does not exist there — use `/d/projects/grc-rag` for
  file work and `wsl.exe -e bash -lc '...'` for anything Python. The two
  have separate `/tmp`. Put non-trivial scripts in a `.py` file under the
  session scratchpad and pass the path; inline quoting through two shells
  breaks on apostrophes and backticks. Bash-tool cwd drifts back to `D:\`
  between calls — use absolute paths.
- **Every check runs under `uv run`** — `bash tests/rerun-identical.sh`
  on its own cannot import `grc_rag` and exits 2.
- **`cli eval` costs DeepSeek tokens and is not run-to-run
  deterministic** at temperature 0 (`eval/README.md`). The committed
  numbers carry the date they were true. Re-run it deliberately, once,
  and if the numbers move, that variance is itself a finding about how
  much weight the committed report can bear.
- **The index must exist**: `uv run python -m grc_rag.query.index`
  rebuilds it (~1 min, gitignored Class C, 1,739 chunks over 6 files).
- **Ask before adding any dependency.** An audit should need none.
- **Public repo, manual commits.** No secrets, `.env` untracked,
  `DEEPSEEK_API_KEY` never echoed.
- **One owner per fact.** decisions.md owns decisions; the README carries
  numbers with dates; AGENTS.md owns conventions. If the audit finds two
  documents disagreeing, that is a defect to report, not to average.
- Session close: commit + push, verify `status -sb` shows no `[ahead]`.
  Push from Windows git — WSL has no SSH key.

Start with step 1, and read D7 → D13 as one argument before touching
anything.
