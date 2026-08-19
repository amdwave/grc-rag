"""Audit measurement 2: the control experiment nobody ran — the full
51-question eval with the gate disabled (floor=None), plus the 10
TOC-probe questions through full generation.

Scoring replicates cli.cmd_eval exactly, except refusal correctness is
recorded twice: strict (mode matches refusal_source, which floor=None
cannot satisfy for gate rows) and mechanism-agnostic (refused at all).

Run from /mnt/d/projects/grc-rag:
    uv run python diagnostics/runners/audit-control-eval.py
Writes diagnostics/runs/audit-control-eval.json (never touches
eval/corpus.eval.report.md).
"""
import json
import sys

from dotenv import load_dotenv

sys.path.insert(0, "src")
load_dotenv()   # repo root is the working directory; finds .env there

from grc_rag.query.engine import Engine, cite, cited_ids, load_eval

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

eng = Engine(floor=None)

out = {"eval": [], "probe": []}

hit = cit = ver = n_ans = 0
refused_any = refused_strict = 0
n_refuse = 0
for q in load_eval("eval/corpus.eval.jsonl"):
    a = eng.answer(q["question"])
    cited = cited_ids(a.text)
    row = {"id": q["id"], "kind": q["kind"], "mode": a.mode,
           "best_dense": a.best_dense, "verified": a.verified,
           "cited": cited, "text": a.text}
    if q["expected_behavior"] == "answer":
        n_ans += 1
        got_ids = [s.id for s in a.sources]
        by_id = {s.id: s for s in a.sources}

        def base(c):
            if c in by_id:
                return by_id[c]
            return next((s for i, s in by_id.items()
                         if c.startswith(i + "(")), None)
        good = [s for s in (base(c) for c in cited)
                if s and s.id in q["expected_chunk_ids"]]
        row["hit@5"] = any(i in got_ids for i in q["expected_chunk_ids"])
        row["citation"] = (a.mode == "answered" and bool(good)
                          and any(s.date_basis == q["expected_date_basis"]
                                  for s in good)
                          and any(q["expected_citation"] in cite(s)
                                  for s in good))
        hit += row["hit@5"]
        cit += row["citation"]
    else:
        n_refuse += 1
        want_mode = ("refused-gate" if q["refusal_source"] == "gate"
                     else "refused-generation")
        row["refusal_source_expected"] = q["refusal_source"]
        row["refused_strict"] = a.mode == want_mode
        row["refused_any"] = a.refused
        refused_strict += row["refused_strict"]
        refused_any += row["refused_any"]
    ver += a.verified
    out["eval"].append(row)
    print(f'{q["id"]}  {a.mode:<19} dense {a.best_dense:.4f}  '
          f'ver {a.verified}')

print(f"\nCONTROL (floor=None): hit@5 {hit}/{n_ans}  citation "
      f"{cit}/{n_ans}  refused-any {refused_any}/{n_refuse}  "
      f"refused-strict {refused_strict}/{n_refuse}  verified {ver}/51")

for q in load_eval(f"{SETS}/audit-toc-probe.jsonl"):
    a = eng.answer(q["question"])
    cited = cited_ids(a.text)
    anchors = q["expected_anchor"].split("|")
    anchor_hit = any(c == an or c.startswith(an + "(")
                     for c in cited for an in anchors)
    out["probe"].append({"id": q["id"], "mode": a.mode,
                         "expected_anchor": q["expected_anchor"],
                         "anchor_cited": anchor_hit,
                         "verified": a.verified, "cited": cited,
                         "text": a.text})
    print(f'{q["id"]}  {a.mode:<19} anchor_cited {anchor_hit}  '
          f'ver {a.verified}')

with open(f"{RUNS}/audit-control-eval.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print(f"\nwrote {RUNS}/audit-control-eval.json")
