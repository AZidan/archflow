---
description: "Where the project stands: phase, mode, active release, and what to run next"
---


# /archflow-status — Project status and what to run next

## Step 1 — Project status

Read `.archflow/current-phase.yaml` and `.archflow/project-settings.yaml` if they exist, and report:
- current phase + `phase_file`
- `project_type`
- `mode` (quick | full)
- design system: from `.archflow/design-system.yaml` — `{design_system} ({platform} · {library})`, or
  `not set — run /archflow-design` when the project has a UI and the file is missing
- `active_release` (and, from `.archflow/releases/{active_release}.yaml`, its progress: stories done / total)
- open blocking issues: any story in the active release with an `issues[]` entry that is
  `status: open` and `severity: blocking`, as `{story-id} — {n} open blocking`. Omit the line when
  there are none. These are review findings that stop a story reaching `done`, and nothing else
  surfaces them.
- what is sensible to run next (see Step 2)

Edge cases:
- If `.archflow/roadmap.yaml` is v1.0 (has `phases:` / no `schema_version`): suggest `/archflow-migrate`.
- If `.archflow/current-phase.yaml` is missing: `No project onboarded. Run /archflow-onboard (existing codebase) or /archflow-init (new project) to get started.`

## Step 2 — Next step

End with the command (or two) that moves the project forward from where it stands, each with one
line on why. Read it off the state above, for example:
- no release started, or the active release has no stories → `/archflow-feature` (add a story) or
  `/archflow-release new`
- a backlog stub is next up but not detailed → `/archflow-groom {story-id}`
- a `ready` story → `/archflow-feature {story-id}` to branch and build it; several queued →
  `/archflow-autopilot`
- a story waiting on its design or contract gate → `/archflow-design {story-id}` or
  `/archflow-contract {story-id}`
- an open blocking issue → fix it on that story before anything else
- every story in the active release `done` → `/archflow-release ship`
- state looks inconsistent → `/archflow-doctor`

Do not print the command list. Close with this line, as is:

```
All commands, and how Archflow works: /archflow-help
```
