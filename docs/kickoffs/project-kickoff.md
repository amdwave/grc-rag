# Kickoff: regulatory-source RAG for GRC work

## Who I am and why this exists

I'm an IT professional based in Costa Rica working toward senior EU security/compliance roles (Security/Compliance Engineer, AI Governance / Information Security Officer). I also produce GRC content under the "GRC for Engineers" brand. I run a personal IT lab — WSL2/Ubuntu on a workstation laptop with an RTX 3500 Ada (12GB VRAM) and 128GB RAM. I'm a strong visual learner.

This project is a RAG system over **regulatory primary sources** — the actual text of the instruments I need to interrogate for GRC work and content. Purpose: ask "what does Article 15 of the AI Act require for high-risk systems?" and get an answer grounded in the real article, with a citation I can verify. This is a portfolio project as much as a tool: the design decisions should be ones I can explain in an interview.

## Where this lives — decided pre-kickoff

- Repo: `D:\projects\grc-rag\` (from WSL: `/mnt/d/projects/grc-rag`). The session roots here. House rules load automatically from `D:\AGENTS.md` via the ancestor `CLAUDE.md`; follow them, including session close (commit + push).
- If Decision 2 splits the corpus into its own repo, that repo is `D:\projects\grc-corpus\`.
- Backup classes (storage-strategy §3.3): code, docs, markdown corpus, eval set = Class A, git-tracked. `index/` (LanceDB files, embeddings) = Class C — gitignored, no backup, rebuildable from the corpus. Raw fetched source + fetch manifest = **committed**: a consolidated version fetched today is not re-downloadable later once the Commission consolidates again, so it fails the cheap-rebuild test.
- Model weights (BGE-M3, reranker, any local LLM) live in the Hugging Face cache on WSL ext4 — never in the repo, never on D:\.
- Storage-strategy bookkeeping is already done (v6.23, 2026-08-17): folder in the §4 tree, `index\` in the §3.3 map, preventive exclude lines in both backup exclude files. If Decision 2 creates `grc-corpus\`, that folder needs its own storage-strategy edit — surface it at that session's close.

## Working style — project-specific rules

(House habits — bluntness, push-back, recommendations-not-option-lists, verification — are already loaded from `D:\AGENTS.md`. These are additions.)

- Don't scaffold the whole system up front. One instrument end to end, then generalize.
- No LlamaIndex, LangChain, or similar frameworks. Plain Python. The point is understanding the internals; frameworks hide exactly what I'm trying to learn. Small focused libraries are fine.
- Ask before adding any dependency, service, or piece of infrastructure that wasn't discussed.
- Everything executes in WSL2/Ubuntu. Python on this machine is WSL-only.
- Package management: uv.
- Code lives in three buckets, enforced by a small import check that runs before anything else: **fetch** may use the network; **convert/chunk** is deterministic and offline (no network imports, byte-identical reruns); **query** may use the network. A new module that fits no bucket fails the check — classify it, don't widen the allowlist. (book2rag's `tests/check-imports.py` pattern; it replaced a proposed two-repo split there, and it's an interview-explainable control.)

## Phase 0 — settle three decisions before writing any code

Interview me on these one at a time. Argue for a position, let me push back, then record the outcome in `docs/decisions.md` (short ADR-style entries, one per decision — including the pre-kickoff decisions above, marked as such). Don't move on until each is settled.

### Decision 1: CLI tool vs HTTP service

Options: (a) a CLI I run in a terminal, or (b) an HTTP service (OpenAI-compatible or custom) I can later point other interfaces at — I have a separate voice-in/voice-out RAG project that could eventually consume this. Consider: how much complexity a service adds now, whether a CLI-first design with a clean internal API can grow into a service later, and what actually gets used day to day.

### Decision 2: single repo vs separate content repo — and visibility

The markdown corpus is a first-class artifact — when the Commission amends an article, `git diff` on the markdown should show exactly what changed. Options: (a) code and corpus in one repo, or (b) a separate versioned content repo the code consumes.

This decision is entangled with **visibility and licensing**: as a portfolio project, the code repo should be public from day one. EUR-Lex and NIST content is redistributable; CIS Controls text likely is not. So either the corpus repo is private, or CIS text stays out of every repo, or the split isolates the problem. Decide the shape that keeps the code public without a licensing landmine.

Also consider: corpus size over time, whether other tools (the voice project, GRC-for-Engineers content work) consume the corpus directly, and CI/versioning ergonomics.

### Decision 3: local vs cloud, decided per layer

Two layers, very different reversibility:

- **Generation model** is trivially swappable — an API call behind an interface. Local (Qwen3 14B Q4_K_M via llama-server) vs a frontier cloud model. Cloud will be meaningfully better at nuanced reasoning over retrieved chunks. The corpus is 100% public documents, so there's no confidentiality argument for on-prem here.
- **Embedding model** is effectively permanent — vectors are only comparable within one model, so switching means re-embedding the whole corpus, and cloud embedding models get deprecated on someone else's schedule. A pinned local model file can't be.

My lean: local embeddings, cloud generation behind an OpenAI-compatible client so backends swap freely. Challenge that if you disagree. Also decide: which cloud provider(s), and how API keys are handled (env / .env gitignored — never committed, never echoed; house rule).

## Corpus — the target set

**EU instruments** (source from EUR-Lex; use the HTML/XHTML representation, not PDF — article and recital boundaries are already in the DOM. Prefer the consolidated version where one exists. **English (ENG) only for v1**; every chunk carries a `language` field so multilingual is purely additive later):

- EU AI Act — Regulation (EU) 2024/1689, CELEX 32024R1689
- GDPR — Regulation (EU) 2016/679, CELEX 32016R0679
- NIS2 — Directive (EU) 2022/2555, CELEX 32022L2555
- DORA — Regulation (EU) 2022/2554, CELEX 32022R2554

**NIST** (structured formats, not PDF, wherever they exist):

- SP 800-53 Rev. 5 — OSCAL catalog (usnistgov/oscal-content on GitHub)
- SP 800-171 Rev. 3 — OSCAL where available
- CSF 2.0 — structured export via NIST's CPRT tool (JSON/CSV)

**Other:**

- CIS Controls v8.x — licensing handled per Decision 2
- ENISA guidance — mostly PDFs; this is where a document parser (Docling) is actually justified

Verify all URLs and identifiers at fetch time — don't trust these from memory.

## Architecture — decisions already made

Settled unless you have a strong objection; if you do, raise it before building.

**Ingest (runs once per document, output committed):**

1. Fetch — one fetcher per source family (EUR-Lex HTML, NIST OSCAL/CPRT, generic PDF). Raw source saved with a fetch manifest (URL, timestamp, checksum) and committed.
2. Convert — to clean markdown. Custom parser for EUR-Lex HTML, OSCAL loader for NIST, Docling only for leftover PDFs. Markdown is the canonical corpus; it's what gets versioned and diffed. Each conversion writes a per-document verification report beside the markdown (counts, structure checks, anomalies) — read it by eye; in book2rag every real bug was invisible in totals and obvious on sight. Reports must not be matchable by corpus globs (`*.report.md` matches `*.md`) — consumers name or filter explicitly, never glob.
3. Chunk — on **structural boundaries**, not fixed token windows:
   - Articles are the unit. Long articles split at numbered paragraphs, parent path prepended so the chunk knows where it lives (`AI Act › Chapter III › Article 15 › (4)`).
   - Recitals: one chunk per recital (they're short); parent path `AI Act › Recital (47)`.
   - Annexes: split at the annex's own numbered sections/points, same parent-path rule — Annex III alone is too big to be one chunk.
   - Every chunk carries: instrument, article/section id, CELEX or NIST identifier, source URL, version date, language.
4. Index — dense + lexical into LanceDB.

**Query (runs per question):**

1. Hybrid retrieval, rank-fused (RRF) — dense embeddings + a lexical leg, always both. Pure vector search fails on exact identifiers ("Article 15" retrieves 14 and 16 too); the lexical leg catches the literal token.
2. Rerank — cross-encoder takes top ~20 candidates down to ~5.
3. Relevance gate — **before any model call**. Below a tuned similarity floor, print a fixed refusal string and make no generation request at all. Two rules from book2rag, both earned: the gate reads the **dense score alone**, never the fused or BM25 score (BM25 scores high on any question sharing common words — the opposite of what a refusal test needs); and **an untuned floor is decoration** — it's only meaningful against the model that produced the vectors, so tune it with the eval's unanswerable questions (score in-corpus vs out-of-corpus questions, see where the floor sits) before trusting a single refusal.
4. Generate — answer strictly from retrieved chunks, every claim cited to a chunk id, temperature 0.
5. Verify — mechanical, post-generation: every quoted span (≥ ~20 chars) must appear verbatim in a **retrieved** chunk, not merely somewhere in the corpus — that stronger check validates the citation for free. Implementation traps already paid for in book2rag: fold smart punctuation to ASCII *before* quote extraction; strip our own markup markers from both sides before matching; extract quotes segment-wise, not by naive regex pairing (legal text nests quotes). Verification failure flags the quote and exits non-zero.
6. Citation rendering — **anchor honesty**: a citation never claims more precision than the chunk's anchor supports. Render "Article 15(4)" only when the chunk is anchored at paragraph level; otherwise "Article 15". A too-precise citation is the *system's* fabrication, not the model's.

Reference implementation for 3–5: `D:\projects\book2rag\rag_query.py` and `docs/yogananda-rag-blueprint.md` §5–§7. Read it, don't fork it — different stack, same guarantees.

**Stack:**

- Embeddings: BGE-M3 (MIT, 8k context, multilingual — matters because EU instruments exist in 24 languages and I work across EN/ES).
- Lexical leg: **verify at build time** whether LanceDB can index BGE-M3's sparse output. If not — likely — use LanceDB's built-in BM25 full-text search as the lexical leg. Do not hand-roll a sparse index either way.
- Reranker: bge-reranker-v2-m3.
- Vector store: LanceDB (embedded, file-based, no server). No Qdrant/pgvector for a solo lab.
- Generation: OpenAI-compatible client interface; concrete backend per Decision 3.
- Python, uv.

VRAM note: if generation ends up local, Qwen3 14B Q4 (~9GB) + BGE-M3 (~1.2GB) fits in 12GB with modest context; otherwise embed as a batch job before loading the LLM.

## Phase 1 — one instrument, end to end

The AI Act only. Nothing else until this round-trips cleanly. Two hard gates where you stop and wait for me:

1. Fetch the AI Act HTML from EUR-Lex; raw source + manifest committed.
2. Convert to markdown with article/recital/annex structure preserved. The conversion check must include an **order-sensitive** comparison against an independent extraction — every bag-of-words check (token counts, recall/precision totals) is blind to content shredded into the wrong order, and book2rag passed three such checks on a corrupted book. `D:\ai\extractors\seqcheck.py` exists for exactly this.
   **⛔ Gate A: show me representative samples (an article with numbered paragraphs, a recital, an annex section) and wait for my sign-off before chunking. Conversion quality is where these projects quietly fail.**
3. Chunk per the rules above; dump chunks to a readable file so I can eyeball boundaries.
4. Embed and index.
5. Draft a **20-question eval set** — questions with known-correct article answers, stored as data. Include adversarial ones: questions about neighboring articles, questions the corpus can't answer (refusal expected).
   **⛔ Gate B: I review and approve the eval set before anything is tuned against it — otherwise the same model authors the answer key and grades itself.**
6. Wire the query path; run the eval. Report retrieval hit rate at k=5, citation correctness (right article), and refusal correctness on the unanswerable questions. Tune the relevance-gate floor from the eval's in-corpus vs out-of-corpus score distributions and record the chosen floor with its evidence. Also run a **sentinel test**: plant a distinctive nonsense string in one chunk, ask a question that retrieves it, confirm it comes back in the answer — context overflow truncates silently and the answers still look fine. Re-run it after any backend or model change.
7. Iterate on chunking/retrieval until the eval is solid.

Then, and only then, generalize fetch/convert for GDPR, NIS2, DORA — same code, different identifiers.

## Milestones — not one session

Work in order; ending a session at a gate is success, not shortfall. Commit + push at every session close.

- **M1** — Phase 0 decisions recorded; repo scaffold matching them (including repo `AGENTS.md` + `CLAUDE.md` shim per house convention; don't over-build).
- **M2** — AI Act fetch → markdown, through Gate A.
- **M3** — chunks + index.
- **M4** — eval set through Gate B; query path; eval report.
- **M5** — `README.md` describing the architecture for an interviewer + one Mermaid pipeline diagram (I archive diagrams as PNG/SVG in Obsidian/GitHub).

Start with Decision 1.
