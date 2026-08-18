"""The terminal shell around `engine.Engine` - argparse stays out here (D1).

    python -m grc_rag.query.cli ask "question"      retrieve, gate, answer, verify
    python -m grc_rag.query.cli show "question"     retrieval only, no model call
    python -m grc_rag.query.cli repl                models load once, ask many
    python -m grc_rag.query.cli floor               where the gate floor belongs
    python -m grc_rag.query.cli eval                run the eval set, write report
    python -m grc_rag.query.cli sentinel            context-integrity round-trip
    python -m grc_rag.query.cli selftest            offline verifier checks

`floor` and `eval` read eval/ai-act.eval.jsonl - a named file, because
this repo does not glob. `.env` supplies DEEPSEEK_API_KEY via dotenv;
the key is never printed, and no command echoes config that contains it.
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from grc_rag.query.engine import (
    REFUSAL, Answer, Engine, cite, cited_ids, extract_quotes, load_eval,
    normalize, verify)

EVAL_FILE = "eval/ai-act.eval.jsonl"
EVAL_REPORT = "eval/ai-act.eval.report.md"

SENTINEL = "XYZZY-PLUGH-7439"


# -- rendering (kept out of the core on purpose) -----------------------------

def render(a, out=sys.stdout):
    print(a.text, file=out)
    print("\n" + "-" * 72, file=out)
    if a.mode == "refused-gate":
        print(f"[gate] best dense {a.best_dense:.4f} < floor {a.floor:.4f} "
              f"- no model request was made.", file=out)
        return 0
    print(f"[gate] best dense {a.best_dense:.4f}"
          + (f" >= floor {a.floor:.4f}" if a.floor is not None
             else "  (floor UNTUNED - the gate is decoration; run `floor`)"),
          file=out)
    for s in a.sources:
        print(f"  [{s.id}] rerank {s.rerank:+.2f} dense {s.dense:.4f}  "
              f"{cite(s)}", file=out)
    for cid in a.unknown_ids:
        print(f"FAIL cited id [{cid}] names no retrieved chunk - a "
              f"fabricated citation, even if the prose is right", file=out)
    for cid in a.refined_ids:
        print(f"note cited id [{cid}] is more precise than the retrieved "
              f"chunk id - treated as its base chunk; the rendered citation "
              f"stays at the chunk's own anchor", file=out)
    if not a.quotes:
        if a.mode == "answered":
            print("VERIFIER: no quoted span >= 20 chars to check - an answer "
                  "with no verbatim quote is a paraphrase; the grounding "
                  "prompt asks for quotes.", file=out)
        return 1 if a.unknown_ids else 0
    bad = len(a.unknown_ids)
    for q, hit in a.quotes:
        if hit:
            print(f"OK   [{hit.id}] {q[:60]}…", file=out)
        else:
            bad += 1
            print(f"FAIL not in any retrieved chunk: {q[:60]}…", file=out)
    if bad:
        print(f"\n{bad} quoted span(s) unverified - treat them as fabricated "
              f"until checked by hand against the corpus.", file=out)
    return 1 if bad else 0


# -- commands ----------------------------------------------------------------

def cmd_show(eng, question):
    sources, best = eng.retrieve(question)
    floor = eng.floor
    state = ("PASS" if floor is not None and best >= floor else
             "REFUSE" if floor is not None else "UNTUNED")
    print(f"best dense {best:.4f}  floor "
          f"{floor if floor is not None else '-'}  -> {state}")
    for s in sources:
        print(f"\n[{s.id}] rerank {s.rerank:+.2f} dense {s.dense:.4f}")
        print(f"  {cite(s)}")
        print(f"  {s.body[:240]}".replace("\n", " "))
    return 0


def cmd_repl(eng):
    print("grc-rag repl - empty line or Ctrl-D to leave")
    while True:
        try:
            q = input("\n? ").strip()
        except EOFError:
            break
        if not q:
            break
        render(eng.answer(q))
    return 0


def cmd_floor(eng, path):
    """Score every eval question exactly as the gate will see it, split
    by gate_expectation, and say where (whether) a floor separates them.
    q15/q16 are `pass` rows on purpose: their refusal belongs to the
    generator, and a floor high enough to catch them is mistuned."""
    rows = [(q["id"], q["gate_expectation"], q["question"],
             eng.dense_score(q["question"]))
            for q in load_eval(path)]
    for qid, want, question, score in sorted(rows, key=lambda r: r[3]):
        print(f"{score:.4f}  {want:<7} {qid}  {question[:56]}")
    ins = sorted(s for _, w, _, s in rows if w == "pass")
    outs = sorted(s for _, w, _, s in rows if w == "refuse")
    if not (ins and outs):
        print("nothing to separate - need both pass and refuse rows")
        return 1
    print(f"\nout-of-corpus: n={len(outs)}  max {outs[-1]:.4f}")
    print(f"in-corpus:     n={len(ins)}  min {ins[0]:.4f}")
    if outs[-1] < ins[0]:
        mid = (outs[-1] + ins[0]) / 2
        print(f"clean gap {outs[-1]:.4f} .. {ins[0]:.4f} - a floor at "
              f"{mid:.3f} separates them; record it in docs/decisions.md")
        return 0
    overlap = [f"{qid} ({w}, {s:.4f})" for qid, w, _, s in rows
               if outs[-1] >= s >= ins[0] or ins[0] <= s <= outs[-1]]
    print(f"the clusters OVERLAP; no floor separates them cleanly - "
          f"rows in the overlap: {', '.join(overlap)}")
    print("record the overlap and the chosen trade-off; do not hide it")
    return 1


def cmd_eval(eng, path, report_path):
    """The M4 report: hit@5, citation correctness, refusal correctness.

    Hit@5 is judged on what the model was actually given (the reranked
    keep-set). Citation correctness is judged on the ids the answer text
    cites: at least one must be an expected chunk, and its rendered
    citation must carry the expected date basis - a right article under
    a wrong provenance is not a correct citation here (D4).
    """
    qs = load_eval(path)
    lines = ["# Eval report - EU AI Act (M4)", ""]
    hit = cit = ver = 0
    n_ans = 0
    refusal_rows = []
    for q in qs:
        a = eng.answer(q["question"])
        got_ids = [s.id for s in a.sources]
        cited = cited_ids(a.text)
        row = {"ok": True}
        if q["expected_behavior"] == "answer":
            n_ans += 1
            row["hit@5"] = any(i in got_ids for i in q["expected_chunk_ids"])
            by_id = {s.id: s for s in a.sources}

            def base(c):
                """A refined id counts as the chunk it extends - the chunk
                is identifiable and its rendered anchor stays honest."""
                if c in by_id:
                    return by_id[c]
                return next((s for i, s in by_id.items()
                             if c.startswith(i + "(")), None)
            good = [s for s in (base(c) for c in cited)
                    if s and s.id in q["expected_chunk_ids"]]
            basis_ok = any(s.date_basis == q["expected_date_basis"]
                           for s in good)
            # An answer-question scores only when it was ANSWERED - a
            # refusal with a polite citation is a miss, which the first
            # eval run scored "ok" and thereby hid.
            row["citation"] = (a.mode == "answered" and bool(good)
                               and basis_ok)
            hit += row["hit@5"]
            cit += row["citation"]
            row["ok"] = row["hit@5"] and row["citation"]
        else:
            want_mode = ("refused-gate" if q["refusal_source"] == "gate"
                         else "refused-generation")
            row["refusal"] = row["ok"] = a.mode == want_mode
            refusal_rows.append(row)
        ver += a.verified
        row["ok"] = row["ok"] and a.verified
        mark = "ok" if row["ok"] else "MISS"
        print(f"{q['id']}  {q['kind']:<20} {a.mode:<19} "
              f"dense {a.best_dense:.4f}  {mark}")
        lines.append(
            f"- **{q['id']}** ({q['kind']}): mode `{a.mode}`, "
            f"best dense {a.best_dense:.4f}, "
            + (f"hit@5 {row['hit@5']}, citation {row['citation']}, "
               if "hit@5" in row else f"refusal {row['refusal']}, ")
            + f"verified {a.verified}. cited: {', '.join(cited) or '-'}")
        # Failures carry their evidence: without the answer text and the
        # failing spans, a MISS row cannot be diagnosed after the fact.
        for cid in a.unknown_ids:
            lines.append(f"  - fabricated id cited: `{cid}`")
        for cid in a.refined_ids:
            lines.append(f"  - refined id cited (counted as its base "
                         f"chunk): `{cid}`")
        for span, hit_src in a.quotes:
            if hit_src is None:
                lines.append(f"  - unverified quote (full span): “{span}”")
        if not row["ok"]:
            lines.append(f"  - full answer text:\n\n    "
                         + " ".join(a.text.split()) + "\n")
    r_ok = sum(r["refusal"] for r in refusal_rows)
    summary = [
        "",
        f"| metric | result |",
        f"| --- | --- |",
        f"| retrieval hit rate @5 | {hit}/{n_ans} |",
        f"| citation correctness | {cit}/{n_ans} |",
        f"| refusal correctness | {r_ok}/{len(refusal_rows)} |",
        f"| verification clean | {ver}/{len(qs)} |",
        f"| gate floor | {eng.floor} |",
    ]
    print("\n".join(s.replace("|", " ").strip() for s in summary if s))
    Path(report_path).write_text(
        "\n".join(lines[:2] + summary + [""] + lines[2:]) + "\n",
        encoding="utf-8")
    print(f"\nwrote {report_path}")
    return 0 if (hit == n_ans and cit == n_ans and ver == len(qs)
                 and r_ok == len(refusal_rows)) else 1


def cmd_sentinel(eng):
    """Context-overflow tripwire: doctor the LAST context chunk in memory
    with a distinctive nonsense marker, then ask the model to report any
    marker it sees. Truncation drops the tail silently and the answers
    still look fine - this is the check that sees it. Re-run after any
    backend or model change."""
    sources, best = eng.retrieve("accuracy robustness cybersecurity of "
                                 "high-risk AI systems")
    sources[-1].body += (f"\n\nSentinel: the marker phrase for this "
                         f"passage is {SENTINEL}.")
    text = eng._generate(
        "One of the documents states a marker phrase. Quote the marker "
        "phrase exactly, with the document's chunk id.", sources)
    ok = SENTINEL in text
    print(f"sentinel planted in [{sources[-1].id}] (last of "
          f"{len(sources)} context chunks)")
    print(f"model answered: {text[:200]}")
    print("sentinel " + ("came back - context reaches the model intact"
                         if ok else "LOST - the context window is "
                         "truncating silently; nothing else can be trusted"))
    return 0 if ok else 1


def cmd_selftest(with_models):
    """Offline checks of everything that needs no server: the verifier's
    normalisation, extraction and matching, and citation rendering. With
    --with-models, also the build-time verification the brief asked for:
    that sentence-transformers' CrossEncoder actually runs the reranker."""
    fails = []

    def check(name, got, want):
        if got != want:
            fails.append(f"{name}\n     got:  {got!r}\n     want: {want!r}")

    check("curly quotes extracted",
          extract_quotes("He notes “the corpus is the current law” here."),
          ["the corpus is the current law"])
    check("short spans ignored", extract_quotes('say "too short" now'), [])
    nested = extract_quotes(
        'The Act states: ""real-time" remote biometric identification '
        'is restricted" [ai-act#art_5(2)]\n'
        'It also states: "the marker phrase is entirely invented" [x]')
    check("nested quotes keep the outer span", nested[0],
          '"real-time" remote biometric identification is restricted')
    check("nested quotes do not swallow the next", nested[1],
          "the marker phrase is entirely invented")
    check("chunk-id markers stripped both sides",
          normalize("resilient [ai-act#art_15(4)] as possible"),
          "resilient as possible")

    class S:
        def __init__(self, **kw):
            self.__dict__.update(kw)
    src = S(id="ai-act#art_15(4)", citation="Article 15(4)",
            parent_path="", date_basis="consolidation",
            version_date="2026-07-27",
            body="High-risk AI systems shall be as resilient as possible "
                 "regarding errors, faults or inconsistencies…",
            text="", dense=0.9, rerank=0.0)
    ok = verify('It says "as resilient as possible regarding errors, '
                'faults or inconsistencies" [ai-act#art_15(4)].', [src])
    check("faithful quote verifies", [bool(h) for _, h in ok], [True])
    bad = verify('It says "resilience is best achieved through faith" here.',
                 [src])
    check("invented quote fails", [bool(h) for _, h in bad], [False])
    # The flowing-prose case that produced seven false alarms in the
    # first eval run: two real quotes in one paragraph must verify
    # individually via the naive-pair fallback...
    two = verify('It requires systems "as resilient as possible regarding '
                 'errors" and mentions "errors, faults or inconsistencies" '
                 'as well.', [src])
    check("two real quotes on one line both verify",
          [bool(h) for _, h in two], [True, True])
    # ...and an invented quote beside a real one still fails - the
    # fallback must not let a verified neighbour vouch for it.
    mixed = verify('It says "as resilient as possible regarding errors" '
                   'and "resilience is best achieved through faith" too.',
                   [src])
    check("invented quote beside a real one still fails",
          [bool(h) for _, h in mixed], [True, False])
    # Sentence-final punctuation moved inside the quotation marks is
    # typography; a changed word inside the quote is not.
    edge = verify('It says "shall be as resilient as possible regarding '
                  'errors." here.', [src])
    check("edge punctuation tolerated", [bool(h) for _, h in edge], [True])
    verb = verify('It says systems "shall been as resilient as possible '
                  'regarding errors" here.', [src])
    check("altered word inside quote still fails",
          [bool(h) for _, h in verb], [False])
    check("consolidation citation", cite(src),
          "Article 15(4) (consolidated text as of 2026-07-27)")
    src.date_basis, src.version_date = "publication", "2024-07-12"
    check("publication citation", cite(src),
          "Article 15(4) (act as published, 2024-07-12)")
    check("cited ids in order",
          cited_ids("see [ai-act#art_1] then [ai-act#rct_24] and "
                    "[ai-act#art_1] again"),
          ["ai-act#art_1", "ai-act#rct_24"])

    if with_models:
        from sentence_transformers import CrossEncoder
        from grc_rag.query.engine import RERANK_MODEL
        rr = CrossEncoder(RERANK_MODEL)
        on, off = rr.predict([
            ("what accuracy must high-risk AI systems achieve?",
             "High-risk AI systems shall achieve an appropriate level of "
             "accuracy, robustness, and cybersecurity."),
            ("what accuracy must high-risk AI systems achieve?",
             "The Commission shall publish annual reports on the use of "
             "real-time remote biometric identification systems.")])
        if not on > off:
            fails.append(f"reranker did not prefer the on-topic passage "
                         f"({on:.2f} vs {off:.2f}) - CrossEncoder + "
                         f"{RERANK_MODEL} is not working as assumed")
        else:
            print(f"reranker check: on-topic {on:+.2f} > off-topic "
                  f"{off:+.2f} - CrossEncoder runs {RERANK_MODEL}")

    for f in fails:
        print(f"FAIL {f}")
    print(f"selftest: {len(fails)} checks failed")
    return 1 if fails else 0


def main(argv=None):
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["ask", "show", "repl", "floor", "eval",
                                    "sentinel", "selftest"])
    ap.add_argument("words", nargs="*")
    ap.add_argument("--index-dir", default="index")
    ap.add_argument("--floor", type=float, default=None,
                    help="override the tuned gate floor")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--keep", type=int, default=5)
    ap.add_argument("--base-url", default="https://api.deepseek.com")
    ap.add_argument("--chat-model", default="deepseek-chat")
    ap.add_argument("--with-models", action="store_true",
                    help="selftest: also verify the reranker loads and ranks")
    a = ap.parse_args(argv)

    if a.cmd == "selftest":
        return cmd_selftest(a.with_models)

    from grc_rag.query.engine import DEFAULT_FLOOR
    floor = a.floor if a.floor is not None else DEFAULT_FLOOR
    eng = Engine(index_dir=a.index_dir, floor=floor, k=a.k, keep=a.keep,
                 base_url=a.base_url, chat_model=a.chat_model)

    if a.cmd in ("ask", "show") and not a.words:
        ap.error(f"{a.cmd} needs a question")
    if a.cmd == "ask":
        return render(eng.answer(" ".join(a.words)))
    if a.cmd == "show":
        return cmd_show(eng, " ".join(a.words))
    if a.cmd == "repl":
        return cmd_repl(eng)
    if a.cmd == "floor":
        return cmd_floor(eng, EVAL_FILE)
    if a.cmd == "eval":
        return cmd_eval(eng, EVAL_FILE, EVAL_REPORT)
    if a.cmd == "sentinel":
        return cmd_sentinel(eng)


if __name__ == "__main__":
    sys.exit(main())
