#!/usr/bin/env python3
"""Make the three import buckets a check, not a claim.

    uv run python tests/check-imports.py     # from the repo root
    exit 0 = the guarantee holds, 1 = it does not

AGENTS.md states three buckets and nothing enforced them until this file.
It is book2rag's `tests/check-imports.py` pattern, rewritten for this
repo's package layout - same control, different tree.

  FETCH     src/grc_rag/fetch/    May reach the network; that is its job.
                                  Writes corpus/raw/ and the manifests.
  CONVERT   src/grc_rag/convert/  The guarantee lives here: standard
                                  library only, no network module, no
                                  clock and no entropy - a converter that
                                  stamps the time cannot rerun
                                  byte-identically, and byte-identical
                                  reruns are the property this bucket
                                  sells. It may not import a fetch or
                                  query module either: a network import
                                  one indirection away is still a network
                                  import.
  QUERY     src/grc_rag/query/    Reaches an inference endpoint and loads
                                  models. Network permitted; third-party
                                  imports still have to be on the
                                  approved list, because "ask before
                                  adding a dependency" is a repo rule
                                  everywhere, not only in convert.

AN UNCLASSIFIED MODULE IS A FAILURE, and that is the whole point

A check that only inspects the files someone remembered to list is a
record of the last incident, not a control. Bucket membership is NOT
inferred from the directory: a new file dropped into convert/ would then
classify itself, which is exactly the accident worth catching. Every
module is named in one of the three lists below, and any *.py under
src/grc_rag/ that is in none of them fails the run and asks to be
classified. `tests/probe-check.sh` demonstrates that failing, because a
control nobody has watched fail is a control nobody has tested.

Package `__init__.py` files are the one exception: they carry no imports
and no calls at all, and the check enforces that rather than bucketing
them.

WHAT IT DOES NOT PROVE, stated because a check whose limits are unwritten
gets trusted past them

  * The import surface, not runtime behaviour. Nothing here stops a
    convert module from opening a socket through a name it computes at
    runtime. It catches the realistic accident - a new dependency, a new
    binary, a new unclassified file - not a determined evasion.
  * `tests/` is NOT scanned, deliberately: the checks import book2rag's
    seqcheck.py off-tree and must stay independent of the pipeline they
    check. The cost is that a pipeline module hidden in tests/ escapes
    the buckets. Pipeline code belongs under src/grc_rag/; that is a
    convention, not something enforced here.
  * Determinism is only fenced, not proven. The clock and entropy
    modules are refused at import; byte-identical output is demonstrated
    by running the converter twice and comparing hashes, which is a
    different check (tests/rerun-identical.sh).
  * A subprocess target that is not a string literal cannot be read, and
    is failed rather than passed over in silence - this repo shells out
    to nothing at all, so there is no legitimate opaque call to spare.

It prints the full table on success as well as failure: a check that
leaves no trace when it passes cannot be told apart from one that did
not run.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "src" / "grc_rag"

# Every module, named. Add a new file here or the check fails on it.
FETCH = ["fetch/eurlex.py"]
CONVERT = ["convert/eurlex_html.py", "convert/chunk.py"]
QUERY = ["query/index.py", "query/engine.py", "query/cli.py"]

BUCKETS = (("fetch", FETCH), ("convert", CONVERT), ("query", QUERY))

# AGENTS.md's approved list. Adding to it is a conversation, not an edit.
APPROVED = {"lancedb", "sentence_transformers", "openai", "dotenv", "docling"}

NETWORK = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "poplib",
           "imaplib", "telnetlib", "xmlrpc", "webbrowser", "asyncio",
           "asyncore", "email"}

# Same output twice from the same input, or the corpus diff is noise.
NONDETERMINISTIC = {"random", "secrets", "uuid", "time", "datetime",
                    "tempfile"}

EXEC_CALLS = {"run", "Popen", "call", "check_call", "check_output", "system"}
ALLOWED_EXE = set()          # this repo shells out to nothing

BUCKET_OF = {name: bucket for bucket, names in BUCKETS for name in names}


def targets(node, rel):
    """Every module path an import node could name, dotted-parts form.

    Relative imports are resolved against the importing file's package,
    so `from .eurlex_html import x` inside convert/ resolves the same way
    Python will resolve it at runtime. Each candidate is returned both as
    the module itself and as module+name, because `from grc_rag.convert
    import eurlex_html` names a module through the `from` clause.
    """
    if isinstance(node, ast.Import):
        return [a.name.split(".") for a in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []
    if node.level:
        pkg = list(Path(rel).parent.parts)
        base = pkg[:len(pkg) - (node.level - 1)] if node.level > 1 else pkg
        base = ["grc_rag"] + base
    else:
        base = []
    mod = base + ((node.module or "").split(".") if node.module else [])
    return [mod] + [mod + [a.name] for a in node.names]


def local_path(parts):
    """A candidate as a repo-relative module path, or None if not ours."""
    if not parts or parts[0] != "grc_rag":
        return None
    rest = parts[1:]
    if not rest:
        return None
    p = "/".join(rest) + ".py"
    return p if (PKG / p).exists() else None


def scan(path, rel):
    """What this module imports, shells out to, and globs."""
    tree = ast.parse(path.read_text("utf-8"), filename=str(path))
    roots, local, exes, opaque, globs = set(), set(), set(), 0, set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            cands = targets(n, rel)
            hits = {local_path(c) for c in cands} - {None}
            if hits:
                local |= hits
                continue
            for c in cands:
                if c and c[0] != "grc_rag":
                    roots.add(c[0])
                    break
        elif isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else \
                f.id if isinstance(f, ast.Name) else None
            if name not in EXEC_CALLS or not n.args:
                continue
            a = n.args[0]
            if isinstance(a, (ast.List, ast.Tuple)) and a.elts:
                a = a.elts[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                exes.add(a.value)
            else:
                opaque += 1
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            # `*.md` matches `ai-act.report.md`. AGENTS.md: consumers name
            # or filter explicitly, never glob the corpus by extension.
            if "*.md" in n.value and "*.report.md" not in n.value:
                globs.add(n.value)
    return {
        "roots": roots,
        "third": sorted(m for m in roots if m not in sys.stdlib_module_names),
        "net": sorted(m for m in roots if m in NETWORK),
        "clock": sorted(m for m in roots if m in NONDETERMINISTIC),
        "local": sorted(local),
        "exes": sorted(exes),
        "opaque": opaque,
        "globs": sorted(globs),
    }


def main():
    listed = [n for _, names in BUCKETS for n in names]
    found = sorted(str(p.relative_to(PKG)).replace("\\", "/")
                   for p in PKG.rglob("*.py"))
    inits = [f for f in found if Path(f).name == "__init__.py"]
    modules = [f for f in found if f not in inits]
    failures = []

    print(f"import check - {PKG}")
    print(f"{'module':<24}{'bucket':<10}{'3rd-party':<12}{'network':<10}"
          f"{'in-repo':<26}exec")

    for bucket, names in BUCKETS:
        for rel in names:
            p = PKG / rel
            if not p.exists():
                continue
            s = scan(p, rel)
            ex = s["exes"] + (["<opaque>"] * bool(s["opaque"]))
            print(f"{rel:<24}{bucket:<10}{','.join(s['third']) or '-':<12}"
                  f"{','.join(s['net']) or '-':<10}"
                  f"{','.join(s['local']) or '-':<26}{','.join(ex) or '-'}")

            bad_dep = [m for m in s["third"] if m not in APPROVED]
            if bad_dep:
                failures.append(
                    f"{rel}: imports {', '.join(bad_dep)} - not on AGENTS.md's "
                    f"approved list. Ask, don't add.")
            if bucket == "convert":
                if s["net"]:
                    failures.append(
                        f"{rel}: imports a network module: "
                        f"{', '.join(s['net'])} - this bucket guarantees no "
                        f"network")
                if s["clock"]:
                    failures.append(
                        f"{rel}: imports {', '.join(s['clock'])} - the clock, "
                        f"entropy and temp names break byte-identical reruns")
                cross = [t for t in s["local"]
                         if BUCKET_OF.get(t) in ("fetch", "query")]
                if cross:
                    failures.append(
                        f"{rel}: imports {', '.join(cross)} - a convert module "
                        f"may not reach the network one indirection away")
            unknown = [t for t in s["local"] if t not in BUCKET_OF]
            if unknown:
                failures.append(f"{rel}: imports unclassified module(s): "
                                f"{', '.join(unknown)}")
            bad_exe = sorted(e for e in s["exes"] if e not in ALLOWED_EXE)
            if bad_exe:
                failures.append(f"{rel}: shells out to {', '.join(bad_exe)} - "
                                f"nothing in this repo may")
            if s["opaque"]:
                failures.append(f"{rel}: {s['opaque']} exec call(s) whose "
                                f"target is not a literal - unreadable, so "
                                f"refused")
            if s["globs"]:
                failures.append(
                    f"{rel}: globs the corpus by extension "
                    f"({', '.join(s['globs'])}) - that pattern matches "
                    f"*.report.md too")

    for rel in inits:
        p = PKG / rel
        tree = ast.parse(p.read_text("utf-8"), filename=str(p))
        noise = [n for n in ast.walk(tree)
                 if isinstance(n, (ast.Import, ast.ImportFrom, ast.Call))]
        print(f"{rel:<24}{'(marker)':<10}{'-':<12}{'-':<10}{'-':<26}-")
        if noise:
            failures.append(f"{rel}: a package marker carries {len(noise)} "
                            f"import(s)/call(s) - it is in no bucket, so it "
                            f"may carry none")

    print()
    unclassified = [f for f in modules if f not in listed]
    missing = [f for f in listed if f not in modules]
    if unclassified:
        failures.append(
            "unclassified module(s): " + ", ".join(unclassified)
            + " - add each to FETCH, CONVERT or QUERY in this file. A new "
              "sibling of the converters arriving unnoticed is what this "
              "check exists to catch.")
    if missing:
        failures.append("listed but not on disk: " + ", ".join(missing)
                        + " - renamed or deleted? update this file")
    stray = sorted(str(p.relative_to(ROOT)).replace("\\", "/")
                   for p in (ROOT / "src").rglob("*.py")
                   if PKG != p.parent and PKG not in p.parents)
    if stray:
        failures.append("python outside the package: " + ", ".join(stray)
                        + " - it is in no bucket and nothing checks it")

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1
    n = {b: len(names) for b, names in BUCKETS}
    print(f"OK - {n['convert']} convert module(s) stdlib-only, network-free, "
          f"clock-free, shelling out to nothing; {n['fetch']} fetch, "
          f"{n['query']} query; {len(inits)} package markers empty")
    print("     not scanned: tests/ (independent of the pipeline by design)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
