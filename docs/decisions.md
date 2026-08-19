# Decision register — grc-rag

Short ADR-style entries. One per decision, newest last. Pre-kickoff decisions
are recorded here for completeness and marked as such.

## D0 — Location, backup classes, model weights (pre-kickoff)

**Status:** decided pre-kickoff, recorded 2026-08-17.

- Repo at `D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules
  from `D:\AGENTS.md` apply, including session close (commit + push).
- Backup classes per storage-strategy §3.3: code, docs, markdown corpus, eval
  set = Class A, git-tracked. `index/` (LanceDB, embeddings) = Class C —
  gitignored, rebuildable from corpus.
- Raw fetched source + fetch manifest are **committed**: a consolidated
  EUR-Lex version fetched today is not re-downloadable once the Commission
  consolidates again, so it fails the cheap-rebuild test.
- Model weights (BGE-M3, reranker, any local LLM) live in the Hugging Face
  cache on WSL ext4 — never in the repo, never on `D:\`.
- Storage-strategy bookkeeping for this folder done in v6.23 (2026-08-17).

## D1 — CLI, not HTTP service (for now)

**Status:** decided 2026-08-17.

**Context.** Day-to-day use is a terminal question→answer loop. A separate
voice-in/voice-out RAG project may eventually consume this system, which
argued for an HTTP service (OpenAI-compatible or custom). A service adds a
process lifecycle, port, wire schema, and client — none of which improve
retrieval, and a wire schema designed with zero consumers is how APIs end up
wrong.

**Decision.** CLI, built as a thin shell over an importable library core.
No HTTP service until the voice project is actually ready to consume one.

Two constraints are part of the decision, because they are what keep the
service option cheap later:

1. **Importable core:** `answer(question) -> Answer` returns a structured
   object (answer text, chunks, citations, scores). argparse and terminal
   rendering stay strictly outside the core. No global state.
2. **REPL mode:** the CLI gets an interactive loop so BGE-M3 and the reranker
   load once per session, not once per question. This removes the only real
   latency argument for a persistent service.

**Trigger to revisit:** the voice project (or any second consumer) is ready to
integrate. At that point wrap the core in a thin HTTP adapter shaped by what
that consumer actually needs.

## D2 — One public repo; CIS text in no repo

**Status:** decided 2026-08-17.

**Context.** The markdown corpus is a first-class, diffable artifact. The code
repo must be public from day one (portfolio). EUR-Lex and NIST content is
redistributable; CIS Controls text likely is not. Options were one repo, or a
separate versioned content repo (`D:\projects\grc-corpus\`).

**Decision.** Single public repo. No `grc-corpus` repo.

- **Atomicity is the load-bearing reason:** the corpus is a build artifact of
  the converter, so a converter fix and the regenerated markdown diff land in
  one commit, reviewable together. Split repos make that two commits in two
  repos with nothing enforcing sync.
- Size is a non-issue (tens of MB of well-diffing text). If that ever changes,
  splitting later via `git filter-repo` preserves corpus history; merging
  repos back is the painful direction.
- **CIS Controls text stays out of every repo:** raw + markdown live under a
  gitignored `corpus/local/` path; only its fetch manifest (URL, version,
  checksum) is committed. "Local-only source" is a first-class pipeline
  concept, not a special case.
- Consumers (voice project, content work) read the corpus by path; no repo
  boundary needed.

**Cost accepted:** the CIS copy exists only on this disk, behind CIS's
registration wall — not guaranteed re-fetchable. It needs a backup home per
storage-strategy, decided when the CIS source is actually built (not before).

**Consequence:** no `grc-corpus` folder, so no additional storage-strategy
edit — the pre-kickoff v6.23 bookkeeping already covers everything.

## D3 — Local embeddings, cloud generation via DeepSeek

**Status:** decided 2026-08-17.

**Context.** Two layers with opposite reversibility. Constraints from
storage-strategy: zero-recurring-spend (register #17), DeepSeek BYO-key
pay-per-token is the established inference lane (register #19, third-party
egress accepted in #20 for client content — stricter than this 100%-public
corpus). The Claude subscription ends ~2026-08-31 and is not renewed; an
earlier draft of this decision recommended Anthropic as the cloud backend and
was corrected against these constraints.

**Decision.**

- **Embeddings: local, pinned BGE-M3** (+ bge-reranker-v2-m3), HF cache on
  WSL ext4. Vectors are only comparable within one model and cloud embedding
  models get deprecated on someone else's schedule; a pinned local file
  cannot be. Multilingual fits the EN/ES roadmap. Backend-independent
  argument — this half survives any generation-layer change.
- **Generation: cloud, DeepSeek default** — the existing key, pay-per-token
  (pennies per query at RAG scale), no new vendor, no new subscription.
  Local Qwen3 14B Q4 via llama-server is the fallback backend.
- **Interface: one plain `openai`-client adapter**, `base_url` + `model` +
  key from config. DeepSeek, llama-server, and the Gemini API all speak the
  OpenAI wire protocol, so one adapter covers every backend in play. If a
  non-OpenAI-compatible provider ever matters, that is the day a small
  internal Protocol appears — not before.
- **Named zero-cost alternate: Gemini API free tier** via its
  OpenAI-compatible endpoint (base_url + key swap). Deliberately decoupled
  from the Google AI Pro subscription, whose justification lives entirely in
  the backup layer (register #18) — the API free tier exists independently.
  Verify endpoint/terms at build time; do not trust this entry's vendor
  trivia.
- Temperature 0 at generation stands — DeepSeek and llama-server accept it.
  The real groundedness guarantee is the verify step + citation contract,
  not sampling determinism.
- **Keys:** `DEEPSEEK_API_KEY` in gitignored `.env`; `.env.example`
  committed with names only; never echoed, never committed. python-dotenv
  approved as a dependency for loading it.

**Trigger to revisit:** DeepSeek pricing/terms change materially (same
trigger as register #19), or eval quality shows generation is the
bottleneck — then swap backends through the adapter and re-run the eval.

## D4 — The corpus is two documents, because the recitals are

**Status:** decided 2026-08-17, during M2.

**Context.** The plan said "fetch the AI Act, consolidated, English". At
fetch time the consolidated representation
(`02024R1689-20260727`, current after Regulation (EU) 2026/1744) turned
out to contain **no recitals at all** — EUR-Lex consolidations carry the
enacting terms and the annexes only. Measured, not assumed: zero `rct_`
ids and zero occurrences of "whereas" in the consolidated HTML, against
180 recitals in the original OJ publication. The recitals matter for this
system: they are what an AI Act question about intent or scope is
usually answered from.

Three options: drop the recitals; take everything from the original OJ
text and lose the amendments; or carry both.

**Decision.** Both, as two files with two provenances.

    corpus/eu/ai-act.md            enacting terms + annexes  02024R1689-20260727
    corpus/eu/ai-act.recitals.md   recitals                  32024R1689

- **One file per source document, never a merged file.** The two have
  different CELEX ids, different dates and different legal status; a
  single file would have to carry per-section provenance, and the first
  time it was wrong a chunk would cite the current law for text that was
  superseded. Front matter carries `celex`, `source_url`, `source_sha256`
  and `version_date` per file, so every M3 chunk inherits a provenance
  that is true for all of it.
- **Paths are stable across consolidations.** The version lives in the
  front matter, not the filename, so the next consolidation rewrites
  `ai-act.md` in place and `git diff` shows exactly what the Commission
  changed. That is the whole reason the markdown is versioned.
- Recitals are not amended by amending acts — they belong to the act as
  adopted — so the recitals file does not go stale when the enacting
  terms are re-consolidated. The amending act's own recitals are a
  separate document, and out of scope until there is a reason.

**Cost accepted:** an M3 chunk from the recitals file is dated 2024-07-12
while its neighbours in the enacting file are dated 2026-07-27. Citation
rendering has to say which — that is a feature, not a wart.

## D5 — The raw file is committed as served; the manifest carries two hashes

**Status:** decided 2026-08-17, during M2.

**Context.** Two fetches of the same unchanged act produce different
bytes. Measured: EUR-Lex stamps a per-response Dynatrace RUM id into one
`<script data-dtconfig="…">` attribute in the head, and nothing else in
the document differs. A hash that changes on every fetch cannot answer
the only question a fetch manifest exists to answer — has the source
changed?

**Decision.** The raw file is committed **exactly as served** — a
normalised "raw" file is not raw, and provenance is the reason it is in
git at all (D0). The manifest carries `sha256` of the bytes as served
**and** `sha256_normalized` of those bytes with the telemetry attribute
removed, plus a `normalization` field stating the rule in words.

Comparing consolidations means comparing `sha256_normalized`. The
verification that this is the right pair of numbers is in the fetch
itself: two consecutive fetches differ in `sha256` and agree in
`sha256_normalized`.

## D6 — Embedding runtime, and the lexical leg verified rather than assumed

**Status:** decided 2026-08-17, during M3.

**Context.** D3 settled *which* embedding model (pinned local BGE-M3) but
not what runs it, and the architecture brief left one thing explicitly
open: whether LanceDB can index BGE-M3's sparse output, with instructions
to **verify at build time** and fall back to LanceDB's own BM25 rather
than hand-roll a sparse index either way.

**Decision.**

- **sentence-transformers** as the BGE-M3 runtime. FlagEmbedding would
  add dense + sparse + ColBERT in one call, but the sparse half has
  nowhere to live (below), so it would buy a heavier dependency tree for
  an output nothing consumes. Writing pooling and normalisation by hand
  against `transformers` is exactly the kind of detail that silently
  produces slightly-wrong vectors.
- **The lexical leg is LanceDB's native BM25 full-text index**, built
  over the chunk's `text` column at index time. Verified, not assumed:
  `python -m grc_rag.query.index --smoke-only` runs an identifier query
  through the FTS leg and fails if Article 15 does not come back. It
  does: `Article 15 accuracy robustness cybersecurity` returns
  `art_15(1)`, `art_15(3)`, `art_15(2)`. A dense-only index would look
  perfectly healthy at that moment, which is why the check is in the
  build and not in a README.
- **Measured at build:** 871 chunks, 1024-dim vectors on `cuda:0`
  (RTX 3500 Ada, torch 2.13+cu130), `index/` 4.5 MB — Class C, gitignored,
  rebuilt in about a minute once the weights are cached.
- **The virtualenv lives on WSL ext4** (`~/.venvs/grc-rag`, 5.1 GB) via
  `UV_PROJECT_ENVIRONMENT`, not in the repo on `/mnt/d`. Same reasoning
  D0 applied to the model weights: thousands of small files behind the
  NTFS boundary are slow to import and belong to no backup class. The
  repo stays on D:; only the environment moves.

**Not decided here:** rank fusion weights, the reranker's cut-off, and
the relevance-gate floor. All three are tuned against the eval set in M4,
after Gate B — tuning them now would be tuning against nothing.

## D7 — Relevance-gate floor: 0.62 on the dense cosine alone

**Status:** decided 2026-08-17, during M4, after Gate B sign-off.

**Context.** The gate refuses before any model call when retrieval says
the corpus is not about the question. It reads the best dense cosine
alone — never the fused rank and never BM25, which scores high on any
question sharing common words (brief; book2rag's earned rule). The floor
is only meaningful against the model that produced the vectors (BGE-M3,
D6), tuned from the approved eval set's distributions, measured by
`python -m grc_rag.query.cli floor`.

**Measured** (20 questions, best dense cosine per question):

| cluster | n | range |
|---|---|---|
| out-of-corpus (`gate_expectation: refuse`) | 4 | 0.4918 – 0.6151 |
| in-corpus (`gate_expectation: pass`) | 16 | 0.6264 – 0.8020 |

Clean gap 0.6151 → 0.6264; **floor 0.62**, the midpoint.

- The hardest out-of-corpus case was ISO/IEC 42001 (0.6151), not the
  GDPR question the eval README predicted (0.5669) — management-system
  vocabulary sits closer to Article 17's than GDPR's does to anything.
- q15/q16 (repealed provisions) score 0.6379 and 0.6967 — above the
  floor **by design**: their refusal belongs to the generator, and a
  floor high enough to catch them would be mistuned (eval README).

**Cost accepted.** The gap is real but narrow (0.011) and rests on four
out-of-corpus samples. The floor is permissive at the margin: a
near-domain out-of-corpus question can score above 0.62 and reach the
generator, whose grounding prompt is the second line of defence.

**Trigger to revisit:** any change to the corpus, chunking, or embedding
model shifts both distributions — re-run `cli.py floor` and re-record.
Adding Phase 2 instruments (GDPR, NIS2, DORA) converts today's
out-of-corpus questions into in-corpus ones; the eval set needs new
out-of-corpus rows at that point, not just a re-run.

## D8 — Fetching through Cellar, because EUR-Lex's human site challenges robots

**Status:** decided 2026-08-18, during M6.

**Context.** M6 opened by fetching GDPR and got HTTP 202 and an AWS WAF
page — "we need to verify that you're not a robot" — from
`eur-lex.europa.eu/legal-content`. Measured before concluding anything:
the same challenge came back for the AI Act's own landing page, which
had fetched cleanly the day before, so this is the host's posture toward
this client and not something GDPR or the fetcher did. Defeating a bot
challenge was never on the table.

The identifier discovery in `fetch.eurlex` was the real casualty. Its
whole design is that a consolidated id is *discovered, never
remembered*, and the two opinions it reconciled — the "Current
consolidated version" status line and the `data-celex` attribute — both
live on the blocked page. Guessing an id that still returns 200 is
precisely the failure that function exists to prevent.

**Decision.** Fetch through the Publications Office's Cellar service
(`publications.europa.eu/resource/celex/<id>`, `--source cellar`, now
the default). `--source legal-content` keeps the old route for the day
the challenge lifts.

Measured before switching, not assumed — the risk was that Cellar serves
a *third* HTML skin, which would have confounded every M6 finding with
"Cellar-specific" noise:

| | legal-content | Cellar |
|---|---|---|
| `eli-subdivision`, AI Act consolidated / OJ | 121 / 303 | 121 / 303 |
| class vocabulary | — | identical but one cosmetic `borderOj` |
| two consecutive fetches | differ (Dynatrace RUM id) | byte-identical |

So the converter cannot tell the two apart, and the AI Act conversions
are byte-identical after the switch. Cellar content-negotiates: it
answers 404 to `text/html` and serves the document only for
`application/xhtml+xml`.

**Discovery keeps its second opinion**, which is the part that mattered.
The pair is now the Cellar SPARQL endpoint (which consolidated ids
exist) and the consolidated document's own header line
(`02016R0679 — EN — 04.05.2016`). Those are two different services, so a
change to either surfaces as a disagreement rather than a wrong answer.
`fetch` refuses to save a file whose id the document contradicts.

**Costs accepted.**

- A new service in the fetch bucket. Still stdlib-only — no dependency.
- The corpus now has mixed host provenance: the AI Act's committed raw
  files came from legal-content and are **not** re-fetched, because D5
  commits the bytes as served and re-fetching to tidy provenance would
  destroy the thing provenance is for. Every manifest records
  `access_route`, so which is which is readable rather than inferred.
- D5's normalization rule is a no-op on this route (no Dynatrace stamp),
  so `sha256` and `sha256_normalized` are equal here. The rule stays: it
  is still correct, and it is what makes the two routes comparable.

**Trigger to revisit:** the challenge lifts and `--source legal-content`
starts working again — at which point this stays the default anyway,
because a machine interface that does not challenge machines is the
better dependency.

## D9 — GDPR is two documents too, and the converter was never AI-Act-specific

**Status:** decided 2026-08-18, during M6. *(The M6 brief called this
entry D8; the fetch-route change above took that number, since the
register keeps one decision per entry.)*

**Context.** M6's question was how much of `convert/eurlex_html.py` was
EUR-Lex and how much was the AI Act — unknown until measured, per M5.

**What was measured, not assumed.**

| | recitals | articles | annexes | chapters |
|---|---|---|---|---|
| GDPR consolidated `02016R0679-20160504` | 0 | 99 | 0 | 11 |
| GDPR original OJ `32016R0679` | 173 | 99 | 0 | 11 |

**D4 generalizes.** GDPR's consolidation carries no recitals either —
zero `rct_` ids, zero occurrences of "whereas" — so the corpus is
`corpus/eu/gdpr.md` (enacting terms) and `corpus/eu/gdpr.recitals.md`
(recitals), two provenances, exactly as D4 laid down. GDPR has **no
annexes**, confirmed against the fetched HTML in both representations
rather than from recollection.

**One code path, no instrument profile.** The converter needed no
changes to produce the text: 99 articles and 173 recitals, 0
unaccounted and 0 anomalies on the first run of each. A cross-check
independent of the totals: the 191,372 characters dropped as
`not-this-part` from the OJ document fall within 755 of the 190,617
emitted as enacting terms from the consolidated document — two separate
conversions agreeing on the size of the same text. Order is clean too,
SPLICE 0 in both directions for all four documents.

**What *was* AI-Act-specific was the provenance, and it failed
silently.** `amending_acts()` matched `celex:<id>`; Cellar writes
`celex/<id>`. On the Cellar route it therefore matched nothing and
returned an empty list — which is also exactly what a genuinely
unmodified act returns, so the front matter asserted that nothing had
been folded in and no check could see the difference. A re-fetched AI
Act would have quietly lost `32026R1744`.

Worse, the relation itself was assumed. GDPR's consolidation exists
because of a **corrigendum**: its table is headed "Corrected by:", its
markers are `►C1`, and the id is `32016R0679R(02)`. The old pattern
`3\d{4}[A-Z]\d{4}` truncates that to `32016R0679` — the act modifying
itself. So `modifying_acts()` now reads the table's own header and emits
`amended_by` **or** `corrected_by`, and two drop rules were renamed to
describe what they actually remove. The AI Act's markdown is
byte-identical after the fix; only its report changed, by two lines.

**Four rows, not one registry.** The four named lists do not hold the
same fact: `query/cli.py`'s `EVAL_FILE`/`EVAL_REPORT` is corpus-wide,
not per-document, so a registry would replace three of four while adding
a Python-to-bash consumer for `rerun-identical.sh`. They also fill at
different milestones — `seqcheck-corpus.py` (now keyed
`<instrument>:<part>`, since a bare `enacting` cannot say whose) and
`rerun-identical.sh` cover GDPR today; `CHUNK_FILES` and the eval pair
stay AI-Act-only until M7 puts chunks behind them. A registry earns its
keep when NIS2 lands and a Directive tests whether the per-document
fields are even stable.

**Cost accepted.** `part: enacting terms and annexes` is the converter's
fixed label and now appears on a document with no annexes. The base
act's own CELEX remains in the modifier list (`corrected_by` includes
`32016R0679`), which predates GDPR; changing it would rewrite the AI
Act's front matter for a cosmetic reason.

**Known defect, deliberately not fixed here.** Source footnotes render
as `( )` — the number is dropped as a `note-mark` inside its own
footnote text. This is Phase 1 debt, present in the AI Act corpus since
M2, not something GDPR introduced. Fixing it rewrites the AI Act
markdown and ripples into chunks and the eval, so it belongs to its own
decision rather than smuggled into M6.

## D10 — The gate floor after GDPR: the clean gap was a small-sample artifact

**Status:** decided 2026-08-18, during M7, after Gate B sign-off on the
extended eval set. **Supersedes D7's value**; D7's reasoning about *what*
the gate reads (best dense cosine alone, never the fused rank, never BM25)
stands unchanged.

**Context.** D7 set the floor at 0.62 from a clean gap — out-of-corpus max
0.6151, in-corpus min 0.6264 — and named its own weakness: "the gap is
real but narrow (0.011) and rests on four out-of-corpus samples," with the
trigger "adding Phase 2 instruments converts today's out-of-corpus
questions into in-corpus ones; the eval set needs new out-of-corpus rows at
that point, not just a re-run." M7 fired that trigger exactly.

**Measured** (38 questions, best dense cosine each, floor run before any
relabelling):

| cluster | n | range |
|---|---|---|
| out-of-corpus | 8 | 0.4918 – 0.6413 |
| in-corpus | 30 | 0.6039 – 0.8040 |

**The clusters overlap.** No threshold separates them. The Cyber Resilience
Act question (vulnerability handling for products with digital elements)
scored 0.6413 — above three genuinely answerable questions, the lowest
being GDPR data portability at 0.6039. ISO 27001, ISO 42001 and HIPAA
breach notification also landed inside the in-corpus range.

This is not a regression. It is the first measurement large enough to show
what D7 could only assert in prose. The old clean gap existed because four
out-of-corpus samples is too few to find the hard cases; five of the eight
rows here were written specifically to be near-domain, and they found them.

**Decision: floor 0.595, placed below every in-corpus question.**

Of the two errors the gate can make, they are not symmetric:

- A **false refusal** tells the user the corpus does not address something
  it does. It is silent, and the user has no way to tell it happened.
- A **false pass** sends documents to the generator that do not answer the
  question. The grounding prompt is written for exactly that case, D7
  already named it "the second line of defence", and the eval reports which
  mechanism refused.

So the binding constraint is "below the lowest in-corpus score". 0.595 is
the midpoint of the resulting gap (0.5864 .. 0.6039), the same tie-break
method D7 used; 0.60 also satisfied the constraint but left 0.0039 of
margin under the lowest real question, which is too thin to survive
ordinary corpus drift.

**The reclassification, and why it is the weak part.** Four out-of-corpus
rows (q20 ISO 42001, q36 CRA, q37 ISO 27001, q38 HIPAA) scored above the
in-corpus minimum and therefore cannot be caught by any acceptable floor.
They were moved from `refusal_source: gate` to `generation`, on the test
q15/q16 already use: the corpus genuinely holds material bearing on the
question's vocabulary — AI Act Article 15 on cybersecurity, Article 17 on
quality management, GDPR Articles 33/34 on breach notification — so
retrieval succeeding is legitimate and the refusal belongs to the
generator.

**That label was chosen after seeing the score, not before.** That ordering
is the argument's weakness and is recorded here and in each row's `notes`
rather than smoothed over. It also means the post-relabel "clean gap
0.5864 .. 0.6039" is clean *by construction*: the honest measurement of the
gate's discriminative power is the overlap above, not the gap the tool
prints afterwards. Anyone re-reading this should take the 8-sample overlap
as the finding.

**The reclassification was then tested, not just argued.** Relabelling
those four predicted that the generator would refuse them. In the M7 eval
run it did, 4 out of 4 — refusal correctness 10/10 overall. That is
evidence the label describes the mechanism rather than excusing the
measurement. It does not repair the ordering problem above; it means the
claim the label makes is checkable and currently holds.

**Cost accepted.** Half the out-of-corpus set now reaches the generator and
costs an API call before being refused. The gate is a cheap first filter,
not a guarantee, and after this entry it is honest about which it is.

**Trigger to revisit:** any corpus, chunking or embedding-model change
(unchanged from D7); or a third instrument, which will move both
distributions again. If a future measurement shows in-corpus questions
below 0.55, the floor is no longer buying anything and the gate should be
reconsidered rather than re-tuned.

## D11 — The citation names the instrument, and the eval finally checks it

**Status:** decided 2026-08-18, during M7.

**Context.** The system's pitch is a citation that can be checked against
the article. With one act, `cite()` rendering "Article 15 (consolidated
text as of 2026-07-27)" was checkable. With two it is not: **Article 15 is
accuracy, robustness and cybersecurity in the AI Act and the right of
access in GDPR.** Both exist; both are Article 15. The rendered citation
named neither act, and the two were distinguishable only because their
consolidation dates happened to differ — an accident of the sources, not a
property of the design.

Found alongside it: `expected_citation` was **dead data**. Fourteen eval
rows carried it, no code read it, and `eval/README.md` stated it was
scored. Citation correctness was in fact judged on cited chunk ids plus
`date_basis`.

**Decision.**

- `Source` carries `instrument`, and `cite()` renders
  `GDPR, Article 15(1) (consolidated text as of 2016-05-04)`. Composed at
  render time rather than baked into the chunk's `citation` field: the
  chunk stores facts, the renderer composes them, and the AI Act's 871
  committed chunks did not need rewriting for a presentation change.
- The same string goes into the prompt the model sees, so grounding gets
  the disambiguation too.
- `expected_citation` is now scored, alongside the id and `date_basis`
  checks. It looks redundant beside the id check and is not: the id check
  passes whatever the renderer prints, so it is blind to the citation
  contract itself. This check fails against the pre-M7 renderer, which is
  what makes it a check rather than a restatement.
- Eval row q33 exists for this: the right of access, whose lexical decoy is
  `ai-act#art_15` — the same article number in the other instrument.

**Cost accepted.** Every `expected_citation` in the eval set had to be
rewritten to the instrument-qualified form, and the eval file was renamed
`ai-act.eval.jsonl` → `corpus.eval.jsonl` (D9: the eval pair is
corpus-wide, and the old name described half of what it now holds).

## D12 — NIS2, the rowspan defect, and the third kind of wrong

**Status:** decided 2026-08-18, during M8, after Gate A sign-off.

**Context.** NIS2 (Directive (EU) 2022/2555) was chosen as the third
instrument on an explicit prediction, recorded at the end of M7: GDPR is a
sibling Regulation and needed no converter changes at all, so *a Directive
is where the remaining assumptions will show*.

**D4 generalizes a third time.** The consolidation `02022L2555-20221227`
carries zero `rct_` ids and zero occurrences of "whereas" against 144
recitals in the OJ text, so NIS2 is two documents with two provenances
like the other two. 46 articles, 3 annexes, 9 chapters. Both parts
converted clean on the first run — 0 unaccounted, 0 anomalies — and the
independent cross-check held: 138,484 characters dropped as
`not-this-part` from the OJ document against 139,430 emitted as enacting
terms from the consolidation, a 946 gap in the same band as GDPR's 755.

**The prediction was right and its reasoning was wrong.** Nothing about
being a Directive broke anything. A Directive's closing formula is a
numbered article — Article 46, "Addressees" — rather than the separate
unnumbered block a Regulation ends with, and the converter handled that by
correctly minting no formula section. What actually exposed a defect was
the shape of the annexes, which is incidental to instrument type. A
Regulation with sector tables would have done the same. Recorded because
the next instrument should be chosen on the shape of its content, not on
its legal form.

**The defect: `rowspan` and `colspan` were never implemented.**

| | rowspan attrs | largest | where they sit |
|---|---|---|---|
| NIS2 | 20 | 17 rows | Annex I/II sector tables — in the corpus |
| EU AI Act | 2 | 2 | both inside the dropped "Amended by" header table |
| GDPR | 0 | — | — |

`table()` read each `<tr>`'s cells in order and padded short rows at the
END, so every continuation row was left-shifted by however many columns
the spans above it occupied. In NIS2's Annex I, "— Distribution system
operators…" — a *Type of entity* — rendered in the *Sector* column. The
bug is as old as the converter. It survived two instruments because the
AI Act's only two spans are in apparatus dropped before rendering.

Fixed by filling the grid properly, tracking which columns each span still
occupies. **`ai-act.md` and `gdpr.md` are byte-identical after the fix**,
which is the check that it repairs NIS2 without disturbing what was
already correct.

**A third kind of wrong, which neither standing check can see.** The
coverage table counts characters and every character was emitted exactly
once. `seqcheck-corpus.py` compares order and the order was unchanged.
Only the *column assignment* was wrong. The two instruments this project
relies on see a multiset and a sequence respectively; a spanned-cell
misalignment is neither. Structure is a third class, and it is currently
caught only by a human reading the tables at Gate A.

**The check disagreed with the design, and the design changed.** The first
fix repeated a spanning cell's text into every row it covered, on the
argument that a retrieval corpus wants each entity row to carry its own
sector. `seqcheck` failed it with 25 splice runs — correctly: repeated
text is text the source does not have at that point, which is exactly the
duplication shape the check exists to find. Continuation cells are now
left empty and only the alignment is repaired. The alternative was to
teach seqcheck about intentional duplication, which is the "tuning the
instrument until it agrees" failure the check's own comments warn against.
The context is not lost in practice: each chunk carries the annex in its
`parent_path` and the header row travels with it.

**Decision: no third standing check, for now.** A structural check that
fires only on tables is a large amount of machinery for one shape, and the
project already has the honest alternative — Gate A exists precisely
because the conversion reports are meant to be read by eye, and this
defect was found that way, on the first instrument that had it.

**Cost accepted, and stated plainly:** a table misalignment in a future
instrument will pass every automated check and reach the corpus if nobody
looks. That is a real hole, not a covered case.

**Trigger to revisit:** a fourth instrument with heavy tables, or any
table defect that reaches the corpus and is found after Gate A rather than
at it. Either means eye-reading did not scale, and the check has to be
built. A cheap first version exists in outline: re-parse each rendered
markdown table and assert its cell count against the source grid's
expanded width times height — an independent recomputation, in the spirit
of seqcheck rather than an assertion by the converter about itself.

**Not done here, deliberately:** NIS2 is converted but not chunked,
indexed or evaluated, exactly as M6 left GDPR. That is M9, and it fires
D10's trigger — a third instrument moves both dense-score distributions,
so the floor must be re-measured rather than assumed, and the eval set
needs NIS2 questions plus replacements for q17, whose subject is now
in-corpus.

## D13 — Three instruments: the gate is a coarse filter, and says so

**Status:** decided 2026-08-18, during M9, after Gate B sign-off on the
51-question set. **Supersedes D10's value**; the reasoning in D7 about
*what* the gate reads — best dense cosine alone, never the fused rank and
never BM25 — still stands.

**Context.** D10 named its own trigger: "a third instrument, which will
move both distributions again." NIS2 fired it. The prediction recorded at
the end of M8 was that the overlap would widen rather than close, because
NIS2 shares heavy vocabulary with both existing acts and its nearest
out-of-corpus neighbours are closer than anything in the M7 set.

**Measured** (51 questions, best dense cosine each, before any
relabelling):

    out-of-corpus (6):  0.5170  0.5346  0.5656  0.5853  0.5927 │ 0.7460
    in-corpus    (45):  0.5947 ....................................... 0.8052

The prediction held. **q50 — how a European cybersecurity certification
scheme is adopted — scored 0.7460, above thirty-four of the
forty-five answerable questions.** No floor that caught it would leave the system
usable; it would silently refuse three quarters of the questions the
corpus can actually answer.

**The trend is the finding, not the number.**

| | out-of-corpus rows | caught at the gate | lowest in-corpus |
|---|---|---|---|
| D7 (M4, one instrument) | 4 | 4 | 0.6264 |
| D10 (M7, two instruments) | 8 | 4 | 0.6039 |
| D13 (M9, three instruments) | 10 | 4 | 0.5947 |

The gate has caught **exactly four questions in every measurement** while
the out-of-corpus set grew from four to ten. Its absolute reach is static
and its coverage is falling. A dense cosine separates questions whose
vocabulary the corpus does not share at all — DORA, ePrivacy, the Data
Act, ISO 22301 — and nothing finer. That is a real capability, and it is
a smaller one than "the gate refuses out-of-corpus questions" implies.

**Decision: floor 0.59**, below every in-corpus question, on D10's
unchanged asymmetry argument — of the two errors only a false refusal is
silent. The gap left after reclassification is 0.5853 .. 0.5927 and its
midpoint is 0.589; 0.59 is that rounded. **Read that gap sceptically:**
its lower bound, 0.5927, is q49, an out-of-corpus question moved into the
pass cluster by the reclassification below. The lowest genuine in-corpus
score is q44 at 0.5947, so the real separation between the nearest
out-of-corpus question and the nearest answerable one is 0.0020. That is
noise, not discrimination.

**Two rows reclassified, and this time the reason came first.** q49 (CER
Directive, physical resilience) and q50 (Cybersecurity Act certification)
move to `refusal_source: generation` on the D10 test — the corpus
genuinely holds bearing material: NIS2 Article 21(2) requires physical and
environmental security, and NIS2 Article 24 is titled "Use of European
cybersecurity certification schemes". **Unlike the four relabelled in M7,
the reason for both was written into the row's `notes` at Gate B, before
any score was measured.** The measurement confirmed a prediction rather
than supplying one. That is the standard the next reclassification should
meet, and the M7 four are still marked as not having met it.

**Cost accepted, and it is larger than D10 assumed.** Six of ten
unanswerable questions now reach the generator. D10 said the grounding
prompt was the second line of defence for exactly these. **The M9 eval
run falsified that for two of them.**

q36 (Cyber Resilience Act vulnerability handling) and q49 (CER Directive
physical resilience) were **answered, not refused** — refusal correctness
10/12. Neither answer is a fabrication: both are `verified True`, every
quote is verbatim, every cited id resolves. They answer a question about
one regime out of the text of another. q36 presents NIS2's coordinated
vulnerability disclosure as the CRA obligations of "a manufacturer of a
product with digital elements"; q49 offers NIS2 Article 21(2), which
protects "the physical environment of network and information systems",
as the resilience duties of a CER "critical entity". Both are terms of
art belonging to acts this corpus does not contain.

This is the multi-instrument failure mode, and it is worse than a bad
refusal because every mechanical check passes. The verifier confirms the
quotes. The citation contract names the right instrument — for the text
quoted. The answer is still wrong, because the question named a regime
nobody checked for. D11 fixed instrument confusion at the RENDERING
layer; this is the same confusion at the REASONING layer, and nothing in
the pipeline currently addresses it.

The honest statement, which the README and eval README now carry: the
gate is a coarse pre-filter for far-out-of-domain questions, the
grounding prompt catches most of the rest, and **at three instruments
neither reliably catches a question about a fourth regime whose subject
matter the corpus partly covers.**

**Two retrieval findings, recorded without acting on them.** q39 (NIS2
risk-management measures) and q22 (GDPR lawful bases) both answered
correctly from RECITALS while the enacting article — Article 21(2) and
Article 6(1) respectively — never entered the top five. Twice, in two
instruments: recital prose matches a natural-language "what must we do"
question better than an enumerated enacting provision does. Neither
answer key was widened afterwards to admit the recitals, because that
would be editing the key to fit the result. It is a chunking or
retrieval-weighting question for a later milestone.

**One Gate B worry that measured clean.** `nis2#anx_I` is 12,759
characters, by far the largest chunk in the corpus, and q42 was written
to find out whether a whole sector grid in one vector still retrieves.
It does: hit@5 and citation both correct. Spanned-table granularity is
not a problem at this size, and the question stays in the set as the
canary if that changes.

**Trigger to revisit — and this one is a redesign, not a re-tune.** A
fourth instrument will not improve any of this and will make the
cross-regime failure above more likely, not less. Before adding one, the
gate's mechanism should be reconsidered. The specific hypothesis worth
testing first: **gate on the reranker's cross-encoder score rather than
the dense cosine.** The cross-encoder judges query-document relevance
directly, which is the question the gate is actually asking, where cosine
similarity measures vocabulary overlap, which is the question it can
answer. It is a hypothesis, not a known fix — it costs a rerank before
the gate, and it must be measured against this same eval set before
anything is claimed for it. D7's warning against gating on BM25 is not an
argument against the cross-encoder: BM25 scores shared words, which is
the failure mode; the cross-encoder is trained on relevance.

## D14 — The audit: the gate stays, its demotion is falsified, and the blind spots get names

**Status:** decided 2026-08-19, during M11, an audit session whose brief
was to attack the conclusions of M6–M10 rather than extend them. Raw
artifacts (scores, control run, probe set, scripts) are under
`/mnt/d/.staging/audit-*`; they are diagnostics, not part of the graded
eval, and none of them were folded into `eval/corpus.eval.jsonl`.

**Context.** Four entries — D7, D10, D13, plus the uncommitted M10
experiment — record the same mechanism degrading, and no session had
asked the prior question: should a pre-generation relevance gate exist
at all? The audit tested five claims the prior sessions were most
confident about. One was falsified; it was this audit's own leading
hypothesis, not the incumbent design.

**Measured — the M10 conclusion survives a 3.6× larger sample.** M10
rested on ten negatives, the same weakness D7 was criticised for. The
audit re-scored the 51 eval rows (reproducing `m10-gate.json` to four
decimals) and added 26 new out-of-corpus questions banded by nearness
(extreme-near: UK GDPR, the Law Enforcement Directive, NIS1, the AI
Liability Directive, the GPAI Code of Practice; out to far: SOC 2,
PCI DSS). On 51 positives (41 eval + 10 independent probes) and 36
negatives, the best any threshold mechanism achieves at zero false
refusals: dense 19/36, rerank 16/36, OR 21/36. Every optimal threshold
has **zero margin** — it sits exactly on a positive's score. Fifteen of
36 negatives are uncatchable by any combination, including six of the
seven extreme-near regimes; a question about the Commission's own
prohibited-practices guidelines reranks at +0.89 against a corpus that
genuinely covers Article 5. Both scores measure topicality. Answerability
is not in them, and no wider sample changes that.

**Measured — the control experiment nobody ran, and it falsified the
demotion.** The full 51-question eval with `floor=None`: hit@5 37/39 and
citation 36/39, identical to the committed run. Refusal correctness fell
10/12 → 8/12. Of the four questions the gate catches, q18 (DORA) and
q51 (ISO 22301) were refused by the generator anyway; **q34 (ePrivacy)
came back as a hedged non-refusal** — substantively honest, but not the
refusal contract — **and q35 (Data Act) came back as a fluent
cross-regime answer**, the "provider of data processing services"
answered out of GDPR Article 20 data portability, verified True. The
grounding prompt is not a superset of the gate. The gate's correctness
contribution is narrow — far-band questions only — but real, and it is
deterministic where generation refusal measurably is not. "The gate is
a cost optimisation with no correctness claim" was this audit's highest-
value hypothesis, and it is wrong.

**Measured — the answer key holds up.** Ten questions authored from the
three instruments' tables of contents alone, before this session read
the eval file, on subjects the eval does not touch (joint controllers,
child consent, BCRs, logging retention, sandboxes, the entity registry,
information-sharing arrangements): 10/10 retrieval hit@5, 10/10 answers
citing the expected article, three verifier flags all in the known
benign classes (ellipsis elision, bracket-adapted verbs). An eval set
drifted toward its system would outperform blind questions; this one
does not. The M7 relabel ordering (D10) remains a recorded process
defect, but the set itself is sound, and D13's pre-registration standard
stands as the bar.

**Measured — run-to-run variance, quantified once.** The control pass
doubles as the deliberate re-run: headline metrics identical, refusal
behaviour on non-gate rows identical, verification flipped on 4 of 51
rows (q24 False→True; q40, q43, q45 True→False). The nondeterminism
lives in how the model quotes, not in what it retrieves or refuses. The
committed report's headline bears weight; any single row's verification
flag is a one-run sample.

**Decision.**

- **The gate stays: 0.59 on the best dense cosine, unchanged.** Not
  because it discriminates — it does not, and D13's honesty about that
  stands — but because removing it measurably loses deterministic
  refusals that generation does not reliably replace, and costs nothing.
- **Its claim is restated once more, downward:** a deterministic
  far-band refusal, nothing finer. The scores contain topicality only.
- **The OR-gate is rejected**, closing the question M10 parked: +2
  catches on the widened sample (21 vs 19), bought with a second tuned
  threshold at zero margin on no holdout.
- **D13's cross-encoder hypothesis is closed, negative.** Measured by
  M10 at n=10 and re-measured here at n=36: reranker-gating is not
  better than the dense cosine (16 vs 19 at zero false refusals), and
  the failure is structural, not statistical.
- **Score-threshold redesigns are a dead end and no further ones should
  be measured.** The open frontier is the cross-regime class (N5): q36,
  q49, and now q35 are answered from the wrong law by a pipeline whose
  every check passes. Anything that closes it must operate on regime
  identity — which acts the question names versus which acts the corpus
  holds — not on retrieval scores. Designing that is deliberately out of
  scope for an audit; it is the first question of whatever milestone
  precedes a fourth instrument.
- **The defect-class inventory is a document of its own:**
  [defect-classes.md](defect-classes.md). Twenty-four classes, seven
  with no mechanical coverage, two of those previously unrecorded —
  index staleness against the committed chunks (X1) and quote-to-
  citation binding (N4). Cheap closures are recorded there; building
  them belongs to a milestone, not an audit.

**Cost accepted.** Unchanged from D13, now with numbers on the widened
sample: the gate catches 16 of 36 audit negatives, the generator refuses
some of the rest nondeterministically, and the extreme-near band is
answered wrongly with verified citations. The README's limitations
section already says this; the inventory now says it per class.

**Trigger to revisit:** unchanged from D13 for the floor. For the
mechanism: a fourth instrument, or building the N5 countermeasure —
whichever comes first, and the audit's position is that N5 comes first.

## D15 — Closing two blind spots: the index can be stale, and a real quote can carry the wrong id

**Status:** decided 2026-08-19, during M12, implementing the two cheap
closures D14 recorded and deliberately did not build. Both are defect
classes the audit *discovered* rather than inherited — nobody had
accepted them, because nobody had noticed them.

**Context.** D14's inventory found seven classes with no mechanical
coverage. Five were already known and accepted in writing. Two were not:

- **X1, index staleness.** `index/` is Class C — gitignored,
  rebuildable, no backup (D0). Correct classification, with an
  unwritten consequence: nothing tied the built index to the chunk
  files in git. `rerun-identical.sh` checks the converter and chunker
  against the committed corpus and never opens the index.
- **N4, quote-to-citation binding.** `verify()` asked whether *some*
  retrieved chunk held a quoted span; the cited-id check asked whether
  the ids named retrieved chunks. Neither asked whether *the chunk the
  answer pointed at* held the quote.

**Why X1 is the more serious of the two, and why it was invisible.**
A stale index is self-consistent. The verifier matches quotes against
the bodies the **index** served, so an index built from superseded
chunks verifies its own answers perfectly; the eval grades ids that
resolve — in the stale table; every check passes and the whole
disagrees with the repository. Every other guarantee in this pipeline
silently assumed a property nothing established.

**Decision — X1: the build stamps its provenance, and a check compares
it.** A successful build writes `index/source-manifest.json`: the
SHA-256 of each of the six chunk files it read, plus the embedder name
and dimension. `tests/index-current.py` re-hashes the committed files
and compares.

- **The manifest lives inside `index/`** and is therefore Class C with
  everything else there. It describes the derived artifact, not the
  corpus, so committing it would put a hash of the corpus in two places
  and create exactly the two-owners-one-fact drift this project treats
  as a defect.
- **Removed before a rebuild, written only after the smoke test
  passes.** A build that fails or is interrupted leaves the index
  *unvouched* rather than vouched-for by a stale record.
- **Three exit codes, because there are three states:** 2 = no index or
  no manifest, nothing to compare; 1 = a manifest exists and disagrees;
  0 = agrees. A check that answers "no" the same way for "you have not
  built it yet" and "what you built disagrees with git" trains people
  to ignore it — the same distinction `probe-check.sh` makes about
  permission-denied versus file-not-found.
- **The embedder is compared alongside the file hashes.** An index
  built by a different model is stale in the same way even when every
  chunk file matches, and the D13 floor is only meaningful against the
  vectors BGE-M3 produced.
- **`tests/index-probe.sh` demonstrates the control failing**, on
  `probe-check.sh`'s three-run structure: clean, doctored, clean again.
  It doctors the manifest rather than a committed chunk file — the same
  comparison either way, but the manifest is gitignored, so a probe that
  dies halfway leaves nothing in the corpus to clean up. Watched
  failing on all three paths before shipping: a one-byte append to a
  chunk file, a doctored hash, and a doctored embedder name.

**Decision — N4: the quote must be in the chunk the answer pointed at.**
`check_attribution()` pairs each quoted span with the first chunk id at
or after it (the grounding prompt's rule 2 puts the id after the quote)
and requires **that chunk to contain the span**.

- **Asked as containment in the cited chunk, not as agreement with
  `verify()`'s match.** Legal text repeats itself across chunks — a
  recital and its enacting article share phrasing — so the first body
  that happens to hold a span says nothing about which one the model
  meant. "Follow the citation and find the quote" is both the reader's
  question and immune to that ambiguity.
- **It fails the answer, like a fabricated id**, because the failure is
  the same from the reader's side: a citation that does not support the
  claim beside it.
- **Reported only for spans `verify()` accepted.** A span the model
  elided or bracket-adapted is in no chunk at all, so it fails an
  attribution test too — but that is the verifier's finding, already
  reported, and repeating it as a second defect would inflate this
  check with defects it did not find.
- **A span with no id after it is unattributed, not misattributed** —
  a weaker and different defect, reported as itself.

**Measured before shipping, and the number is zero.** Replaying the 61
answer texts captured during the D14 audit (51 eval + 10 probe) against
freshly retrieved sources: 307 quoted spans, 290 carrying an id, **10
attribution failures — every one of them the already-caught elision or
bracket-adaptation kind, and none a true misattribution.** The selftest
carries the case that separates the two checks: a span verbatim in
`art_15(4)` printed beside `[ai-act#art_9]`, where `verify()` passes and
attribution fails.

**So this check is a guard against an unexercised class, and says so.**
DeepSeek did not misattribute once in 290 opportunities. That is a
reason to ship the check cheaply and not to claim it found anything —
the class was real in the design and is currently not real in the
output. If it never fires, that is the honest result.

**The eval was deliberately NOT re-run.** Neither change touches
retrieval or generation, and the attribution clause is measured to fire
zero times on 61 real answers, so the committed report's numbers stand
as of their date. A re-run would replace one dated number with another
and — per the audit's own variance finding, 4 of 51 verification flags
flipping across identical runs — the movement would be noise attributed
to this milestone. The next deliberate re-run belongs to whatever
changes retrieval or generation.

**The README's claim was corrected.** It sold "three mechanical checks
standing between the model and a plausible fabrication". The three are
real, and *standing between* overstates them: D14 found seven classes
no check sees. The sentence now says the checks are load-bearing and
not a barrier, and points at the inventory.

**Cost accepted.** The manifest is one more file a build writes, and a
rebuild is now required after any chunk change before the checks pass —
which is the point, but it does mean a chunker change is a two-step
operation. `index-current.py` compares against the working tree, not
against HEAD: it answers "does the index serve what you would query",
which is the useful question and not quite the same as "what is
committed".

**Trigger to revisit:** N4 firing on a real answer — the first one is
worth reading closely, because a model that misattributes once will do
it in patterns. For X1, a second consumer of the index (the voice
project, D1) would want the manifest read at query time rather than by
a standing check.

## D16 — N5: the regime pre-flight, adopted narrowly, and what the measurement cost the premise

**Status:** decided 2026-08-19, during M13, the design session D14 named
as the next question. **Design and measurement only — deliberately not
implemented**, for the reason in "What happens next" below.

The predictions were pre-registered before each run and are committed
unedited at [n5-preregistration.md](n5-preregistration.md), including
the three that were falsified; this entry owns the decision and the
results. Raw artifacts (run scripts, JSON output, the 23-question
hard-class set) stay in `/mnt/d/.staging/n5-*` as diagnostics and are
not folded into the graded eval.

**Context.** D14 recorded N5 — a question about a regime the corpus does
not hold, answered fluently out of an adjacent one — as the highest-value
open problem, and constrained its solution: whatever closes it must
operate on **regime identity**, not on retrieval scores, because D14
closed the score-threshold direction on measurement.

**Discovery first, and it reframed the problem.** Reading the ten
`unanswerable` rows shows the failures and the successes splitting on a
single line: **whether the question names its own regime.**

| | outcome |
|---|---|
| q18 DORA, q20 ISO 42001, q34 ePrivacy, q51 ISO 22301 — act named | refused correctly |
| **q36 CRA, q49 CER, q35 Data Act — regime carried in a term of art** | **answered wrongly** |

The generator already handles a named act. The blind spot is regime
identity carried implicitly, in a term like "product with digital
elements", "critical entity" or "data processing service".

**The hypothesis, and why it inverts a standing rule.** The grounding
prompt forbids outside knowledge — correct for content, and the reason
this system does not fabricate. But regime identity is precisely what
parametric memory is good at and the corpus is bad at: any competent
model knows whose term "product with digital elements" is. **The
anti-fabrication rule is therefore the cause of the N5 blind spot**,
because it denies the pipeline the one faculty that resolves it. So
split the two questions: **world knowledge for "whose law is this?",
corpus only for "what does it say?"**

**The design.** A short call carrying **no documents**, asking the model
to name the instruments the question concerns; the reply is then matched
against the closed set the corpus holds. No overlap → refuse, without
ever sending the documents. It is a membership test rather than a
judgement because the corpus holds exactly three instruments — the same
move D11 made for citations, putting the claim where a check can reach
it.

**The methodological finding, which is the most transferable thing here.**
The 26 out-of-corpus questions written during the M11 audit were treated
as a holdout. **They are not a holdout for this question.** Almost all of
them name their regime explicitly, because M11 authored them to score a
*gate* — a similarity threshold, where phrasing hardly matters. Measured:
the shipped pipeline refuses **25 of 26**. The sharpest evidence is a
same-regime pair — q36 asks about "a manufacturer of a product with
digital elements" and is answered wrongly; **n10 asks the Cyber
Resilience Act by name and is refused.** A test set inherited from a
different question can look like evidence and measure nothing. Building
`n5-hardclass.jsonl` — 15 out-of-corpus questions on the q36/q49 recipe
plus 8 in-corpus rows phrased the same way — was the session's real work.

**Measured.**

| set | shipped pipeline fails | pre-flight catches | combined fails |
|---|---|---|---|
| audit negatives, act named (26) | 1 | 1 of that 1 | **0/26** |
| eval `unanswerable` (10) | 2 (q36, q49) | 4/4 of the hard subset | **0/10** |
| **hard class, act unnamed (15)** | **5** | 10/15 | **2/15** |

False refusals: **0 out of 59 in-corpus questions** (51 across the eval
and probes, 8 in the hard class).

All four cases no score threshold can reach — q35, q36, q49, q50 — are
identified with the correct regime named: Data Act, Cyber Resilience
Act, Critical Entities Resilience Directive, Cybersecurity Act. q50
scored 0.7460 on the dense cosine, above thirty-four of the
forty-five answerable questions, and is not reachable by any floor at
all.

**Decision: adopt, positioned after the gate, with a narrow claim.**

- **It runs AFTER retrieval and the gate, not before.** The gate refuses
  12 of 26 negatives at zero API cost on local GPU, and D3's
  zero-recurring-spend constraint means free refusals are worth keeping.
  N5 lives specifically in questions that *survive* the gate — q36, q49
  and q50 all passed it comfortably — so the pre-flight only ever costs
  money where it can help, and remains far cheaper than the generation
  call it prevents.
- **It is a second gate, not a replacement.** It fails differently from
  everything else: the dense gate sees vocabulary distance, the
  grounding prompt sees whether documents bear on the question, and this
  sees whose law the question is. Three independent failure modes is the
  property this project has valued since D6.
- **GENERAL fails OPEN.** When the model cannot attribute a question to
  any instrument, that is not evidence it belongs to one the corpus
  lacks. Derived from D10's asymmetry — only a false refusal is silent —
  and **not** from these numbers: the strict reading scores better on
  negatives (32/36 vs 31/36) and was rejected anyway, because it
  falsely refuses q16, a `repealed` row whose refusal must come from
  generation (eval README). Pre-registration P4 disqualified it before
  the numbers existed.
- **Multi-label: any overlap passes.** A cross-instrument question
  genuinely belongs to two regimes; refusing because it *also* touches
  an absent act would break q47 and every `cross_instrument` row.

**The claim, stated as narrowly as the evidence supports.** The
pre-flight roughly halves the hard-class failure rate, 5/15 → 2/15, at
no measured cost in false refusals. **It does not solve N5.** Two
failures survive, and both are instructive: h04 names "DORA; NIS2
Directive" — correct regime named, and the any-overlap rule passes it —
and h15 asks about an "operator of essential services", which the model
attributes to NIS2 and the generator then answers, silently equating a
repealed Directive's term with its successor's. Its own answer text
writes `an operator of essential services (an "essential entity")`.
Nearly right for a practitioner; wrong as law.

**Predictions, and how they fared** (pre-registered before each run):

- **P1 falsified, informatively.** Predicted 6–12 of 26 audit negatives
  answered; actual 1, and 1 of 8 individually named rows. That failure
  is what exposed the holdout problem above.
- **P2 held.** ≥20/26 caught (22), ≤3/51 false refusals (2 strict,
  0 fail-open).
- **P3 falsified.** I predicted the cross-instrument rows would break
  first. Every one passed, including q47 and q48 where the model named
  both regimes. The weakness was elsewhere entirely: GENERAL on
  naturally-phrased questions.
- **P4 held and did real work** — it disqualified the higher-scoring
  policy before the scores were known.
- **P6 held** (5 of 15, bottom of the 5–10 range).
- **P7 failed.** Predicted 12–15 caught; actual 10. The design is weaker
  than I expected, and the entry says so rather than quietly widening
  the range.
- **P8 held, twice over,** and is the practical warning: both defects
  found in this session were **mine, in string matching, and each
  flipped a verdict.** `"GENERAL" in reply` also matches
  "General-Purpose AI Code of Practice" — that one alone flipped n17,
  the single shipped failure among the audit negatives, from caught to
  missed. The alias `gdpr` matches "UK GDPR", a different instrument, so
  a correct model answer was scored as a miss. Neither is a modelling
  problem. **A production version will fail at membership testing before
  it fails at regime identification**, and the alias table must be
  derived from the corpus's own `instrument` field with qualified names
  ("UK GDPR", "Swiss FADP") treated as distinct rather than as aliases.

**Cost accepted.** One extra model call per gate-passing question, small
because it carries no documents. A model judgement enters the critical
path — mitigated, not eliminated, by grading it against a closed set.
And the hard class was constructed adversarially, so 5/15 is the failure
rate under deliberate pressure, not in ordinary use; the named-regime
measurement (1/26) is much closer to typical.

**What happens next, and why not now.** Implementing this changes
refusal behaviour, which requires the eval re-run and a decision entry
of its own — D14's discipline, and the reason this entry stops at a
design. One experiment should come first, because it is cheap and would
otherwise cost a second eval run: **ask the pre-flight for the
instrument that DEFINES the terms the question uses, not every
instrument that is relevant.** Three of the five hard-class misses (h04,
h06, h08) name the correct out-of-corpus regime *alongside* an in-corpus
one, so a primary-instrument rule could recover them. It is not free:
q44's reply began "ENISA" — not an instrument at all — so a naive
first-named rule would refuse a good question. Measure it against these
same 23 rows plus the 51, and only then implement.

**Trigger to revisit:** a fourth instrument, which changes the closed
set and makes the alias table load-bearing rather than incidental; or
the primary-instrument experiment above returning a better rule.
