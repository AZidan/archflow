# /archflow init — Initialize Archflow in a Project

Lightweight command for setting up Archflow in a new or existing project.

## Usage
```
/archflow init              → Initialize Archflow in the current project
```

## Prerequisites
- Must be run from the project's root directory

---

## Flow

### Step 1: Check If Already Initialized

Check if `.archflow/current-phase.yaml` exists in the project root.

**If it exists:**
```
Archflow is already initialized in this project.

Current phase: [N] ([Phase Name])
Project type: [type]

Run /archflow to see available commands.
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
Then load and follow `skills/archflow/commands/onboard.md`.

---

#### If "New project"

Proceed to Step 3.

### Step 3: Create Project State Files

1. **Create `.archflow/` directory** if it doesn't exist:
```bash
mkdir -p .archflow
```

2. **Create `.archflow/current-phase.yaml`** with Phase 1 defaults:
```yaml
phase: 1
phase_name: "Strategy & Planning"
phase_file: "phases/phase-1-strategy.md"

# Project metadata
project_type: null  # Will be set during Phase 1
onboarded: false

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

### Step 4: Update Project CLAUDE.md

If `CLAUDE.md` does NOT exist in the project root, create it:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

If `CLAUDE.md` ALREADY exists, append the Archflow section to the end:

```markdown

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

### Step 5: Print Summary

```
Archflow initialized at Phase 1 (Strategy & Planning).

Created:
  .archflow/current-phase.yaml
  CLAUDE.md [created / updated with Archflow section]

Next steps:
  - Run Phase 1 to define your product strategy
  - The product-strategist agent will create:
    → .archflow/project-context.md (business goals, tech stack, architecture)
    → .archflow/roadmap.yaml (feature roadmap and sprint planning)
```

---

## Notes
- This command is idempotent — it won't overwrite existing `.archflow/current-phase.yaml`
- For existing codebases, always use `/archflow onboard` instead (it determines the correct phase via audit)
- The `project_type` field is left as `null` and will be set during Phase 1
