---
description: Set up Archflow in a NEW, empty project — creates .archflow/ and starts at Phase 1
---

# /archflow:init — Initialize Archflow in a Project

> **Before you start:** run `/archflow:doctor` to see what is installed and what is
> missing. It reports only — it never installs anything — and it names the exact command
> for each gap.

Lightweight command for setting up Archflow in a new or existing project.

## Usage
```
/archflow:init              → Initialize Archflow in the current project
```

## Prerequisites
- Must be run from the project's root directory

---

## Flow

### Step 0: Initialize Git (MANDATORY)

Before creating any Archflow files:

1. Check if git is already initialized:
   ```bash
   git rev-parse --is-inside-work-tree 2>/dev/null
   ```

2. If NOT initialized, ask user:
   "Initialize git repository? [Yes / No]"
   - If Yes: `git init`
   - If No: WARN "Archflow strongly recommends git. Proceeding without it."

3. After `.archflow/` files are created (end of Step 3), make the initial commit:
   ```bash
   git add .archflow/
   git commit -m "chore: initialize archflow (Phase 1)"
   ```

---

### Step 1: Check If Already Initialized

Check if `.archflow/current-phase.yaml` exists in the project root.

**If it exists:**
```
Archflow is already initialized in this project.

Current phase: [N] ([Phase Name])
Project type: [type]

Run /archflow:status to see available commands.
```
Done — exit the command.

---

### Step 2: New Project or Existing Codebase?

Ask the user:
```
Is this a new project or an existing codebase?
```

Options:
- **Existing codebase** — Has source code that needs to be analyzed and onboarded
- **New project** — Starting from scratch, no existing code

#### If "Existing codebase"

Redirect to the full onboarding wizard:
```
For existing codebases, use the full onboarding wizard which analyzes
your code, imports context from external tools, and determines the
correct development phase.
```
Then load and follow `${CLAUDE_PLUGIN_ROOT}/commands/onboard.md`.

---

#### If "New project"

Proceed to Step 3.

### Step 3: Create Project State Files

1. **Create `.archflow/` directory** if it doesn't exist:
```bash
mkdir -p .archflow
```

2. **Copy `workflow.md` into the project's `.archflow/`:**
   - Source: `${CLAUDE_PLUGIN_ROOT}/skills/archflow/workflow.md` (the plugin's install path)
   - Destination: `.archflow/workflow.md`
   - This file defines the git branching strategy (feature → task → subtask branches, approval gates). It MUST be present in every Archflow project so Phase 3 agents can read it from the repo context.

3. **Create the two project files.** They are split on purpose: one is a CURSOR rewritten at every
   phase transition, the other is SETTINGS that change almost never.

   **`.archflow/project-settings.yaml`** — how this project works:
```yaml
schema_version: "2.1"
project_type: null          # set during Phase 1, or detected by /archflow:onboard
api_contract_path: "docs/api-contract.md"

# Agents carry no technology of their own — they read this and build in what it names.
# null means "not determined": the agent asks rather than assuming.
stack: {}                   # filled by Step 4a

# Which optional agents run automatically, and where. Empty list = available on
# request but never automatic.
optional_agents: {}         # filled by Step 4a2
```

   **`.archflow/current-phase.yaml`** — where this project is:
```yaml
phase: 1
phase_name: "Strategy & Planning"
phase_file: "phases/phase-1-strategy.md"

onboarded: false

# Ceremony mode + active release pointer
mode: quick          # new projects start in quick; graduate to full when they grow (/archflow:mode)
active_release: null # slug of the one in_progress release; null until one is being built

# Phase tracking
phases_completed: []
phases_partial: []
phases_skipped: []
phases_not_applicable: []

# Gaps
gaps: []

# Git workflow
git_workflow: "workflow.md"

# Feature tracking
current_feature: null
feature_status: "ready"
status: "initialized"
```

### Step 4: Copy Phases, Schemas and Design Systems (if not present)

Copy these from the plugin into the project's `.archflow/`:
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/phases/` → `.archflow/phases/`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/schemas/` → `.archflow/schemas/`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/design-systems/` → `.archflow/design-systems/`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/stacks/` → `.archflow/stacks/`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/workflow.md` → `.archflow/workflow.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/test-accounts.example.yaml` → `.archflow/`

**Copy per FILE, not per directory.** Skip a file that already exists; copy every one that does not.
Checking whether the *directory* exists is how a project ends up permanently missing files added by
a later plugin version — it has `schemas/`, so nothing is ever copied into it again, and an agent
told to read a file that was never delivered stops. `/archflow:doctor` reports this drift and
`--fix` repairs it, but the cheap fix is not to create it here.

Never overwrite a file the project already has. A user may have edited a design system or a phase
file deliberately.

These are reference files that agents read during execution. They must be in the project repo so agents always have access regardless of plugin cache state.

### Step 4a: Choose the Stack

Every agent that writes code reads `stack:` from `project-settings.yaml` and builds in what it names.
The agents carry no technology of their own, so an unset field is not a default — it is a question
the agent will ask you later, mid-story. Answering here is cheaper.

1. **Offer the profiles.** Read `.archflow/stacks/*.yaml`, filter by the project type if it is
   already known, and show each `label` with its `description`. Always offer two more options:
   ```
   Which stack?

     1. NestJS + PostgreSQL + React      TypeScript end to end
     2. FastAPI + PostgreSQL + React     Python backend, TypeScript web
     3. Express + MongoDB + Next.js      Lighter JavaScript stack, server-rendered web
     4. React Native (iOS + Android)     Cross-platform mobile
     5. Native iOS + Android             SwiftUI and Jetpack Compose

     6. Something else                   answer field by field
     7. Decide later                     agents will ask when they need it
   ```

2. **On a profile**, copy its `stack:` block into `project-settings.yaml`, then show it and offer to
   change any field. A profile is a starting point, not a commitment.

3. **On "Something else"**, ask only the fields the project type actually needs. A `backend_only`
   project is never asked about styling. Leave anything the user is unsure about as `null` — an
   honest null is better than a guess, because the agent will ask with the repo in front of it.

4. **On "Decide later"**, write `stack: {}`. Say plainly what that means: the first agent to need a
   technology will stop and ask. That is a legitimate choice for a project whose stack is genuinely
   undecided, and a bad one for a project that just has not written it down.

Never install anything here. This step writes YAML and nothing else.

### Step 4a2: Optional review steps

Four agents are useful but not on the critical path: `code-reviewer`, `a11y-expert`,
`ui-animation-designer` and `doc-writer`. They are always available on request. This decides which
of them join automatically, and where.

Ask once. Pre-select by `mode`, and say that pre-selection out loud so the user knows what they are
accepting:

```
Optional review steps. Any of these can still be run on request even if not automatic.

  [{x if full}] Code review on every story         code-reviewer, after tests pass
  [{x if full and has UI}] Accessibility review on every story   a11y-expert
  [ ] Motion design during design                  ui-animation-designer
  [ ] Documentation before shipping                doc-writer

  ({quick mode: nothing is pre-selected — quick keeps the loop short.
    full mode: code review is pre-selected, and accessibility too if this project has a UI.})
```

Write the answer as hook points, not booleans:

```yaml
optional_agents:
  code-reviewer:         [story_review, release_quality]   # if chosen
  a11y-expert:           [story_review]                    # if chosen
  ui-animation-designer: [design]                          # if chosen
  doc-writer:            [pre_ship]                        # if chosen
```

Anything not chosen is written as an empty list, so the file records the decision rather than
leaving it ambiguous. Never omit a key — an absent key and an empty list mean the same thing to the
framework, but only the empty list tells the next reader that someone was asked.

### Step 4b: Choose the Design System

The design system is chosen **once per project**. Every agent that produces or reviews UI builds
against it for the rest of the project's life — it is never a per-feature decision.

Skip this step entirely if the user says the project has no UI (a library, a CLI, a backend-only
service). Write no `design-system.yaml` in that case.

1. **Ask the platform**, then run the picker. Both live in one place: read
   `${CLAUDE_PLUGIN_ROOT}/commands/design.md` and follow **Step 3 — `pick`** inline. It asks the
   platform, filters `.archflow/design-systems/*.md` by that platform's compatibility (frontmatter
   `platforms` map — a hard gate, so e.g. Liquid Glass is never offered for a web target), shows
   each surviving file's section 1 as the option text, always offers
   "Custom / match my brand" (which selects `custom-tokens` and asks for a tokens file path or
   offers to generate a starter one), and writes `.archflow/design-system.yaml`.

2. **If the user answers "Decide later"** to the platform question, write no
   `design-system.yaml`. Phase 2 (Design) will run the picker before it produces its first
   wireframe — the gate is in `.archflow/phases/phase-2-design.md`.

The file written is:
```yaml
design_system: material3          # matches the filename in .archflow/design-systems/
platform: flutter                 # the project's UI platform
library: flutter_material         # concrete package/library to import from
theme:
  mode: [light, dark]
  brand_tokens: null              # optional path to a tokens.json override
```

### Step 5: Update Project CLAUDE.md

If `CLAUDE.md` does NOT exist in the project root, create it:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`
- **Design system**: see `.archflow/design-system.yaml` — every UI agent must read it and follow
  `.archflow/design-systems/{design_system}.md` before producing any UI output

Commands:
- `/archflow:status` — Show status and available commands
- `/archflow:feature` — Start a new feature from the roadmap
- `/archflow:design` — Show or change the project's design system
```

If `CLAUDE.md` ALREADY exists, append the Archflow section to the end:

```markdown

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`
- **Design system**: see `.archflow/design-system.yaml` — every UI agent must read it and follow
  `.archflow/design-systems/{design_system}.md` before producing any UI output

Commands:
- `/archflow:status` — Show status and available commands
- `/archflow:feature` — Start a new feature from the roadmap
- `/archflow:design` — Show or change the project's design system
```

### Step 5: Print Summary

```
Archflow initialized at Phase 1 (Strategy & Planning).

Created:
  .archflow/current-phase.yaml
  .archflow/design-system.yaml       [or: not set — chosen in Phase 2]
  CLAUDE.md [created / updated with Archflow section]

Mode: quick (single implicit release, gates auto-satisfied).
  Switch anytime with /archflow:mode full.

Design system: [Label] ([platform] · [library])
  Change it anytime with /archflow:design.

Next steps:
  - Run Phase 1 to define your product strategy
  - The Phase 1 agents will create:
    → .archflow/project-context.md (business goals, tech stack, architecture)
    → .archflow/roadmap.yaml (v2.0 index: mode, epic labels, release pipeline)
    → .archflow/backlog.yaml (full scope as stubs; releases are carved from it just-in-time)
  - At the end of Phase 1, your FIRST release is created + started (quick mode
    auto-creates an implicit "current" release) — that's what Phases 2–3 build.
```

---

## Notes
- This command is idempotent — it won't overwrite existing `.archflow/current-phase.yaml`
- For existing codebases, always use `/archflow:onboard` instead (it determines the correct phase via audit)
- `project_type` is left `null` in `project-settings.yaml` and is set during Phase 1
- The design system is a once-per-project choice. If it is deferred at init, Phase 2 asks before
  producing the first wireframe. Change it later with `/archflow:design` — note that changing it
  does not retrofit UI already built
