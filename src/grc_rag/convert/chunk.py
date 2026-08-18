#!/usr/bin/env python3
"""The markdown corpus -> retrieval chunks, split on structure, never on tokens.

    python -m grc_rag.convert.chunk --doc corpus/eu/ai-act.md
    python -m grc_rag.convert.chunk --doc corpus/eu/ai-act.recitals.md

THE RULE, AND WHY IT IS NOT A TOKEN WINDOW

A fixed window cuts Article 15 in half mid-sentence and hands the reader
half an obligation with no way to know it. The instrument already has
boundaries a lawyer would recognise, so those are the boundaries:

  articles    the unit. An article longer than SPLIT chars splits at its
              own top-level markers - "1." paragraphs, or "(1)" points
              where the article is a list of definitions - and nowhere
              else. Shorter articles stay whole: a two-sentence article
              cut in two would be two useless chunks.
  recitals    one chunk each. They are single paragraphs by construction.
  annexes     at their own sections first, then at their numbered points,
              by the same length rule. Annex III alone is 7,400
              characters and nobody wants that as one chunk.

Every chunk carries the path it lives at - `EU AI Act › Chapter III ›
Section 2 › Article 15 › (4)` - prepended to the text that gets embedded,
because "paragraph 4" means nothing without it and the lexical leg needs
"Article 15" to be IN the chunk to match on it.

TWO TEXTS PER CHUNK, DELIBERATELY

`body` is the act's words, verbatim and nothing else. `text` is what gets
embedded: the path, the headings, the chapeau where there is one, then
the body. They are separate fields because M4 verifies every quoted span
against a RETRIEVED chunk, and that check has to run against the law's
words, not against a header this file wrote.

THE COVERAGE CHECK, AGAIN, AND STRONGER

Each chunk body must be found in the source markdown, in document order,
starting where the previous one ended. That single check proves three
things at once: nothing was dropped, nothing was duplicated, and nothing
was reordered - the ordering property `tests/seqcheck-corpus.py` needs a
whole instrument for, this one gets for free, because the bodies are
verbatim substrings. Text that no chunk claims is reported by name and
fails the run.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CHUNKER = "grc_rag.convert.chunk/1"

# An article longer than this splits at its own markers. Chosen against
# the corpus, not guessed: the median article is ~2,100 characters and
# the median numbered paragraph ~390, so this leaves short articles whole
# and splits the ones no reader would want in one piece.
SPLIT = 2000
# A chapeau this short is context, not a chunk of its own: "For the
# purposes of this Regulation, the following definitions apply:" answers
# no question. It joins the first chunk's body and is repeated into its
# siblings' embedded text.
CHAPEAU = 400

RE_H = re.compile(r"^(#{1,4})\s+(.*?)(?:\s+\{#([^}]+)\})?\s*$")
RE_MARKER = re.compile(r"^(\d+[a-z]*)\.\s+|^\((\w+)\)\s+")
RE_RECITAL = re.compile(r"^Recital \((\d+)\)$")
RE_ANNEX = re.compile(r"^ANNEX ([IVXL]+)\b")
RE_ARTICLE = re.compile(r"^Article (\d+[a-z]*)\b")
RE_SECTION = re.compile(r"^(Section|Part)\s+([A-Z0-9IVXL]+)", re.I)


def front_matter(text):
    """The `---` block at the top, as a dict. Lists become lists."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.index("\n---\n", 4)
    meta, key = {}, None
    for line in text[4:end].split("\n"):
        if line.startswith("  - ") and key:
            meta.setdefault(key, []).append(line[4:].strip())
        elif ":" in line:
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            meta[key] = value if value else []
    return meta, text[end + 5:]


class Unit:
    """A heading and everything under it, with its ancestors remembered."""

    def __init__(self, level, title, anchor, path):
        self.level, self.title, self.anchor = level, title, anchor
        self.path = path                    # ancestor titles, outermost first
        self.blocks = []                    # (text, offset) in document order


def units(body, offset0):
    """The markdown as a flat list of units, in document order."""
    out, stack, cur = [], [], None
    pos = 0
    for para in re.split(r"\n\s*\n", body):
        start = body.index(para, pos) if para else pos
        pos = start + len(para)
        text = para.strip("\n")
        if not text.strip():
            continue
        h = RE_H.match(text)
        if h:
            level, title, anchor = len(h.group(1)), h.group(2).strip(), h.group(3)
            while stack and stack[-1].level >= level:
                stack.pop()
            # The H1 is the act's full formal title - 500 characters of
            # "…amending Regulations (EC) No 300/2008, (EU) No 167/2013…".
            # Prepending that to every chunk's embedded text buries the
            # part that identifies it and gives every chunk in the corpus
            # the same first 300 characters. The instrument name says the
            # same thing in three words.
            cur = Unit(level, title, anchor,
                       [u.title for u in stack if u.level > 1])
            stack.append(cur)
            out.append(cur)
            continue
        if cur is None:                      # text before any heading
            cur = Unit(0, "", None, [])
            out.append(cur)
        cur.blocks.append((text, start + offset0))
    return out


def groups(blocks):
    """Blocks split into (marker, blocks) runs at their top-level markers.

    A block that starts at column 0 with "4." or "(12)" opens a new run;
    indented points and unnumbered subparagraphs belong to the run they
    follow. Anything before the first marker is the chapeau, marker None.
    """
    out = []
    for text, off in blocks:
        m = RE_MARKER.match(text) if not text.startswith(" ") else None
        if m or not out:
            out.append(((m.group(1) or m.group(2)) if m else None, []))
        out[-1][1].append((text, off))
    return out


def kind_of(unit):
    if RE_RECITAL.match(unit.title):
        return "recital"
    if RE_ANNEX.match(unit.title):
        return "annex"
    if unit.level == 4 and RE_ARTICLE.match(unit.title):
        return "article"
    if unit.level == 3 and RE_SECTION.match(unit.title):
        return "annex-section" if any(RE_ANNEX.match(p) for p in unit.path) \
            else "section"
    if unit.level == 2:
        return "division"
    return "other"


def number_of(kind, title):
    for rx in (RE_RECITAL, RE_ANNEX, RE_ARTICLE, RE_SECTION):
        m = rx.match(title)
        if m:
            return m.group(m.lastindex)
    return None


def label(kind, number, marker):
    """The citation, claiming no more precision than the chunk has.

    A chunk that covers a whole article cites the article. Only a chunk
    that IS one numbered paragraph may cite the paragraph - rendering
    "Article 15(4)" for a chunk holding all of Article 15 would be this
    system's fabrication, not the model's.
    """
    if kind == "recital":
        return f"Recital ({number})"       # the form the act itself uses
    base = {"article": "Article", "annex": "Annex"}.get(kind, "")
    head = f"{base} {number}".strip() if number else ""
    if marker is None:
        return head or "—"
    return f"{head}({marker})"


def chunk_id(stem, anchor, marker):
    return f"{stem}#{anchor}" + (f"({marker})" if marker else "")


def build(doc, meta, src_text, stem):
    """Units in, chunks out. The only place the rules above are applied."""
    out, anomalies = [], []
    body_start = len(src_text) - len(doc)

    for unit in units(doc, body_start):
        kind = kind_of(unit)
        if not unit.blocks:
            continue                        # a heading with only children
        if kind in ("division", "section", "other") and unit.level <= 3 \
                and not unit.blocks:
            continue

        number = number_of(kind, unit.title)
        anchor = unit.anchor or slug(unit)
        path = [meta.get("instrument", "")] + unit.path + [unit.title]
        gs = groups(unit.blocks)
        total = sum(len(t) for _, bl in gs for t, _ in bl)

        # One chunk, or one per marker? Length decides, but only where
        # there is more than one marker to split at.
        markers = [g for g in gs if g[0] is not None]
        if total <= SPLIT or len(markers) < 2:
            merged = [b for _, bl in gs for b in bl]
            out.append(make(meta, kind, number, None, anchor, path, merged,
                            "", stem))
            continue

        chapeau = ""
        if gs[0][0] is None:
            head_text = "\n\n".join(t for t, _ in gs[0][1])
            if len(head_text) <= CHAPEAU:
                chapeau = head_text
                gs = [(markers[0][0], gs[0][1] + markers[0][1])] + markers[1:]
            else:
                gs = [gs[0]] + markers
        for marker, bl in gs:
            out.append(make(meta, kind, number, marker, anchor, path, bl,
                            chapeau if marker != gs[0][0] else "", stem))

    seen = {}
    for c in out:
        if c["id"] in seen:
            anomalies.append(f"duplicate chunk id {c['id']}")
        seen[c["id"]] = 1
    return out, anomalies


def slug(unit):
    """A stable anchor for a heading EUR-Lex gave none - annex sections."""
    m = RE_SECTION.match(unit.title)
    parent = next((p for p in unit.path if RE_ANNEX.match(p)), "")
    pa = RE_ANNEX.match(parent)
    base = f"anx_{pa.group(1)}" if pa else "sec"
    return f"{base}_sct_{m.group(2)}" if m else base


def make(meta, kind, number, marker, anchor, path, blocks, chapeau, stem):
    body = "\n\n".join(t for t, _ in blocks)
    trail = f" › ({marker})" if marker else ""
    parent = " › ".join(p for p in path if p) + trail
    text = parent + "\n\n" + (chapeau + "\n\n" if chapeau else "") + body
    return {
        "id": chunk_id(stem, anchor, marker),
        "instrument": meta.get("instrument"),
        "part": meta.get("part"),
        "kind": kind,
        "unit_number": number,
        "marker": marker,
        "anchor": anchor,
        "citation": label(kind, number, marker),
        "parent_path": parent,
        "celex": meta.get("celex"),
        "source_url": meta.get("source_url"),
        "version_date": meta.get("version_date"),
        "language": meta.get("language", "en"),
        "chars": len(body),
        "offset": blocks[0][1],
        "body": body,
        "text": text,
    }


# ------------------------------------------------------------------ checking

def coverage(chunks, src_text):
    """Every body verbatim in the source, in order, starting after the last.

    Order matters and is free here: a body that exists in the document
    but EARLIER than the previous chunk's end is out of order, and one
    that is not found at all was dropped or altered. Both fail.
    """
    pos, faults, covered = 0, [], 0
    for c in sorted(chunks, key=lambda c: c["offset"]):
        found = src_text.find(c["body"], pos)
        if found < 0:
            elsewhere = src_text.find(c["body"])
            faults.append(
                f"{c['id']}: body not found in the source after offset "
                f"{pos}" + (f" (it is at {elsewhere}, i.e. out of order)"
                            if elsewhere >= 0 else " (not present at all)"))
            continue
        covered += len(c["body"])
        pos = found + len(c["body"])
    return faults, covered


def unclaimed(chunks, doc, body_start):
    """Source paragraphs no chunk carries, headings excepted."""
    claimed = []
    for c in chunks:
        claimed.append((c["offset"], c["offset"] + len(c["body"])))
    claimed.sort()
    out = []
    pos = 0
    for para in re.split(r"\n\s*\n", doc):
        start = doc.index(para, pos)
        pos = start + len(para)
        text = para.strip()
        if not text or RE_H.match(text):
            continue
        off = start + body_start
        if not any(a <= off < b for a, b in claimed):
            out.append(" ".join(text.split())[:100])
    return out


def report(path, doc_path, meta, chunks, faults, unclaimed_paras, anomalies,
           covered, src_text):
    sizes = sorted(c["chars"] for c in chunks)
    by_kind = {}
    for c in chunks:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    L = [f"# Chunk report — {doc_path.name}", "",
         f"`{meta.get('celex')}` ({meta.get('part')}), split by `{CHUNKER}` "
         f"at SPLIT={SPLIT} chars, chapeau≤{CHAPEAU}.", "",
         "Boundaries are the thing to read here. The dump beside this file "
         "carries every chunk in full, in document order.", "",
         "## Counts", "", "| what | n |", "| --- | --- |",
         f"| chunks | {len(chunks)} |"]
    for k, n in sorted(by_kind.items()):
        L.append(f"| … {k} | {n} |")
    L += [f"| whole-unit chunks | {sum(1 for c in chunks if not c['marker'])} |",
          f"| split-at-marker chunks | {sum(1 for c in chunks if c['marker'])} |",
          "", "## Size", "", "| stat | chars |", "| --- | --- |",
          f"| smallest | {sizes[0]:,} |",
          f"| median | {sizes[len(sizes) // 2]:,} |",
          f"| p90 | {sizes[int(0.9 * len(sizes))]:,} |",
          f"| largest | {sizes[-1]:,} |", ""]
    big = [c for c in chunks if c["chars"] > 4000]
    L.append(f"Chunks over 4,000 characters ({len(big)}) — kept whole "
             f"because splitting them would cut inside a single provision:")
    L.append("")
    for c in sorted(big, key=lambda c: -c["chars"])[:10]:
        L.append(f"- `{c['id']}` {c['chars']:,} — {c['citation']}")
    if not big:
        L.append("- none")
    L += ["", "## Coverage", "",
          "Each chunk body must appear in the source markdown verbatim, in "
          "document order, after the previous one ends. That proves nothing "
          "was dropped, duplicated or reordered — a bag-of-words check "
          "proves none of the three.", "",
          f"- {'PASS' if not faults else 'FAIL'} — every body verbatim and in "
          f"order ({len(chunks)} chunks, {covered:,} characters)"]
    for f in faults[:10]:
        L.append(f"  - {f}")
    L += [f"- {'PASS' if not unclaimed_paras else 'FAIL'} — no source "
          f"paragraph left unclaimed ({len(unclaimed_paras)})"]
    for u in unclaimed_paras[:10]:
        L.append(f"  - {u}")
    L += ["", "## Anomalies", ""]
    L += [f"- {a}" for a in anomalies] or ["None."]
    L += ["", "## What this report does not tell you", "",
          "- Whether the boundaries are the RIGHT ones. Coverage proves the "
          "text survived; only reading the dump says whether a chunk answers "
          "a question on its own.",
          "- Nothing about retrieval. A chunk can be perfectly bounded and "
          "still never be retrieved; that is the eval's job in M4.", ""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def dump(path, chunks):
    L = []
    for c in chunks:
        L.append("=" * 78)
        L.append(f"{c['id']}   [{c['citation']}]   {c['chars']:,} chars")
        L.append(c["parent_path"])
        L.append("-" * 78)
        L.append(c["body"])
        L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", required=True,
                    help="a corpus markdown file, named explicitly")
    ap.add_argument("--out-dir", default="corpus/chunks")
    a = ap.parse_args(argv)

    doc_path = Path(a.doc)
    src_text = doc_path.read_text("utf-8")
    meta, body = front_matter(src_text)
    stem = doc_path.name.split(".")[0]
    chunks, anomalies = build(body, meta, src_text, stem)

    faults, covered = coverage(chunks, src_text)
    loose = unclaimed(chunks, body, len(src_text) - len(body))

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = doc_path.name[:-3]
    jsonl = out_dir / f"{name}.chunks.jsonl"
    with jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for c in sorted(chunks, key=lambda c: c["offset"]):
            fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    dump(out_dir / f"{name}.chunks.txt",
         sorted(chunks, key=lambda c: c["offset"]))
    report(out_dir / f"{name}.chunks.report.md", doc_path, meta, chunks,
           faults, loose, anomalies, covered, src_text)

    print(f"{doc_path}  ->  {jsonl}")
    sizes = sorted(c["chars"] for c in chunks)
    print(f"  {len(chunks)} chunks, {covered:,} chars covered, "
          f"median {sizes[len(sizes) // 2]:,}, largest {sizes[-1]:,}")
    print(f"  coverage faults {len(faults)}, unclaimed paragraphs "
          f"{len(loose)}, anomalies {len(anomalies)}")
    return 1 if (faults or loose or anomalies) else 0


if __name__ == "__main__":
    sys.exit(main())
