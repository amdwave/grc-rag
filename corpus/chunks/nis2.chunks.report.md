# Chunk report — nis2.md

`02022L2555-20221227` (enacting terms and annexes), split by `grc_rag.convert.chunk/1` at SPLIT=2000 chars, chapeau≤400.

Boundaries are the thing to read here. The dump beside this file carries every chunk in full, in document order.

## Counts

| what | n |
| --- | --- |
| chunks | 214 |
| … annex | 3 |
| … article | 210 |
| … division | 1 |
| whole-unit chunks | 27 |
| split-at-marker chunks | 187 |

## Size

| stat | chars |
| --- | --- |
| smallest | 49 |
| median | 340 |
| p90 | 1,586 |
| largest | 12,759 |

Chunks over 4,000 characters (2) — kept whole because splitting them would cut inside a single provision:

- `nis2#anx_I` 12,759 — Annex I
- `nis2#anx_II` 4,308 — Annex II

## Coverage

Each chunk body must appear in the source markdown verbatim, in document order, after the previous one ends. That proves nothing was dropped, duplicated or reordered — a bag-of-words check proves none of the three.

- PASS — every body verbatim and in order (214 chunks, 139,945 characters)
- PASS — no source paragraph left unclaimed (0)

## Anomalies

None.

## What this report does not tell you

- Whether the boundaries are the RIGHT ones. Coverage proves the text survived; only reading the dump says whether a chunk answers a question on its own.
- Nothing about retrieval. A chunk can be perfectly bounded and still never be retrieved; that is the eval's job in M4.

