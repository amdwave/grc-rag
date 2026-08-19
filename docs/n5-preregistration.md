# N5 design — pre-registered predictions, written BEFORE any measurement

M13, 2026-08-19. Written before running a single question, because D10's
recorded weakness was choosing a label after seeing the score and D13's
standard is that the reason comes first. Anything below that the
measurement contradicts is a finding, not something to quietly edit.

> **What this file owns:** the predictions *as they were written, before
> the runs*, and nothing else. The decision, the results and their
> interpretation belong to
> [decisions.md D16](decisions.md#d16--n5-the-regime-pre-flight-adopted-narrowly-and-what-the-measurement-cost-the-premise),
> which is the document to read first. This one is committed so the
> claim "the reason came first" is checkable rather than asserted — the
> M11 kickoff's own criticism of leaving load-bearing evidence in a
> scratchpad. **It is not updated to match the outcomes**; P1, P3 and P7
> below were falsified and are left exactly as written.
>
> Raw measurement artifacts live in [diagnostics/](../diagnostics/):
> the run scripts, their JSON output, and `n5-hardclass.jsonl` (the 23
> questions). They are diagnostics and are deliberately NOT folded into
> `eval/corpus.eval.jsonl`.

## The reframing this session starts from

Discovery, not memory: reading the ten `unanswerable` rows shows the
failures and the successes split on one line.

| | question names its regime | outcome |
|---|---|---|
| q18 DORA, q20 ISO 42001, q34 ePrivacy, q51 ISO 22301 | **yes, explicitly** | refused correctly |
| q37 ISO 27001, q38 HIPAA | no, but distinctive artefact terms | refused correctly |
| **q36 CRA, q49 CER, q35 Data Act** | **no — regime carried in a term of art** | **answered wrongly** |

"product with digital elements" and "data processing service" occur
**zero** times in the corpus; "critical entity" occurs on one line. The
signal is present and nothing reads it.

**The hypothesis this session tests.** The grounding prompt forbids
outside knowledge — correctly, for content. But regime identity is
exactly what parametric memory is good at and the corpus is bad at: an
LLM knows "product with digital elements" is the CRA's term. The
anti-fabrication rule is therefore the *cause* of the N5 blind spot,
because it denies the pipeline the one faculty that could resolve it.
Separate the two questions: **world knowledge for "whose law is this?",
corpus only for "what does it say?"**

## Design under test — the regime pre-flight

A short model call BEFORE the documents call: name the legal
instrument(s) the question concerns, using world knowledge. Match the
answer against the closed set the corpus holds {EU AI Act, GDPR, NIS2}.
No match → refuse without ever sending the documents.

Why this is mechanically checkable rather than a prompt hope: the corpus
holds exactly three instruments, so the declaration is graded against a
closed set, not judged. That is the same move D11 made for citations —
put the claim somewhere a check can reach it.

Cost argument: the pre-flight carries no documents, so it is far cheaper
than the call it prevents. On a refusal it SAVES money.

## Predictions

**P1 — baseline N5 rate on the 26 audit negatives.** These were authored
in M11 for gate scoring and have never been generated against, so they
are a genuine holdout. Run through the shipped pipeline I predict
**6–12 of 26 answered rather than refused.**

Named as most likely to fail, before seeing anything:
n03 (NIS1 — repealed by the corpus's own NIS2), n06 (LED), n07 (UK
GDPR — substantively identical to GDPR Art 33, so the model should
produce "72 hours" from the wrong act), n08 (AI Liability), n10 (CRA),
n12 (CER), n17 (GPAI Code of Practice), n19 (SCCs — GDPR Art 46 names
them without containing them).

Least likely to fail (distinctive vocabulary, far band): n22 SOC 2,
n23 PCI DSS, n25 CCPA, n26 PIPL, n21 IEC 62443.

**P2 — regime pre-flight discrimination.** Over all 87 questions:
- **≥ 20 of 26** audit negatives correctly named as a regime outside the
  closed set.
- **≤ 3 of 51** in-corpus questions (41 eval positives + 10 probes)
  falsely flagged as outside it.

**P3 — where the pre-flight will be weakest, named in advance.** The
cross-instrument rows, because their regime is genuinely plural:
q47 (ransomware hitting personal data — NIS2 *and* GDPR), q31, q32,
q33, q48. If the design fails, I expect it to fail here first, by naming
one instrument and refusing on the other. The design must therefore be
multi-label: ANY overlap with the closed set passes.

**P4 — the repealed rows are the trap.** q15/q16 ask about provisions
the AI Act no longer contains. Their regime IS the AI Act, so the
pre-flight should pass them and leave the refusal to generation, exactly
as D7 and the eval README require. A design that refuses q15/q16 at the
pre-flight has broken the generation-honesty test and must be rejected
even if its N5 numbers look good.

**P5 — what would falsify the whole approach.** If the pre-flight cannot
beat the shipped baseline's refusal rate on the 26 negatives without
exceeding 3 false refusals, regime declaration is not the mechanism and
this session should report that and stop, not tune it. A second
threshold, a score cut-off, or a hand-tuned instrument alias list would
all be re-runs of the mistake D14 closed.

## Addendum, written after the first two measurements and before the third

P1 was **falsified**, and the reason is a methodological finding that
matters more than the prediction: the shipped pipeline refused **25 of
26** audit negatives, not the 6–12 predicted, and 1 of the 8 rows named
as likely failures actually failed.

**The audit negatives test the wrong class.** Nearly all 26 name their
regime explicitly ("under DORA", "the Cyber Resilience Act", "ISO
22301"), because M11 authored them to score a *gate* — a similarity
threshold, where phrasing barely matters. Naming is exactly what the
generator already handles. The sharpest evidence is a same-regime pair:
q36 asks about "a manufacturer of a product with digital elements" and
is **answered wrongly**; n10 asks the CRA by name and is **refused**.

So the treated-as-holdout set was a holdout for gate scoring, not for
N5. The hard class — regime carried implicitly in a term of art — has
exactly four known instances (q35, q36, q49, q50), all in the eval. The
pre-flight catches 4/4, which is precisely the four-sample evidence this
project condemned in D7 and again in D10. It is not enough to recommend
on.

`n5-hardclass.jsonl` is the missing instrument: 15 out-of-corpus
questions built on the q36/q49 recipe — a real term of art from a real
non-corpus regime, the act never named, on a subject where the corpus
holds tempting adjacent material — plus 8 in-corpus questions phrased
the same way, to measure whether that phrasing style causes false
refusals. Terms were checked against the corpus before any model saw
the set: 7 of 15 occur in it, because EU recitals cross-reference other
regimes constantly. That kills the cheap lexical "is the term absent"
design outright, and makes this set harder than intended rather than
easier. h13 is flagged debatable in advance and excluded from headline
figures.

**P6 — baseline on the hard class.** Given q36 and q49 both fail, I
predict the shipped pipeline answers **5–10 of the 15** wrongly. If it
answers 2 or fewer, N5 is a much smaller problem than D14 assumed and
this session should say so rather than design around it.

**P7 — pre-flight on the hard class.** I predict it catches **12–15 of
15**, and produces **0–2 false refusals** on the 8 in-corpus rows. The
in-corpus rows are the real risk: q16 and q43 showed that natural
phrasing without an act name can return GENERAL.

**P8 — the two string-matching defects found so far are the design's
real implementation risk**, not the model's judgement. `"GENERAL" in
reply` matched "General-Purpose AI Code of Practice"; the alias `gdpr`
matched "UK GDPR", a different instrument. Both were mine, both flipped
a verdict, and both were membership tests done sloppily. I predict any
production version fails here before it fails at regime identification.

## Out of scope, deliberately

Implementing the design in `engine.py`. This session measures and
decides; a mechanism that changes refusal behaviour needs the eval
re-run and its own decision entry, which belongs to whatever milestone
ships it. Same discipline D14 held to.
