"""Audit analysis: what can any score-threshold gate achieve, on the
widened sample. Pure stdlib; reads audit-gate-scores.json.

Ground truth follows M10's convention: all `unanswerable` rows are
negatives (refusal_source ignored), everything else in-corpus is a
positive. Probes are positives. Sample: 51 positives, 36 negatives.
"""
import itertools
import json

rows = json.load(open("diagnostics/runs/audit-gate-scores.json"))

positives = [r for r in rows if not r["neg"]]
negatives = [r for r in rows if r["neg"]]
print(f"positives {len(positives)}  negatives {len(negatives)}")

def sweep(pos, neg, key, allowed_fr):
    """Best threshold for score[key]: refuse if score < t. Returns
    (caught, false_refusals, t, margin_to_next_positive)."""
    best = (0, 0, None, None)
    cands = sorted({r[key] for r in pos + neg})
    for t in cands + [max(cands) + 1e-6]:
        fr = sum(1 for r in pos if r[key] < t)
        if fr > allowed_fr:
            continue
        caught = sum(1 for r in neg if r[key] < t)
        if caught > best[0]:
            above = [r[key] for r in pos if r[key] >= t]
            margin = min(above) - t if above else None
            best = (caught, fr, t, margin)
    return best

def sweep_or(pos, neg, allowed_fr):
    """Independent floors on dense and rerank; refuse if either is
    below its floor. Exhaustive over candidate thresholds."""
    dcands = sorted({r["dense"] for r in pos + neg}) + [1.0]
    rcands = sorted({r["rerank"] for r in pos + neg}) + [2.0]
    best = (0, 0, None, None)
    for dt, rt in itertools.product(dcands, rcands):
        fr = sum(1 for r in pos if r["dense"] < dt or r["rerank"] < rt)
        if fr > allowed_fr:
            continue
        caught = sum(1 for r in neg
                     if r["dense"] < dt or r["rerank"] < rt)
        if caught > best[0]:
            best = (caught, fr, dt, rt)
    return best

for label, pos, neg in [
        ("M10 sample (41 pos eval, 10 neg eval)",
         [r for r in positives if r["group"] == "eval"],
         [r for r in negatives if r["group"] == "eval"]),
        ("widened (51 pos incl probes, 36 neg)", positives, negatives)]:
    print(f"\n== {label} ==")
    for afr in (0, 1, 2):
        d = sweep(pos, neg, "dense", afr)
        r = sweep(pos, neg, "rerank", afr)
        o = sweep_or(pos, neg, afr)
        print(f" allow {afr} FR:  dense {d[0]}/{len(neg)} @<{d[2]:.4f} "
              f"(margin {d[3]:.4f})   rerank {r[0]}/{len(neg)} "
              f"@<{r[2]:.4f} (margin {r[3]:.4f})   "
              f"OR {o[0]}/{len(neg)} @ dense<{o[2]:.4f} rerank<{o[3]:.4f}")

# current shipped gate on the widened negatives
print("\n== shipped gate (dense < 0.59) on all 36 negatives ==")
caught = [r["id"] for r in negatives if r["dense"] < 0.59]
print(f" catches {len(caught)}/36: {', '.join(caught)}")

# band breakdown: what does each mechanism see per difficulty band
print("\n== per-band (new negatives only), best 0-FR thresholds "
      "from widened sweep ==")
d0 = sweep(positives, negatives, "dense", 0)[2]
r0 = sweep(positives, negatives, "rerank", 0)[2]
print(f" thresholds: dense<{d0:.4f}  rerank<{r0:.4f}")
for band in ("extreme-near", "near", "mid", "far"):
    sub = [r for r in negatives if r.get("band") == band]
    if not sub:
        continue
    dc = sum(1 for r in sub if r["dense"] < d0)
    rc = sum(1 for r in sub if r["rerank"] < r0)
    ec = sum(1 for r in sub if r["dense"] < d0 or r["rerank"] < r0)
    print(f" {band:<13} n={len(sub)}  dense {dc}  rerank {rc}  either {ec}")

# the uncatchable set: negatives above every 0-FR threshold
unc = [r for r in negatives if r["dense"] >= d0 and r["rerank"] >= r0]
print(f"\n== uncatchable at 0 FR (n={len(unc)}) ==")
for r in sorted(unc, key=lambda r: -r["rerank"]):
    tag = r.get("regime") or r["id"]
    print(f" {r['id']:<4} {tag:<15} dense {r['dense']:.4f} "
          f"rerank {r['rerank']:+.4f}")
