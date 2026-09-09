# Onboarding — presentation and finalization

Loaded by `/archflow:onboard` at Phase C, once the audit and synthesis are done. These are output
shapes: what to show the user, what to write, and what to clean up. None of it is needed while the
audit is running.

## STEP C4: Presentation

Present using the format from `phase-onboarding.md`:
```
ONBOARDING COMPLETE

Project: [Name] ([Type]: [Tech Stack])
Recommended Phase: [N] ([Phase Name])

Generated Artifacts:
  ✅ project-context.md (by product-strategist — domain research + [source] synthesis)
  ✅ roadmap.yaml ([N] epics, [M] stories: [X] done, [Y] in-progress, [Z] backlog)
  ...

Review each artifact? [Yes / Trust the agents]
```

If "Yes": present each artifact for approval/editing, one at a time.

**For failed agents:** Show which artifacts were not generated and offer fallback options:
```
⚠️ [artifact] — Agent failed. Options:
  - Import from file
  - Describe manually
  - Skip (record as gap)
```

## STEP C5: Finalize & Cleanup

1. **Create the two project files.** Settings that describe the project and the cursor that says
   where it is are separate on purpose — the cursor is rewritten at every phase transition.

**`.archflow/project-settings.yaml`:**
```yaml
schema_version: "2.1"
project_type: "{detected_type}"

# API contract (flexible path — any format)
api_contract_path: "{found_path_or_null}"

# The project's technologies, DETECTED from the repo. Agents carry none of their own — they read
# this and build in what it names. Write null for anything you could not determine; an honest null
# makes the agent ask, a wrong value makes it silently misbuild. Omit sections that do not apply.
# Schema: .archflow/schemas/project-settings-schema.yaml
stack:
  language: "{detected_or_null}"
  backend:  {framework: "...", database: "...", orm: "...", auth: "..."}
  web:      {framework: "...", language: "...", styling: "...", state: "..."}
  mobile:   {framework: "...", ios: "...", android: "..."}
  test:     {unit: "...", integration: "...", e2e: "..."}
  ci: "{detected_or_null}"
  hosting: "{detected_or_null}"
  package_manager: "{detected_or_null}"

# Which optional agents run automatically (Step 2a2). Empty list = on request only.
optional_agents: {}
```

**`.archflow/current-phase.yaml`:**
```yaml
phase: {recommended_phase}
phase_name: "{phase_name}"
phase_file: "phases/phase-{N}-{name}.md"

onboarded: true
onboarded_at: "{ISO timestamp}"

# Phase tracking
phases_completed: [...]
phases_partial: [...]
phases_skipped: [...]
phases_not_applicable: [...]

# Gaps user chose to skip
gaps: [...]

# Git workflow
git_workflow: "workflow.md"

# Feature tracking
current_feature: null
feature_status: "ready"
status: "onboarded"
```

2. **Copy workflow.md, phases, schemas and design-systems into the project's `.archflow/`:**
   - Copy `${CLAUDE_PLUGIN_ROOT}/skills/archflow/workflow.md` → `.archflow/workflow.md`
   - Copy `${CLAUDE_PLUGIN_ROOT}/skills/archflow/phases/` → `.archflow/phases/` (skip files that already exist)
   - Copy `${CLAUDE_PLUGIN_ROOT}/skills/archflow/schemas/` → `.archflow/schemas/` (skip files that already exist)
   - Copy `${CLAUDE_PLUGIN_ROOT}/skills/archflow/design-systems/` → `.archflow/design-systems/` (skip files that already exist; skip the whole directory for `backend_only`)
   - Copy `${CLAUDE_PLUGIN_ROOT}/skills/archflow/stacks/` → `.archflow/stacks/` (skip files that already exist)
   - Copy `${CLAUDE_PLUGIN_ROOT}/skills/archflow/test-accounts.example.yaml` → `.archflow/` (skip if present)
   - These files define the git branching strategy, the canonical formats and the design-system references. They MUST be in the project repo so Phase 3+ agents can read them from the repo context regardless of plugin cache state.

2a2. **Ask about optional review steps** and write `optional_agents` into `project-settings.yaml`.
   Same question and same mode-based pre-selection as `/archflow:init` Step 4a2 — read that file and
   follow it rather than restating the options here.

   An existing codebase gives you evidence the question does not: if the repo already has a11y
   tooling in its dev dependencies or a CI accessibility job, say so and pre-select accessibility
   review. If it has a required-reviewers rule or a CODEOWNERS file, mention that code review is
   already enforced outside Archflow and let the user decide whether they want it here too.

2b. **Write `.archflow/design-system.yaml`** from what STEP A3 recorded (skip for `backend_only`,
   and skip if the user answered "This project has no UI"):
```yaml
design_system: "{chosen}"       # matches the filename in .archflow/design-systems/
platform: "{platform}"          # the project's UI platform
library: "{library}"            # from that file's frontmatter platforms map
theme:
  mode: [light, dark]
  brand_tokens: null            # or the tokens.json path collected in A3
```

3. **Create or update `CLAUDE.md` with Archflow section:**

If `CLAUDE.md` does NOT exist in the project root, create it with global project instructions derived from the onboarding analysis:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Brief description from project-context.md — what the app does, tech stack summary]

## Common Commands

[Detected from package.json scripts, Makefile, or common patterns for the tech stack]

## Architecture

[Key architectural patterns, directory structure, path aliases — derived from audit]

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: [N] ([Phase Name]) — see `.archflow/current-phase.yaml`
- **Project Settings**: `.archflow/project-settings.yaml` — type, stack, contract path,
  optional agents. Agents read the stack from here and build in what it names
- **Project Context**: `.archflow/project-context.md`
- **Roadmap**: `.archflow/roadmap.yaml` ([N] epics, [M] proposed features)
- **API Contract**: `{api_contract_path}`
- **Design System**: `.archflow/design-system.yaml` — every UI agent must read it and follow
  `.archflow/design-systems/{design_system}.md` before producing any UI output

Commands:
- `/archflow:status` — Show status and available commands
- `/archflow:feature` — Start a new feature from the roadmap
```

If `CLAUDE.md` ALREADY exists, append the Archflow section to the end:

```markdown
