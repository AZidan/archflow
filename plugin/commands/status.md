---
description: Where the project stands: phase, mode, active release, and what to run next
---

# /archflow:status — Project status + available commands

## Step 1 — Project status

Read `.archflow/current-phase.yaml` if it exists and report:
- current phase + `phase_file`
- `project_type`
- `mode` (quick | full)
- design system: from `.archflow/design-system.yaml` — `{design_system} ({platform} · {library})`, or
  `not set — run /archflow:design` when the project has a UI and the file is missing
- `active_release` (and, from `.archflow/releases/{active_release}.yaml`, its progress: stories done / total)
- what is sensible to run next (see the command list below)

Edge cases:
- If `.archflow/roadmap.yaml` is v1.0 (has `phases:` / no `schema_version`): suggest `/archflow:migrate`.
- If `.archflow/current-phase.yaml` is missing: `No project onboarded. Run /archflow:onboard (existing codebase) or /archflow:init (new project) to get started.`

## Step 2 — Available commands

```
Archflow — Phase-Based Development Workflow

  /archflow:status        This screen — current phase, active release, what to run next

  /archflow:init          Initialize Archflow in a new project
                          (creates .archflow/ state files, sets Phase 1)

  /archflow:onboard       Onboard an existing codebase to the phase framework
                          (detect project type, import context, audit, set phase)

  /archflow:migrate       Migrate a v1.0 project to schema v2.0
                          (releases replace phases, sprints retired, multi-file split)

  /archflow:mode          Show or switch the ceremony mode (quick | full)

  /archflow:release       Inspect / manage releases (status, new, start, ship)

  /archflow:setup-mcp     Configure MCP servers for external tools
                          (Jira, Notion, Linear, GitHub, SuperDesign, etc.)

  /archflow:groom         Detail a backlog stub into a `ready` story
                          (acceptance criteria, subtasks, gates — stays in the backlog)

  /archflow:feature       Add a story — to the backlog, or straight into the active release
                          (from description, external tool link, or existing backlog stub)

  /archflow:autopilot     Run queued release stories unattended on one branch
                          (blocker interview first, then silent; one report at the end)

  /archflow:design        The project's design system, or one story's screens
                          (/archflow:design S7-20 clears that story's design gate)
                          (chosen once per project; every UI agent builds against it)

  /archflow:contract      The API contract architecture, or one story's endpoints
                          (/archflow:contract S7-20 clears that story's contract gate)

  /archflow:doctor        Check the environment and project state — what is missing and
                          how to fix it (add --validate to check state files against schemas)

  /archflow:studio        Open Archflow Studio, a local web workspace over these files
                          (beta — stop | status | port <n>)
```
