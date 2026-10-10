---
description: "Where the project stands: phase, mode, active release, and what to run next"
---

# /archflow:status — Project status and what to run next

## Step 1 — Project status

Read `.archflow/current-phase.yaml` and `.archflow/project-settings.yaml` if they exist, and report:
- current phase + `phase_file`
- `project_type`
- `mode` (quick | full)
- design system: from `.archflow/design-system.yaml` — `{design_system} ({platform} · {library})`, or
  `not set — run /archflow:design` when the project has a UI and the file is missing
- `active_release` (and, from `.archflow/releases/{active_release}.yaml`, its progress: stories done / total)
- open blocking issues: any story in the active release with an `issues[]` entry that is
  `status: open` and `severity: blocking`, as `{story-id} — {n} open blocking`. Omit the line when
  there are none. These are review findings that stop a story reaching `done`, and nothing else
  surfaces them.
- what is sensible to run next (see Step 2)

Edge cases:
- If `.archflow/roadmap.yaml` is v1.0 (has `phases:` / no `schema_version`): suggest `/archflow:migrate`.
- If `.archflow/current-phase.yaml` is missing: `No project onboarded. Run /archflow:onboard (existing codebase) or /archflow:init (new project) to get started.`

## Step 2 — Next step

End with the command (or two) that moves the project forward from where it stands, each with one
line on why. Read it off the state above. The cases are in priority order: suggest from the first
one that applies, and add a second only if it is independent of the first.
1. state looks inconsistent → `/archflow:doctor`
2. an open blocking issue → fix it on that story first (`/archflow:issue {story-id}` lists them).
   It stops the story reaching `done`
3. a `parked` story → print each one's `parked.question`, then `/archflow:autopilot resume`, which
   asks every story parked in the active release on this checkout and builds the ones answered, whether the runs
   that parked them are still open, have finished, or were aborted. Count parked stories the way
   resume does: `status: parked` in the release file on the current checkout only. Resume also
   names any other local run branch whose run parked a story, since that work may be there and not
   here: check that branch out and run resume there. If an interrupted `running` run is also
   waiting, resume continues it first while its run branch exists (if the branch is gone,
   resume stops and points at `/archflow:autopilot abort`), and the parked questions wait for the
   next resume. If a planned `--plan` run is also waiting, resume asks which one to pick up. A
   parked story blocks shipping the release by default
4. a story `in_progress` → carry on building it on its branch; it goes to `review` when every
   subtask is complete
5. a story in `review` → finish its gate: qa-engineer, then pm-reviewer, then the user's approval
6. a story waiting on its design or contract gate → `/archflow:design {story-id}` or
   `/archflow:contract {story-id}`
7. a `ready` story → `/archflow:feature {story-id}` to branch and build it; several queued →
   `/archflow:autopilot`
8. a backlog stub is next up but not detailed → `/archflow:groom {story-id}`
9. the active release has no stories → `/archflow:feature` (add a story). In `full` mode with no
   release in progress, `/archflow:release new` (or `/archflow:release start {slug}` for one
   already planned). `quick` mode has a single implicit release, so never suggest `release new`
   there
10. every story in the active release `done` → `/archflow:release ship`

Do not print the command list. Close with this line, as is:

```
All commands, and how Archflow works: /archflow:help
```
