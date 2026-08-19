"""The decisive measurement: shipped pipeline AND regime pre-flight on
the hard class — regime carried in a term of art, act never named.

This is the set the eval and the M11 audit negatives both lack. 15
out-of-corpus rows on the q36/q49 recipe, 8 in-corpus rows phrased the
same way to catch false refusals.

    uv run python -u diagnostics/runners/n5-hardclass-run.py
"""
import json
import sys

from dotenv import load_dotenv

sys.path.insert(0, "src")
load_dotenv()   # repo root is the working directory; finds .env there

from grc_rag.query.engine import DEFAULT_FLOOR, Engine, cited_ids, load_eval

SETS = "diagnostics/sets"
RUNS = "diagnostics/runs"

# Re-declared here rather than imported: the pre-flight script's module
# name has a hyphen, and copying the two constants is cheaper than a
# loader shim. They must stay identical to n5-preflight.py.
CORPUS_REGIMES = {
    "EU AI Act": ["ai act", "artificial intelligence act",
                  "regulation (eu) 2024/1689", "2024/1689", "aia"],
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

import re


def declared(reply):
    low = reply.lower()
    return sorted(n for n, al in CORPUS_REGIMES.items()
                  if any(re.search(r"(?<![a-z0-9])" + re.escape(a)
                                   + r"(?![a-z0-9])", low) for a in al))


def is_general(reply):
    return reply.strip().upper().rstrip(".") == "GENERAL"


eng = Engine(floor=DEFAULT_FLOOR)


def preflight(question):
    r = eng.client.chat.completions.create(
        model=eng.chat_model, temperature=0,
        messages=[{"role": "system", "content": PREFLIGHT_PROMPT},
                  {"role": "user", "content": question}])
    return r.choices[0].message.content.strip()


rows = []
for q in load_eval(f"{SETS}/n5-hardclass.jsonl"):
    reply = preflight(q["question"])
    hits = declared(reply)
    verdict = "pass" if (hits or is_general(reply)) else "refuse"
    a = eng.answer(q["question"])
    rows.append({**q, "preflight_reply": reply, "declared": hits,
                 "preflight": verdict, "mode": a.mode,
                 "best_dense": a.best_dense, "verified": a.verified,
                 "cited": cited_ids(a.text), "text": a.text})
    print(f'{q["id"]:<4} {q["truth"]:<14} shipped={a.mode:<19} '
          f'preflight={verdict:<7} [{", ".join(hits) or "-"}] {reply[:45]}')

neg = [r for r in rows if r["truth"] == "out-of-corpus"]
pos = [r for r in rows if r["truth"] == "in-corpus"]
head = [r for r in neg if not r.get("debatable")]

print(f"\n== HARD CLASS: {len(neg)} out-of-corpus, {len(pos)} in-corpus ==")
ans = [r for r in neg if r["mode"] == "answered"]
ans_h = [r for r in head if r["mode"] == "answered"]
print(f"shipped pipeline answered wrongly: {len(ans)}/{len(neg)}  "
      f"(headline, excl. debatable: {len(ans_h)}/{len(head)})")
for r in ans:
    print(f"   {r['id']} {r['regime']:<32} verified={r['verified']} "
          f"cited {', '.join(r['cited'][:3]) or '-'}")

caught = [r for r in neg if r["preflight"] == "refuse"]
caught_h = [r for r in head if r["preflight"] == "refuse"]
fr = [r for r in pos if r["preflight"] == "refuse"]
print(f"\npre-flight caught: {len(caught)}/{len(neg)}  "
      f"(headline: {len(caught_h)}/{len(head)})")
print(f"pre-flight FALSE REFUSALS: {len(fr)}/{len(pos)}")
for r in fr:
    print(f"   {r['id']} ({r['regime']}): {r['preflight_reply'][:60]}")
missed = [r for r in neg if r["preflight"] == "pass"]
print(f"pre-flight missed ({len(missed)}):")
for r in missed:
    print(f"   {r['id']} {r['regime']:<32} declared={r['declared']} "
          f"reply={r['preflight_reply'][:45]}")

fixed = [r for r in ans if r["preflight"] == "refuse"]
print(f"\nWHAT IT BUYS: of {len(ans)} shipped failures, the pre-flight "
      f"refuses {len(fixed)}: {', '.join(r['id'] for r in fixed) or '-'}")

json.dump(rows, open(f"{RUNS}/n5-hardclass.json", "w"), indent=1)
print(f"\nwrote {RUNS}/n5-hardclass.json")
