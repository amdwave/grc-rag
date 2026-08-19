"""N5 analysis: what the pre-flight buys, under both readings of GENERAL.

Two policies, and the choice between them is NOT made by whichever
scores better here — that would be the post-hoc fit D10 recorded as its
own weakness. It is derived from a decision that predates this
measurement: D10's asymmetry, that of the two errors only a false
refusal is silent.

  strict     refuse whenever the reply names no corpus instrument.
  fail-open  a reply of GENERAL means the model could not attribute the
             question to ANY instrument. That is not evidence it belongs
             to one the corpus lacks, so it passes and the existing
             mechanisms get their turn.

Reported both ways regardless, so the reader can see the size of what
the principle costs.

    python3 diagnostics/runners/n5-analyse.py
"""
import json

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

rows = json.load(open(f"{RUNS}/n5-preflight.json"))


def is_general(reply):
    """The GENERAL sentinel is the WHOLE reply, not a substring of it.

    Found the hard way: `"GENERAL" in reply` also matches
    "General-Purpose AI Code of Practice", which is a specific
    instrument name and the exact opposite of the sentinel's meaning.
    That single substring test flipped n17 - the one question the
    shipped pipeline answers wrongly - from caught to missed.
    """
    return reply.strip().upper().rstrip(".") == "GENERAL"


def verdict(r, fail_open):
    if r["declared"]:
        return "pass"
    if fail_open and is_general(r["reply"]):
        return "pass"
    return "refuse"


neg = [r for r in rows if r["truth"] == "out-of-corpus"]
pos = [r for r in rows if r["truth"] == "in-corpus"]

print(f"sample: {len(pos)} in-corpus, {len(neg)} out-of-corpus "
      f"({len(rows)} total)\n")

for label, fo in (("strict     ", False), ("fail-open  ", True)):
    caught = [r for r in neg if verdict(r, fo) == "refuse"]
    fr = [r for r in pos if verdict(r, fo) == "refuse"]
    print(f"{label} caught {len(caught):>2}/{len(neg)}   "
          f"false refusals {len(fr):>2}/{len(pos)}"
          + (f"   -> {', '.join(r['id'] for r in fr)}" if fr else ""))

print()
FO = True
missed = [r for r in neg if verdict(r, FO) == "pass"]
print(f"fail-open: negatives NOT caught ({len(missed)}):")
for r in missed:
    print(f"  {r['id']:<5} {r.get('regime', r.get('kind','')):<15} "
          f"declared {r['declared']}  reply: {r['reply'][:70]}")

fr = [r for r in pos if verdict(r, FO) == "refuse"]
print(f"\nfail-open: false refusals ({len(fr)}):")
for r in fr:
    print(f"  {r['id']:<5} {r.get('kind', r['group']):<20} "
          f"reply: {r['reply'][:70]}")

# GENERAL rate — how often the model declines to attribute at all.
gen = [r for r in rows if not r["declared"] and is_general(r["reply"])]
print(f"\nreplies of GENERAL: {len(gen)}  "
      f"({sum(1 for r in gen if r['truth'] == 'in-corpus')} in-corpus, "
      f"{sum(1 for r in gen if r['truth'] == 'out-of-corpus')} out)")
for r in gen:
    print(f"  {r['id']:<5} {r['truth']}")

# What the pre-flight adds ON TOP of the shipped mechanisms, on the 26
# audit negatives: the baseline says which the shipped system answered.
try:
    base = {b["id"]: b for b in json.load(open(f"{RUNS}/n5-baseline.json"))}
except FileNotFoundError:
    base = {}
if base:
    an = [i for i, b in base.items() if b["mode"] == "answered"]
    print(f"\nshipped baseline on the 26 negatives: {len(an)} answered "
          f"(each an N5 instance)")
    saved = [i for i in an if verdict(
        next(r for r in rows if r["id"] == i), FO) == "refuse"]
    still = [i for i in an if i not in saved]
    print(f"  pre-flight would refuse {len(saved)}/{len(an)} of them: "
          f"{', '.join(saved) or '-'}")
    print(f"  still answered wrongly:  {len(still)}: "
          f"{', '.join(still) or '-'}")
    for i in still:
        r = next(x for x in rows if x["id"] == i)
        print(f"    {i} {base[i]['regime']}: preflight said "
              f"{r['declared']} / {r['reply'][:50]}")
