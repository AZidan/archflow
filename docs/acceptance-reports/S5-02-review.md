# Acceptance Review Report
## Release: v2-5-0 | Story: S5-02 | Date: 2026-10-10

### Verdict
**REJECTED**

One P1 defect: `resume` only offers the parked stories of the newest finished or aborted run. When
two runs in the same release each leave a story parked, the older run's story can't be reached
until the newer one's question is answered. If the user waives the newer story instead (a path this
story adds), the older one is never offered again. `/archflow:status` still lists the older story's
question and says resume will ask it. That fails AC 1 and AC 3 in a realistic multi-night release.
Everything else holds up.

### How this was tested
- **Tooling**: pytest (already in the project, `stack.test.unit: pytest`), `plugin/scripts/validate_archflow.py`,
  `scripts/build-adapters.mjs --check`, the repo's own real-git replay harness in
  `tests/test_autopilot_resume_qa.py`, and one probe of my own built on that harness. Nothing was installed.
- **Commands**:
  - `python3 -m pytest tests/test_autopilot_resume.py tests/test_autopilot_resume_qa.py -q` → `89 passed in 25.43s`
  - `python3 -m pytest tests -q -x` → `852 passed in 104.42s`
  - `python3 plugin/scripts/validate_archflow.py` → `11 state file(s) valid`
  - `node scripts/build-adapters.mjs --check` → every adapter `is up to date`
  - `diff -r plugin/skills/archflow/schemas .archflow/schemas` → identical
  - `python3 docs/acceptance-reports/S5-02-evidence/two_runs_probe.py` → output in `two_runs_probe.out`
- **Environment**: branch `resume/finished-runs` at `bb4d434`, story diff `cf68104..HEAD`. This is a
  backend_only framework repo with no running app, so "end to end" means the suite and the replays
  above, plus reading `plugin/commands/autopilot.md` the way the agent that has to execute it would.

### Summary
- **Total acceptance criteria**: 6
- **Passed**: 4 · **Failed**: 2 · **Blocked**: 0

### Criterion results

- **AC 1**: After a run finishes with parked stories, there is one documented command that picks them up once their questions are answered
  - **Result**: FAIL (P1)
  - **Evidence**: The single-run cases work. `test_replay_of_a_normal_run_commits_off_main_and_resume_finds_the_parked_story`
    and `test_replay_follow_on_builds_the_answered_story_and_then_resume_has_nothing` replay a finished
    run with a parked story and a follow-on run that builds it. I walked rule 2 for each of these
    situations: still on the run branch, back on `base_branch` with the run unmerged (cross-branch
    scan), run merged into `base_branch` and deleted, run aborted, and a `--plan` run also waiting
    (resume asks which one to pick up). All of them resolve.
    The two-run case fails. `autopilot.md:353` defines the candidate as *"the newest ledger whose
    `status` is `finished` or `aborted` … whose `queue[]` holds an item in state `parked` whose story
    is still `status: parked`"*, and rule 2 asks only *that* ledger's stories. Probe
    (`S5-02-evidence/two_runs_probe.out`): run 2026-10-08-1 parked B, then run 2026-10-09-1 parked D.
    The user can't answer D yet, so they waive it on each resume:
    ```
    status case 3 would list parked: ['B', 'D']
    harness _scan (all ledgers): ['B', 'D']
    resume #1: doc-literal candidate ledger + questions asked = ('2026-10-09-1', ['D'])
    resume #2: doc-literal candidate ledger + questions asked = ('2026-10-09-1', ['D'])
    resume #3: doc-literal candidate ledger + questions asked = ('2026-10-09-1', ['D'])
    B ever asked: False
    ```
    The repo's harness `_scan` gathers parked stories from every finished ledger, so it differs from
    the doc here and can't catch this. No test covers two finished runs with parked stories.
  - **Defect**: Expected: the user answers B's question and gets B built. Actual: resume asks only
    D. While D is parked, which includes after a waiver, B can't be reached. → I-25

- **AC 2**: The end-of-run report's 'Next:' line names a command that actually works for a finished run
  - **Result**: PASS
  - **Evidence**: `autopilot.md:291`: `Next: /archflow:autopilot resume — asks the parked questions,
    then builds the stories you answer`. `:294-298` require the line to work after `finished` and
    after `aborted`, and switch to `Next: review {run-branch} and merge it yourself` when nothing is
    parked. Step 4's closing write exempts `abort` and `report` (`:307-312`). Tests:
    `test_report_next_line_names_resume_for_parked_stories`, `test_next_line_without_parked_stories_does_not_name_resume`,
    `test_abort_report_next_line_names_a_command_that_works_for_an_aborted_run`, `test_step4_closing_write_exempts_abort`.
    For a single finished run, the command it names works (AC 1 evidence).

- **AC 3**: /archflow:status's parked-story advice matches the real resume path
  - **Result**: FAIL (P1, same root cause as AC 1)
  - **Evidence**: `plugin/commands/status.md:34-39` covers the open, finished and aborted cases, the
    interrupted-`running` case, and the `--plan` case. All five adapters match (`build-adapters --check`).
    It says *"print its `parked.question`, then `/archflow:autopilot resume`, which asks it and builds
    the story once answered"*. In the two-run case above, status prints B's question, and resume asks
    D's question and never B's. Minor wording drift: *"resume continues that run first"* doesn't hold
    when the interrupted run's branch is gone everywhere. Since I-24, resume then stops and tells the
    user to `abort` (I-28).
  - **Defect**: → I-25 (blocking) and I-28 (minor)

- **AC 4**: A run with no parked stories is not resurrected by resume; aborted runs stay aborted
  - **Result**: PASS
  - **Evidence**: Rule 2 never reopens or edits the source ledger (`:422-425`), and rule 3 covers the
    finished, aborted and nothing-parked cases (`:457-463`). Replays:
    `test_a_finished_run_is_not_resurrected_from_the_preflight_copy_on_base_branch`,
    `test_i20_fresh_clone_of_base_branch_resumes_nothing`, `test_i20_an_aborted_run_stays_aborted`,
    `test_an_aborted_planned_run_that_never_started_stays_aborted`,
    `test_started_planned_run_is_not_restarted_once_its_run_branch_is_gone_everywhere`,
    `test_gone_running_run_does_not_silently_start_an_older_planned_run`. The guard hook ignores
    `finished`/`aborted` ledgers (`test_finished_run_with_parked_stories_does_not_arm_the_guard`,
    `test_aborted_run_with_parked_stories_does_not_arm_the_guard`), and the validator skips them as records.

- **AC 5**: Tests cover resume on a finished run with parked stories, one without, and an aborted run
  - **Result**: PASS
  - **Evidence**: A finished run with parked stories:
    `test_replay_of_a_normal_run_commits_off_main_and_resume_finds_the_parked_story` and the
    follow-on replay. One without: `test_a_finished_run_is_not_resurrected_…` and
    `test_a_finished_run_without_parked_stories_is_not_resurrected`. Aborted:
    `test_an_aborted_run_with_a_parked_story_hands_it_to_rule_2`, `test_i20_an_aborted_run_stays_aborted`,
    and `test_follow_on_from_an_aborted_run_…`. 89/89 pass, and the full suite is 852/852. The tests
    have gaps (two finished runs, an interrupted follow-on), but they cover the three named cases.

- **AC 6**: CHANGELOG has a Fixed entry
  - **Result**: PASS
  - **Evidence**: `CHANGELOG.md:49-66` has four Fixed bullets. I checked each claim against
    `cf68104`. The old resume did refuse a `--plan` ledger because it had no run branch (base
    `autopilot.md:284-286`), and the old `abort` did print the Step 4 report that set the run
    `finished` (base `:291`). The bullets are honest, and the first is readable to a user. Cosmetic:
    the last bullet has one line over 130 characters.

### Blocking defects (must fix)
1. **I-25**: resume only reaches the newest finished/aborted run's parked stories
   (`plugin/commands/autopilot.md:353-357`). → Make the parked candidate every still-parked story
   across every finished or aborted ledger of the active release, deduped per story and grouped by
   source run. Ask them all. Either let `resumes` take a list, or start one follow-on per source
   run. Make `status.md` case 3 say the same. Add a two-run replay test, and align the harness so
   `_scan` and the doc agree, which makes the test bind.

### Non-blocking observations
1. **I-26 (P2)**: The follow-on ledger is written "per Step 2c" (`status: preflight`), then enters
   "Step 3 from its story loop" (`:455`). Read literally, that skips Step 3's
   `status: running` write. The follow-on replay sets `running` by hand, so the test assumes the
   other reading. If that follow-on is interrupted, the next resume sees a `preflight` ledger whose
   run branch exists and refuses it as a planned run, then tells the user to `abort`. After the abort,
   the in-progress stories are neither parked nor queued. Fix: say the follow-on sets `running` before its story loop.
2. **I-27 (P2)**: Rule 2 assumes a merged and deleted run branch went into `base_branch`
   (`:441-446`). If the user merged it into another branch (such as `main`, which the report's "not
   merged to main" line invites), the scan finds the parked story there. Rule 2 then re-reads a stale
   `base_branch` and tells the user the story was "resolved since", which is false. It should say
   where the state is and that autopilot can't write there. The name of the new run branch cut in
   that path is also never given: Step 2c takes it from the interview, which a follow-on skips.
3. **I-28 (P3)**: `status.md:36-37` says resume "continues" an interrupted `running` run. When that
   run's branch is gone everywhere, resume stops and asks for `abort` (`autopilot.md:411-418`).
4. After 7 fix passes, autopilot.md's *Subcommands* section is still followable, but it's dense:
   the `resume` block is about 120 lines, and *Where autopilot commits* is restated in three places.
   I read it in full and found no contradiction other than I-26.

### Recommendation
Fix I-25 (and ideally I-26 in the same pass, since both touch rule 2) and re-run pm-reviewer. Don't
mark the story done.
