VERDICT: FAIL

# Code Review: S5-02 Resume parked work after an autopilot run finishes

- **Release:** v2-5-0 · **Branch:** `resume/finished-runs` · **Diff:** `cf68104..HEAD`
  (implementation 20633e7, fix aed55f7, QA 8797045 / 745136e / d1f6897)
- **Date:** 2026-10-10 · **Reviewer:** code-reviewer (story_review)
- **Result:** 1 blocking (I-6), 4 minor (I-7..I-10). Already recorded and not repeated here: I-1..I-4
  (fixed), I-5 (open, minor).

## Design System Compliance

Not applicable. `project_type: backend_only`; the diff is command prose, a schema field, tests, and
one sentence of copy in the Jekyll marketing page (`docs/index.html:680`), which uses the classes
already on that page. The missing `.archflow/design-system.yaml` is not a finding for this repo.

## Checks run

| Check | Result |
|---|---|
| `python3 -m pytest -q tests/` | 801 passed, 1 xfailed (I-5, strict) |
| `python3 -m pytest -q tests/test_autopilot_resume*.py` | 38 passed, 1 xfailed |
| `node scripts/build-adapters.mjs --check` | all six adapters up to date |
| `diff` of both `autopilot-schema.yaml` mirrors | identical |
| `python3 plugin/scripts/validate_archflow.py .` | 11 state files valid |
| `/archflow <sub>` form in changed files | none (only CHANGELOG:394, which says it is retired) |

## Code Review Summary

**Overall assessment:** The design is sound and the prose is careful. A finished or aborted ledger
stays a record, the follow-on run is linked by `resumes`, only the active release is considered,
prerequisites come before any write, and a `preflight` ledger never silently wins over parked
stories. The report's `Next:` line, status case 3, the README and the landing page all name the same
command. The schema field is optional, validated by pattern, and mirrored, and the validator and
guard hook already handle both ledgers correctly; the tests confirm this by running them.

It fails on one point: the story's own acceptance criterion "aborted runs stay aborted" is false as
`autopilot.md` now reads (I-6).

## Rulings on the two QA-flagged items

**(a) `abort` → Step 4 → "Set `status: finished`": in scope, recorded as I-6 (blocking).**
`abort` (`autopilot.md:348`) sets `status: aborted` and then prints Step 4. Step 4 ends at
`autopilot.md:259` with "Set `status: finished`, `finished_at`, and stop." Nothing exempts abort.
`report` (`:346`) carries "Read-only", which overrides that last sentence; `abort` has no such
clause. The defect itself predates the story, but this story makes it count:
- the AC "aborted runs stay aborted" is about this exact state;
- the new text at `:248-249` says outright that "`abort` prints this same report", which strengthens
  the literal reading;
- rule 2 and the abort paragraph (`:321-324`, `:349-351`) promise that the aborted ledger keeps its
  status.

Read literally, the step overwrites `aborted` with `finished`. Resume would still pick the parked
stories up, because rule 2 accepts both, so nothing is lost in practice. What breaks is the audit
record, and the AC is false as written. Suggested fix (one clause): end Step 4 with "Set
`status: finished` and `finished_at` — unless this report is being printed by `abort` (status stays
`aborted`) or `report` (read-only) — and stop."

**(b) Resume rule 1 checks the run branch on a `preflight` ledger: out of scope, not recorded.**
This is real. Step 3 creates the run branch, so a `--plan` ledger has no branch yet, and rule 1
(`:317-318`) would "report and stop". Step 2c (`:107`) still says `resume` starts a planned run.
None of S5-02's criteria depend on it, though: every criterion is about parked stories after a run
finishes or is aborted, and the parked-story path (rule 2) works. One caveat: the I-3 fix added the
choice "start the planned run {run-id}" at `:311`, so the story now offers an option that leads into
this dead end. I recommend a backlog stub or a separate issue chosen by the user. Suggested fix:
rule 1 verifies the branch only for a `running` ledger, and a `preflight` ledger goes to Step 3,
which creates the branch.

## Critical Issues

**I-6 (blocking): `abort` overwrites `aborted` with `finished` through Step 4.**
`plugin/commands/autopilot.md:259` (with `:348`). See ruling (a). This makes the AC "aborted runs
stay aborted" false as written.

## High Priority Issues

None.

## Medium Priority Issues

**I-7 (minor): rule 2 writes state before checking out the run branch, and the candidate scan never
says which branch's `.archflow/` it reads.**
`plugin/commands/autopilot.md:295-300, 331-338`. The rule 2 bullets go in this order: write the new
ledger, edit the release file (clear `parked`, set `in_progress`), then "Build on the source run's
`run_branch` … check it out". Two problems follow.
1. The writes leave the tree dirty before the checkout. If the run branch's copy of the release
   file differs from the current branch's, `git checkout` refuses ("would be overwritten"), or it
   carries the edits across without anyone saying so. Prerequisites demand a clean tree for exactly
   this reason.
2. Step 3.7 commits the source ledger and the parked state on the run branch, or on the task branch
   (where Parking step 3 writes it is ambiguous, and that predates this story). A user who reviewed
   the run and switched back to `base_branch` without merging runs `resume` in a tree that has
   neither the finished ledger nor `status: parked`. They get "Nothing to resume", the exact dead end
   this story closes.

Suggested fix: resolve the candidate from the run branch named by the newest ledger reachable from
`git log --all`, or tell the user to run `resume` on the run branch. Check out the run branch first,
then write the follow-on ledger and the release-file edits there.

**I-8 (minor): the `blocks_release` waiver conflicts with "nothing answered → change nothing".**
`plugin/commands/autopilot.md:325-330`. Rule 2 says the user "may waive `parked.blocks_release`" when
asked the questions, then says "If nothing was answered, stop: write no ledger and change nothing."
A waiver only matters for a story that stays parked, because an answered story leaves `parked` and the
flag no longer applies. Read literally, "change nothing" throws away the one case the waiver exists
for. Suggested fix: "If nothing was answered, write no ledger; record any `blocks_release` waiver on
the story in the release file, and stop."

## Low Priority Issues

**I-9 (minor): a QA test is now vacuous.**
`tests/test_autopilot_resume_qa.py:97-108`, `test_abort_report_next_line_names_a_command_that_works_for_an_aborted_run`.
It asserts `not (aborted_refused and …)`, where `aborted_refused` tests for the phrase "`aborted` run
is never resumed". The fix removed that phrase, so the test passes whatever the rest of the file
says. Its docstring admits this, and `test_abort_hands_its_parked_stories_to_resume_rule_2` now holds
the real check. Delete the vacuous test, or turn it into a positive assertion. More broadly, most
prose tests pin whole sentences ("If nothing was answered, stop: write no ledger and change
nothing"), so any reword breaks them while proving nothing about behaviour. Pinning the contract is
the only option for markdown, but key terms such as `resumes:`, `follow-on run`, `Nothing to resume.`
and `` `finished` or `aborted` `` would be less brittle than full clauses. The validator and guard
tests (`test_autopilot_resume.py:236-286`) test real behaviour and are good.

**I-10 (minor): schema status descriptions still imply only `preflight`/`running` are resumable.**
`plugin/skills/archflow/schemas/autopilot-schema.yaml:42-45` (and its `.archflow/` mirror). Lines 42
and 43 say "Resumable." for `preflight` and `running`, and `finished`/`aborted` say nothing. After
this change, a reader of the schema alone would conclude that a finished run's parked stories cannot
come back. Suggested fix: add "Its still-parked stories can be picked up by `resume` in a follow-on
run (`resumes`); the ledger itself is never reopened." to both.

## Positive Observations

- Treating finished and aborted ledgers as immutable records, with a new linked ledger, keeps the
  validator's `is_historical_autopilot_run` and the guard hook's `running|preflight` check correct
  without any code change. The tests show this by running the real validator and the real
  `guard-git.mjs` on fixture ledgers.
- Prerequisites come before any write, other releases are excluded, and an empty answer set writes
  nothing. These are the right guards for an unattended lane.
- The `Next:` line now has a defined fallback when nothing is parked, so it never sends the user to a
  command that would refuse.
- One command, worded the same way in usage, Step 4, the subcommand, status.md, README, the landing
  page and CHANGELOG. Adapters are regenerated and the schema mirrors match.
- The CHANGELOG entry explains the bug from the user's side and lists every behaviour change.

## Recommendations

1. Fix I-6: exempt `abort` (and `report`) from Step 4's closing status write.
2. Fix I-7: check out the run branch before writing anything, and say where `resume` looks.
3. Fix I-8: settle what a waiver does when nothing was answered.
4. Fix I-9 and I-10 while in the files.
5. File (b) as its own item: `resume` on a `preflight` ledger dead-ends at the branch check.
6. I-5 remains open from QA.
