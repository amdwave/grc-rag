# kickoffs — how each session was framed before it started

These are the briefs each working session was handed, committed
unedited. They are **history, not specification** — the same status
[original-brief.md](../original-brief.md) carries. Where a kickoff and
the decision register disagree, [decisions.md](../decisions.md) wins:
a kickoff records what was *believed and intended* at the start of a
session, and several of them were wrong in ways the session then
measured.

That is exactly why they are worth keeping. A register entry tells you
what was decided; a kickoff tells you what question was being asked and
what the author expected the answer to be. The gap between the two is
where this project's real findings live.

| file | milestone | what it asked for |
|---|---|---|
| [project-kickoff.md](project-kickoff.md) | the project | The origin brief — scope, constraints, why regulatory primary sources, why no RAG framework |
| [m02-kickoff.md](m02-kickoff.md) | M2 | AI Act fetch → markdown, through ⛔ Gate A |
| [m04-kickoff.md](m04-kickoff.md) | M4 | The eval set through ⛔ Gate B, then the query path |
| [m05-kickoff.md](m05-kickoff.md) | M5 | The README an interviewer reads, one diagram, and the filing |
| [m06-kickoff.md](m06-kickoff.md) | M6 | The second instrument, and finding out what was AI-Act-specific |
| [m11-audit-kickoff.md](m11-audit-kickoff.md) | M11 | **The audit** — is the refusal architecture load-bearing, and what do the checks not see? |
| [m14-kickoff.md](m14-kickoff.md) | M14 | **Not yet run.** Ship the regime pre-flight, or report why it should not be |

## Two things to notice

**The set has gaps, and they are not all the same kind of gap.** No
kickoff file survives for M3, M7, M8, M9 or M10. M12 and M13 never had
one: they ran as continuations of the M11 audit session, in the same
conversation, so their brief was a sentence rather than a document —
which is also why D15 and D16 lean so heavily on D14 for context. Read
the register for those milestones, not this directory.

**The audit kickoff is the one to read if you only read one.** It is
the clearest statement of how this project treats its own prior work:
"Everything those sessions concluded is a claim to test, not a finding
to inherit. The register is well-written and internally consistent,
which is exactly the failure mode to watch for: a document that argues
fluently for its own decisions is not evidence they were right." It
also contains the complaint that eventually produced
[diagnostics/](../../diagnostics/) — that the M10 gate experiment "was
run from a scratchpad, not committed."

## Where they used to live, and why they moved

`D:\.staging\`, a scratch directory shared with unrelated projects and
excluded from recursive search by `D:\.ignore`. Same reasoning as the
diagnostics migration: evidence that a committed decision depends on
should not live somewhere unsearchable and unbacked. The paths inside
each file still refer to `D:\` and to WSL mount points, because that is
what they said at the time and these are not edited to match the
present. The single exception is one relative link in `m14-kickoff.md`,
repointed so it still resolves from this directory.
