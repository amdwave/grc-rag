# Defect classes — what can go wrong, and which check sees it

Written during the M11 audit (2026-08-19, D14); X1 and N4 closed in M12
the same day (D15). The four defects this
project has actually found — the 10^25 superscript (M4), the
Cellar-route provenance loss (D9), the rowspan misalignment (D12), the
cross-regime answers (D13) — each exposed a *class*, and two of the four
passed every mechanical check. This document enumerates the classes so
the next gap is a known hole rather than a surprise.

One owner per fact: decisions.md owns the decisions cited; the eval
README owns the run properties; this file owns only the class → check
mapping. **Coverage** column: `check` = a standing mechanical check
fails on it; `eval` = the graded eval catches it as a regression;
`human` = only a person reading something sees it; `none` = nothing
sees it today.

| # | class | real instance | what sees it | coverage |
|---|---|---|---|---|
| F1 | source drift (Commission re-consolidates) | — | manifest `sha256_normalized` on re-fetch (D5) | check |
| F2 | wrong document identity (bad CELEX/consolidation id) | — | discovery's two independent opinions; fetch refuses a contradicted id (D8) | check |
| C1 | text dropped by the wrong *named* rule | **10^25 → "10" (M4)** | coverage table balances anyway — the drop is named, just wrong. Caught by a human drafting q01; q01 canaries this instance only | human |
| C2 | text shredded, duplicated or reordered | — | `seqcheck-corpus.py`, in-order verbatim | check |
| C3 | structure misassigned (cell in wrong column) | **rowspan (D12)** | nothing automated; Gate A eye. D12 sketched a grid-arithmetic check, unbuilt | human |
| C4 | front matter asserts a falsehood (metadata not derived from the document) | **`amending_acts` empty match (D9)** | nothing; found by code reading. The second-opinion pattern exists for the fetch id, not for the amendment list | none |
| K1 | chunk text loss/duplication/reorder | — | chunk report: every body verbatim, in order, no paragraph unclaimed | check |
| K2 | wrong chunk boundaries (unit can't answer alone) | q22/q39 recital-wins symptom (D13) | human reads the dump; eval hit@5 indirectly | human/eval |
| X1 | index stale against committed chunks | — | `tests/index-current.py` — the build stamps chunk-file SHA-256s + embedder into `index/source-manifest.json`; the check re-hashes and compares, `index-probe.sh` demonstrates it failing (D15) | check |
| X2 | lexical leg silently absent | — | `index --smoke-only` identifier query (D6) | check (at build) |
| R1 | retrieval miss (right chunk not in top-k) | q22, q39 | eval hit@5 | eval |
| G1 | gate false refusal — silent to the user | — | `cli floor` distributions; eval | eval |
| G2 | gate false pass | 6 of 10 eval negatives | eval refusal correctness; the grounding prompt refuses most near-band negatives but not deterministically, and D14's control run shows it is not a superset of the gate (q34/q35 slipped when the gate was off) | eval |
| N1 | fabricated quote (≥ 20 chars, quoted) | — | verifier, verbatim against retrieved bodies | check |
| N2 | fabricated *unquoted* claim (paraphrase) | — | grounding prompt + cited-id check only; README names the hole | none (named) |
| N3 | fabricated citation id | — | cited-id check; unknown id fails the answer | check |
| N4 | quote attributed to the wrong retrieved chunk | — | `check_attribution()` requires the cited chunk to contain the span; fails the answer. Measured 0/290 attributed spans on 61 real answers — a guard against an unexercised class, not a description of the model (D15) | check |
| N5 | cross-regime answer — right text, wrong law | **q36/q49 (M9, D13); q35 joins when the gate is off (D14)** | nothing mechanical; eval canaries the known rows. Verifier, citation contract and gate all pass it; the gate currently masks q35's exposure rather than seeing it | none (eval canaries) |
| N6 | context silently truncated | — | `cli sentinel`, on demand | check (on demand) |
| N7 | run-to-run flip (answer ↔ refusal at temp 0) | q03, q10, q12–q14, M4 | known property, measured, not checkable per run (eval README) | named |
| T1 | citation more precise than the chunk (refined id) | routine | warned, counted as base chunk — a policy, not a defect (D11) | check |
| T2 | renderer stops naming instrument or date basis | pre-M7 renderer | `expected_citation` clause in eval scoring (D11) | eval |
| E1 | answer key drifts toward the system (post-hoc relabels) | **M7's four rows (D10)** | Gate B ordering discipline; M9 met the pre-registration standard, M7 did not and stays marked. M11's TOC probe is the countermeasure: questions authored from tables of contents alone, scored blind | human/process |
| E2 | eval author is the system's builder | — | M11 probe: 10 questions from tables of contents alone, 10/10 retrieval hit@5, 10/10 answers citing the expected article, 3 verifier flags all known-benign — the set is not measurably self-serving; the residual (one mind, 51 questions) stands | measured once |

## The reading that matters

Classes with **no** mechanical coverage: C1, C3, C4, N2, N5.

X1 and N4 were on that list when the M11 audit wrote it, as the two
classes nobody had noticed, let alone accepted. **Both were closed in
M12 (D15)** and now carry checks that have been watched failing. The
five that remain are all previously known and accepted in writing: C1
canaried by q01, C3 via D12, C4 by code reading, N2 in the README, N5
in D13.

Two are conversion-side and cheap enough to build when they next
matter:

- **C3**: D12's sketch stands — re-parse each rendered table, assert
  cell count against the source grid's expanded width × height. Its
  trigger is a fourth instrument with heavy tables.
- **C4**: derive-and-compare like D8's discovery — the amendment list
  read from the modifiers table must agree with the consolidation id's
  own claim about what was folded in.

C1, N2 and N5 have no cheap mechanical closure. C1's honest mitigation
is what already happens: named drop rules, reports read by eye, and an
eval canary per caught instance. N2 is inherent — an unquoted claim is
not mechanically checkable, which is why the prompt demands quotes and
the CLI flags an answer that carries none. N5 is the multi-instrument
failure mode; anything that closes it changes the answer path, which is
a redesign decision (D14), not a check, and D14's position is that it
is the next design question this project should take on.
