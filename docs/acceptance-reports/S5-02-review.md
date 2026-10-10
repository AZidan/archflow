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

---

## Re-review — 2026-10-11 (after fix passes 8–12 and the "current branch only" simplification)

### Verdict
**ACCEPTED**

I-25 is resolved under the design the user approved. Parked stories now come from the release file
on the branch you're on. Resume asks those questions and names every other local run branch that
may hold parked work. I re-ran my two-runs scenario with my own probe, written from the doc rather
than from the repo's replay model. Each run branch asks its own story and points at the other.
Waiving D three times never hides B, and after B is built the pointer to its branch goes away. All
six criteria pass. I found three minor issues (I-46..I-48), none of which blocks acceptance.

### How this was tested
- **Tooling**: pytest (already in the project), `plugin/scripts/validate_archflow.py`,
  `scripts/build-adapters.mjs --check`, real-git probes of my own, and a detached worktree for
  mutation runs. Nothing was installed.
- **Commands** (branch `resume/finished-runs` at `2f102d9`):
  - `python3 -m pytest tests/test_autopilot_resume.py tests/test_autopilot_resume_qa.py -q` → `110 passed in 68.79s`
  - `python3 -m pytest tests -q` → `873 passed in 147.95s`
  - `python3 plugin/scripts/validate_archflow.py` → `11 state file(s) valid` (also after my release-file edit)
  - `node scripts/build-adapters.mjs --check` → all six adapters `is up to date`
  - `diff -r plugin/skills/archflow/schemas .archflow/schemas` → identical
  - `python3 docs/acceptance-reports/S5-02-evidence/rereview_two_runs_probe.py` → `rereview_two_runs_probe.out`
  - the same with `--mutate-no-pointer` (negative control) → `SECTION 1: FAIL [...]`
  - `python3 docs/acceptance-reports/S5-02-evidence/rereview_partial_answer_probe.py` → `rereview_partial_answer_probe.out`
  - Mutations in a detached worktree (removed afterwards): deleting autopilot.md's *Other run
    branches* paragraph → 4 tests fail. Rewriting status.md's "minus any it says were picked up"
    → 110 pass (I-48).
- **Environment**: no running app (backend_only framework repo). "End to end" means the suite, the
  real-git probes, and reading `plugin/commands/autopilot.md` and `status.md` the way the executing
  agent would.

### Summary
- **Total acceptance criteria**: 6
- **Passed**: 6 · **Failed**: 0 · **Blocked**: 0

### Criterion results

- **AC 1**: After a run finishes with parked stories, there is one documented command that picks them up once their questions are answered
  - **Result**: PASS
  - **Evidence**: The command is `/archflow:autopilot resume`, run on the branch that holds the park
    (autopilot.md *Subcommands*: Parked stories, rule 2, Other run branches). Step 4 commits the
    finish on the run branch and stops, so the user is already on that branch. From any other
    branch, resume prints `Parked work from {run-id} may be on {run_branch}: check it out and run
    /archflow:autopilot resume there.` The I-25 scenario, replayed by
    `rereview_two_runs_probe.py` (run 2 started from run 1's branch the way Step 1 reads it, so its
    queue is `['C', 'D']`):
    ```
    [after run 2] on r1-overnight: resume asks ['D']; points at [('2026-10-08-1', 'r1-autopilot')]
    [resume #1..#3, D waived] on r1-overnight: resume asks ['D']; points at [('2026-10-08-1', 'r1-autopilot')]
    [base] on r1: resume asks []; points at [('2026-10-08-1', 'r1-autopilot'), ('2026-10-09-1', 'r1-overnight')]
    [run 1 branch] on r1-autopilot: resume asks ['B']; points at [('2026-10-09-1', 'r1-overnight')]
    [run 1 branch after B's follow-on] on r1-autopilot: resume asks []; points at [('2026-10-09-1', 'r1-overnight')]
    [run 2 branch after B's follow-on] on r1-overnight: resume asks ['D']; points at []
    main tip: init
    SECTION 1: PASS
    ```
    Negative control: with the pointer rule removed, the probe fails at every step that depends on
    it. The repo's replay tests check the same journey with their own model
    (`test_two_runs_park_b_and_d_each_run_branch_asks_its_own_and_points_at_the_other`,
    `test_follow_on_on_one_run_branch_leaves_the_other_runs_park_where_it_was`,
    `test_pm_probe_two_finished_runs_merged_on_base_…`). I also walked the WIP-branch guard, the
    run that was merged into base and deleted, the merge into `main`, and the picked-up / I-45
    paths. Each one either reaches the question or names the branch where it can be answered.
  - **Caveat** (I-47, minor and pre-existing): if the user goes back to `base_branch` and starts a
    new `/archflow:autopilot` there, rather than `resume` or `status`, Step 1 sees the parked story
    as `ready` and queues it again. Section 2 of the probe shows the queue `['A', 'B', 'C', 'D']`
    with `t/B` still present. This is outside the story: Step 1 is unchanged, and both `status`
    and `resume` on base point at the run branch.

- **AC 2**: The end-of-run report's 'Next:' line names a command that actually works for a finished run
  - **Result**: PASS
  - **Evidence**: `autopilot.md:291` reads `Next: /archflow:autopilot resume — asks the parked
    questions, then builds the stories you answer`. `:294-298` require it to work after `finished`
    and after `aborted`, and the user is on the run branch when it prints, so the command works
    there as written. With nothing parked, the line becomes `review {run-branch} and merge it
    yourself`. The `abort` and `report` exemptions are at `:307-312`. Pinned by
    `test_report_next_line_…`, `test_next_line_without_parked_stories_…` and `test_abort_report_next_line_…`.
  - **Minor** (I-46): a follow-on run that builds only the answered stories counts as "nothing
    parked". The report then says "nothing for resume to pick up", but a story the user left
    unanswered is still parked and blocking on that branch, and resume asks it
    (`rereview_partial_answer_probe.out`: `resume on the same branch now: ('follow-on', ['B'])`).
    The line still names a working command and nothing is lost, so this is P2.

- **AC 3**: /archflow:status's parked-story advice matches the real resume path
  - **Result**: PASS
  - **Evidence**: `status.md:33-38` counts parked stories the way resume does: the release file on
    this checkout only, minus the ones resume reports as picked up. It also fires on the
    *Other run branches* lines and defers to resume's own rules when a run is also waiting, which
    resolves I-28's wording. In the probe, every branch's status list matches resume's (B and D
    each on its own branch, pointers only on base). All adapters regenerate unchanged. The old
    two-step wording is gone from README, `docs/index.html` and status.
  - **Minor** (I-48): the "minus any it says were picked up" clause isn't pinned by any test.

- **AC 4**: A run with no parked stories is not resurrected by resume; aborted runs stay aborted
  - **Result**: PASS
  - **Evidence**: Rule 2 treats each ledger as a record that is never edited, and rule 3 prints
    `Nothing to resume.`. A gone `running` branch stops with an `abort` instruction and doesn't
    restart. A `preflight` run whose branch exists anywhere is refused. Replays:
    `test_a_finished_run_is_not_resurrected_…`, `test_fresh_clone_of_base_branch_resumes_nothing`,
    `test_an_aborted_run_stays_aborted[*]`, `test_an_aborted_planned_run_that_never_started_stays_aborted`,
    `test_started_planned_run_is_not_restarted_once_its_run_branch_is_gone_everywhere[*]`,
    `test_gone_running_run_does_not_silently_start_an_older_planned_run`. All pass.

- **AC 5**: Tests cover resume on a finished run with parked stories, one without, and an aborted run
  - **Result**: PASS
  - **Evidence**: All three named cases have replays on real git (above). The two-run case that
    caused the original rejection now has three replays. 110/110 pass, and the full suite is
    873/873. Removing the pointer paragraph from the doc fails 4 tests, so the doc pins bind.

- **AC 6**: CHANGELOG has a Fixed entry
  - **Result**: PASS
  - **Evidence**: `CHANGELOG.md` has four Fixed bullets. The first now describes the
    current-branch behaviour ("asks the questions of the stories parked on the branch you are on
    … names any other run branch that may hold parked work"), which matches the shipped doc. The
    other three (abort stays aborted, `--plan` start, committed ledger writes) were checked against
    base in the first review and still hold.

### Product read: is the journey coherent and is autopilot.md followable?
Yes. The user's path is short. The run ends on its branch with `Next: resume`. Resume asks there,
and from anywhere else it points at the right branch. `status` says the same thing. The *Subcommands*
`resume` block is still long (about 130 lines) and dense, as noted in I-44. I read it as the
executing agent would and found no contradiction. Each stop says what was written (nothing, or
the release file only) and which command to run next.

### Blocking defects (must fix)
None.

### Non-blocking observations (recorded as issues)
1. **I-46 (P2, minor)**: after a partial-answer follow-on, the Next line says nothing is left for
   resume, but an unanswered story is still parked on that branch (`autopilot.md:297`). → When the
   run branch's release file still holds a parked story, keep `Next: /archflow:autopilot resume`,
   or list those stories in the report.
2. **I-47 (P2, minor, pre-existing)**: a fresh `/archflow:autopilot` on `base_branch` re-queues a
   story parked on an unmerged run branch and rebuilds it beside its WIP branch (`autopilot.md:47`).
   → Have Step 1 print resume's *Other run branches* lines and ask before queueing. Alternatively,
   defer it to the backlog.
3. **I-48 (P3, minor)**: there's no doc pin for status.md's picked-up clause. → Add a wording pin
   like the existing status tests.

### Recommendation
Proceed. The story can move on to the user's approval. The three minor issues are the user's to
fix in place or defer.
