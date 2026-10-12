VERDICT: PASS

# S2-06 /archflow:help, and status drops the command list: code review

- Story: S2-06 (release v2-5-0), branch `help/help-command`
- Scope: `git diff 7f65432..HEAD` (implementation ff65815, e239370; QA tests c5735ad). The QA report
  in the diff was read for its issues, not reviewed.
- Reviewer: code-reviewer, story_review pass
- Checks run: `python3 -m pytest -q tests/test_help_command.py tests/test_command_registration.py`
  gave 32 passed. `node scripts/build-adapters.mjs --check` reports every adapter up to date.
  `diff -q` of `instructions.md`, `reference.md` and `phases/onboarding/finalize.md` between
  `plugin/skills/archflow/` and `.archflow/` shows no difference.

## Design System Compliance

Not applicable. The project is `backend_only` and has no `.archflow/design-system.yaml`. The only
markup change is one `<span class="font-mono text-xs">help</span>` in `docs/index.html`, which reuses
the existing class of its siblings. As with earlier reviews, the missing design system is not filed.

## Summary

The change does what the story asks. `help.md` lists all 17 files in `plugin/commands/`, one line
each, and every usage note matches its command's own description and argument-hint. The primer's
facts check out against `reference.md` (pipeline order, the `parked` side status, at most one
release `in_progress`, quick as the init default, 2.25 and 2.5 skippable) with one exception (I-4).
`status.md` keeps both edge cases (v1.0 roadmap → `/archflow:migrate`; missing `current-phase.yaml`
→ onboard or init), the design system line and the blocking-issues line, and ends with the help
pointer. No blocking defects. Four minor findings, I-4 to I-7, none duplicating QA's I-1 to I-3.

## What was checked

| Area | Result |
|------|--------|
| help lists exactly `plugin/commands/` | Pass. Test is line-anchored inside the fenced block, so primer mentions do not count, and it checks duplicates both ways |
| Usage notes vs command files | Pass. Arguments match each `argument-hint` (release, mode, studio, telemetry, doctor, issue) |
| Primer accuracy | One inaccuracy (I-4) |
| status edge cases kept | Pass (migrate, onboard/init, design system line, blocking issues) |
| status next-step guidance | Gaps (I-5) |
| Test robustness | help drift test is solid; status test is weak (I-6) |
| Mirror discipline | Pass. `SKILL.md` has no `.archflow/` copy and never had one |
| No `/archflow <sub>` form | Pass. No added line uses it |
| No command count on `docs/index.html` | Pass, and now guarded by a test |
| Telemetry | Pass. No hand-kept allowlist; `knownCommands()` and each adapter's `commands.json` pick help up, and tests cover every host |
| CHANGELOG | Pass. Added and Changed entries under `[Unreleased]` describe the change accurately |
| Every command surface | Pass. CLAUDE.md, README.md, instructions.md, reference.md, SKILL.md, both guides, site, and the CLAUDE.md templates in init, onboard and finalize |

## Critical Issues

None.

## High Priority Issues

None.

## Medium Priority Issues

None.

## Low Priority Issues (all recorded as minor)

### I-4 The help primer says autopilot "never merges"

`plugin/commands/help.md:78`: "/archflow:autopilot asks its questions up front instead, but never
merges." Autopilot does merge: on ACCEPTED it merges the task branch into the run branch
(`plugin/commands/autopilot.md:144`), and `done` is the one transition that requires a merge
(`:166`). What it never does is merge to `main` (`reference.md:101-102`). A user reading help will
expect autopilot to leave every story on its own unmerged branch.

Fix: "...but never merges to main."

### I-5 status's next-step list skips the states a release spends most time in

`plugin/commands/status.md:28-39`. The list maps a stub, a gate, a `ready` story, a blocking issue,
an all-done release and inconsistent state. It has nothing for a story that is `in_progress`,
`review` or `parked`. Mid-release, one of those is usually what status finds. `parked` matters most:
the story is waiting on a question only the user can answer, and it blocks the ship by default
(`reference.md:39-41`), so status should surface it and tell the user to answer it.

Two smaller points in the same list:
- The blocking-issue case says "before anything else" but sits fifth. A model reading the list top
  to bottom can suggest `/archflow:feature {story-id}` first. Put it at the top, or say the cases
  are in priority order.
- "no release started → `/archflow:release new`" does not fit `quick` mode, which runs a single
  implicit release (`reference.md:43-44`; `release.md:33`). Scope that suggestion to `full` mode.

Fix: add `in_progress`/`review` (resume the story, or wait on QA and pm-reviewer) and `parked`
(answer the parked question), move the blocking case first, and qualify `release new` by mode.

### I-6 The status test lets a trimmed command list come back

`tests/test_command_registration.py:106`: `assert named < set(shipped())` fails only when status.md
names all 17 commands. A command list re-added with one command missing, or a list of 15, passes.
The `"Available commands" not in body` check only catches the old heading word for word. The
`splitlines()[-2]` check also depends on the closing fence being the last line of the file.

Fix: bound the number of distinct commands status may name (it names 12 today, its own title included), or apply the same
line-anchored regex `help_command_list()` uses and assert status has no indented `/archflow:<name>`
list. Read the pointer line with a search for the fenced line rather than a fixed offset.

### I-7 instructions.md reflow breaks the file's line width

`plugin/skills/archflow/instructions.md:46` (mirrored in `.archflow/instructions.md` and the six
adapter copies) is now about 130 columns. The rest of the file wraps near 100. This file is injected
into every session and is meant to stay tidy. Rewrap the paragraph.

## Positive Observations

- `help_command_list()` is a well-built drift guard. It reads only the fenced command block,
  anchors on line starts, and reports missing, stale and duplicate entries separately with readable
  messages.
- `test_every_adapter_commands_json_matches_the_plugin` closes the telemetry gap for every host
  without a hand-kept list.
- `test_site_states_no_total_command_count` turns a standing rule into a check.
- The status/help split is clean: every command status names is a next step or an edge-case fix, and the help pointer
  is the fixed last line.
- The help and primer prose is plain and specific, with no filler.

## Recommendations

1. I-5: fill the status next-step gaps (`parked` first). It changes what users are told to do.
2. I-4: one-word accuracy fix in the primer.
3. I-6: tighten the status test so the trim stays enforced.
4. I-7: rewrap instructions.md.
