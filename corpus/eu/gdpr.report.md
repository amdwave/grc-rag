# Conversion report — REGULATION (EU) 2016/679 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 27 April 2016 on the protection of natural persons with regard to the processing of personal data and on the free movement of such data, and repealing Directive 95/46/EC (General Data Protection Regulation) (Text with EEA relevance)

Source `02016R0679-20160504` (consolidated-html), converted by `grc_rag.convert.eurlex_html/1`.
Raw file sha256 `a681ff22f32f125749af6e9694722436…`, 462,324 bytes fetched 2026-08-18T13:44:42Z.

Read this by eye. In book2rag every real conversion bug was invisible in the totals and obvious on sight.

## Counts

| what | n |
| --- | --- |
| chapters | 11 |
| sections | 15 |
| articles | 99 |
| tables rendered | 0 |
| source footnotes | 3 |
| markdown lines | 917 |
| characters emitted | 194,527 |

## Structure checks

- PASS — article numbering continuous (lettered insertions allowed)
- PASS — numbered paragraphs never repeat or run backwards
- PASS — no article heading with no text under it

Numbering gaps, which a consolidation makes legitimately when a provision is repealed — read them, do not assume them:

- none

## Coverage — every character in the source body, accounted for

A count of what came out cannot see what was left behind. Each text node in the body is emitted or dropped by a named rule; anything else is unaccounted and fails the run.

| disposition | characters |
| --- | --- |
| emitted | 190,617 |
| dropped: modifiers-toc — the 'Amended by' / 'Corrected by' table of modifying acts | 401 |
| dropped: disclaimer — the 'no legal effect' disclaimer | 398 |
| dropped: amendment-marker — ▼B / ►M1◄ / ►C1◄ consolidation markers | 57 |
| dropped: reference — the consolidation's running reference line | 38 |
| dropped: note-mark — footnote reference marks (oj-note-tag, or a superscript following an opening parenthesis) | 6 |
| **unaccounted** | **0** |

## Anomalies

None.

## What this report does not tell you

- Nothing here is order-sensitive. Text shredded into the wrong order leaves every count above unchanged; `tests/seqcheck-corpus.py` is the check that sees it.
- Formatting (italics, bold) is not preserved and is not counted as a loss. Content superscripts are kept inline as ^N; only footnote reference marks are dropped.

