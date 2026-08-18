#!/usr/bin/env python3
"""EUR-Lex HTML -> the canonical markdown corpus, with every character accounted for.

    python -m grc_rag.convert.eurlex_html \\
        --raw corpus/raw/eu/ai-act/02024R1689-20260727.en.html \\
        --part enacting --out corpus/eu/ai-act.md

    python -m grc_rag.convert.eurlex_html \\
        --raw corpus/raw/eu/ai-act/32024R1689.en.html \\
        --part recitals --out corpus/eu/ai-act.recitals.md

TWO SKINS, ONE SPINE

EUR-Lex serves the same act in two different HTML vocabularies: the
consolidated text comes from CONVEX (`p.title-article-norm`, `div.norm`,
`div.grid-container.grid-list`) and the Official Journal text comes from
Formex (`p.oj-ti-art`, `p.oj-normal`, two-column `<table>`). What both
share is the ELI spine: `div.eli-subdivision` carrying structural ids -
`art_15`, `rct_47`, `anx_III`. The spine is what this parser trusts;
the classes only say what role a paragraph plays.

WHY TWO SOURCE DOCUMENTS

The consolidated version contains NO recitals - EUR-Lex consolidations
carry the enacting terms and annexes only, and this act's consolidation
is the current law after Regulation (EU) 2026/1744. The recitals exist
only in the original OJ publication. So the corpus is two files with two
provenances rather than one file that quietly mixes them:

    corpus/eu/ai-act.md            enacting terms + annexes, 02024R1689-<date>
    corpus/eu/ai-act.recitals.md   recitals,                 32024R1689

Each carries its own CELEX, URL and source hash in its front matter, so a
chunk can always say which document it came from and as of when.

COVERAGE IS THE CHECK

Counting what came out says nothing about what was left behind. So every
text node in the body is accounted for exactly once: emitted, or dropped
by a NAMED rule with its character count printed in the report. Text that
is neither is `unaccounted`, and unaccounted text fails the run. That is
the check that catches a converter silently walking past a subtree,
which no output-side count can see.

WHAT THIS DOES NOT DO

  * It does not preserve italics, bold or superscript formatting: the
    corpus is text for retrieval and diffing. Footnote reference marks
    are removed from the running text (they would otherwise appear as
    bare digits mid-sentence) and the footnote texts themselves are
    emitted in their own section.
  * It does not keep the consolidation's amendment markers (`▼B`,
    `►M1◄`) inline. They are editorial apparatus, not the act's words,
    and inline they would poison retrieval. The acts that amended the
    text are recorded in the front matter instead.
  * It does not verify the text against anything. Ordering is checked
    against an independent extraction by `tests/seqcheck-corpus.py`,
    which is deliberately not this code.
"""
import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

CONVERTER = "grc_rag.convert.eurlex_html/1"
VOID = {"br", "hr", "img", "meta", "link", "col", "input", "area", "base"}
INDENT = "   "                       # per nesting level; see the note in emit()

# Text that is deliberately not part of the corpus. Every rule here is
# printed in the report with the number of characters it removed - a drop
# nobody can see is indistinguishable from a bug.
DROP_RULES = {
    "script": "<script>/<style> payloads",
    "reference": "the consolidation's running reference line",
    "disclaimer": "the 'no legal effect' disclaimer",
    "modifiers-toc": "the 'Amended by' table of amending acts",
    "amendment-marker": "▼B / ►M1◄ consolidation markers",
    "note-mark": "superscript footnote reference marks",
    "eli-line": "the trailing ELI / ISSN publication lines",
    "oj-masthead": "the Official Journal masthead and issue line",
    "not-this-part": "structure belonging to the other output file",
}


class Node:
    __slots__ = ("tag", "attrs", "kids", "parent", "text", "state")

    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.kids, self.text, self.state = [], "", None

    cls = property(lambda self: self.attrs.get("class", ""))
    ident = property(lambda self: self.attrs.get("id", ""))

    def has(self, name):
        return name in self.cls.split()


class DOM(HTMLParser):
    """Small forgiving tree. stdlib only: this bucket may not add one."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        # Whitespace-only nodes are KEPT. EUR-Lex separates a point's
        # number from its text with a non-breaking space in its own
        # element, and `str.strip()` treats U+00A0 as whitespace - so
        # dropping blank nodes silently produced "2.Directive 2009/48/EC".
        # They cost nothing in the coverage pass, which counts stripped
        # characters.
        n = Node("#text", {}, self.cur)
        n.text = data
        self.cur.kids.append(n)


def parse(html):
    d = DOM()
    d.feed(html)
    body = descend(d.root, lambda n: n.tag == "body")
    if body is None:
        raise SystemExit("convert: no <body> - is this the HTML "
                         "representation?")
    return body


def descend(node, pred):
    if pred(node):
        return node
    for k in node.kids:
        r = descend(k, pred)
        if r is not None:
            return r
    return None


def texts(node, out=None):
    """Every text node under `node`, in document order."""
    out = [] if out is None else out
    if node.tag == "#text":
        out.append(node)
    for k in node.kids:
        texts(k, out)
    return out


def mark(node, state):
    for t in texts(node):
        if t.state is None:
            t.state = state


# ------------------------------------------------------------------ inline text

SPACE = re.compile(r"[\s ]+")


def inline(node, drops):
    """The readable text of a node, with the apparatus removed and counted.

    Footnote marks and amendment markers are removed HERE rather than in
    a post-pass over the string: at this point they are still identifiable
    elements. Once flattened, `(5)` in the middle of a recital is
    indistinguishable from the act's own numbering, and stripping it by
    shape deletes the act's text.
    """
    parts = []

    def walk(n):
        if n.tag == "#text":
            n.state = "emitted"
            parts.append(n.text)
            return
        if n.tag in ("script", "style"):
            drop(n, "script", drops)
            return
        if n.has("modref") or n.has("arrow"):
            drop(n, "amendment-marker", drops)
            return
        if n.has("oj-note-tag") or (n.tag == "span" and n.has("superscript")):
            drop(n, "note-mark", drops)
            return
        for k in n.kids:
            walk(k)

    walk(node)
    return SPACE.sub(" ", "".join(parts)).strip()


def drop(node, rule, drops):
    n = 0
    for t in texts(node):
        if t.state is None:
            t.state = f"drop:{rule}"
            n += len(t.text.strip())
    drops[rule] = drops.get(rule, 0) + n


# ------------------------------------------------------------------ block render

MARKER = re.compile(r"^\(?([0-9]+[a-z]?|[a-z]{1,2}|[ivxlc]+)\)?\.?$", re.I)


def pair(node):
    """(marker, body node) for a marker/text pair, or None.

    Both skins express "(a) some text" as two cells: CONVEX as a
    grid-list div, Formex as a two-column table row. One function reads
    both, because the difference is presentational and the meaning is
    identical.
    """
    if node.tag == "div" and node.has("grid-list"):
        cols = [k for k in node.kids if k.tag in ("div", "p")]
        if len(cols) == 2:
            return cols[0], cols[1]
    if node.tag == "table":
        rows = [r for r in descendants(node) if r.tag == "tr"]
        if len(rows) == 1:
            cells = [c for c in rows[0].kids if c.tag == "td"]
            if len(cells) == 2:
                return cells[0], cells[1]
    return None


def descendants(node, out=None):
    out = [] if out is None else out
    for k in node.kids:
        out.append(k)
        descendants(k, out)
    return out


def is_table(node):
    """A real content table: more than one row, or more than two columns."""
    if node.tag != "table":
        return False
    rows = [r for r in descendants(node) if r.tag == "tr"]
    if len(rows) > 1:
        return True
    return bool(rows) and len([c for c in rows[0].kids if c.tag == "td"]) != 2


# Heading elements the render pass met but nobody had read. Collected
# here rather than threaded through six call sites; `convert()` clears it
# on entry and folds it into the report's anomalies, and it holds text,
# not state, so reruns stay byte-identical.
UNREAD_HEADINGS = []

HEADING = ("title-article-norm", "stitle-article-norm", "oj-ti-art",
           "oj-sti-art", "title-annex-1", "title-annex-2", "oj-doc-ti",
           "title-division-1", "title-division-2")


def is_heading(node):
    return any(node.has(c) for c in HEADING) or node.has("eli-title")


def structural(node):
    """Does this node introduce its own block, rather than run-on text?"""
    return pair(node) is not None or is_table(node)


def render(node, depth, out, drops):
    """One structural node to markdown lines, recursively.

    Indentation is 3 spaces per level and nothing deeper is ever emitted
    as an indented block, so no legal point can be mistaken for a code
    fence by a markdown renderer - a level's indent is always shorter
    than its parent's content column, so each level dedents out of the
    parent list item instead of nesting into it.
    """
    if node.tag in ("script", "style"):
        drop(node, "script", drops)
        return
    if node.tag in ("hr", "br", "col", "colgroup"):
        return
    if node.has("modref") or node.has("arrow"):
        drop(node, "amendment-marker", drops)
        return
    if is_heading(node):
        # Already written as the markdown heading - but only if something
        # actually read it. An unread heading element used to be marked
        # "emitted" here regardless, which is how Annex X's title went
        # missing while the coverage table still said nothing was left
        # behind. Unread heading text is rendered as a paragraph rather
        # than lost, and named in the report.
        if any(t.state is None and t.text.strip() for t in texts(node)):
            text = inline(node, drops)
            if text:
                out.append(INDENT * depth + text)
                UNREAD_HEADINGS.append(text[:80])
        return

    p = pair(node)
    if p is not None:
        m, body = p
        marker = inline(m, drops)
        points(body, depth, out, drops, marker)
        return

    if is_table(node):
        table(node, depth, out, drops)
        return

    # A numbered paragraph in the consolidated skin: <span class="no-parag">
    # holds "1." and the sibling div holds the paragraph's first sentence.
    nums = [k for k in node.kids if k.tag == "span" and k.has("no-parag")]
    if nums:
        marker = inline(nums[0], drops)
        rest = Node("div", {}, node.parent)
        rest.kids = [k for k in node.kids if k is not nums[0]]
        points(rest, depth, out, drops, marker)
        return

    if node.has("title-gr-seq-level-1") or node.has("title-gr-seq-level-2") \
            or node.has("oj-ti-grseq-1"):
        # The annexes' own divisions. EUR-Lex gives this class both to
        # "Section A. …" and to bare "1." point markers, so the text
        # decides: a named division becomes a heading, a marker stays a
        # marker. Making all of them headings would have turned Annex IV's
        # points into sections.
        text = inline(node, drops)
        if RE_SUBDIVISION.match(text):
            out.append(f"### {text}")
        elif text and out and RE_BARE_DIVISION.match(out[-1]):
            # "Section 1" and its title are two sibling elements in
            # Annex XI, exactly as chapters are in the enacting terms.
            out[-1] = f"{out[-1]} — {text}"
        elif text:
            out.append(INDENT * depth + text)
        return

    if node.tag in ("p", "span", "#text") or node.has("norm") \
            or node.has("oj-normal") or node.has("list"):
        # A paragraph that carries points inside it - "…lays down:" followed
        # by (a), (b), (c) - is not one paragraph. Flattening it was the
        # second bug the coverage pass could not see: the characters were
        # all present, glued into one line, which is exactly the class of
        # defect only a sequence check or an eye catches.
        if any(structural(k) for k in node.kids):
            points(node, depth, out, drops, "")
            return
        text = inline(node, drops)
        if text:
            out.append(INDENT * depth + text)
        return

    for k in node.kids:
        render(k, depth, out, drops)


def points(body, depth, out, drops, marker):
    """A block's own text at `depth`, the points it introduces one deeper.

    `marker` is the number or letter this block is labelled with; it is
    prefixed to the first line of text, or emitted alone if the block is
    nothing but a label.
    """
    kids = [k for k in body.kids
            if not (k.tag == "#text" and not k.text.strip())]
    lead, first = [], True
    for k in kids:
        sub = []
        render(k, depth + 1 if structural(k) else depth, sub, drops)
        if sub and first and marker and not structural(k):
            sub[0] = INDENT * depth + f"{marker} {sub[0].lstrip()}"
            first = False
        lead.extend(sub)
    if first and marker:
        if lead:                       # label, then only nested structure
            lead.insert(0, INDENT * depth + marker)
        else:
            lead.append(INDENT * depth + marker)
    out.extend(lead)


def table(node, depth, out, drops):
    """A real table, as a markdown pipe table. Annex XIV is the only one."""
    rows = []
    for tr in [r for r in descendants(node) if r.tag == "tr"]:
        cells = [inline(c, drops).replace("|", "\\|")
                 for c in tr.kids if c.tag in ("td", "th")]
        if any(cells):
            rows.append(cells)
    if not rows:
        return
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    pad = INDENT * depth
    out.append(pad + "| " + " | ".join(rows[0]) + " |")
    out.append(pad + "|" + "|".join([" --- "] * width) + "|")
    for r in rows[1:]:
        out.append(pad + "| " + " | ".join(r) + " |")


def block(node, drops, depth=0):
    """Render a node and return its markdown paragraphs, blank-separated."""
    out = []
    for k in node.kids:
        render(k, depth, out, drops)
    return [line for line in out if line.strip()]


# ------------------------------------------------------------------ the parts

RE_ART = re.compile(r"^art_([0-9]+[a-z]*)$")
RE_RCT = re.compile(r"^rct_([0-9]+)$")
RE_ANX = re.compile(r"^anx_([IVXL]+[a-z]*)$")
RE_DIVISION = re.compile(r"^(CHAPTER|SECTION|TITLE)\s+([IVXL0-9]+)", re.I)
RE_SUBDIVISION = re.compile(r"^(Section|Part|Chapter|Title)\s+"
                            r"[A-Z0-9IVXL]+\s*[.:—-]?(\s+\S.*)?$", re.I)
RE_BARE_DIVISION = re.compile(r"^### (Section|Part|Chapter|Title)\s+"
                              r"[A-Z0-9IVXL]+\s*[.:—-]?$", re.I)


def heading_of(node, drops):
    """(number text, title text) for an article, from either skin."""
    num = descend(node, lambda n: n.has("title-article-norm")
                  or n.has("oj-ti-art"))
    tit = descend(node, lambda n: n.has("stitle-article-norm")
                  or n.has("oj-sti-art"))
    return (inline(num, drops) if num is not None else "",
            inline(tit, drops) if tit is not None else "")


RE_CONTAINER = re.compile(r"^(enc_|cpt_|tit_|pbl_)")


def is_container(node):
    """A wrapper that holds structure rather than text of its own.

    The consolidation nests chapter and section divs (`cpt_III`,
    `cpt_III.sct_2`) but gives them no class, so containers are
    recognised by id shape and by being a classless div. Recursing is
    what the first version of this walk got wrong: it treated the body's
    children as the whole document and silently left 332,493 characters
    - the entire enacting text - unvisited. The coverage pass is what
    said so.
    """
    if node.tag != "div":
        return False
    if RE_CONTAINER.match(node.ident) or ".sct_" in node.ident:
        return True
    return node.has("eli-container") or (not node.ident and not node.cls)


def contains_id(node, prefix):
    if node.ident.startswith(prefix):
        return True
    return any(contains_id(k, prefix) for k in node.kids)


def anchor_for(node):
    """The nearest enclosing structural id, as a markdown-safe anchor."""
    n = node.parent
    while n is not None:
        if n.ident and (RE_CONTAINER.match(n.ident) or ".sct_" in n.ident):
            return n.ident.replace(".", "_")
        n = n.parent
    return None


def convert(body, part, drops, anomalies):
    """Document order in, markdown sections out."""
    md, struct = [], {"articles": [], "recitals": [], "annexes": [],
                      "chapters": [], "sections": [], "footnotes": 0,
                      "tables": 0, "formula": False}
    UNREAD_HEADINGS.clear()

    def walk(node):
        ident, cls = node.ident, node.cls
        if node.tag in ("script", "style"):
            drop(node, "script", drops)
            return
        if node.tag in ("hr", "br", "col", "colgroup"):
            return
        if node.tag == "#text":
            return                        # whitespace between blocks
        if node.has("modref") or node.has("arrow"):
            drop(node, "amendment-marker", drops)
            return
        if node.has("reference") or node.has("disclaimer"):
            drop(node, "disclaimer" if node.has("disclaimer") else "reference",
                 drops)
            return
        if node.has("hd-modifiers"):
            drop(node, "modifiers-toc", drops)
            return

        m = RE_RCT.match(ident)
        if m:
            if part != "recitals":
                drop(node, "not-this-part", drops)
                return
            num = m.group(1)
            cells = pair(descend(node, lambda n: n.tag == "table") or node)
            if cells is None:
                text = inline(node, drops)
            else:
                printed = inline(cells[0], drops)
                text = inline(cells[1], drops)
                if printed.strip("() ") != num:
                    anomalies.append(
                        f"recital {num}: printed marker is {printed!r}")
            md.append(f"## Recital ({num}) {{#rct_{num}}}")
            md.append(text)
            struct["recitals"].append(num)
            return

        m = RE_ART.match(ident)
        if m:
            if part != "enacting":
                drop(node, "not-this-part", drops)
                return
            num, title = heading_of(node, drops)
            for sel in (lambda n: n.has("title-article-norm") or n.has("oj-ti-art"),
                        lambda n: n.has("eli-title")):
                h = descend(node, sel)
                if h is not None:
                    mark(h, "emitted")
            md.append(f"#### {num}" + (f" — {title}" if title else "")
                      + f" {{#art_{m.group(1)}}}")
            md.extend(block(node, drops))
            struct["articles"].append(m.group(1))
            if not title:
                anomalies.append(f"article {m.group(1)}: no title element")
            elif re.search(r"[’'\"]$", title):
                anomalies.append(
                    f"article {m.group(1)}: title ends with a stray quote - "
                    f"{title!r}. It is in EUR-Lex's own HTML and is kept "
                    f"verbatim; the corpus does not correct its source.")
            return

        m = RE_ANX.match(ident)
        if m:
            if part != "enacting":
                drop(node, "not-this-part", drops)
                return
            # Annex X labels BOTH its heading lines `title-annex-1`
            # (15 of that class against 12 `title-annex-2`, for 14
            # annexes), so reading the title by class alone lost the
            # title of Annex X entirely - counted as emitted, never
            # written. The heading elements are taken in document order
            # instead: first is the label, whatever follows is the title.
            heads = [n for n in descendants(node)
                     if n.has("title-annex-1") or n.has("title-annex-2")
                     or n.has("oj-doc-ti")]
            label = (inline(heads[0], drops) if heads
                     else f"ANNEX {m.group(1)}")
            title = " ".join(x for x in
                             (inline(h, drops) for h in heads[1:]) if x)
            md.append(f"## {label}" + (f" — {title}" if title else "")
                      + f" {{#anx_{m.group(1)}}}")
            md.extend(block(node, drops))
            struct["annexes"].append(m.group(1))
            struct["tables"] += len([n for n in descendants(node)
                                     if is_table(n)])
            return

        if ident.startswith("fnp_"):
            if part != "enacting":
                drop(node, "not-this-part", drops)
                return
            md.append("## Formula {#formula}")
            md.extend(block(node, drops))
            struct["formula"] = True
            return

        if node.has("eli-main-title") or node.has("title-doc-first") \
                or node.has("title-doc-last") \
                or node.has("title-doc-oj-reference") \
                or node.has("oj-hd-ti") or node.has("oj-hd-coll") \
                or node.has("oj-hd-lg") or node.has("oj-hd-date") \
                or node.has("oj-hd-uniq"):
            drop(node, "reference", drops)   # the H1 carries the title instead
            return

        if part == "enacting":
            if node.has("title-division-1") or node.has("oj-ti-section-1"):
                label = inline(node, drops)
                kind = (RE_DIVISION.match(label).group(1).lower()
                        if RE_DIVISION.match(label) else "chapter")
                anchor = anchor_for(node)
                md.append(("### " if kind == "section" else "## ") + label
                          + (f" {{#{anchor}}}" if anchor else ""))
                (struct["sections"] if kind == "section"
                 else struct["chapters"]).append(label)
                return
            if node.has("title-division-2") or node.has("oj-ti-section-2"):
                title = inline(node, drops)
                if md and md[-1].startswith("#"):
                    head, _, anch = md[-1].partition(" {#")
                    md[-1] = f"{head} — {title}" + (f" {{#{anch}" if anch
                                                    else "")
                else:
                    md.append(f"## {title}")
                return
            if node.has("footnote") or node.has("oj-note"):
                struct["footnotes"] += 1
                if struct["footnotes"] == 1:
                    md.append("## Source footnotes {#footnotes}")
                md.append(inline(node, drops))
                return
            if node.tag == "table" and not ident:
                drop(node, "modifiers-toc", drops)
                return
            if node.has("oj-normal"):
                drop(node, "eli-line", drops)
                return
        else:
            # Recitals file: the same document also carries the articles,
            # the annexes and the OJ masthead. They are the other file's
            # job, dropped by name rather than walked into.
            if node.tag == "table" and not ident:
                drop(node, "oj-masthead", drops)
                return
            if node.has("oj-note"):
                struct["footnotes"] += 1
                if struct["footnotes"] == 1:
                    md.append("## Source notes {#notes}")
                md.append(inline(node, drops))
                return
            if is_container(node) and not contains_id(node, "rct_"):
                drop(node, "not-this-part", drops)
                return
            if not is_container(node):
                drop(node, "not-this-part", drops)
                return

        if is_container(node):
            for k in node.kids:
                walk(k)
            return

        if any(t.text.strip() for t in texts(node)):
            # Nothing claimed it, and it is left unmarked on purpose: the
            # coverage pass reports it as unaccounted, which fails the run.
            anomalies.append(
                f"unhandled element <{node.tag} class={cls!r} id={ident!r}>: "
                f"{inline_preview(node)}")

    for kid in body.kids:
        walk(kid)
    for text in UNREAD_HEADINGS:
        anomalies.append(
            f"heading element no heading rule read, emitted as a paragraph "
            f"so it is not lost: {text!r}")
    return md, struct


def inline_preview(node):
    t = " ".join(" ".join(x.text for x in texts(node)).split())
    return (t[:90] + "…") if len(t) > 90 else t


def slug(heading):
    s = re.sub(r"[^a-z0-9]+", "_", heading.lower().lstrip("# ")).strip("_")
    return s[:40]


# ------------------------------------------------------------------ the report

def sequence_gaps(nums):
    """Numbering that skips or repeats, as a list of human sentences.

    Inserted articles are lettered (4a, 60a, 75a-d), which is normal in a
    consolidation and must not be reported as a gap - only the numeric
    part is required to be non-decreasing, and a repeat of the same
    numeric stem is only allowed when the letters differ.
    """
    out, prev, seen = [], 0, set()
    for n in nums:
        m = re.match(r"^(\d+)([a-z]*)$", n)
        if not m:
            out.append(f"{n}: not a number")
            continue
        v = int(m.group(1))
        if n in seen:
            out.append(f"{n}: appears twice")
        seen.add(n)
        if v < prev:
            out.append(f"{n}: out of order after {prev}")
        elif v > prev + 1 and not m.group(2):
            out.append(f"{n}: follows {prev} - "
                       f"{v - prev - 1} missing in between")
        prev = max(prev, v)
    return out


def roman_gaps(items):
    order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
             "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
             "XX"]
    out, prev = [], -1
    for it in items:
        if it not in order:
            out.append(f"{it}: not a roman numeral this check knows")
            continue
        i = order.index(it)
        if i != prev + 1:
            out.append(f"ANNEX {it}: follows "
                       f"{order[prev] if prev >= 0 else 'nothing'}")
        prev = i
    return out


def paragraph_runs(md):
    """Top-level numbered paragraphs, per heading they sit under.

    Keyed by every heading, not only articles: the annexes number their
    own points from 1 and the first version of this check, which reset
    only on `#### Article`, read all fourteen annexes as a continuation
    of Article 113 and reported a 75-element run. The check was wrong,
    not the corpus.
    """
    runs, cur = {}, None
    for line in md:
        if line.startswith("#"):
            cur = line.lstrip("# ").split(" {#")[0][:60]
            runs.setdefault(cur, [])
            continue
        m = re.match(r"^(\d+)([a-z]*)\.\s", line)      # column 0 only
        if m and cur:
            runs[cur].append((int(m.group(1)), m.group(2)))
    return {k: v for k, v in runs.items() if v}


def numbering_faults(runs):
    """Repeats and reversals fail; gaps are reported but do not.

    A consolidation legitimately omits deleted provisions - Article 10(5)
    was repealed by Regulation (EU) 2026/1744 and the source prints
    1, 2, 3, 4, 6. Failing on that would train the reader to ignore this
    check. What no legitimate source does is repeat a number or go
    backwards, and that is what text shredded into the wrong order looks
    like.
    """
    faults, gaps = [], []
    for head, seq in runs.items():
        prev, seen = 0, set()
        for v, letter in seq:
            key = f"{v}{letter}"
            if key in seen:
                faults.append(f"{head}: paragraph {key} appears twice")
            elif v < prev:
                faults.append(f"{head}: paragraph {key} follows {prev}")
            elif v > prev + 1 and prev == 0:
                # Numbering that continues across a division (Annex I
                # Section B starts at 13) is not a gap. Reported anyway,
                # in its own words, because a repealed first point looks
                # identical from here and the reader is the one who can
                # tell them apart.
                gaps.append(f"{head}: numbering starts at {v}, not 1")
            elif v > prev + 1:
                gaps.append(f"{head}: {v} follows {prev} "
                            f"({v - prev - 1} not present)")
            seen.add(key)
            prev = max(prev, v)
    return faults, gaps


def report(path, meta, struct, drops, unaccounted, anomalies, md, source):
    L = []
    a = L.append
    a(f"# Conversion report — {meta['title']}")
    a("")
    a(f"Source `{meta['celex']}` ({meta['representation']}), "
      f"converted by `{CONVERTER}`.")
    a(f"Raw file sha256 `{meta['source_sha256'][:32]}…`, "
      f"{source['bytes']:,} bytes fetched {source['fetched_at_utc']}.")
    a("")
    a("Read this by eye. In book2rag every real conversion bug was "
      "invisible in the totals and obvious on sight.")
    a("")
    a("## Counts")
    a("")
    a("| what | n |")
    a("| --- | --- |")
    for k in ("chapters", "sections", "articles", "recitals", "annexes"):
        if struct[k]:
            a(f"| {k} | {len(struct[k])} |")
    a(f"| tables rendered | {struct['tables']} |")
    a(f"| source footnotes | {struct['footnotes']} |")
    a(f"| markdown lines | {len(md)} |")
    a(f"| characters emitted | {sum(len(x) for x in md):,} |")
    a("")
    a("## Structure checks")
    a("")
    checks = []
    if struct["articles"]:
        checks.append(("article numbering continuous "
                       "(lettered insertions allowed)",
                       sequence_gaps(struct["articles"])))
    if struct["recitals"]:
        checks.append(("recital numbering continuous",
                       sequence_gaps(struct["recitals"])))
    if struct["annexes"]:
        checks.append(("annexes in order", roman_gaps(struct["annexes"])))
    faults, gaps = numbering_faults(paragraph_runs(md))
    checks.append(("numbered paragraphs never repeat or run backwards",
                   faults))
    empty = [h for h, nxt in zip(md, md[1:] + [""])
             if h.startswith("####") and (nxt.startswith("#") or not nxt)]
    checks.append(("no article heading with no text under it", empty))
    for name, problems in checks:
        a(f"- {'PASS' if not problems else 'FAIL'} — {name}"
          + ("" if not problems else f" ({len(problems)})"))
        for p in problems[:12]:
            a(f"  - {p}")
    a("")
    a("Numbering gaps, which a consolidation makes legitimately when a "
      "provision is repealed — read them, do not assume them:")
    a("")
    if gaps:
        for g in gaps[:20]:
            a(f"- {g}")
        if len(gaps) > 20:
            a(f"- … and {len(gaps) - 20} more")
    else:
        a("- none")
    a("")
    a("## Coverage — every character in the source body, accounted for")
    a("")
    a("A count of what came out cannot see what was left behind. Each text "
      "node in the body is emitted or dropped by a named rule; anything "
      "else is unaccounted and fails the run.")
    a("")
    a("| disposition | characters |")
    a("| --- | --- |")
    a(f"| emitted | {meta['emitted_chars']:,} |")
    for rule, n in sorted(drops.items(), key=lambda kv: -kv[1]):
        a(f"| dropped: {rule} — {DROP_RULES.get(rule, '?')} | {n:,} |")
    a(f"| **unaccounted** | **{sum(len(t.text.strip()) for t in unaccounted):,}"
      f"** |")
    a("")
    if unaccounted:
        a("### Unaccounted text (this is a failure)")
        a("")
        for t in unaccounted[:25]:
            where = t.parent
            a(f"- `<{where.tag} class={where.cls!r} id={where.ident!r}>` "
              f"{' '.join(t.text.split())[:120]}")
        if len(unaccounted) > 25:
            a(f"- … and {len(unaccounted) - 25} more")
        a("")
    a("## Anomalies")
    a("")
    if anomalies:
        for x in anomalies[:40]:
            a(f"- {x}")
        if len(anomalies) > 40:
            a(f"- … and {len(anomalies) - 40} more")
    else:
        a("None.")
    a("")
    a("## What this report does not tell you")
    a("")
    a("- Nothing here is order-sensitive. Text shredded into the wrong "
      "order leaves every count above unchanged; `tests/seqcheck-corpus.py` "
      "is the check that sees it.")
    a("- Formatting (italics, bold, superscripts) is not preserved and is "
      "not counted as a loss.")
    a("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ front matter

def front_matter(meta):
    L = ["---"]
    for k, v in meta.items():
        if v is None or k == "emitted_chars":
            continue
        if isinstance(v, list):
            L.append(f"{k}:")
            L.extend(f"  - {x}" for x in v)
        else:
            L.append(f"{k}: {v}")
    L.append("---")
    return L


def amending_acts(body):
    """CELEX ids of the acts this consolidation folds in, in page order."""
    out = []
    for n in descendants(body):
        href = n.attrs.get("href", "")
        m = re.search(r"celex:(3\d{4}[A-Z]\d{4})", href, re.I)
        if m and m.group(1).upper() not in out:
            out.append(m.group(1).upper())
    return out


def doc_title(body, drops):
    node = descend(body, lambda n: n.has("eli-main-title"))
    if node is None:
        node = descend(body, lambda n: n.has("oj-doc-ti"))
    return inline(node, drops) if node is not None else ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True)
    ap.add_argument("--part", required=True, choices=("enacting", "recitals"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--instrument", default="EU AI Act")
    ap.add_argument("--report", default=None,
                    help="default: the output stem plus .report.md")
    a = ap.parse_args(argv)

    raw = Path(a.raw)
    src = json.loads(raw.with_name(raw.name.replace(".html", ".manifest.json"))
                     .read_text("utf-8"))
    html = raw.read_text("utf-8")
    body = parse(html)

    drops, anomalies = {}, []
    title = doc_title(body, drops)
    md, struct = convert(body, a.part, drops, anomalies)

    unaccounted = [t for t in texts(body) if t.state is None and t.text.strip()]
    emitted = sum(len(t.text.strip()) for t in texts(body)
                  if t.state == "emitted")

    celex = src["celex"]
    vdate = celex.split("-")[1] if "-" in celex else None
    meta = {
        "instrument": a.instrument,
        "title": title or src.get("doc_title") or celex,
        "part": ("enacting terms and annexes" if a.part == "enacting"
                 else "recitals"),
        "celex": celex,
        "representation": src["representation"],
        "version_date": (f"{vdate[:4]}-{vdate[4:6]}-{vdate[6:]}"
                         if vdate else None),
        "language": "en",
        "source_url": src["requested_url"],
        "source_sha256": src["sha256"],
        "source_sha256_normalized": src.get("sha256_normalized"),
        "fetched_at_utc": src["fetched_at_utc"],
        "converter": CONVERTER,
        "amended_by": (amending_acts(body) if a.part == "enacting" else None),
        "emitted_chars": emitted,
    }

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(front_matter(meta) + [""] + [f"# {meta['title']}", ""]
                     + interleave(md)) + "\n"
    out.write_text(text, encoding="utf-8")

    rep = Path(a.report) if a.report else out.with_suffix(".report.md")
    report(rep, meta, struct, drops, unaccounted, anomalies, md, src)

    print(f"{a.part:9} {celex}  ->  {out}")
    print(f"  {len(md)} blocks, {emitted:,} chars emitted, "
          f"{sum(drops.values()):,} dropped by rule, "
          f"{sum(len(t.text.strip()) for t in unaccounted):,} unaccounted")
    print(f"  articles {len(struct['articles'])}  recitals "
          f"{len(struct['recitals'])}  annexes {len(struct['annexes'])}  "
          f"anomalies {len(anomalies)}")
    print(f"  report: {rep}  sha256 "
          f"{hashlib.sha256(out.read_bytes()).hexdigest()[:16]}…")
    if unaccounted:
        print(f"  FAIL: {len(unaccounted)} text node(s) neither emitted nor "
              f"dropped by a named rule - see the report")
    return 1 if unaccounted else 0


def interleave(md):
    """A blank line between blocks - except inside a table.

    Markdown tables are the one construct here whose rows have to be
    adjacent; a blank line between them turns each row into its own
    paragraph of pipes, which is what Annex XIV rendered as at first.
    """
    out = []
    for line in md:
        if out and not (out[-1].lstrip().startswith("|")
                        and line.lstrip().startswith("|")):
            out.append("")
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
