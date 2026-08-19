# Eval set — EU AI Act, GDPR, NIS2

`corpus.eval.jsonl` is the answer key the query path is graded against — and,
after ⛔ Gate B sign-off, tuned against. It is data, Class A, git-tracked
(decisions.md D0). Fifty-one questions, one JSON object per line.

One file for the whole corpus, not one per instrument: the questions that
matter most here are the ones that could be answered from the wrong act, and
those belong to no single instrument (decisions.md D9).

**Status: twenty questions approved at ⛔ Gate B on 2026-08-17 (floor tuned
after, as D7); extended to thirty-eight and re-approved on 2026-08-18
(D10); extended to fifty-one for NIS2 and re-approved the same day (D13).
In every case the set was fixed before anything was tuned against it.**

## Why these questions

Five kinds from the M4 brief, one the corpus forced in M4, and one that
only became possible in M7 when a second act arrived:

| kind | n | what it tests |
|---|---|---|
| `direct` | 17 | one clearly correct unit; across scope, penalties, transparency, annexes, registration, GPAI, and on the GDPR side breach timing, lawful bases, fine tiers, DPIA trigger, transfers, DPO. NIS2 adds risk-management measures, the essential-entity fine tier, the essential/important split, the early-warning deadline, and one question aimed squarely at the Annex I sector table |
| `neighbour_adversary` | 9 | questions whose surface vocabulary points at the wrong neighbouring article — what the lexical leg and reranker exist for. GDPR's are 18-not-17, 34-not-33, 20-not-15. NIS2's are Article 20 board duties against Article 21's measures, and the ENISA vulnerability database against incident reporting |
| `recital` | 7 | answered by a recitals file, which carries the as-published provenance while enacting neighbours carry the consolidation — the provenance-honest-citation test (D4), now run on both acts |
| `relocated` | 1 | Regulation (EU) 2026/1744 moved a provision (old 10(5) → new 4a); parametric memory answers with the old number, the corpus with the new — corpus must win |
| `cross_instrument` | 5 | the same subject, or the same article NUMBER, lives in more than one act. q47/q48 are the pair that matters most: a ransomware incident hitting personal data, where NIS2 wants 24h/72h to the CSIRT and GDPR 72h to the supervisory authority. q31 automated decisions (GDPR 22, decoys AI Act 86/14), q32 fundamental-rights assessment (AI Act 27, decoy GDPR 35), q33 right of access (GDPR 15, decoy AI Act 15 — same number, different provision). Retrieving the right act is the test |
| `repealed` | 2 | provisions the 2026 consolidation no longer contains (Article 10(5) by number, Annex I point 1); the honest output is a refusal or redirect **from the generator**, because retrieval legitimately succeeds |
| `unanswerable` | 10 | out-of-corpus (DORA, ePrivacy, Data Act, CRA, CER, Cybersecurity Act, ISO 42001, ISO 27001, ISO 22301, HIPAA), all near-domain on purpose — NIS2's own sister Directive is among them. Four are caught by the gate; six retrieve too well for any usable floor and are expected at the regime pre-flight since M14 (D17) — see the floor section |

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
- `gate_expectation` / `refusal_source` — the load-bearing distinction,
  three mechanisms since M14 (D17):
  - `gate` — dense score below floor, no model call (four far-band rows);
  - `preflight` — the gate passes, and the regime pre-flight names an
    instrument outside the closed set the corpus holds (six rows; each
    row's notes carry the attribution reasoning, written from the
    mechanism's definition before the M14 run — D13's ordering standard);
  - `generation` (`repealed` rows) — gate AND pre-flight must PASS
    (Article 10 / Annex I chunks retrieve well, and the regime IS the AI
    Act) and the refusal must come from generation honesty. Tuning the
    floor high enough to "catch" q15/q16 would be tuning the wrong knob —
    these two are excluded from the floor's out-of-corpus distribution by
    design — and a pre-flight that refuses them has broken this test
    (pre-registration P4 disqualified a better-scoring policy on exactly
    that ground).
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
3. **Refusal correctness** — the 12 `refuse` questions, graded BY
   MECHANISM per `refusal_source`: 4 must refuse at the gate, 6 at the
   regime pre-flight, and 2 (`repealed`) must pass both and refuse in
   generation. A refusal from the wrong layer is a miss.

## Floor tuning, and what three instruments did to it

In-corpus distribution: every `gate_expectation: pass` question. Out-of-corpus:
every `gate_expectation: refuse` one. Run `python -m grc_rag.query.cli floor`.

**The gate has caught exactly four questions in every measurement, while
the out-of-corpus set grew from four to ten.**

| | out-of-corpus rows | caught at the gate | lowest in-corpus |
|---|---|---|---|
| M4, one instrument (D7) | 4 | 4 | 0.6264 |
| M7, two instruments (D10) | 8 | 4 | 0.6039 |
| M9, three instruments (D13) | 10 | 4 | 0.5947 |

The absolute number is static and the coverage is falling. M4's clean gap
was a four-sample artifact; by M7 the clusters overlapped; by M9 the
Cybersecurity Act question (q50) scored **0.7460 — above thirty-four of
the forty-five answerable questions**, and no floor that caught it would leave
the system usable. A dense cosine separates questions whose vocabulary the
corpus does not share at all, and nothing finer.

The trade-off chosen, and why (decisions.md D13, superseding D10): the
floor sits **below every in-corpus question**, because of the two errors
only a false refusal is silent — the user is told the corpus does not cover
something it does, and cannot tell that is wrong. Six unanswerable questions
therefore pass the gate; since M14 (D17) they are expected at the regime
pre-flight, which names the instrument the question's terms belong to and
refuses on no overlap with the corpus's closed set.

Those six carried `refusal_source: generation` until M14 on the test
q15/q16 use: the corpus genuinely holds material bearing on their subject,
so retrieval succeeding is legitimate. **How each label was arrived at
differs between them, and each row says which.** The four added in M7 were
relabelled after their scores were seen — the ordering is the weak part of
that argument. The two added in M9 had the reason written into their notes
at Gate B, before any score existed. The M14 move to `preflight` was
derived from the mechanism's definition and written into each row's notes
before the eval run; the run then confirmed or refuted a prediction rather
than supplying a label.

Do not quietly raise the floor until q15/q16 refuse at the gate — that masks
the generation-honesty test rather than passing it.

## Two run properties, observed during M4 and still true

- **DeepSeek at temperature 0 is not run-to-run deterministic.** Across
  four eval runs with identical settings, individual questions flipped
  between a clean answer and a hedged refusal (q03, q10, q12–q14 each
  did at least once). The metrics in the committed report are one run's
  numbers, not a constant of the system.
- **A question about an act the corpus does NOT hold can be answered
  from one it does.** M9's worst result: q36 (Cyber Resilience Act) and
  q49 (CER Directive) were answered rather than refused, out of NIS2's
  vulnerability-disclosure and physical-environment provisions. Both are
  `verified True` — every quote verbatim, every cited id resolving, the
  instrument correctly named for the text quoted. The answers are wrong
  anyway, because "product with digital elements" and "critical entity"
  are terms of art belonging to acts that are not in the corpus. No
  mechanical check in this pipeline catches that, and adding instruments
  makes it likelier: there is always something topically adjacent to
  answer from. Read refusal correctness with this in mind.
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
