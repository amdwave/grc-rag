#!/usr/bin/env python3
"""Does the corpus carry the source's text IN ORDER? (order-sensitive check)

    python tests/seqcheck-corpus.py gdpr:enacting   # one document
    python tests/seqcheck-corpus.py enacting        # that part, every act
    python tests/seqcheck-corpus.py both            # everything

WHY, IN ONE PARAGRAPH

Every check in the conversion report compares bags: articles counted,
characters emitted, characters dropped by rule. All of them are blind, by
construction, to text that is PRESENT IN THE WRONG ORDER - both sides
hold the same multiset, so nothing moves. book2rag passed three such
checks on a book whose margin gloss had been shredded through its body
sentences. `D:\\ai\\extractors\\seqcheck.py` is the instrument that
finally saw it, and this file points it at this corpus rather than
reimplementing it: it imports `Corpus`, `check`, `emit` and
`corpus_blocks` from that file and supplies the one thing that has to be
local - a second, INDEPENDENT extraction of the same raw HTML.

WHAT "INDEPENDENT" MEANS HERE, AND WHAT IT DOES NOT

The independent side is a regex tag-strip: no DOM, no tree walk, no
shared code with the converter, driven only by the raw bytes that were
committed. It is independent of the CONVERTER, which is the thing under
test - a converter bug that reorders or duplicates text cannot also
reorder this extraction. It is NOT independent of EUR-Lex: both sides
read the same HTML, so a defect in the source itself is invisible to
this check and would need a different representation (the PDF) to catch.
That limit is stated because a check whose limits are unwritten gets
trusted past them.

READING THE OUTPUT

SPLICE runs are the finding: the corpus travels further between two
matching anchors than the source does, which is what interleaved or
duplicated text looks like. Those fail the run. DROPOUT and ABSENT runs
are expected here and do not fail it: the converter declares its drops
(the amendment markers, the disclaimer, the 'Amended by' table) and text
the corpus deliberately does not carry can only show up as a dropout.
Read them against the report's coverage table - a dropout that no drop
rule accounts for is a real finding, and only a human can say which is
which.
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEQCHECK = Path("/mnt/d/ai/extractors/seqcheck.py")

# Keyed <instrument>:<part>. The bare part names this started with were
# already ambiguous the moment a second act arrived - "enacting" cannot
# say whose. Rows, not a registry: the four named lists in this repo do
# not carry the same fields (query/cli.py's eval pair is corpus-wide,
# not per-document) and they fill up at different milestones, so one
# table would be an abstraction over things that only look alike.
PARTS = {
    "ai-act:enacting": {
        "raw": "corpus/raw/eu/ai-act/02024R1689-20260727.en.html",
        "md": "corpus/eu/ai-act.md",
    },
    "ai-act:recitals": {
        "raw": "corpus/raw/eu/ai-act/32024R1689.en.html",
        "md": "corpus/eu/ai-act.recitals.md",
    },
    "gdpr:enacting": {
        "raw": "corpus/raw/eu/gdpr/02016R0679-20160504.en.html",
        "md": "corpus/eu/gdpr.md",
    },
    "gdpr:recitals": {
        "raw": "corpus/raw/eu/gdpr/32016R0679.en.html",
        "md": "corpus/eu/gdpr.recitals.md",
    },
    "nis2:enacting": {
        "raw": "corpus/raw/eu/nis2/02022L2555-20221227.en.html",
        "md": "corpus/eu/nis2.md",
    },
    "nis2:recitals": {
        "raw": "corpus/raw/eu/nis2/32022L2555.en.html",
        "md": "corpus/eu/nis2.recitals.md",
    },
}

# The apparatus the converter drops by name. Removed here too, by a
# different mechanism (regex on the raw bytes, not a tree walk), so the
# two sides are comparing the same scope. Anything removed here is
# removed BY NAME - widening these patterns to silence a run would be
# tuning the instrument until it agrees.
SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
APPARATUS = re.compile(
    r'<p class="(?:modref|arrow|disclaimer|reference|hd-modifiers)"[^>]*>'
    r".*?</p>", re.S)
NOTE_MARK = re.compile(r'<span class="(?:oj-super oj-note-tag|superscript)"'
                       r"[^>]*>.*?</span>", re.S)
TAG = re.compile(r"<[^>]+>")
BLOCK_END = re.compile(r"</(?:p|td|div|tr|table|h[1-6])>", re.I)

import html as _html                                            # noqa: E402


def strip(fragment):
    """Raw HTML fragment -> blocks of text, by regex alone."""
    s = SCRIPT.sub(" ", fragment)
    s = APPARATUS.sub(" ", s)
    s = NOTE_MARK.sub(" ", s)
    out = []
    for piece in BLOCK_END.split(s):
        text = _html.unescape(TAG.sub(" ", piece))
        text = " ".join(text.split())
        if text:
            out.append(text)
    return out


def items_enacting(raw):
    """The enacting terms, the annexes and the source footnotes.

    The body ends at the earlier of two markers: the page's own scripts,
    or the close of <body>. legal-content appends fifteen <script> tags
    of TOC furniture after the last provision, so "<script" was the end
    of the text there; Cellar appends none, and scoping to "<script"
    raised ValueError rather than checking anything - the enacting order
    check simply did not run. Taking the earlier of the two leaves the
    legal-content scope byte-identical to what it was, which is the
    point: this widens where the check WORKS, not what it accepts.
    """
    start = raw.index('<div class="eli-container"')
    ends = [raw.find(m, start) for m in ("<script", "</body")]
    found = [e for e in ends if e != -1]
    if not found:
        raise SystemExit(
            "seqcheck: the raw file ends with neither a <script> nor a "
            "</body> after the eli-container. Look at it before relaxing "
            "this - an unbounded scope silently checks the wrong text.")
    return [{"where": "html", "label": "enacting", "text": t}
            for t in strip(raw[start:min(found)])]


RE_RCT = re.compile(r'<div class="eli-subdivision" id="rct_(\d+)">', re.S)
RE_NOTE = re.compile(r'<p class="oj-note"[^>]*>.*?</p>', re.S)


RE_AFTER_RECITALS = re.compile(r'id="(?:art_1|enc_1|pbl_)')


def items_recitals(raw):
    """Each recital as its own item, plus the OJ notes the corpus keeps.

    The last recital ends where the enacting terms begin. The first
    version of this ran 20,000 characters past it and pulled Article 1
    into "recital 180", which seqcheck then reported as three splices -
    a defect in the harness, not the corpus. The scope of a check is part
    of the check.
    """
    out, marks = [], list(RE_RCT.finditer(raw))
    for i, m in enumerate(marks):
        if i + 1 < len(marks):
            end = marks[i + 1].start()
        else:
            after = RE_AFTER_RECITALS.search(raw, m.end())
            end = after.start() if after else len(raw)
        for t in strip(raw[m.start():end]):
            out.append({"where": f"rct_{m.group(1)}", "label": "recital",
                        "text": t})
    for m in RE_NOTE.finditer(raw):
        for t in strip(m.group(0)):
            out.append({"where": "note", "label": "oj-note", "text": t})
    return out


def load_seqcheck():
    if not SEQCHECK.exists():
        sys.exit(f"seqcheck: {SEQCHECK} not found. It is the instrument this "
                 f"check is built on; without it there is no order check, "
                 f"and pretending otherwise would be worse than failing.")
    spec = importlib.util.spec_from_file_location("seqcheck", SEQCHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(part, sq):
    cfg = PARTS[part]
    raw = (ROOT / cfg["raw"]).read_text("utf-8")
    md = sq.FRONTMATTER.sub("", (ROOT / cfg["md"]).read_text("utf-8"))
    corpus = sq.Corpus(md)
    items = (items_enacting(raw) if part.endswith(":enacting")
             else items_recitals(raw))

    print(f"### {part}: {cfg['md']} vs an independent regex extraction "
          f"of {Path(cfg['raw']).name}")
    print(f"    corpus {len(corpus.stream):,} folded chars, "
          f"{len(items)} source blocks")
    res = sq.check(items, corpus)
    sq.emit(res, "source -> corpus")
    print()
    back = sq.check(sq.corpus_blocks(md), sq.Corpus(sq.index_text(items)),
                    invert=True)
    sq.emit(back, "corpus -> source")
    print()
    splices = len(sq.classify(res["runs"])[0]) + len(sq.classify(back["runs"])[0])
    return splices


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("both", "all"):
        parts = list(PARTS)
    elif which in ("enacting", "recitals"):
        parts = [k for k in PARTS if k.endswith(":" + which)]
    elif which in PARTS:
        parts = [which]
    else:
        sys.exit(f"seqcheck: no such part {which!r}. Known: "
                 f"{', '.join(PARTS)} - or 'enacting'/'recitals' for that "
                 f"part of every instrument, or 'both' for all of them.")
    sq = load_seqcheck()
    print(f"seqcheck {SEQCHECK} (window {sq.W} chars)\n")
    splices = 0
    for p in parts:
        splices += run(p, sq)
        print()
    if splices:
        print(f"FAIL - {splices} splice run(s): the corpus carries text the "
              f"source does not have at that point. That is the shape of "
              f"shredded or duplicated text; read the samples above.")
        return 1
    print("OK - no splices in either direction. Dropouts and absent items, "
          "where present, are the converter's declared drops; check them "
          "against the coverage table in the conversion report.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
