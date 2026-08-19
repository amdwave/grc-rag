# M6 kickoff: the second instrument, and finding out what was AI-Act-specific

Session roots at `D:\` (house convention); the repo is
`D:\projects\grc-rag\` (WSL: `/mnt/d/projects/grc-rag`). House rules load
automatically from `D:\AGENTS.md`; the repo's rules do **not** auto-load
from here — **read `D:\projects\grc-rag\AGENTS.md` first**, then
`docs/decisions.md` (D0–D7). `D:\` itself is not a git repo — every git
command takes `-C D:\projects\grc-rag`.

**Model plan (decided 2026-08-17): this milestone runs on Opus 5 at high
effort.** M5 ran on Sonnet 5 because it was documentation-shaped; this is
M2-shaped — a converter meeting a source document nobody has looked at
yet, where the failure mode is a corpus that is quietly wrong and passes
every total. Drop to Sonnet 5 mid-session if step 3 turns out to be
mechanical (the GDPR HTML matching the AI Act's DOM closely enough that
the converter needs no real changes). Budget note that cuts the other
way: per D3 the Claude subscription ends ~2026-08-31 and is not renewed,
so there are roughly two weeks of sessions left and headroom held back
past that date is headroom wasted. Scope M6 and M7 to land inside it.

## What is on disk (M1–M5 done, both gates signed off)

Phase 1 is complete and public: the AI Act end to end, 871 chunks over
two provenance-distinct documents, eval 14/14 hit@5, 14/14 citation, 6/6
refusal (2026-08-17), gate floor 0.62 recorded as D7, and a README
written for an interviewer with the pipeline as one Mermaid diagram.
`docs/original-brief.md` carries the original architecture brief;
`docs/decisions.md` supersedes it where they disagree.

**What M5 established about generalizing, by reading the code rather
than assuming:**

- **Already instrument-agnostic.** `fetch.eurlex` is CELEX-parameterized
  (`--celex`, `--out`); only its `--out` default names the AI Act. Chunk
  ids take their namespace from the markdown filename stem
  (`chunk.py:399`), so `corpus/eu/gdpr.md` yields `gdpr#art_15` with no
  code change.
- **Four named lists that a second instrument touches**, every one of
  them deliberate — this repo does not glob:
  `tests/seqcheck-corpus.py` `PARTS` (its keys, `enacting` / `recitals`,
  are already ambiguous once there are two instruments),
  `tests/rerun-identical.sh` (`RAW_ENACTING` / `RAW_RECITALS` and its
  file list), `query/index.py` `CHUNK_FILES`, and `query/cli.py`
  `EVAL_FILE` / `EVAL_REPORT`.
- **Unknown until measured:** how much of `convert/eurlex_html.py` is
  EUR-Lex and how much is the AI Act.

**Goal — M6 only:** GDPR fetched and converted to markdown, through
⛔ Gate A, with the converter's instrument-specific parts named rather
than guessed. **Not** chunking, indexing, or eval rework — those are M7,
after the gate. A session that ends at a gate is complete.

## Steps

1. **Fetch GDPR.** CELEX `32016R0679`, into `corpus/raw/eu/gdpr/`.
   GDPR before NIS2 or DORA for two reasons: it is the closest
   structural sibling (a Regulation from the same EUR-Lex HTML family,
   so step 3 isolates *instrument*-specific converter logic rather than
   confounding it with directive structure), and it is the eval's
   hardest out-of-corpus separator at 0.5669 (D7), so it is the one
   addition that most directly exercises D7's trigger in M7. NIS2 is the
   better second: a Directive is where the converter's remaining
   assumptions will show. The
   consolidated id comes from the fetcher's own discovery output, never
   consolidated id comes from the fetcher's own discovery output, never
   from this brief or from memory — run without `--expect` first, read
   what it prints, then re-run with `--expect <that id>` so the run is
   pinned and reproducible. Raw file as served plus both manifest hashes
   (D5); raw + manifests committed (D0).
2. **Measure whether D4 generalizes — do not assume it.** D4 is a
   measurement about the AI Act's consolidation, not a law about
   EUR-Lex: count `rct_` ids and occurrences of "whereas" in both
   representations, exactly as D4 did. The number decides whether GDPR
   is one document or two, and it goes in the register either way.
   (GDPR also has no annexes, unlike the AI Act — confirm that against
   the fetched HTML rather than against recollection.)
3. **Convert, and let the converter tell you what was AI-Act-specific.**
   `convert.eurlex_html --instrument "GDPR"` against the fetched raw.
   Every failure is the finding. Two rules hold: the coverage table must
   still account for **every** character as emitted or dropped by a
   *named* rule, and a new drop rule is a decision to record, not a
   patch to apply — the 10^25 defect was a drop attributed to a rule
   that was simply the wrong rule. Write the per-document report and
   read it by eye.
   **⛔ Gate A: representative samples — an article with numbered
   paragraphs, a recital, and whatever GDPR has where the AI Act had
   annexes — and wait for sign-off before anything is chunked.**
4. **Decide the shape of the four named lists**, once the corpus files
   exist: does each grow a second row, or does one document registry
   replace all four? Recommend the registry only if step 3 shows the
   per-document facts are the same four fields in each place; otherwise
   four rows beat a premature abstraction. Whatever is chosen, the
   checks must cover GDPR before the session closes.
5. **Record D8** — what steps 2 and 3 settled: one document or two, one
   code path or an instrument profile, one registry or four lists, and
   the cost accepted.
6. **Close-out checks.** All four standing checks plus `cli selftest`,
   every one under `uv run` (see gotchas). Corpus, reports, manifests
   and decision entry committed. If the corpus grew, the README's counts
   and their "as of" date are now wrong — fix them in the same commit;
   the README carries numbers with the date they were true.

## What M7 will owe, named now so it is not a surprise

Adding GDPR fires D7's own trigger: eval q19 (GDPR) stops being an
out-of-corpus question and becomes an answerable one. The eval set needs
**new** out-of-corpus rows and the floor needs re-measuring against both
distributions — not a re-run of the old set with the old floor.

## Constraints and gotchas

- **Python is WSL-only.** Export `UV_PROJECT_ENVIRONMENT=$HOME/.venvs/grc-rag`
  in every shell. WSL `/tmp` does not persist between commands.
- **Every check runs under `uv run`** — `bash tests/rerun-identical.sh`
  on its own cannot import `grc_rag` and exits 2 on "first conversion
  failed". M5 found that command wrong in the README and fixed it; do
  not reintroduce it.
- **Ask before any new dependency.** A second EUR-Lex regulation should
  need none. If the converter starts wanting one, that is the signal
  that the parser is being *widened* rather than generalized — stop and
  say so.
- **Do not re-run `cli eval`.** Its numbers are quoted in the README
  with their date, and DeepSeek at temperature 0 is not run-to-run
  deterministic. The eval is M7's business.
- **Public repo, manual commits.** No secrets, `.env` untracked,
  `DEEPSEEK_API_KEY` never echoed. Nothing personal beyond what a
  portfolio carries — `docs/original-brief.md` is the standard.
- **One owner per fact.** decisions.md owns the decisions; the README
  links and carries only numbers with dates; AGENTS.md owns the
  conventions.
- Session close: commit + push, verify `status -sb` shows no `[ahead]`.

Start with step 1.
