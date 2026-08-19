# M14 kickoff: ship the regime pre-flight, or report why it should not be

Session roots at `D:\` (house convention); the repo is
`D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules load
automatically from `D:\AGENTS.md`; the repo's rules do **not** auto-load
from here — **read `D:\projects\grc-rag\AGENTS.md` first**. `D:\` is not
a git repo — every git command takes `-C D:\projects\grc-rag`.

**Model plan: Fable 5 at high effort.** Most of this milestone is
well-specified — one measurement whose decision rule is already written
down, then an implementation D16 has already designed. What earns the
top tier is §3: changing an answer key after a mechanism changes is the
exact move D10 recorded as its own weakness, and getting it wrong
quietly is worse than getting it wrong loudly. Budget: the Claude
subscription ends ~2026-08-31 and is not renewed, so roughly ten
sessions remain.

## What you are inheriting

M13 designed a **regime pre-flight** for defect class N5 — a question
about a regime the corpus does not hold, answered fluently out of an
adjacent one — and deliberately stopped before implementing it. Read
`docs/decisions.md` **D13 → D16** in order, then
`docs/defect-classes.md`, then `docs/n5-preregistration.md`, then
`eval/README.md`.

The one-paragraph version, which you should verify rather than trust:
the generator already refuses a question that NAMES an absent act
(25/26). It fails when regime identity is carried in a term of art —
"product with digital elements", "critical entity". The pre-flight is a
documents-free model call naming which instruments the question
concerns, matched against the closed set the corpus holds. Measured, it
halves the hard-class failure rate (5/15 → 2/15) with **0 false refusals
in 59 in-corpus questions**. It does not solve N5. Say "halves", never
"fixes".

Artifacts are **committed in the repo** under `diagnostics/` — migrated
there at the end of M13, so anything you remember reading about
`/mnt/d/.staging/n5-*` is a stale path. Read
[diagnostics/README.md](../../diagnostics/README.md)
before using them; it states what each set was built for and, more
importantly, what each is NOT evidence of.

    diagnostics/sets/n5-hardclass.jsonl       the 23-question hard-class set
    diagnostics/sets/audit-negatives.jsonl    the 26 M11 negatives
    diagnostics/sets/audit-toc-probe.jsonl    the 10 blind-authorship probes
    diagnostics/runners/n5-preflight.py       the pre-flight prompt + alias matcher
    diagnostics/runners/n5-hardclass-run.py   shipped-vs-preflight on the 23
    diagnostics/runners/n5-baseline.py        the 26 through the shipped pipeline
    diagnostics/runners/n5-analyse.py         both GENERAL policies
    diagnostics/runs/                         every dated output, incl. m10-gate.json

**Runners execute from the repo root**, not from their own directory.
The two that need no API key or GPU are the cheap way to confirm the
directory still reproduces before you change anything:

    uv run python diagnostics/runners/n5-analyse.py
    uv run python diagnostics/runners/audit-gate-analysis.py

## 1. The experiment that must come first

D16 names it: **ask the pre-flight for the instrument that DEFINES the
terms the question uses, not every instrument that is relevant.** Three
of the five hard-class misses (h04, h06, h08) name the correct
out-of-corpus regime *alongside* an in-corpus one, and the any-overlap
rule passes them.

It is not free, and the counter-example is already known: q44's reply
began "ENISA" — not an instrument at all — so a naive first-named rule
falsely refuses a good question. Measure, do not assume.

Run the variant against **the same 23 hard-class rows plus the 51 eval
rows**, exactly as `diagnostics/runners/n5-hardclass-run.py` and
`n5-preflight.py` do now. Add the variant as a **new** runner beside
them rather than editing either in place — the committed outputs in
`diagnostics/runs/` are the D16 baseline you are comparing against, and
overwriting them destroys the comparison.

**The decision rule, pre-registered here so it is not chosen after the
numbers:**

- Adopt the defining-instrument variant **only if** it catches **≥ 12 of
  15** hard-class negatives **and** produces **≤ 1 false refusal across
  all 59 in-corpus rows** (51 eval + 8 hard-class in-corpus).
- If it catches more but costs 2 or more false refusals, **keep the D16
  variant.** D10's asymmetry is unchanged: only a false refusal is
  silent.
- If neither variant clears 12/15, ship the D16 variant as measured and
  record that the ceiling is lower than hoped. Do **not** try a third
  prompt, then a fourth. Two variants is measurement; five is tuning,
  and D14 closed that road for the gate already.

## 2. Implementation, if §1 clears it

Positioned **after retrieval and the gate**, never before — the gate
refuses 12 of 26 negatives at zero API cost, and N5 lives specifically
in questions that survive it (q36, q49 and q50 all passed the gate
comfortably).

**Build the matcher's tests before the matcher.** D16's P8 held twice:
both defects M13 found were in string matching, and each flipped a
verdict. `"GENERAL" in reply` also matches "General-Purpose AI Code of
Practice"; the alias `gdpr` matches "UK GDPR", a different instrument.
A production version will fail at membership testing before it fails at
regime identification. So, in `cli.py selftest`, before anything else:

- the GENERAL sentinel is the WHOLE reply, not a substring;
- a jurisdiction-qualified name ("UK GDPR", "Swiss FADP") is NOT the
  instrument it qualifies;
- the alias table derives from the corpus's own `instrument` field
  rather than being hand-listed, with any additions documented;
- multi-label: any overlap with the closed set passes.

Then the plumbing: a new `Answer.mode` of `refused-preflight`, rendered
in `cli.py`, counted in `cmd_eval`, and added to the README's mermaid
pipeline diagram as a fourth guard. `docs/defect-classes.md`'s N5 row
moves from "design decided" to whatever is then true.

## 3. The trap — the eval's refusal_source

⚠ **This is the part to slow down on.** The eval grades refusal
correctness *by mechanism*: `refusal_source` is `gate` or `generation`,
and `cmd_eval` maps it to an expected mode. A third mechanism changes
what some rows should expect — and q36 and q49 are exactly the rows the
pre-flight is designed to catch, which means **relabelling them is
changing the answer key in the direction of the result.** That is D10's
recorded weakness, and D13 set the standard that beat it: write the
reason into each row's `notes` **before** the run, then let the
measurement confirm or refute a prediction rather than supply one.

So: decide each row's expected mechanism from the mechanism's
definition, write it down with its reasoning, and only then run. Rows to
think about, at least: q36, q49 (currently `generation`, currently
failing); q20, q37, q38, q50 (currently `generation`, currently
passing — does the pre-flight now catch them, and *should* it?); and
q15/q16, which are `repealed`, not out-of-corpus, and **must** still
reach generation. A pre-flight that refuses q15/q16 has broken the
generation-honesty test; D16's P4 disqualified a better-scoring policy
on exactly that ground.

Whether the hard-class rows should be promoted into
`eval/corpus.eval.jsonl` is a **Gate B question, not yours to decide
alone** — ask. They were authored by the system's builder against a
known weakness, which is precisely the drift `eval/README.md` warns
about.

## 4. Re-run the eval, once, deliberately

Only after §3. `cli eval` costs DeepSeek tokens and is not run-to-run
deterministic at temperature 0 — D14 measured 4 of 51 verification flags
flipping across identical runs. Run it **once**, record the date, and
update the README's numbers and `eval/corpus.eval.report.md` together.
If a number moves in a direction the change does not explain, that is a
finding, not something to average away.

Then D17: the decision, its evidence, its cost, and its trigger to
revisit. If §1 says the pre-flight should not ship, D17 says so and the
milestone is still a success — a measured negative is what D14 was for.

## Constraints and gotchas

- **Python is WSL-only.** Export `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/grc-rag`
  in every shell. Claude Code's Bash tool is **Git Bash (MINGW), not
  WSL**: `/mnt/d` does not exist there — use `/d/projects/grc-rag` for
  file work and `wsl.exe -e bash -lc '...'` for anything Python. Put
  non-trivial scripts in a `.py` file and pass the path; inline quoting
  through two shells breaks on apostrophes, and a long heredoc of
  markdown will break too — write those with the file-writing tool.
  Bash-tool cwd drifts back to `D:\` — use absolute paths.
- **`load_dotenv()` needs the explicit path** when the script lives
  outside the repo: `load_dotenv("/mnt/d/projects/grc-rag/.env")`.
  M13 lost a full run to a 401 for want of this.
- **Redirect with `python -u`**, or the log stays empty until the
  process exits and you cannot watch progress.
- **Seven standing checks now**, all must pass at close:

      uv run python tests/check-imports.py
      uv run bash tests/probe-check.sh
      uv run bash tests/rerun-identical.sh
      uv run python tests/seqcheck-corpus.py both
      uv run python tests/index-current.py
      uv run bash tests/index-probe.sh
      uv run python -m grc_rag.query.cli selftest

- **A chunk change now requires an index rebuild** before
  `index-current.py` passes (D15). Rebuild:
  `uv run python -m grc_rag.query.index` (~1 min).
- **Ask before adding any dependency.** This needs none.
- **Public repo, manual commits.** No secrets, `.env` untracked,
  `DEEPSEEK_API_KEY` never echoed.
- **One owner per fact.** decisions.md owns decisions; the README carries
  numbers with the date they were true; `defect-classes.md` owns the
  class→check mapping; `n5-preregistration.md` owns M13's predictions
  **as written** and is never edited to match outcomes.
- Session close: commit + push, verify `status -sb` shows no `[ahead]`.
  **Push from Windows git — WSL has no SSH key.** Long commit messages
  go through `git commit -F <file>`; PowerShell here-strings mangle
  embedded quotes.

## What not to do

- Do not tune the pre-flight prompt past two variants (§1).
- Do not fold the hard-class questions into the graded eval without
  asking (§3).
- Do not re-run `cli eval` a second time to get a nicer number (§4).
- Do not claim the pre-flight fixes N5. It halves one class's rate on an
  adversarially-built 15-question sample, and h04 and h15 still get
  through.

Start by reading D13 → D16 as one argument, then §1.
