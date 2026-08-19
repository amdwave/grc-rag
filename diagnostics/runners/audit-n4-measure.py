"""N4 measurement, split by cause — the number that decides fail vs warn.

A span the model elided ("...") or bracket-adapted ("aim[]") is in NO
retrieved chunk, so it fails an attribution check too. That is the
EXISTING verifier's finding (N1 / the known-benign misquote classes),
not evidence of misattribution, and counting it as N4 would inflate the
new check with defects the old one already reports.

The true N4 signal is the span verify() ACCEPTS — some retrieved chunk
holds it verbatim — printed beside an id that does not. Only that span
sends a reader to a chunk where the quote is not.

    uv run python diagnostics/runners/audit-n4-measure.py
"""
import json
import sys

sys.path.insert(0, "src")
from grc_rag.query.engine import (
    Engine, check_attribution, load_eval, verify)

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

eng = Engine(floor=None)
data = json.load(open(f"{RUNS}/audit-control-eval.json"))

qtext = {q["id"]: q["question"]
         for q in load_eval("eval/corpus.eval.jsonl")}
qtext.update({q["id"]: q["question"]
              for q in load_eval(f"{SETS}/audit-toc-probe.jsonl")})

rows = data["eval"] + data["probe"]
tot = {"spans": 0, "attributed": 0, "unverifiable": 0, "n4": 0}
n4_rows, unver_rows = [], []

for r in rows:
    sources, _ = eng.retrieve(qtext[r["id"]])
    verified = {span: hit for span, hit in verify(r["text"], sources)}
    res = check_attribution(r["text"], sources)
    n4, unver = [], 0
    for span, cid, src, ok in res:
        tot["spans"] += 1
        if cid:
            tot["attributed"] += 1
        if ok:
            continue
        # Failed attribution. Which cause?
        if verified.get(span) is None:
            unver += 1          # in no chunk at all - verify()'s finding
            tot["unverifiable"] += 1
        else:
            n4.append((span, cid, verified[span].id))
            tot["n4"] += 1
    if n4:
        n4_rows.append((r["id"], n4))
    if unver:
        unver_rows.append((r["id"], unver))
    flag = "  <-- N4" if n4 else ""
    print(f'{r["id"]:<5} spans {len(res):>2}  N4 {len(n4)}  '
          f'already-unverified {unver}{flag}')

print(f'\n{len(rows)} answers | {tot["spans"]} spans | '
      f'{tot["attributed"]} attributed')
print(f'  already caught by verify() (elision / adaptation): '
      f'{tot["unverifiable"]}  in {len(unver_rows)} answers')
print(f'  NEW - verify() passes, cited chunk does not hold it: '
      f'{tot["n4"]}  in {len(n4_rows)} answers')

for qid, n4 in n4_rows:
    print(f"\n=== {qid} ===")
    for span, cid, real in n4:
        print(f"  cited [{cid}] but the span lives in [{real}]")
        print(f"    “{span[:150]}”")

json.dump({"totals": tot,
           "n4": [{"id": q, "spans": [{"span": s, "cited": c, "actual": a}
                                      for s, c, a in b]}
                  for q, b in n4_rows]},
          open(f"{RUNS}/audit-n4-measure.json", "w"), indent=1)
print(f"\nwrote {RUNS}/audit-n4-measure.json")
