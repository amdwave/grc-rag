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

TWO ACCESS ROUTES, ONE DOCUMENT

EUR-Lex's human site (`legal-content`) sits behind an AWS WAF bot
challenge: as of 2026-08-18 it answers HTTP 202 and a "verify that
you're not a robot" page to every request from this tool, which is not
something to defeat. The Publications Office's Cellar service is the
machine-facing front door for the same documents and answers plainly.
Measured before switching: Cellar returns the same ELI spine (identical
`eli-subdivision` counts on both AI Act representations) and the same
class vocabulary bar one cosmetic `borderOj`, so the converter cannot
tell the two apart. `--source legal-content` keeps the old route for the
day the challenge lifts.

Discovery moves with it. The landing page's two opinions - the status
line and the `data-celex` - are unreachable, so the pair becomes the
Cellar SPARQL endpoint (which consolidated ids exist) and the
consolidated document's own header line ("02016R0679 - EN -
04.05.2016"). Those are two different services, so a change to either
shows up as a disagreement rather than as a wrong answer, which was the
whole point of the original pair.

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
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://eur-lex.europa.eu/legal-content"
CELLAR = "https://publications.europa.eu/resource/celex"
SPARQL = "https://publications.europa.eu/webapi/rdf/sparql"
# Cellar content-negotiates, and answers 404 to text/html: it serves the
# document only for application/xhtml+xml. Measured, not guessed.
ACCEPT = {"cellar": "application/xhtml+xml",
          "legal-content": "text/html,application/xhtml+xml"}
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
# A consolidated text states its own identity in its first line:
# "Consolidated TEXT: 32016R0679 — EN — 04.05.2016   02016R0679 — EN
# — 04.05.2016 — 000.002". Matched against the tag-stripped document for
# the same reason the status line is: EUR-Lex splits it across elements.
RE_CONSOL_SELF = re.compile(r"(0\d{4}[A-Z]\d{4})\s*[—-]\s*[A-Z]{2}\s*"
                            r"[—-]\s*(\d{2})\.(\d{2})\.(\d{4})")
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


def get(url, accept=ACCEPT["legal-content"]):
    """One GET, returning (bytes, final url, status, content-type)."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        "Accept-Language": "en",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return (r.read(), r.geturl(), r.status,
                r.headers.get("Content-Type", ""))


def landing_url(celex):
    return f"{BASE}/EN/TXT/?uri=CELEX%3A{celex}"


def html_url(celex):
    return f"{BASE}/EN/TXT/HTML/?uri=CELEX:{celex}"


def cellar_url(celex):
    return f"{CELLAR}/{celex}"


def doc_url(celex, source):
    return cellar_url(celex) if source == "cellar" else html_url(celex)


def consolidated_prefix(base_celex):
    """`32016R0679` -> `02016R0679`: the sector digit is 0 when consolidated."""
    return "0" + base_celex[1:]


def sparql_consolidated(base_celex):
    """Which consolidated ids of this act exist, straight from Cellar's RDF.

    This replaces reading them off the landing page. It is the metadata
    store rather than a rendered page, so it is the sturdier of the two
    opinions - but it is still only one, and `fetch` checks it against
    what the document says about itself.
    """
    prefix = consolidated_prefix(base_celex)
    query = ("PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>\n"
             "SELECT ?celex WHERE {\n"
             "  ?w cdm:resource_legal_id_celex ?celex .\n"
             f'  FILTER(STRSTARTS(STR(?celex), "{prefix}"))\n'
             "} ORDER BY ?celex")
    url = SPARQL + "?" + urllib.parse.urlencode(
        {"query": query, "format": "application/sparql-results+json"})
    body, _, status, _ = get(url, accept="application/sparql-results+json")
    if status != 200:
        raise SystemExit(f"eurlex: Cellar SPARQL returned HTTP {status}")
    rows = json.loads(body)["results"]["bindings"]
    return sorted({r["celex"]["value"] for r in rows})


def discover_cellar(base_celex):
    """Cellar's half of the discovery pair. Same record shape as `discover`."""
    ids = sparql_consolidated(base_celex)
    if not ids:
        raise SystemExit(
            f"eurlex: Cellar knows no consolidated version of {base_celex}. "
            f"Either the act has never been consolidated or the CDM property "
            f"changed - look at the endpoint before changing this code.")
    return {
        "landing_url": None,
        "discovery_route": "cellar-sparql",
        "sparql_endpoint": SPARQL,
        "current_consolidated": max(ids),   # ids sort by their date suffix
        "consolidated_versions": ids,
        "status_line_agrees": None,         # checked against the document
        "doc_title": None,
    }


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


def stated_consolidation(text):
    """What the document says its own consolidated id is, or None."""
    m = RE_CONSOL_SELF.search(flatten(text))
    if not m:
        return None
    base, d, mo, y = m.groups()
    return f"{base}-{y}{mo}{d}"


def fetch(celex, out_dir, kind, discovery=None, source="cellar"):
    url = doc_url(celex, source)
    body, final, status, ctype = get(url, accept=ACCEPT[source])
    text = body.decode("utf-8", "replace")
    problems = shape_ok(text, celex)

    # The second opinion. Discovery said this id is current; the document
    # has to agree that it is that id. Only a consolidated text carries
    # the line - the OJ representation has no consolidation to state.
    stated = stated_consolidation(text) if celex.startswith("0") else None
    if celex.startswith("0"):
        if stated is None:
            problems.append(
                "the document states no consolidated id in its header, so "
                "discovery has no second opinion to agree with")
        elif stated != celex:
            raise SystemExit(
                f"eurlex: discovery asked for {celex} but the document says "
                f"it is {stated}. Refusing to save a file whose provenance "
                f"two sources disagree about.")
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
        "access_route": source,
        "sha256": hashlib.sha256(body).hexdigest(),
        "sha256_normalized": hashlib.sha256(
            RE_TELEMETRY.sub(b"", body)).hexdigest(),
        "normalization": NORMALIZATION,
        "stated_consolidation": stated,
        "bytes": len(body),
        "raw_file": raw.name,
        "doc_title": title.group(1).strip() if title else None,
        "shape_problems": problems,
        "discovery": discovery,
    }
    (out_dir / f"{celex}.en.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    if stated:
        print(f"  {kind:<17} {celex}  (document agrees: {stated})")
    else:
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
    ap.add_argument("--source", choices=("cellar", "legal-content"),
                    default="cellar",
                    help="which EUR-Lex route to fetch through. Default "
                         "cellar: legal-content is behind a bot challenge "
                         "(see the module docstring).")
    a = ap.parse_args(argv)
    if not (a.consolidated or a.original):
        ap.error("choose --consolidated, --original, or both")

    out = Path(a.out)
    print(f"EUR-Lex fetch - base act {a.celex}  (route: {a.source})")
    problems = []
    try:
        disc = (discover_cellar(a.celex) if a.source == "cellar"
                else discover(a.celex))
    except urllib.error.URLError as e:
        raise SystemExit(f"eurlex: cannot reach EUR-Lex: {e}")
    where = ("Cellar SPARQL" if a.source == "cellar" else "the landing page")
    print(f"  consolidated versions per {where}: "
          f"{', '.join(disc['consolidated_versions'])}")
    print(f"  current: {disc['current_consolidated']}")
    if a.source == "cellar":
        print("  second opinion: the document's own header, checked at fetch")
    else:
        print(f"  status line agrees: {disc['status_line_agrees']}")
    if a.expect and a.expect != disc["current_consolidated"]:
        raise SystemExit(
            f"eurlex: --expect {a.expect} but EUR-Lex now says "
            f"{disc['current_consolidated']} is current. The act has been "
            f"consolidated again: re-fetch deliberately, re-convert, and "
            f"read the diff - do not paper over this.")

    if a.consolidated:
        _, p = fetch(disc["current_consolidated"], out, "consolidated-html",
                     disc, a.source)
        problems += p
    if a.original:
        _, p = fetch(a.celex, out, "oj-html", disc, a.source)
        problems += p
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
