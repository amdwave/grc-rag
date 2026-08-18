# Chunk report — ai-act.recitals.md

`32024R1689` (recitals), split by `grc_rag.convert.chunk/1` at SPLIT=2000 chars, chapeau≤400.

Boundaries are the thing to read here. The dump beside this file carries every chunk in full, in document order.

## Counts

| what | n |
| --- | --- |
| chunks | 238 |
| … division | 58 |
| … recital | 180 |
| whole-unit chunks | 180 |
| split-at-marker chunks | 58 |

## Size

| stat | chars |
| --- | --- |
| smallest | 30 |
| median | 826 |
| p90 | 2,286 |
| largest | 4,443 |

Chunks over 4,000 characters (1) — kept whole because splitting them would cut inside a single provision:

- `ai-act#rct_53` 4,443 — Recital (53)

## Coverage

Each chunk body must appear in the source markdown verbatim, in document order, after the previous one ends. That proves nothing was dropped, duplicated or reordered — a bag-of-words check proves none of the three.

- PASS — every body verbatim and in order (238 chunks, 239,692 characters)
- PASS — no source paragraph left unclaimed (0)

## Anomalies

None.

## What this report does not tell you

- Whether the boundaries are the RIGHT ones. Coverage proves the text survived; only reading the dump says whether a chunk answers a question on its own.
- Nothing about retrieval. A chunk can be perfectly bounded and still never be retrieved; that is the eval's job in M4.

