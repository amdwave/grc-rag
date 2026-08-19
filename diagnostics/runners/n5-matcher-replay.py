"""Replay every committed pre-flight reply through the PRODUCTION
matcher (engine.declared_regimes + is_general) and diff the verdicts
against the runner matcher that produced the measurements.

Why this exists: the runners matched by word-boundary SUBSTRING, and the
production matcher is exact-segment membership - deliberately stricter,
because D16's P8 recorded that "UK GDPR" substring-matching the alias
`gdpr` flipped a verdict. The M14 adoption decision rests on the runner
numbers, so the production matcher must reproduce those verdicts on the
same replies, and every difference must be an INTENDED one (a qualified
name now treated as distinct). An unintended flip here means the
implementation changed what was measured.

No API, no GPU - reads committed runs/ JSON only, like n5-analyse.py.

    uv run python diagnostics/runners/n5-matcher-replay.py
"""
import json
import sys

sys.path.insert(0, "src")

from grc_rag.query.engine import declared_regimes, is_general, regime_aliases

RUNS = "diagnostics/runs"
REGIMES = regime_aliases(["EU AI Act", "GDPR", "NIS2"])

# Differences the design REQUIRES: a jurisdiction-qualified name is not
# the instrument it qualifies, so the production matcher must refuse
# where the substring matcher passed. n07's reply is "UK GDPR" in both
# the D16 baseline and the M14 defining run, so it flips in both files -
# meaning the production pipeline catches 22/26 audit negatives where
# the runners measured 21/26. Keyed by (file, id).
INTENDED = {("n5-preflight.json", "n07"),
            ("n5-preflight-defining.json", "n07")}


def verdict(reply):
    hits = declared_regimes(reply, REGIMES)
    return "pass" if (hits or is_general(reply)) else "refuse"


rows = []
for fname, reply_key, verdict_of in (
        ("n5-preflight.json", "reply", None),
        ("n5-hardclass.json", "preflight_reply", None),
        ("n5-preflight-defining.json", "reply", None)):
    for r in json.load(open(f"{RUNS}/{fname}")):
        reply = r[reply_key]
        # The runner verdict, recomputed fail-open from the stored reply
        # with the runner's own substring rule - n5-preflight.json
        # stored the strict verdict, so stored fields are not
        # comparable across files; the reply is.
        import re
        low = reply.lower()
        runner_hits = sorted(
            n for n, al in REGIMES.items()
            if any(re.search(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])",
                             low) for a in al))
        runner = "pass" if (runner_hits or is_general(reply)) else "refuse"
        rows.append((fname, r["id"], runner, verdict(reply), reply))

flips = [(f, i, a, b, rep) for f, i, a, b, rep in rows if a != b]
unintended = [x for x in flips if (x[0], x[1]) not in INTENDED]

print(f"replayed {len(rows)} committed replies through the production matcher")
print(f"verdict flips vs the runner matcher: {len(flips)}")
for f, i, a, b, rep in flips:
    tag = "intended" if (f, i) in INTENDED else "UNINTENDED"
    print(f"  {tag:<10} {f:<28} {i:<5} {a} -> {b}   {rep[:55]}")

if unintended:
    print("\nFAIL: the production matcher does not reproduce the measured "
          "verdicts; the M14 numbers do not transfer to it.")
    sys.exit(1)
print("\nok: every difference is the intended qualified-name rule; the "
      "measured numbers transfer to the production matcher.")
