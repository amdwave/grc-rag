# Conversion report — REGULATION (EU) 2016/679 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 27 April 2016 on the protection of natural persons with regard to the processing of personal data and on the free movement of such data, and repealing Directive 95/46/EC (General Data Protection Regulation) (Text with EEA relevance)

Source `32016R0679` (oj-html), converted by `grc_rag.convert.eurlex_html/1`.
Raw file sha256 `962539af03738bf552319ff4ce42d69e…`, 806,864 bytes fetched 2026-08-18T13:44:43Z.

Read this by eye. In book2rag every real conversion bug was invisible in the totals and obvious on sight.

## Counts

| what | n |
| --- | --- |
| recitals | 173 |
| tables rendered | 0 |
| source footnotes | 21 |
| markdown lines | 368 |
| characters emitted | 161,394 |

## Structure checks

- PASS — recital numbering continuous
- PASS — numbered paragraphs never repeat or run backwards
- PASS — no article heading with no text under it

Numbering gaps, which a consolidation makes legitimately when a provision is repealed — read them, do not assume them:

- none

## Coverage — every character in the source body, accounted for

A count of what came out cannot see what was left behind. Each text node in the body is emitted or dropped by a named rule; anything else is unaccounted and fails the run.

| disposition | characters |
| --- | --- |
| emitted | 157,921 |
| dropped: not-this-part — structure belonging to the other output file | 191,372 |
| dropped: oj-masthead — the Official Journal masthead and issue line | 55 |
| dropped: note-mark — footnote reference marks (oj-note-tag, or a superscript following an opening parenthesis) | 24 |
| dropped: reference — the consolidation's running reference line | 0 |
| **unaccounted** | **0** |

## Anomalies

None.

## What this report does not tell you

- Nothing here is order-sensitive. Text shredded into the wrong order leaves every count above unchanged; `tests/seqcheck-corpus.py` is the check that sees it.
- Formatting (italics, bold) is not preserved and is not counted as a loss. Content superscripts are kept inline as ^N; only footnote reference marks are dropped.

