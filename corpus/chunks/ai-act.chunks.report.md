# Chunk report — ai-act.md

`02024R1689-20260727` (enacting terms and annexes), split by `grc_rag.convert.chunk/1` at SPLIT=2000 chars, chapeau≤400.

Boundaries are the thing to read here. The dump beside this file carries every chunk in full, in document order.

## Counts

| what | n |
| --- | --- |
| chunks | 633 |
| … annex | 39 |
| … annex-section | 26 |
| … article | 566 |
| … division | 2 |
| whole-unit chunks | 69 |
| split-at-marker chunks | 564 |

## Size

| stat | chars |
| --- | --- |
| smallest | 69 |
| median | 404 |
| p90 | 1,265 |
| largest | 5,485 |

Chunks over 4,000 characters (4) — kept whole because splitting them would cut inside a single provision:

- `ai-act#art_5(1)` 5,485 — Article 5(1)
- `ai-act#footnotes` 4,623 — —
- `ai-act#anx_VII(4)` 4,547 — Annex VII(4)
- `ai-act#art_60(4)` 4,526 — Article 60(4)

## Coverage

Each chunk body must appear in the source markdown verbatim, in document order, after the previous one ends. That proves nothing was dropped, duplicated or reordered — a bag-of-words check proves none of the three.

- PASS — every body verbatim and in order (633 chunks, 380,379 characters)
- PASS — no source paragraph left unclaimed (0)

## Anomalies

None.

## What this report does not tell you

- Whether the boundaries are the RIGHT ones. Coverage proves the text survived; only reading the dump says whether a chunk answers a question on its own.
- Nothing about retrieval. A chunk can be perfectly bounded and still never be retrieved; that is the eval's job in M4.

