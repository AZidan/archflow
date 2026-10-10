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

---

## Re-check after fix passes 2-3

**PASS.** Scope: `git diff 7864959..HEAD` (6ad86a4, 96ea739). Every acceptance criterion holds as
written. I-6 is resolved, and so are I-7 through I-11. Four new findings, all minor. I-15 (qa) is
still open and is not repeated here.

### Checks run

- `pytest tests/test_autopilot_resume.py tests/test_autopilot_resume_qa.py`: 54 passed, 1 xfailed
  (strict xfail for I-15). Full suite: 817 passed, 1 xfailed.
- `node scripts/build-adapters.mjs --check`: all six adapters up to date. The adapter copies of
  `autopilot-schema.yaml` differ from the plugin copy only by the host translations (command
  spelling, the `AskUserQuestion` wording on Gemini).
- `.archflow/schemas/autopilot-schema.yaml` and `plugin/skills/archflow/schemas/autopilot-schema.yaml`
  are identical.
- `plugin/scripts/validate_archflow.py`: 11 state files valid.
- No `/archflow <sub>` form in the story diff.
- Stack (`project-settings.yaml`): javascript + pytest. Nothing was installed.

### Verification of earlier findings

| Id | Verdict | Evidence |
|----|---------|----------|
| I-6 (blocking) | Resolved | Step 4 (`autopilot.md:264-269`) now names `abort` and `report` as callers that skip the closing write. `abort` (`:397-400`) commits `aborted` first, then prints Step 4 with that write skipped. `report` (`:394-395`) says the same. An aborted run stays `aborted`. |
| I-7 | Resolved | "Where the scan reads" (`:317-331`) reads every local branch with `for-each-ref` / `ls-tree` / `show` and checks nothing out. When answers were given, rule 2 checks out the run branch (or `base_branch`) before any write (`:371-375`). |
| I-8 | Resolved | Rule 2 now separates "nothing answered and nothing waived" from "nothing answered, some waived" (`:364-370`). A waiver is offered only for unanswered stories, which is the only case where it applies, and it is recorded. |
| I-9 | Resolved | The vacuous test is now a positive assertion on the `Next:` line, Step 4's aborted clause, and rule 2's `finished` or `aborted`. Earlier tests now use key terms or whitespace-normalised regexes, not exact line breaks. |
| I-10 | Resolved | The `finished` and `aborted` descriptions in both schema mirrors now say the ledger is never reopened and that still-parked stories come back in a follow-on run. |
| I-11 | Resolved | Rule 1 (`:345-353`) splits `preflight` (no run branch yet, set `running`, go to Step 3) from `running` (verify the branch). The remaining gap, where the committed preflight ledger lives, is I-15. |

### New material: correctness

- **Terminal commits (I-12 fix).** The finish, abort and plan writes each commit the ledger alone,
  with a named message and a named branch. This is correct for finish. abort is I-18 below. --plan is I-15.
- **Cross-branch scan and de-dup.** Sound. "Most advanced status" correctly lets a merged or run-branch
  `finished` copy outrank a stale `running` copy. Reading the release file from the same source
  branch keeps ledger and story state consistent. The scan rests on one claim the rest of the file
  does not back up (I-16).
- **Rule 2 re-read and stop paths (I-14 fix).** Both the waiver-only path and the answered path
  re-read on the branch they will write to, and stop without writing when nothing is still parked.
  Correct. The waiver-only path can commit on `main` (I-17).
- **MAY / MUST NOT.** These now agree. MAY allows recording the waiver the user gives in person.
  MUST NOT says "any other story (beyond recording that waiver)". The Parked-stories section says
  "never by autopilot" and means "never decided by autopilot". That is consistent, since autopilot
  only records the waiver.

### New material: clarity

The `resume` section is now about 95 lines and is still followable. The order (prerequisites,
gather, de-dup, choose, rules 1-3) matches the order an agent has to work in, and each rule-2 case
starts with a bold condition. Two passages could be tighter. Neither is filed as an issue:
- The candidate definition (`:310-313`) says to read story state from
  `.archflow/releases/{active_release}.yaml` "only", which reads like the working-tree file. Eight
  lines later the scan says to read it from the source branch. Adding "on the run's source branch
  (below)" at `:313` would remove the double reading.
- `:109-110` ("Every ledger status write is committed as it is made") is stated generally. On a
  normal run, the ledger is first written in 2c on the current branch, and Step 3 then checks out
  `base_branch`. The same carry-over gap as I-15 applies whenever those two branches differ. Fix it
  together with I-15 rather than as a separate issue.

### New findings

**I-16 (minor): the scan assumes the `parked` state is committed on the run branch, but Parking
never says so.**
`plugin/commands/autopilot.md:317` (with `:192-197`, `:130-131`, `:153`). "Where the scan reads"
states that "A run commits its ledger and its stories' `parked` state on the run branch". The
candidate predicate (`:312`) and rule 2's re-read (`:375`) both depend on that. The steps that write
the state do not say where to commit it:
- Step 3.2 sets `in_progress` and commits after creating the task branch.
- Parking step 3 sets `parked` without naming a branch.
- Step 3.7 commits "the ledger and the release file with the story's work".

A natural reading of these steps puts the `parked` block on the unmerged WIP task branch. In that
case the run branch shows the story as `ready` or `in_progress`, and `resume` reports
`Nothing to resume.` (or "resolved since"). That is the dead end this story closes. This ambiguity
existed before the story, but the story's resume path now depends on it. Suggested fix: Parking
steps 3-4 should say to switch back to the run branch, then commit the `parked` block and the ledger
entry there.

**I-17 (minor): the waiver-only path can commit straight to `main`.**
`plugin/commands/autopilot.md:366-370`. "Nothing answered, some waived" checks out the source branch
and commits the release file there. Once a run is merged and its run branch deleted, the source
branch is any branch that holds the ledger, and on a tie it is the current checkout. That can be
`main`. Every other autopilot write goes to a run, task or base branch. Suggested fix: if the source
branch is `main` (or the default branch), record the waiver on `base_branch` instead, or stop and
tell the user.

**I-18 (minor): `abort` does not say which ledger it targets, or that it checks out the branch it
commits on.**
`plugin/commands/autopilot.md:397-400`. The I-12 fix made `abort` commit "on the branch it lives on
(the run branch ...)". It does not say:
- which ledger counts as "the current run" when the run's ledger exists only on the run branch, as
  happens for a user back on `base_branch`. `resume` scans every branch, but `abort` does not.
- that it checks out that branch first, under the clean-tree prerequisite.

Run from `base_branch`, `abort` finds nothing, or a stale `running` copy, or commits on the wrong
branch. Suggested fix: "`abort` finds the run like `resume` (newest `preflight`/`running` after the
branch scan and de-dup), checks out its branch, then writes and commits."

**I-19 (minor): the CHANGELOG has an entry for a regression that never shipped, and the first entry
has grown to 17 lines.**
`CHANGELOG.md:74-78`. The entry that starts "`resume` looked at other branches only when the current
checkout had nothing to resume" describes behaviour added in fix pass 2 of this same unreleased story.
No user ever had it. Part of the "three ledger writes uncommitted" entry (`:69-73`), the stop at the
report's `Next:` line, is also new in this story. The abort entry and the `--plan` branch-check
entry fix behaviour that did ship and should stay. Suggested fix: delete the cross-branch entry, fold
"always reads every local branch" into the first entry's sentence about branches, and trim the first
entry to the user-visible change. A user does not need every sub-case listed.

### Test quality

The added tests are string and regex matches on markdown, which is the only practical option here.
They are now keyed on terms (`Keep one copy per \`run_id\``, `ledger alone on the run branch`) and
section-scoped regexes rather than whole sentences, so they are less brittle than before. One is
negative-only: `test_branch_scan_does_not_stop_at_the_first_checkout_with_a_candidate`
(`tests/test_autopilot_resume_qa.py:250`) passes on any text that lacks one phrase. This is the same
pattern as I-9, but `test_branch_scan_dedups_one_run_across_branches` asserts the positive ("always,
from ... every local branch"), so nothing is left uncovered. It can be deleted. The real-behaviour
tests (validator and guard hook on fixture ledgers) are unchanged and still cover the finished,
no-parked and aborted cases from the AC.

### Recommendations

1. I-16 before shipping v2-5-0, because it sits on the AC-1 path: say where Parking commits the
   `parked` block.
2. I-15 together with the `:109-110` generalisation: one rule for where the first ledger commit lands.
3. I-17 and I-18: small wording fixes in rule 2 and `abort`.
4. I-19: fold the CHANGELOG.
