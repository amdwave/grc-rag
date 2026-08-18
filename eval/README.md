# Eval set — EU AI Act (Phase 1, M4)

`ai-act.eval.jsonl` is the answer key the query path is graded against — and,
after ⛔ Gate B sign-off, tuned against. It is data, Class A, git-tracked
(decisions.md D0). Twenty questions, one JSON object per line.

**Status: DRAFT — awaiting Gate B sign-off. Nothing has been tuned against it.**

## Why these questions

Five kinds, per the M4 brief, plus one that the corpus itself forced:

| kind | n | what it tests |
|---|---|---|
| `direct` | 6 | one clearly correct unit; spread across scope, penalties, transparency, annexes, registration, GPAI |
| `neighbour_adversary` | 4 | questions whose surface vocabulary points at the wrong neighbouring article — what the lexical leg and reranker exist for |
| `recital` | 3 | answered by the recitals file, which carries the 2024 as-published provenance while enacting neighbours carry the 2026 consolidation — the provenance-honest-citation test (D4) |
| `relocated` | 1 | Regulation (EU) 2026/1744 moved a provision (old 10(5) → new 4a); parametric memory answers with the old number, the corpus with the new — corpus must win |
| `repealed` | 2 | provisions the 2026 consolidation no longer contains (Article 10(5) by number, Annex I point 1); the honest output is a refusal or redirect **from the generator**, because retrieval legitimately succeeds |
| `unanswerable` | 4 | out-of-corpus (NIS2, DORA, GDPR, ISO 42001), all near-domain on purpose; the gate must refuse them on the dense score |

## Fields

- `question` — as a GRC practitioner would ask it; only q02/q15/q16 name a
  provision literally (that is the lexical-leg test, not an accident).
- `expected_behavior` — `answer` or `refuse`.
- `expected_chunk_ids` — any-of set for retrieval hit@k. Empty for refusals.
- `expected_citation` — string the rendered citation must contain, at the
  precision the chunk's own `citation` field supports (anchor honesty: never
  grade for more precision than the chunk carries).
- `expected_date_basis` — `consolidation` (current **as of** 2026-07-27) or
  `publication` (the act **as published**, 2024-07-12). A rendered citation
  that shows a date must say which (D4). Recital questions are the live test.
- `gate_expectation` / `refusal_source` — the load-bearing distinction:
  - `unanswerable` → gate refuses (dense score below floor, no model call);
  - `repealed` → gate PASSES (Article 10 / Annex I chunks retrieve well) and
    the refusal must come from generation honesty. Tuning the floor high
    enough to "catch" q15/q16 would be tuning the wrong knob — these two are
    excluded from the floor's out-of-corpus distribution by design.
- `distractors` — the neighbouring unit(s) the question is built to pull;
  for error analysis, not scoring.
- `redirect_ok` — for `repealed` only: a redirect the corpus supports counts
  as a correct refusal, e.g. "no 10(5) in the current text; the subject
  matter is now Article 4a".

## Scoring (per M4 brief step 7)

1. **Retrieval hit rate @ k=5** — after rerank: any `expected_chunk_ids`
   member in the top 5. Denominator: the 14 questions with non-empty
   `expected_chunk_ids`.
2. **Citation correctness** — final answer cites `expected_citation` (and on
   dated renderings, the right `date_basis`). Same denominator.
3. **Refusal correctness** — the 6 `refuse` questions, split by
   `refusal_source`: 4 must refuse at the gate, 2 must pass the gate and
   refuse in generation.

## Floor tuning (step 5)

In-corpus distribution: the 14 `answer` questions. Out-of-corpus: the 4
`gate_expectation: refuse` questions. q19 (GDPR) is deliberately the hardest
separator — the AI Act text cites Regulation (EU) 2016/679 constantly. If the
distributions overlap there, record the overlap and the chosen trade-off in
decisions.md; do not quietly move the floor until q15/q16 start refusing at
the gate, which would mask the generation-honesty test.

## Two run properties, observed during M4

- **DeepSeek at temperature 0 is not run-to-run deterministic.** Across
  four eval runs with identical settings, individual questions flipped
  between a clean answer and a hedged refusal (q03, q10, q12–q14 each
  did at least once). The metrics in the committed report are one run's
  numbers, not a constant of the system.
- **A `verified False` row is not automatically a system failure.** The
  verifier flags every non-verbatim quote; a model that elides the
  middle of a quotation with "..." or adapts a verb to fit its sentence
  is misquoting, and the flag is the system working. Read the report's
  full-span evidence lines before treating the flag as a defect.

## The corpus defect this set caught, since fixed

Drafting q01 (10^25 FLOPs threshold) exposed a conversion defect: the
converter dropped EUR-Lex's `<span class="superscript">25</span>` as a
footnote mark, so Article 51(2) read "greater than 10." Fixed the same
day (a superscript is a footnote mark only after an opening parenthesis;
content superscripts render as `^N`), corpus and index rebuilt. q01
stays in the set as the standing regression canary: if it ever answers
without "10^25", the converter has regressed.
