# Conversion report — REGULATION (EU) 2024/1689 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 13 June 2024 laying down harmonised rules on artificial intelligence and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act) (Text with EEA relevance)

Source `02024R1689-20260727` (consolidated-html), converted by `grc_rag.convert.eurlex_html/1`.
Raw file sha256 `dcf7d6c5ba9f6619f545759b9600b8f4…`, 853,875 bytes fetched 2026-08-17T23:45:23Z.

Read this by eye. In book2rag every real conversion bug was invisible in the totals and obvious on sight.

## Counts

| what | n |
| --- | --- |
| chapters | 13 |
| sections | 16 |
| articles | 119 |
| annexes | 14 |
| tables rendered | 6 |
| source footnotes | 11 |
| markdown lines | 1677 |
| characters emitted | 391,584 |

## Structure checks

- PASS — article numbering continuous (lettered insertions allowed)
- PASS — annexes in order
- PASS — numbered paragraphs never repeat or run backwards
- PASS — no article heading with no text under it

Numbering gaps, which a consolidation makes legitimately when a provision is repealed — read them, do not assume them:

- Article 10 — Data and data governance: 6 follows 4 (1 not present)
- Section A. List of Union harmonisation legislation based on : numbering starts at 2, not 1
- Section B. List of other Union harmonisation legislation: numbering starts at 13, not 1
- Section B — Information to be submitted by providers of high: 8 follows 6 (1 not present)

## Coverage — every character in the source body, accounted for

A count of what came out cannot see what was left behind. Each text node in the body is emitted or dropped by a named rule; anything else is unaccounted and fails the run.

| disposition | characters |
| --- | --- |
| emitted | 385,694 |
| dropped: modifiers-toc — the 'Amended by' / 'Corrected by' table of modifying acts | 583 |
| dropped: disclaimer — the 'no legal effect' disclaimer | 398 |
| dropped: amendment-marker — ▼B / ►M1◄ / ►C1◄ consolidation markers | 349 |
| dropped: script — <script>/<style> payloads | 120 |
| dropped: reference — the consolidation's running reference line | 38 |
| dropped: note-mark — footnote reference marks (oj-note-tag, or a superscript following an opening parenthesis) | 38 |
| **unaccounted** | **0** |

## Anomalies

- article 1: title ends with a stray quote - "Subject matter'". It is in EUR-Lex's own HTML and is kept verbatim; the corpus does not correct its source.

## What this report does not tell you

- Nothing here is order-sensitive. Text shredded into the wrong order leaves every count above unchanged; `tests/seqcheck-corpus.py` is the check that sees it.
- Formatting (italics, bold) is not preserved and is not counted as a loss. Content superscripts are kept inline as ^N; only footnote reference marks are dropped.

