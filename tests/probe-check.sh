#!/usr/bin/env bash
# Does the import check actually fail on an unclassified module?
#
#     bash tests/probe-check.sh        # exit 0 = the control works
#
# Asserting that it would is not evidence. This drops a real module into
# the package that is named in none of the three bucket lists, runs the
# check, and requires it to fail FOR THAT REASON - the run before and the
# run after must both pass, so a check that was broken all along cannot
# be mistaken for a check that caught the probe.
set -u
cd "$(dirname "$0")/.." || exit 2
PY="${PY:-python3}"
PROBE=src/grc_rag/convert/_probe_unclassified.py
WANT="unclassified module(s): convert/_probe_unclassified.py"

if [ -e "$PROBE" ]; then
    echo "probe: $PROBE already exists - refusing to overwrite it"; exit 2
fi
trap 'rm -f "$PROBE"' EXIT

"$PY" tests/check-imports.py >/dev/null 2>&1
before=$?
if [ "$before" -ne 0 ]; then
    echo "probe: the check already fails without the probe (exit $before)."
    echo "       Fix that first - this test cannot attribute anything."
    "$PY" tests/check-imports.py
    exit 2
fi

printf '%s\n' \
    '"""Written by tests/probe-check.sh and removed by it. In no bucket."""' \
    'import urllib.request  # noqa: F401' > "$PROBE"

out=$("$PY" tests/check-imports.py 2>&1)
rc=$?
rm -f "$PROBE"

after=0
"$PY" tests/check-imports.py >/dev/null 2>&1 || after=$?

echo "$out" | sed -n '/^FAIL/,$p'
echo
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -qF "$WANT" \
   && [ "$after" -eq 0 ]; then
    echo "probe OK - clean run 0, probe run 1 naming the probe, clean again 0"
    exit 0
fi
echo "probe FAILED - clean $before, with probe $rc (wanted 1), after $after"
printf '%s' "$out" | grep -qF "$WANT" || echo "  the failure did not name the probe: expected \"$WANT\""
exit 1
