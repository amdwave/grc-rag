#!/usr/bin/env bash
# Does the converter really produce byte-identical output on a rerun?
#
#     bash tests/rerun-identical.sh      # exit 0 = yes
#
# The import check fences the clock and the entropy modules out of the
# convert bucket, but that is a fence, not a proof: a dict iterated in
# hash order or a set printed unsorted would pass the import check and
# still churn the corpus diff on every run. This runs the converter twice
# into a scratch directory and compares SHA-256 of every file it writes -
# markdown and report both. It never touches the committed corpus.
set -u
cd "$(dirname "$0")/.." || exit 2
PY="${PY:-python3}"
TMP="${TMPDIR:-/mnt/d/.staging}/grc-rag-rerun"
rm -rf "$TMP"; mkdir -p "$TMP/a" "$TMP/b" || exit 2
trap 'rm -rf "$TMP"' EXIT

RAW_ENACTING=corpus/raw/eu/ai-act/02024R1689-20260727.en.html
RAW_RECITALS=corpus/raw/eu/ai-act/32024R1689.en.html

run_into() {
    local d=$1
    "$PY" -m grc_rag.convert.eurlex_html --raw "$RAW_ENACTING" \
        --part enacting --out "$d/ai-act.md" >/dev/null || return 1
    "$PY" -m grc_rag.convert.eurlex_html --raw "$RAW_RECITALS" \
        --part recitals --out "$d/ai-act.recitals.md" >/dev/null || return 1
    # Chunking is in the same bucket and makes the same promise. It runs
    # from the COMMITTED markdown, not from the fresh conversion above,
    # so a difference here is the chunker's and not an echo of the
    # converter's.
    "$PY" -m grc_rag.convert.chunk --doc corpus/eu/ai-act.md \
        --out-dir "$d" >/dev/null || return 1
    "$PY" -m grc_rag.convert.chunk --doc corpus/eu/ai-act.recitals.md \
        --out-dir "$d" >/dev/null || return 1
}

run_into "$TMP/a" || { echo "rerun: first conversion failed"; exit 2; }
run_into "$TMP/b" || { echo "rerun: second conversion failed"; exit 2; }

fail=0
for f in ai-act.md ai-act.report.md ai-act.recitals.md \
         ai-act.recitals.report.md \
         ai-act.chunks.jsonl ai-act.chunks.txt ai-act.chunks.report.md \
         ai-act.recitals.chunks.jsonl ai-act.recitals.chunks.txt \
         ai-act.recitals.chunks.report.md; do
    a=$(sha256sum "$TMP/a/$f" | cut -d' ' -f1)
    b=$(sha256sum "$TMP/b/$f" | cut -d' ' -f1)
    if [ "$a" = "$b" ]; then
        echo "  same   ${a:0:16}…  $f"
    else
        echo "  DIFFER $f"
        diff "$TMP/a/$f" "$TMP/b/$f" | head -10
        fail=1
    fi
done

# Same run, but also against what is committed: a converter that is
# deterministic and no longer matches the corpus in git means the corpus
# was not regenerated after the last code change.
echo
for f in ai-act.md ai-act.recitals.md; do
    if cmp -s "$TMP/a/$f" "corpus/eu/$f"; then
        echo "  corpus/eu/$f matches a fresh conversion"
    else
        echo "  STALE: corpus/eu/$f differs from a fresh conversion -"
        echo "         regenerate it and commit the diff"
        fail=1
    fi
done
for f in ai-act.chunks.jsonl ai-act.recitals.chunks.jsonl; do
    if cmp -s "$TMP/a/$f" "corpus/chunks/$f"; then
        echo "  corpus/chunks/$f matches a fresh chunking"
    else
        echo "  STALE: corpus/chunks/$f differs from a fresh chunking -"
        echo "         regenerate it and commit the diff"
        fail=1
    fi
done

[ "$fail" -eq 0 ] && echo && echo "OK - byte-identical reruns, corpus current"
exit "$fail"
