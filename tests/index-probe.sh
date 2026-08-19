#!/usr/bin/env bash
# Does the index-currency check actually fail on a stale index?
#
#     bash tests/index-probe.sh        # exit 0 = the control works
#
# Same argument as probe-check.sh: a control nobody has watched fail is a
# control nobody has tested, and X1 is precisely the class where a check
# that silently never fires would be indistinguishable from a healthy
# pipeline. Three runs - clean, doctored, clean again - so a check that
# was broken all along cannot be mistaken for one that caught the probe.
#
# It doctors the MANIFEST rather than a committed chunk file. Same
# comparison either way (a hash disagrees), but the manifest is Class C
# and gitignored, so a probe that dies halfway leaves nothing in the
# corpus to clean up. Restoring it needs no rebuild.
set -u
cd "$(dirname "$0")/.." || exit 2
PY="${PY:-python3}"
MANIFEST=index/source-manifest.json
VICTIM=corpus/chunks/nis2.chunks.jsonl
TMP="${TMPDIR:-/mnt/d/.staging}/grc-rag-index-probe"

if [ ! -f "$MANIFEST" ]; then
    echo "probe: no $MANIFEST - build the index first:"
    echo "       uv run python -m grc_rag.query.index"
    exit 2
fi

"$PY" tests/index-current.py >/dev/null 2>&1
before=$?
if [ "$before" -ne 0 ]; then
    echo "probe: the check already fails without the probe (exit $before)."
    echo "       Fix that first - this test cannot attribute anything."
    "$PY" tests/index-current.py
    exit 2
fi

mkdir -p "$(dirname "$TMP")" || exit 2
cp "$MANIFEST" "$TMP" || exit 2
restore() { cp "$TMP" "$MANIFEST" 2>/dev/null; rm -f "$TMP"; }
trap restore EXIT

# One hash, changed. Not the file on disk: the point is to simulate an
# index built from chunks that are no longer what is committed.
"$PY" - "$MANIFEST" "$VICTIM" <<'EOF' || exit 2
import json, sys
path, victim = sys.argv[1], sys.argv[2]
m = json.load(open(path))
if victim not in m["chunk_files"]:
    sys.exit(f"probe: {victim} is not in the manifest")
m["chunk_files"][victim] = "0" * 64
json.dump(m, open(path, "w"), indent=1)
EOF

out=$("$PY" tests/index-current.py 2>&1)
rc=$?
restore
trap - EXIT

after=0
"$PY" tests/index-current.py >/dev/null 2>&1 || after=$?

echo "$out" | sed -n '/^STALE/,$p'
echo
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -qF "$VICTIM" \
   && [ "$after" -eq 0 ]; then
    echo "probe OK - clean run 0, doctored run 1 naming $VICTIM, clean again 0"
    exit 0
fi
echo "probe FAILED - clean $before, doctored $rc (wanted 1), after $after"
printf '%s' "$out" | grep -qF "$VICTIM" \
    || echo "  the failure did not name $VICTIM"
exit 1
