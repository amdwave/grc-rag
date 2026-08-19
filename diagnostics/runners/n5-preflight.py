"""N5 design under test: the regime pre-flight.

One short model call per question, carrying NO documents. It asks the
model to use world knowledge - the one faculty the grounding prompt
forbids, and the one that resolves regime identity - to name the legal
instrument(s) the question concerns. The reply is then matched against
the closed set the corpus holds.

The whole point is that the reply is graded against a CLOSED SET rather
than judged. The corpus holds exactly three instruments, so
"does this question's regime intersect {AI Act, GDPR, NIS2}?" is a
membership test, not an opinion. Same move D11 made for citations: put
the claim where a check can reach it.

Multi-label by construction (pre-registration P3): a cross-instrument
question genuinely belongs to two regimes, and ANY overlap with the
closed set passes. Refusing a question because it ALSO touches an act we
lack would break q47 and every cross_instrument row.

    uv run python diagnostics/runners/n5-preflight.py
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

# No Engine here on purpose: the pre-flight carries no documents and
# needs no retrieval, so it must not load BGE-M3 or the reranker. That
# is also the cost argument for the design - this call is tiny, and on a
# refusal it replaces the expensive documents call entirely.

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

# What the corpus actually holds. The canonical name plus the aliases a
# model plausibly uses for the SAME act - not a similarity list. An
# alias here must be a name for one of these three instruments and
# nothing else; anything looser turns a membership test back into a
# judgement call.
CORPUS_REGIMES = {
    "EU AI Act": ["ai act", "artificial intelligence act", "regulation (eu) 2024/1689",
                  "2024/1689", "aia"],
    "GDPR": ["gdpr", "general data protection regulation",
             "regulation (eu) 2016/679", "2016/679"],
    "NIS2": ["nis2", "nis 2", "nis2 directive", "nis 2 directive",
             "directive (eu) 2022/2555", "2022/2555",
             "network and information security directive"],
}

PREFLIGHT_PROMPT = """\
You identify which body of law a compliance question belongs to. Use
your general knowledge of legislation - this is NOT a retrieval task and
there are no documents.

Name every legal instrument a practitioner would have to read to answer
the question properly. Use each instrument's common name (for example
"GDPR", "NIS2 Directive", "Cyber Resilience Act", "ISO/IEC 27001").

Pay attention to TERMS OF ART. A question that never names an act may
still belong to one: "product with digital elements", "critical entity"
and "data processing service" are defined terms belonging to specific
instruments, and the instrument that defines the term is the instrument
the question is about.

If several instruments genuinely apply, name them all. If the question
is about a subject rather than any particular instrument, say GENERAL.

Answer with instrument names on ONE line, separated by semicolons.
Nothing else - no explanation, no citations."""


def declared(reply):
    """Which corpus instruments the reply names, by alias membership."""
    low = reply.lower()
    return sorted(name for name, aliases in CORPUS_REGIMES.items()
                  if any(re.search(r"(?<![a-z0-9])" + re.escape(a)
                                   + r"(?![a-z0-9])", low)
                         for a in aliases))


client = OpenAI(base_url="https://api.deepseek.com",
                api_key=os.environ.get("DEEPSEEK_API_KEY", "unset"))


def preflight(question):
    r = client.chat.completions.create(
        model="deepseek-chat", temperature=0,
        messages=[{"role": "system", "content": PREFLIGHT_PROMPT},
                  {"role": "user", "content": question}])
    return r.choices[0].message.content.strip()


def run(qid, question, group, truth, **meta):
    reply = preflight(question)
    hits = declared(reply)
    # PASS = the question's regime intersects what the corpus holds.
    verdict = "pass" if hits else "refuse"
    ok = (verdict == "pass") == (truth == "in-corpus")
    print(f'{qid:<5} {group:<14} want {truth:<11} -> {verdict:<7} '
          f'{"ok" if ok else "MISS":<5} [{", ".join(hits) or "-"}]  {reply[:70]}')
    return {"id": qid, "group": group, "truth": truth, "reply": reply,
            "declared": hits, "verdict": verdict, "ok": ok, **meta}


rows = []
for q in load_eval("eval/corpus.eval.jsonl"):
    truth = "out-of-corpus" if q["kind"] == "unanswerable" else "in-corpus"
    rows.append(run(q["id"], q["question"], "eval", truth, kind=q["kind"]))
for q in load_eval(f"{SETS}/audit-negatives.jsonl"):
    rows.append(run(q["id"], q["question"], "audit-negative",
                    "out-of-corpus", regime=q["regime"], band=q["band"]))
for q in load_eval(f"{SETS}/audit-toc-probe.jsonl"):
    rows.append(run(q["id"], q["question"], "toc-probe", "in-corpus"))

neg = [r for r in rows if r["truth"] == "out-of-corpus"]
pos = [r for r in rows if r["truth"] == "in-corpus"]
caught = [r for r in neg if r["verdict"] == "refuse"]
false_refusals = [r for r in pos if r["verdict"] == "refuse"]

print(f"\n== regime pre-flight ==")
print(f"  out-of-corpus caught: {len(caught)}/{len(neg)}")
print(f"  FALSE REFUSALS:       {len(false_refusals)}/{len(pos)}")
if false_refusals:
    print("  false-refused rows (P3/P4 watch these):")
    for r in false_refusals:
        print(f"    {r['id']} ({r.get('kind', r['group'])}): {r['reply'][:90]}")
missed = [r for r in neg if r["verdict"] == "pass"]
if missed:
    print("  negatives NOT caught:")
    for r in missed:
        print(f"    {r['id']} {r.get('regime', '')}: {r['reply'][:90]}")

json.dump(rows, open(f"{RUNS}/n5-preflight.json", "w"), indent=1)
print(f"\nwrote {RUNS}/n5-preflight.json")
