# grc-rag

RAG over regulatory primary sources — the actual text of the instruments,
answered with a citation that can be checked against the article.

Phase 1 is the EU AI Act only, end to end. Conventions, gates and the
dependency list are in [AGENTS.md](AGENTS.md); every design decision is
recorded in [docs/decisions.md](docs/decisions.md).

## Layout

    src/grc_rag/fetch/     network allowed; writes corpus/raw/ + manifests
    src/grc_rag/convert/   deterministic and offline; writes corpus/*.md
    src/grc_rag/query/     network allowed; reads the corpus (not built yet)
    tests/                 checks, independent of the pipeline they check
    corpus/                raw source, manifests, canonical markdown

Those three package directories are the three import buckets, and
`tests/check-imports.py` is what makes them a check instead of a claim.

## Running

Everything runs in WSL2/Ubuntu, under uv. No third-party dependencies:
fetch and convert are standard library only.

    uv sync
    uv run python tests/check-imports.py          # buckets hold
    bash tests/probe-check.sh                     # …and the check can fail

    # ingest — the AI Act, in two documents (decisions.md D4)
    uv run python -m grc_rag.fetch.eurlex --celex 32024R1689 \
        --consolidated --original --expect 02024R1689-20260727
    uv run python -m grc_rag.convert.eurlex_html \
        --raw corpus/raw/eu/ai-act/02024R1689-20260727.en.html \
        --part enacting --out corpus/eu/ai-act.md
    uv run python -m grc_rag.convert.eurlex_html \
        --raw corpus/raw/eu/ai-act/32024R1689.en.html \
        --part recitals --out corpus/eu/ai-act.recitals.md

    # verification
    bash tests/rerun-identical.sh                 # byte-identical reruns
    uv run python tests/seqcheck-corpus.py both   # order-sensitive

The conversion reports (`corpus/eu/*.report.md`) are meant to be read by
eye, not just exited on: they account for every character in the source
as emitted or dropped by a named rule.
