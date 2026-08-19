"""Variant 2 of the regime pre-flight: ask for the instrument that
DEFINES the terms the question uses, not every instrument a
practitioner would have to read.

D16 recorded why this is worth one measurement: three of the five
hard-class misses (h04, h06, h08) name the correct out-of-corpus regime
ALONGSIDE an in-corpus one, and the any-overlap rule passes them. If
the model is asked for the defining instrument only, those replies
should stop naming the in-corpus neighbour. The matcher is unchanged -
still any-overlap against the closed set, still GENERAL-fails-open
(P4) - so the prompt is the only variable, and the q44 hazard D16
names (a naive first-named RULE refusing a good question) is not taken:
no first-named rule exists here.

The decision rule is pre-registered in docs/kickoffs/m14-kickoff.md
SS1, before this run:
  - adopt only if >= 12 of 15 hard-class negatives caught AND <= 1
    false refusal across the 59 in-corpus rows;
  - better catch rate at 2+ false refusals -> keep the D16 variant;
  - neither variant at 12/15 -> ship D16 as measured, no third prompt.

Runs the same 110 questions as n5-preflight.py plus n5-hardclass-run.py:
51 eval + 26 audit negatives + 10 toc probes + 23 hard class. Pre-flight
calls only - the shipped-pipeline modes are already committed in
runs/n5-hardclass.json and runs/n5-baseline.json and do not change when
the pre-flight prompt does. Writes a NEW output file; the committed
D16 outputs are the baseline being compared against and are not touched.

    uv run python -u diagnostics/runners/n5-preflight-defining.py
"""
import json
import os
import re
import sys

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, "src")
load_dotenv()   # repo root is the working directory; finds .env there

from grc_rag.query.engine import load_eval

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

# Identical to n5-preflight.py and n5-hardclass-run.py - the matcher is
# deliberately NOT the variable in this experiment.
CORPUS_REGIMES = {
    "EU AI Act": ["ai act", "artificial intelligence act",
                  "regulation (eu) 2024/1689", "2024/1689", "aia"],
    "GDPR": ["gdpr", "general data protection regulation",
             "regulation (eu) 2016/679", "2016/679"],
    "NIS2": ["nis2", "nis 2", "nis2 directive", "nis 2 directive",
             "directive (eu) 2022/2555", "2022/2555",
             "network and information security directive"],
}

# The D16 prompt asked for "every legal instrument a practitioner would
# have to read to answer the question properly". This one asks for the
# instrument(s) the question belongs to. The TERMS OF ART paragraph and
# the output format are verbatim from the baseline prompt so the ask is
# the only difference.
DEFINING_PROMPT = """\
You identify which body of law a compliance question belongs to. Use
your general knowledge of legislation - this is NOT a retrieval task and
there are no documents.

Name the legal instrument(s) whose text DEFINES the concepts and terms
of art the question uses - the instrument(s) the question is actually
about. Do NOT add instruments that are merely relevant, related, or
useful background: a practitioner might read several laws to answer
properly, but name only the one(s) the question belongs to. Use each
instrument's common name (for example "GDPR", "NIS2 Directive", "Cyber
Resilience Act", "ISO/IEC 27001").

Pay attention to TERMS OF ART. A question that never names an act may
still belong to one: "product with digital elements", "critical entity"
and "data processing service" are defined terms belonging to specific
instruments, and the instrument that defines the term is the instrument
the question is about.

If the question genuinely belongs to more than one instrument - it asks
how two regimes interact, or its terms are defined in different acts -
name each of them. If the question is about a subject rather than any
particular instrument, say GENERAL.

Answer with instrument names on ONE line, separated by semicolons.
Nothing else - no explanation, no citations."""


def declared(reply):
    """Which corpus instruments the reply names, by alias membership."""
    low = reply.lower()
    return sorted(name for name, aliases in CORPUS_REGIMES.items()
                  if any(re.search(r"(?<![a-z0-9])" + re.escape(a)
                                   + r"(?![a-z0-9])", low)
                         for a in aliases))


def is_general(reply):
    return reply.strip().upper().rstrip(".") == "GENERAL"


client = OpenAI(base_url="https://api.deepseek.com",
                api_key=os.environ.get("DEEPSEEK_API_KEY", "unset"))


def preflight(question):
    r = client.chat.completions.create(
        model="deepseek-chat", temperature=0,
        messages=[{"role": "system", "content": DEFINING_PROMPT},
                  {"role": "user", "content": question}])
    return r.choices[0].message.content.strip()


rows = []


def run(qid, question, group, truth, **meta):
    reply = preflight(question)
    hits = declared(reply)
    general = is_general(reply)
    # Fail-open, the adopted D16 policy: GENERAL is not evidence the
    # regime is outside the corpus.
    verdict = "pass" if (hits or general) else "refuse"
    ok = (verdict == "pass") == (truth == "in-corpus")
    print(f'{qid:<5} {group:<14} want {truth:<13} -> {verdict:<7} '
          f'{"ok" if ok else "MISS":<5} [{", ".join(hits) or "-"}]  {reply[:60]}')
    rows.append({"id": qid, "group": group, "truth": truth, "reply": reply,
                 "declared": hits, "general": general, "verdict": verdict,
                 "ok": ok, **meta})


for q in load_eval("eval/corpus.eval.jsonl"):
    truth = "out-of-corpus" if q["kind"] == "unanswerable" else "in-corpus"
    run(q["id"], q["question"], "eval", truth, kind=q["kind"])
for q in load_eval(f"{SETS}/audit-negatives.jsonl"):
    run(q["id"], q["question"], "audit-negative", "out-of-corpus",
        regime=q["regime"], band=q["band"])
for q in load_eval(f"{SETS}/audit-toc-probe.jsonl"):
    run(q["id"], q["question"], "toc-probe", "in-corpus")
for q in load_eval(f"{SETS}/n5-hardclass.jsonl"):
    run(q["id"], q["question"], "hardclass", q["truth"],
        regime=q["regime"], debatable=q.get("debatable", False))

# ---- the committed D16 baseline, recomputed from its stored replies
# with the same fail-open policy so the comparison is like-for-like
# (n5-preflight.json stored the STRICT verdict; the replies are what
# both policies derive from).
base = {}
for r in json.load(open(f"{RUNS}/n5-preflight.json")):
    hits = declared(r["reply"])
    base[r["id"]] = "pass" if (hits or is_general(r["reply"])) else "refuse"
for r in json.load(open(f"{RUNS}/n5-hardclass.json")):
    base[r["id"]] = r["preflight"]

# ---- scorecard against the pre-registered rule
hard_neg = [r for r in rows if r["group"] == "hardclass"
            and r["truth"] == "out-of-corpus"]
hard_head = [r for r in hard_neg if not r.get("debatable")]
in_corpus = [r for r in rows if r["truth"] == "in-corpus"]

hard_caught = [r for r in hard_neg if r["verdict"] == "refuse"]
hard_caught_head = [r for r in hard_head if r["verdict"] == "refuse"]
false_refusals = [r for r in in_corpus if r["verdict"] == "refuse"]

print(f"\n== defining-instrument variant ==")
print(f"hard-class negatives caught: {len(hard_caught)}/{len(hard_neg)}"
      f"   (headline, excl. debatable h13: "
      f"{len(hard_caught_head)}/{len(hard_head)})")
print(f"FALSE REFUSALS: {len(false_refusals)}/{len(in_corpus)} in-corpus rows")
for r in false_refusals:
    print(f"   {r['id']} ({r.get('kind', r['group'])}): {r['reply'][:80]}")

for qid in ("q15", "q16"):
    row = next(r for r in rows if r["id"] == qid)
    tag = "ok" if row["verdict"] == "pass" else "BROKEN - P4 disqualifies"
    print(f"P4 repealed-row check: {qid} -> {row['verdict']} ({tag})")

audit_neg = [r for r in rows if r["group"] == "audit-negative"]
eval_unans = [r for r in rows if r["group"] == "eval"
              and r["truth"] == "out-of-corpus"]
print(f"audit negatives caught: "
      f"{sum(r['verdict'] == 'refuse' for r in audit_neg)}/{len(audit_neg)}"
      f"   (D16 baseline fail-open: "
      f"{sum(base[r['id']] == 'refuse' for r in audit_neg)}/{len(audit_neg)})")
print(f"eval unanswerable caught: "
      f"{sum(r['verdict'] == 'refuse' for r in eval_unans)}/{len(eval_unans)}"
      f"   (D16 baseline: "
      f"{sum(base[r['id']] == 'refuse' for r in eval_unans)}/{len(eval_unans)})")

print("\nverdict changes vs the D16 baseline:")
changes = [r for r in rows if base.get(r["id"]) not in (None, r["verdict"])]
for r in changes:
    print(f"   {r['id']:<5} {r['truth']:<14} {base[r['id']]:>6} -> "
          f"{r['verdict']:<7} [{', '.join(r['declared']) or '-'}] "
          f"{r['reply'][:60]}")
if not changes:
    print("   none")

print("\n== pre-registered decision rule (m14-kickoff SS1) ==")
adopt = len(hard_caught) >= 12 and len(false_refusals) <= 1
print(f"catches >= 12/15: {len(hard_caught)}/15 -> "
      f"{'yes' if len(hard_caught) >= 12 else 'NO'}")
print(f"false refusals <= 1/{len(in_corpus)}: {len(false_refusals)} -> "
      f"{'yes' if len(false_refusals) <= 1 else 'NO'}")
print(f"=> {'ADOPT defining-instrument variant' if adopt else 'KEEP D16 variant'}")

json.dump(rows, open(f"{RUNS}/n5-preflight-defining.json", "w"), indent=1)
print(f"\nwrote {RUNS}/n5-preflight-defining.json")
