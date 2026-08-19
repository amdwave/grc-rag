# Chunk report — nis2.recitals.md

`32022L2555` (recitals), split by `grc_rag.convert.chunk/1` at SPLIT=2000 chars, chapeau≤400.

Boundaries are the thing to read here. The dump beside this file carries every chunk in full, in document order.

## Counts

| what | n |
| --- | --- |
| chunks | 176 |
| … division | 32 |
| … recital | 144 |
| whole-unit chunks | 144 |
| split-at-marker chunks | 32 |

## Size

| stat | chars |
| --- | --- |
| smallest | 31 |
| median | 630 |
| p90 | 1,444 |
| largest | 2,884 |

Chunks over 4,000 characters (0) — kept whole because splitting them would cut inside a single provision:

- none

## Coverage

Each chunk body must appear in the source markdown verbatim, in document order, after the previous one ends. That proves nothing was dropped, duplicated or reordered — a bag-of-words check proves none of the three.

- PASS — every body verbatim and in order (176 chunks, 134,207 characters)
- PASS — no source paragraph left unclaimed (0)

## Anomalies

None.

## What this report does not tell you

- Whether the boundaries are the RIGHT ones. Coverage proves the text survived; only reading the dump says whether a chunk answers a question on its own.
- Nothing about retrieval. A chunk can be perfectly bounded and still never be retrieved; that is the eval's job in M4.

