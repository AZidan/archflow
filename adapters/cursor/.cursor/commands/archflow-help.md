---
name: archflow-help
description: "Every Archflow command with a one-line usage note, and a short primer on how Archflow works"
---


# /archflow-help — Commands and how Archflow works

Print the two sections below to the user as they are. Read nothing and change nothing: this command
answers "what can I do?", and `/archflow-status` answers "where am I?". If `the text the user wrote after the command` names a
command (e.g. `release`), print only that command's line from the list, then tell the user its full
instructions are in `.cursor/archflow/commands/<name>.md`.

## Commands

```
Archflow — commands (all namespaced /archflow-<name>)

Where you are
  /archflow-status        Current phase, mode, active release, and what to run next
  /archflow-help          This screen: every command, and how Archflow works
  /archflow-doctor        Check the environment and project state, and how to fix what
                          is missing (--validate checks state files against schemas,
                          --fix repairs drift after a plugin upgrade)

Set up
  /archflow-init          Set up Archflow in a NEW project (creates .archflow/, Phase 1)
  /archflow-onboard       Set up Archflow in an EXISTING codebase (audit, detect the
                          stack, import context, pick the phase)
  /archflow-migrate       Upgrade a v1.0 project (sprints) to schema v2.0 (releases);
                          dry-run first, then apply
  /archflow-setup-mcp     Connect an external tool over MCP (Jira, Notion, Linear,
                          GitHub, SuperDesign, ...)

Stories
  /archflow-feature       Add a story to the backlog or straight into the active release,
                          or pull a backlog story in (starts the git workflow)
  /archflow-groom         Detail or refine a story: acceptance criteria, subtasks, gates
                          (a backlog stub, or one already in a release)
  /archflow-design        The project's design system; with a story-id, that story's
                          screens (clears its design gate)
  /archflow-contract      The API contract architecture; with a story-id, that story's
                          endpoints (clears its contract gate)
  /archflow-issue         Record a defect on a story being built, list what is open, or
                          defer a minor one to the backlog (the only way to defer)

Releases and pace
  /archflow-release       The release pipeline: status, new, start, ship
  /archflow-mode          Show or switch the ceremony mode (quick | full)
  /archflow-autopilot     Run queued release stories unattended on one branch
                          (blocker interview first, then silent; one report at the end)

Workspace and settings
  /archflow-studio        Open Archflow Studio, a local web workspace over the same files
                          (beta; stop | status | port <n>)
  /archflow-telemetry     Show or change anonymous usage telemetry (on by default;
                          off opts out)
```

## How Archflow works

```
Phases     The process loop. 1 Strategy → 2 Design → 2.25 Hi-fi design → 2.5 API
           contract → 3 Build → 4 Quality → 5 Launch → 6 Enhancement. Each phase has
           its own instructions (.archflow/phases/) and its own specialist agents.
           2.25 and 2.5 are skipped when they do not apply.

Releases   The product loop, around the phases. A release is a shippable increment
           holding stories. Unscheduled ideas wait in the backlog as stubs. At most
           one release is in progress; /archflow-release ship tags and archives it.

Stories    Each story walks its own readiness pipeline, one step at a time:
           backlog → spec_ready → design_ready → contract_ready → ready →
           in_progress → review → done   (parked = stopped on a question for you)
           Design and contract gates run just in time, one step ahead of the build.

Gates      You approve the end of every phase; nothing moves on without you.
           A story is done only when qa-engineer passes and pm-reviewer returns
           ACCEPTED, with no open blocking issue. Merging to main is always yours.
           /archflow-autopilot asks its questions up front instead, but never merges.

Modes      quick: one implicit release, light gates, one lane (solo; the default).
           full:  an explicit release pipeline, enforced gates, role lanes (teams).

A typical flow
  /archflow-init or /archflow-onboard     set up, once
  /archflow-feature                       add a story
  /archflow-groom S2-11                   detail it when it is next up
  /archflow-feature S2-11                 pull it into the release, branch, build
  /archflow-status                        any time you lose the thread
```

State lives in `.archflow/` as plain files: `current-phase.yaml` (where you are),
`releases/{slug}.yaml` (story status), `backlog.yaml`, and `roadmap.yaml` (the index). The full
rules are in `.archflow/reference.md`.
