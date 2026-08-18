# Chunk report — gdpr.md

`02016R0679-20160504` (enacting terms and annexes), split by `grc_rag.convert.chunk/1` at SPLIT=2000 chars, chapeau≤400.

Boundaries are the thing to read here. The dump beside this file carries every chunk in full, in document order.

## Counts

| what | n |
| --- | --- |
| chunks | 284 |
| … article | 282 |
| … division | 2 |
| whole-unit chunks | 71 |
| split-at-marker chunks | 213 |

## Size

| stat | chars |
| --- | --- |
| smallest | 88 |
| median | 416 |
| p90 | 1,390 |
| largest | 5,835 |

Chunks over 4,000 characters (2) — kept whole because splitting them would cut inside a single provision:

- `gdpr#art_70(1)` 5,835 — Article 70(1)
- `gdpr#art_47(2)` 4,047 — Article 47(2)

## Coverage

Each chunk body must appear in the source markdown verbatim, in document order, after the previous one ends. That proves nothing was dropped, duplicated or reordered — a bag-of-words check proves none of the three.

- PASS — every body verbatim and in order (284 chunks, 187,465 characters)
- PASS — no source paragraph left unclaimed (0)

## Anomalies

None.

## What this report does not tell you

- Whether the boundaries are the RIGHT ones. Coverage proves the text survived; only reading the dump says whether a chunk answers a question on its own.
- Nothing about retrieval. A chunk can be perfectly bounded and still never be retrieved; that is the eval's job in M4.

