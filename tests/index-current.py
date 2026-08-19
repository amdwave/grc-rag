#!/usr/bin/env python3
"""Is the built index actually serving the chunks that are committed?

    uv run python tests/index-current.py     # from the repo root
    exit 0 = current, 1 = STALE, 2 = cannot tell (say why)

THE CLASS THIS CLOSES, and why nothing else could see it

`index/` is Class C - gitignored, rebuildable, no backup (decisions.md
D0). That is the right classification and it has a consequence nobody
had written down until the M11 audit: **a derived artifact can silently
disagree with the artifact it derives from.**

Edit a chunk, commit it, forget to rebuild, and every check in this repo
still passes. `rerun-identical.sh` compares the converter and chunker
against the committed corpus and never opens the index. The verifier
matches quoted spans against the bodies the INDEX served, so an index
built from superseded chunks verifies its own answers perfectly. The
eval grades ids that resolve - in the stale table. Each check is
internally consistent and the whole is wrong. That is defect class X1,
and this file is the only thing that looks at it.

WHAT IT COMPARES

`python -m grc_rag.query.index` stamps `index/source-manifest.json` on a
successful build: the SHA-256 of each of the six chunk files it read,
plus the embedder name and dimension. This re-hashes the committed files
and compares. The hash is the whole check - a length or mtime comparison
would pass on an edit that preserved either, and mtime in particular
survives a git checkout in the wrong order.

The embedder is compared too. An index built by a different model is
stale in the same way even when every chunk file matches, and the floor
in D13 is only meaningful against the vectors BGE-M3 produced.

WHY THE THREE EXIT CODES ARE THREE

A check that answers "no" the same way for "you have not built it yet"
and "what you built disagrees with git" trains people to ignore it. So:

    2   no index, or an index with no manifest (built before this check
        existed, or a build that failed its smoke test). Nothing is
        WRONG; there is nothing to compare. Build it.
    1   a manifest exists and disagrees. This is the defect.
    0   agrees, file by file.

The distinction is the same one probe-check.sh makes about
permission-denied versus file-not-found: two different states must not
collapse into one signal.

WHAT IT DOES NOT PROVE

That the vectors are correct, only that the inputs and the model name
match. A build that read the right files and embedded them wrongly is
`--smoke-only`'s question, not this one. It also cannot see a chunk file
that is uncommitted-but-present: it compares the index against the
working tree, which is what you actually queried.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from grc_rag.query.index import CHUNK_FILES, DIM, MANIFEST, MODEL, sha256


def main():
    index_dir = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "index")
    mpath = index_dir / MANIFEST

    print(f"index currency - {index_dir}")

    if not index_dir.exists():
        print(f"  no index at {index_dir} - nothing to compare.")
        print(f"  build it: uv run python -m grc_rag.query.index")
        return 2
    if not mpath.exists():
        print(f"  index exists but carries no {MANIFEST}.")
        print(f"  Either it predates this check or its build failed the "
              f"smoke test - a build only stamps the manifest once smoke "
              f"passes. Rebuild to find out which:")
        print(f"    uv run python -m grc_rag.query.index")
        return 2

    m = json.loads(mpath.read_text("utf-8"))
    recorded = m.get("chunk_files", {})
    failures, lines = [], []

    for rel in CHUNK_FILES:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"{rel}: in CHUNK_FILES but not on disk")
            lines.append(f"  MISSING  {rel}")
            continue
        want = recorded.get(rel)
        got = sha256(path)
        if want is None:
            failures.append(f"{rel}: committed now, but the index was built "
                            f"without it - the table is missing a whole "
                            f"document")
            lines.append(f"  UNINDEXED {got[:16]}…  {rel}")
        elif want == got:
            lines.append(f"  same     {got[:16]}…  {rel}")
        else:
            failures.append(f"{rel}: committed file is {got[:16]}…, index was "
                            f"built from {want[:16]}…")
            lines.append(f"  DIFFERS  {got[:16]}… vs {want[:16]}…  {rel}")

    for rel in sorted(set(recorded) - set(CHUNK_FILES)):
        failures.append(f"{rel}: the index was built from it, but it is no "
                        f"longer in CHUNK_FILES - the table holds a document "
                        f"the pipeline no longer knows about")
        lines.append(f"  ORPHAN   {rel}")

    print("\n".join(lines))

    if m.get("embed_model") != MODEL or m.get("dim") != DIM:
        failures.append(
            f"embedder: index built with {m.get('embed_model')} "
            f"({m.get('dim')}-dim), this code expects {MODEL} ({DIM}-dim) - "
            f"the vectors are not comparable and the D13 floor does not "
            f"apply to them")
    else:
        print(f"  same     {MODEL} ({DIM}-dim), {m.get('rows')} rows")

    if failures:
        print("\nSTALE - the index does not serve what is committed:")
        for f in failures:
            print(f"  - {f}")
        print("\n  Nothing else in this repo can see this: the verifier "
              "checks quotes\n  against the bodies the INDEX served, so a "
              "stale index verifies its own\n  answers and every downstream "
              "check passes. Rebuild before trusting\n  any eval number:")
        print("    uv run python -m grc_rag.query.index")
        return 1

    print(f"\nOK - all {len(CHUNK_FILES)} chunk files and the embedder match "
          f"the built index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
