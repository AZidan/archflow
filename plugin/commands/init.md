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

3. **Create `.archflow/current-phase.yaml`** with Phase 1 defaults:
```yaml
phase: 1
phase_name: "Strategy & Planning"
phase_file: "phases/phase-1-strategy.md"

# Project metadata
project_type: null  # Will be set during Phase 1
onboarded: false

# v2.0 — ceremony mode + active release pointer
mode: quick          # new projects start in quick mode; graduate to full when they grow (/archflow:mode)
active_release: null # slug of the one in_progress release; null until a release is being built

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

If the project's `.archflow/` does not already contain `phases/`, `schemas/` and `design-systems/`
directories, copy them from the plugin:
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/phases/` → `.archflow/phases/`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/schemas/` → `.archflow/schemas/`
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/design-systems/` → `.archflow/design-systems/`

These are reference files that agents read during execution. They must be in the project repo so agents always have access regardless of plugin cache state.

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
- The `project_type` field is left as `null` and will be set during Phase 1
- The design system is a once-per-project choice. If it is deferred at init, Phase 2 asks before
  producing the first wireframe. Change it later with `/archflow:design` — note that changing it
  does not retrofit UI already built
