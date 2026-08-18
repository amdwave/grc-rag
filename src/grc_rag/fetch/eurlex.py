#!/usr/bin/env python3
"""Fetch an act from EUR-Lex, with the identifier discovered rather than remembered.

    python -m grc_rag.fetch.eurlex --celex 32024R1689 --consolidated
    python -m grc_rag.fetch.eurlex --celex 32024R1689 --original

WHY THE DISCOVERY STEP EXISTS

A consolidated CELEX carries the date of the consolidation
(`02024R1689-20260727`), so it changes every time the Commission
consolidates - and a remembered URL that still returns 200 for an older
consolidation is the failure worth preventing: it looks exactly like a
successful fetch. So this asks EUR-Lex which consolidation is current,
prints what it found, and refuses to proceed if `--expect` says something
else. The base act's own page is the source of that answer.

WHAT IS SAVED

The raw bytes exactly as served, plus a manifest recording the URL that
was requested, the URL that answered, the HTTP status, the SHA-256, the
byte count and the UTC timestamp. Both are committed (decisions.md D0):
a consolidated version fetched today stops being downloadable the moment
the next consolidation replaces it, so it fails the cheap-rebuild test
that would otherwise keep it out of git.

WHAT THIS DOES NOT DO

No parsing beyond identifier discovery and a shape check on the response.
Turning HTML into the corpus is `grc_rag.convert.eurlex_html`, which is
in a bucket that may not touch the network - that separation is the point
of the buckets, and this module is the only half allowed out.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://eur-lex.europa.eu/legal-content"
TOOL = "grc-rag/0.1"
UA = f"{TOOL} (personal research corpus; +https://github.com/amdwave/grc-rag)"
TIMEOUT = 90

# The landing page states the current consolidation twice: once in the
# status line, once as a data-celex on the version link. Both are read and
# required to agree - a page redesign that breaks one silently is then a
# visible disagreement rather than a wrong answer. The status line is
# matched against the tag-stripped page: EUR-Lex splits it across an
# <img>, a <span> and a link, so matching the raw HTML finds nothing and
# reports agreement it never tested.
RE_STATUS = re.compile(r"Current consolidated version:\s*"
                       r"(\d{2})/(\d{2})/(\d{4})")
RE_DATACELEX = re.compile(r'data-celex="(0\d{4}[A-Z]\d{4}-\d{8})"')
RE_TITLE = re.compile(r"<title>([^<]*)</title>", re.I)
RE_TAG = re.compile(r"<[^>]+>")

# EUR-Lex stamps a per-response Dynatrace RUM id into the head of every
# page, so two fetches of the same unchanged act differ in their bytes -
# measured: one <script data-dtconfig="…"> attribute, agentId/rid/rpid,
# nothing else. The raw file is still committed exactly as served, but a
# hash that changes on every fetch cannot answer "has the act changed?",
# so the manifest carries both: `sha256` of what arrived and
# `sha256_normalized` of what arrived minus that attribute.
RE_TELEMETRY = re.compile(rb'\sdata-dtconfig="[^"]*"')
NORMALIZATION = ("data-dtconfig attribute removed (per-response Dynatrace "
                 "RUM id; it changes on every fetch and is not document text)")


def flatten(html):
    """Tags to spaces, entities left alone - enough to read a status line."""
    return " ".join(RE_TAG.sub(" ", html).split())


def get(url):
    """One GET, returning (bytes, final url, status, content-type)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return (r.read(), r.geturl(), r.status,
                r.headers.get("Content-Type", ""))


def landing_url(celex):
    return f"{BASE}/EN/TXT/?uri=CELEX%3A{celex}"


def html_url(celex):
    return f"{BASE}/EN/TXT/HTML/?uri=CELEX:{celex}"


def discover(base_celex):
    """Ask EUR-Lex what the current consolidation of `base_celex` is.

    Returns the discovery record that goes into the manifest. Raises if
    the page does not answer, because a fetch that guesses the identifier
    is the thing this function exists to prevent.
    """
    body, final, status, _ = get(landing_url(base_celex))
    text = body.decode("utf-8", "replace")
    if status != 200:
        raise SystemExit(f"eurlex: landing page for {base_celex} returned "
                         f"HTTP {status}")

    ids = sorted(set(RE_DATACELEX.findall(text)))
    mine = [i for i in ids if i[1:].startswith(base_celex[1:])]
    stated = RE_STATUS.search(flatten(text))
    if not mine:
        raise SystemExit(
            f"eurlex: no consolidated version ids on the page for "
            f"{base_celex}. Either the act has never been consolidated or "
            f"the page changed shape - look at it before changing this code.")
    current = max(mine)                       # ids sort by their date suffix
    if not stated:
        raise SystemExit(
            f"eurlex: the page for {base_celex} lists version ids but no "
            f"'Current consolidated version: dd/mm/yyyy' line. That line is "
            f"the second opinion this function depends on; without it the "
            f"newest id is a guess. Look at the page before relaxing this.")
    d, m, y = stated.groups()
    agree = f"{y}{m}{d}" == current.split("-")[1]
    if not agree:
        raise SystemExit(
            f"eurlex: the page says the current consolidated version is "
            f"{d}/{m}/{y} but the newest version id is {current}. "
            f"Refusing to pick one.")
    return {
        "landing_url": final,
        "current_consolidated": current,
        "consolidated_versions": mine,
        "status_line_agrees": agree,
        "doc_title": (RE_TITLE.search(text).group(1).strip()
                      if RE_TITLE.search(text) else None),
    }


def shape_ok(text, celex):
    """Is this the document, or a cookie wall, an error page, a stub?

    EUR-Lex answers 200 for plenty of things that are not the act. Three
    independent properties have to hold, and the failure names which one
    did not - "fetch failed" is not a diagnosis.
    """
    problems = []
    if len(text) < 100_000:
        problems.append(f"only {len(text):,} characters - the act is ~1 MB")
    if "eli-subdivision" not in text:
        problems.append("no eli-subdivision markers - not the structured "
                        "representation the converter parses")
    # The act's own number, not the CELEX: the OJ representation of
    # 32024R1689 never writes that string anywhere - its title is the
    # Formex filename - and an identity check that fires on every
    # correct fetch teaches you to ignore it.
    m = re.match(r"^[0-9](\d{4})([A-Z])(\d{4})", celex)
    if not m:
        problems.append(f"cannot read an act number out of CELEX {celex}")
    else:
        year, num = m.group(1), m.group(3).lstrip("0")
        if f"{year}/{num}" not in text and celex.split("-")[0] not in text:
            problems.append(f"the document mentions neither {year}/{num} nor "
                            f"{celex.split('-')[0]} - wrong act?")
    return problems


def fetch(celex, out_dir, kind, discovery=None):
    url = html_url(celex)
    body, final, status, ctype = get(url)
    text = body.decode("utf-8", "replace")
    problems = shape_ok(text, celex)
    title = RE_TITLE.search(text)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / f"{celex}.en.html"
    raw.write_bytes(body)
    manifest = {
        "schema": "grc-rag/fetch-manifest/1",
        "source": "EUR-Lex",
        "celex": celex,
        "representation": kind,
        "language": "EN",
        "requested_url": url,
        "final_url": final,
        "http_status": status,
        "content_type": ctype,
        "fetched_at_utc": stamp,
        "user_agent": UA,
        "sha256": hashlib.sha256(body).hexdigest(),
        "sha256_normalized": hashlib.sha256(
            RE_TELEMETRY.sub(b"", body)).hexdigest(),
        "normalization": NORMALIZATION,
        "bytes": len(body),
        "raw_file": raw.name,
        "doc_title": title.group(1).strip() if title else None,
        "shape_problems": problems,
        "discovery": discovery,
    }
    (out_dir / f"{celex}.en.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    print(f"  {kind:<17} {celex}")
    print(f"    {status} {ctype.split(';')[0]}  {len(body):,} bytes  "
          f"sha256 {manifest['sha256'][:16]}…")
    print(f"    {raw}")
    if problems:
        print("    SHAPE PROBLEMS - saved anyway, so you can look at it:")
        for p in problems:
            print(f"      - {p}")
    return manifest, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--celex", required=True,
                    help="base act CELEX, e.g. 32024R1689")
    ap.add_argument("--consolidated", action="store_true",
                    help="fetch the current consolidated version "
                         "(enacting terms and annexes; no recitals)")
    ap.add_argument("--original", action="store_true",
                    help="fetch the act as published in the OJ "
                         "(the only representation carrying the recitals)")
    ap.add_argument("--expect", default=None,
                    help="required consolidated id, e.g. 02024R1689-20260727."
                         " Refuses to fetch anything else.")
    ap.add_argument("--out", default="corpus/raw/eu/ai-act",
                    help="directory for the raw file and its manifest")
    a = ap.parse_args(argv)
    if not (a.consolidated or a.original):
        ap.error("choose --consolidated, --original, or both")

    out = Path(a.out)
    print(f"EUR-Lex fetch - base act {a.celex}")
    problems = []
    try:
        disc = discover(a.celex)
    except urllib.error.URLError as e:
        raise SystemExit(f"eurlex: cannot reach EUR-Lex: {e}")
    print(f"  consolidated versions on the page: "
          f"{', '.join(disc['consolidated_versions'])}")
    print(f"  current: {disc['current_consolidated']}"
          f"  (status line agrees: {disc['status_line_agrees']})")
    if a.expect and a.expect != disc["current_consolidated"]:
        raise SystemExit(
            f"eurlex: --expect {a.expect} but EUR-Lex now says "
            f"{disc['current_consolidated']} is current. The act has been "
            f"consolidated again: re-fetch deliberately, re-convert, and "
            f"read the diff - do not paper over this.")

    if a.consolidated:
        _, p = fetch(disc["current_consolidated"], out, "consolidated-html",
                     disc)
        problems += p
    if a.original:
        _, p = fetch(a.celex, out, "oj-html", disc)
        problems += p
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
