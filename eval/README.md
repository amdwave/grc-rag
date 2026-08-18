# Eval set — EU AI Act + GDPR

`corpus.eval.jsonl` is the answer key the query path is graded against — and,
after ⛔ Gate B sign-off, tuned against. It is data, Class A, git-tracked
(decisions.md D0). Thirty-eight questions, one JSON object per line.

One file for the whole corpus, not one per instrument: the questions that
matter most here are the ones that could be answered from the wrong act, and
those belong to no single instrument (decisions.md D9).

**Status: twenty questions approved at ⛔ Gate B on 2026-08-17 (floor tuned
after, as D7); extended to thirty-eight and re-approved at ⛔ Gate B on
2026-08-18, with the floor re-measured after that (D10). In both cases the
set was fixed before anything was tuned against it.**

## Why these questions

Five kinds from the M4 brief, one the corpus forced in M4, and one that
only became possible in M7 when a second act arrived:

| kind | n | what it tests |
|---|---|---|
| `direct` | 12 | one clearly correct unit; across scope, penalties, transparency, annexes, registration, GPAI, and on the GDPR side breach timing, lawful bases, fine tiers, DPIA trigger, transfers, DPO |
| `neighbour_adversary` | 7 | questions whose surface vocabulary points at the wrong neighbouring article — what the lexical leg and reranker exist for. GDPR's are 18-not-17, 34-not-33, 20-not-15 |
| `recital` | 5 | answered by a recitals file, which carries the as-published provenance while enacting neighbours carry the consolidation — the provenance-honest-citation test (D4), now run on both acts |
| `relocated` | 1 | Regulation (EU) 2026/1744 moved a provision (old 10(5) → new 4a); parametric memory answers with the old number, the corpus with the new — corpus must win |
| `cross_instrument` | 3 | the same subject, or the same article NUMBER, live in both acts. q31 automated decisions (GDPR 22, decoys AI Act 86/14), q32 fundamental-rights assessment (AI Act 27, decoy GDPR 35), q33 right of access (GDPR 15, decoy AI Act 15 — same number, different provision). Retrieving the right act is the test |
| `repealed` | 2 | provisions the 2026 consolidation no longer contains (Article 10(5) by number, Annex I point 1); the honest output is a refusal or redirect **from the generator**, because retrieval legitimately succeeds |
| `unanswerable` | 8 | out-of-corpus (NIS2, DORA, ePrivacy, Data Act, CRA, ISO 42001, ISO 27001, HIPAA), all near-domain on purpose. Four are caught by the gate; four are not, and refuse at generation instead — see the floor section |

## Fields

- `question` — as a GRC practitioner would ask it; only q02/q15/q16 name a
  provision literally (that is the lexical-leg test, not an accident).
- `expected_behavior` — `answer` or `refuse`.
- `expected_chunk_ids` — any-of set for retrieval hit@k. Empty for refusals.
- `expected_citation` — string the rendered citation must contain, at the
  precision the chunk's own `citation` field supports (anchor honesty: never
  grade for more precision than the chunk carries). It names the instrument
  (`GDPR, Article 15(1)`) because "Article 15" is a different provision in
  each act. **This field was inert until M7** — the README claimed it was
  scored and no code read it; it is now checked against the rendered
  citation, which is what makes the instrument part of the contract testable
  rather than merely printed.
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
2. **Citation correctness** — the answer cites a chunk id in
   `expected_chunk_ids`, that chunk's `date_basis` matches, **and** its
   rendered citation contains `expected_citation`. Same denominator. The
   third clause is not a restatement of the first: the id check passes
   whatever the renderer prints, so only this one fails if the renderer
   stops naming the instrument.
3. **Refusal correctness** — the 6 `refuse` questions, split by
   `refusal_source`: 4 must refuse at the gate, 2 must pass the gate and
   refuse in generation.

## Floor tuning, and what M7 measured

In-corpus distribution: every `gate_expectation: pass` question. Out-of-corpus:
every `gate_expectation: refuse` one. Run `python -m grc_rag.query.cli floor`.

**M4's clean gap was a four-sample artifact.** With GDPR in the corpus and
eight out-of-corpus rows instead of four, the clusters **overlap**: the Cyber
Resilience Act question reached 0.6413, above three genuinely answerable
questions (lowest in-corpus 0.6039). No threshold separated them. That is the
honest measure of how well a dense cosine discriminates near-domain questions,
and D7 predicted it in words ("permissive at the margin") on a sample too
small to show it.

The trade-off chosen, and why (decisions.md D10): the floor sits **below every
in-corpus question**, because of the two errors only a false refusal is
silent — the user is told the corpus does not cover something it does, and
cannot tell that is wrong. Four near-domain out-of-corpus questions therefore
reach the generator, whose grounding prompt refuses them. Those four were
**reclassified to `refusal_source: generation` after the measurement**, on the
same test q15/q16 use: the corpus genuinely holds material bearing on their
vocabulary, so retrieval succeeding is legitimate. Each row's `notes` records
that the relabel came after the score, because the ordering is the weak part
of the argument and hiding it would be worse than the weakness.

Do not quietly raise the floor until q15/q16 refuse at the gate — that masks
the generation-honesty test rather than passing it.

## Two run properties, observed during M4 and still true

- **DeepSeek at temperature 0 is not run-to-run deterministic.** Across
  four eval runs with identical settings, individual questions flipped
  between a clean answer and a hedged refusal (q03, q10, q12–q14 each
  did at least once). The metrics in the committed report are one run's
  numbers, not a constant of the system.
- **The verifier cannot tell a quotation from a mention.** A correct
  refusal that names the missing term in quotes — q37 answered "none of
  them mention a \"Statement of Applicability\" or an \"information
  security management system\"" — is flagged as two unverified quotes.
  The span is quoted precisely BECAUSE it is absent, which is the one
  case the verifier's rule cannot express. Read a `verified False` on a
  refusal row with this in mind; it is a limitation of the check, not a
  fabrication by the model.
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
