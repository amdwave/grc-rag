"""Audit measurement 1: dense + rerank scores for every question the gate
could see — the 51 eval rows, 26 new out-of-corpus negatives, and 10
TOC-probe rows. Retrieval only; no generation API calls.

Run from /mnt/d/projects/grc-rag:
    uv run python diagnostics/runners/audit-gate-scores.py
Writes diagnostics/runs/audit-gate-scores.json
"""
import json
import sys

sys.path.insert(0, "src")
from grc_rag.query.engine import Engine, load_eval

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

eng = Engine(floor=None)

def score(qid, question, group, **meta):
    sources, best = eng.retrieve(question)
    return {
        "id": qid, "group": group, **meta, "q": question,
        "dense": best,
        "rerank": max((s.rerank for s in sources), default=0.0),
        "top": [{"id": s.id, "rerank": s.rerank, "dense": s.dense}
                for s in sources],
    }

rows = []
for q in load_eval("eval/corpus.eval.jsonl"):
    rows.append(score(q["id"], q["question"], "eval",
                      kind=q["kind"],
                      neg=q["kind"] == "unanswerable",
                      gate_expectation=q.get("gate_expectation"),
                      refusal_source=q.get("refusal_source")))
    print(f'{rows[-1]["id"]}  dense {rows[-1]["dense"]:.4f}  '
          f'rerank {rows[-1]["rerank"]:+.4f}')

for q in load_eval(f"{SETS}/audit-negatives.jsonl"):
    rows.append(score(q["id"], q["question"], "audit-negative",
                      neg=True, regime=q["regime"], band=q["band"]))
    print(f'{rows[-1]["id"]}  dense {rows[-1]["dense"]:.4f}  '
          f'rerank {rows[-1]["rerank"]:+.4f}  {q["regime"]}')

for q in load_eval(f"{SETS}/audit-toc-probe.jsonl"):
    rows.append(score(q["id"], q["question"], "toc-probe",
                      neg=False, expected_anchor=q["expected_anchor"]))
    print(f'{rows[-1]["id"]}  dense {rows[-1]["dense"]:.4f}  '
          f'rerank {rows[-1]["rerank"]:+.4f}  want {q["expected_anchor"]}')

with open(f"{RUNS}/audit-gate-scores.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1)
print(f"\nwrote {len(rows)} rows to {RUNS}/audit-gate-scores.json")
