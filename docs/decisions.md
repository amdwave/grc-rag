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
