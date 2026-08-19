"""N5 baseline: the 26 M11 audit negatives through the SHIPPED pipeline.

These were authored during the audit for gate scoring and have never
been generated against, so they are a genuine holdout for the question
this session asks: how often does the shipped system answer a question
about a regime it does not hold?

Shipped config means floor=0.59 (D14 kept it). Both mechanisms get their
real chance: the gate first, then the grounding prompt.

    uv run python diagnostics/runners/n5-baseline.py
"""
import json
import sys

from dotenv import load_dotenv

sys.path.insert(0, "src")
load_dotenv()   # repo root is the working directory; finds .env there

from grc_rag.query.engine import DEFAULT_FLOOR, Engine, cited_ids, load_eval

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

eng = Engine(floor=DEFAULT_FLOOR)
rows = []

for q in load_eval(f"{SETS}/audit-negatives.jsonl"):
    a = eng.answer(q["question"])
    rows.append({"id": q["id"], "regime": q["regime"], "band": q["band"],
                 "question": q["question"], "mode": a.mode,
                 "best_dense": a.best_dense, "verified": a.verified,
                 "cited": cited_ids(a.text), "text": a.text})
    print(f'{q["id"]:<4} {q["regime"]:<15} {q["band"]:<13} {a.mode:<19} '
          f'dense {a.best_dense:.4f}  ver {a.verified}')

answered = [r for r in rows if r["mode"] == "answered"]
by_band = {}
for r in rows:
    b = by_band.setdefault(r["band"], [0, 0])
    b[1] += 1
    if r["mode"] == "answered":
        b[0] += 1

print(f'\nBASELINE (shipped, floor={DEFAULT_FLOOR}): '
      f'{len(answered)}/{len(rows)} ANSWERED rather than refused')
print(f'  refused-gate:       '
      f'{sum(1 for r in rows if r["mode"] == "refused-gate")}')
print(f'  refused-generation: '
      f'{sum(1 for r in rows if r["mode"] == "refused-generation")}')
for band in ("extreme-near", "near", "mid", "far"):
    if band in by_band:
        a_, n = by_band[band]
        print(f'  {band:<13} answered {a_}/{n}')
print("\nanswered (each of these is an N5 instance):")
for r in answered:
    print(f'  {r["id"]} {r["regime"]:<15} verified={r["verified"]} '
          f'cited {", ".join(r["cited"][:4]) or "-"}')

json.dump(rows, open(f"{RUNS}/n5-baseline.json", "w"), indent=1)
print(f"\nwrote {RUNS}/n5-baseline.json")
