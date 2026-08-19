# diagnostics — measurement instruments that are NOT the graded eval

> ⚠ **Nothing here grades the system.** `eval/corpus.eval.jsonl` is the
> answer key, it is the only answer key, and it is frozen at ⛔ Gate B
> before anything is tuned against it. The question sets in `sets/` were
> written to *diagnose* specific weaknesses, in some cases after seeing
> the system fail. **Folding any row from here into the eval requires
> Gate B sign-off** — that is the drift `eval/README.md` warns about, and
> the ordering failure D10 recorded against itself.

These exist because the M11 audit kickoff made the complaint that
created this directory: the M10 gate experiment "was run from a
scratchpad, not committed; if its result matters to the audit, it should
become a repo command rather than be re-derived from a chat transcript."
It kept happening. By M13 there were twenty-nine grc-rag files in a
scratch directory shared with unrelated projects and excluded from
search — including the reproduction D14's whole argument rests on.

    sets/       question sets with ground truth — the reusable instruments
    runners/    the scripts that measure, run from the REPO ROOT
    runs/       dated outputs, including runs whose milestone is long past

## The sets, and what each was built to measure

| set | n | built for | what it is good for |
|---|---|---|---|
| `audit-negatives.jsonl` | 26 | M11 (D14) — widening the gate measurement from 10 negatives to 36 | Out-of-corpus questions banded by nearness (`extreme-near` … `far`). **Almost all name their own regime**, because they were written to score a similarity threshold where phrasing hardly matters |
| `audit-toc-probe.jsonl` | 10 | M11 (D14) — testing whether the eval's answer key had drifted toward the system | Written from the instruments' tables of contents alone, without reading the corpus or the eval. The blind-authorship control |
| `n5-hardclass.jsonl` | 23 | M13 (D16) — the N5 cross-regime class | 15 out-of-corpus rows on the q36/q49 recipe (a real term of art, **the act never named**, on a subject the corpus covers adjacently) + 8 in-corpus rows phrased the same way to catch false refusals |

**`audit-negatives.jsonl` is not a holdout for N5, and D16 is emphatic
about why.** Because nearly every row names its act, the shipped
pipeline refuses 25 of 26 — it measures a class the system already
handles. The same-regime pair that proves it: eval q36 asks about "a
manufacturer of a product with digital elements" and is answered
wrongly; `n10` here asks the Cyber Resilience Act **by name** and is
refused. A set inherited from a different question can look like
evidence and measure nothing. `n5-hardclass.jsonl` exists because of
that discovery.

`n5-hardclass.jsonl` carries a `debatable` flag on `h13`, set **before**
any model saw the set: "safety component" occurs 32 times in the corpus
because the AI Act genuinely regulates AI safety components and has its
own CE marking, so an AI Act attribution is defensible. It is excluded
from headline figures and reported separately.

## Running them

Every runner assumes the **repo root** as the working directory — they
do `sys.path.insert(0, "src")` and read `eval/` and `diagnostics/` by
relative path.

    export UV_PROJECT_ENVIRONMENT=$HOME/.venvs/grc-rag
    uv run python diagnostics/runners/n5-analyse.py          # no API, no GPU
    uv run python diagnostics/runners/audit-gate-analysis.py # no API, no GPU
    uv run python diagnostics/runners/n5-matcher-replay.py   # no API, no GPU

Those three recompute their conclusions from committed JSON and are the
cheap way to check this directory still reproduces. The replay one is
also the bridge to production: it feeds every committed pre-flight
reply through `engine.declared_regimes` and fails if any verdict
differs from the runner matcher's, other than the intended
qualified-name flips (D17). The rest load models or call DeepSeek:

| runner | cost | writes |
|---|---|---|
| `audit-gate-scores.py` | GPU, no API | `runs/audit-gate-scores.json` |
| `audit-control-eval.py` | 61 API calls | `runs/audit-control-eval.json` |
| `audit-n4-measure.py` | GPU, no API | `runs/audit-n4-measure.json` |
| `n5-baseline.py` | 26 API calls | `runs/n5-baseline.json` |
| `n5-preflight.py` | 87 API calls (small) | `runs/n5-preflight.json` |
| `n5-hardclass-run.py` | 46 API calls | `runs/n5-hardclass.json` |
| `n5-preflight-defining.py` | 110 API calls (small) | `runs/n5-preflight-defining.json` |

**Redirect with `python -u`** or the log stays empty until the process
exits.

## Why the outputs are committed rather than treated as rebuildable

They look like Class C — derived, therefore regenerable, therefore
gitignored (D0). They are not, and the test D0 itself applies is the
reason: the raw EUR-Lex HTML is committed because a consolidation
fetched today is not re-downloadable once the Commission consolidates
again, so it **fails the cheap-rebuild test**.

These fail it the same way. Re-running costs DeepSeek tokens, and
`eval/README.md` records that DeepSeek at temperature 0 is **not
run-to-run deterministic** — D14 measured 4 of 51 verification flags
flipping across identical runs. So a discarded result is not
recoverable, only replaceable by a different one. That is the same
reasoning that commits `eval/corpus.eval.report.md` with the date it was
true.

## What is in `runs/`, including the archaeology

Current, from M11–M13: the `audit-*` and `n5-*` files, each the output
of the runner it is named after.

Older, recovered from the scratch directory during the M13 migration —
these are the evidence behind decisions that are already committed, and
they had no home until now:

| file | belongs to | why it matters |
|---|---|---|
| `m10-gate.json` | M10 | 51 rows of dense + rerank scores. **The reproduction D14's argument rests on** — the measurement that closed the cross-encoder-gate hypothesis |
| `m9-floor.txt` | M9 (D13) | The floor run behind D13's "the gate has caught exactly four questions in every measurement" |
| `m7-eval.log`, `m9-eval.log` | M7, M9 | Per-question eval runs. `eval/corpus.eval.report.md` only ever holds the latest, so these are the only record of the earlier two |
| `d5-fetch-pair.manifest.json` | M1/M2 (D5) | Was `m1.json`, a name that told you nothing. It is the **second fetch** of `02024R1689-20260727`, four seconds before the committed one: different `sha256`, identical `sha256_normalized`. That pair IS D5's verification that the normalization rule works, and half of it was sitting in a scratch directory |

## Two things this directory does not get

- **The import buckets do not cover it.** `tests/check-imports.py` walks
  `src/grc_rag/` only, so nothing classifies these scripts or checks
  what they import. That is the same accepted cost `tests/` carries and
  is stated here rather than discovered — pipeline code belongs under
  `src/grc_rag/`, and nothing here is pipeline code.
- **No standing check runs them.** They are measurements, not controls:
  they produce numbers a human reads, and they cost money. The seven
  checks in the README are the things that must pass at session close.
  Nothing here is one of them.
