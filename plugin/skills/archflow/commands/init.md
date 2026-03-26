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

3. After all Archflow files are created (end of Step 5), make the initial commit. Stage all files written by this command — the exact set depends on which agents were detected:
   ```bash
   git add .archflow/ AGENTS.md CLAUDE.md .github/ .claude/
   git commit -m "chore: initialize archflow (Phase 1)"
   ```
   Only include paths that actually exist (git add silently ignores non-existent paths).

---

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

### Step 4: Write Universal AGENTS.md + Claude Code Instruction File

#### 4a. Write AGENTS.md (universal cross-agent baseline)

Always write `AGENTS.md` to the project root. This is the open standard file read by all AI coding agents (GitHub Copilot, opencode, Cursor, Gemini CLI, etc.).

If `AGENTS.md` does NOT exist, create it:

```markdown
# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.
It follows the open AGENTS.md standard (https://agents.md), readable by GitHub Copilot,
Claude Code, opencode, Cursor, Gemini CLI, and other AI coding tools.

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

If `AGENTS.md` ALREADY exists, check whether it already contains an `## Archflow Framework` section. If it does, skip the append entirely (idempotent). If it does not, append only the Archflow section to the end:

```markdown

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

#### 4b. Write Claude Code instruction file (CLAUDE.md)

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

If `CLAUDE.md` ALREADY exists, check whether it already contains an `## Archflow Framework` section. If it does, skip the append entirely (idempotent). If it does not, append the Archflow section to the end:

```markdown

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

---

### Step 5: Detect Additional Agents and Generate Their Files

Read `skills/archflow/agent-registry.yaml` to get the full list of supported agents.

Skip the `claude-code` entry — its files were already written in Step 4.

For each remaining agent in the registry:

#### Detection

Run the agent's `detection.command`. If it exits successfully (exit code 0), the agent is confirmed present.

If the command fails or is not available, check the agent's `detection.path` (if it has one). If the path exists in the project, this is a **soft signal only** — always ask the user to confirm:
```
Found [detection.path] — is [Agent Name] active in this project? [Yes / No]
```
Skip this agent if the user answers No.

#### Confirmation (when one or more agents are detected)

After running detection for all agents, present a single confirmation if any were found:
```
Detected AI coding agents: [agent names]

Configure Archflow files for all detected agents? [Yes / Claude Code only / Select]
```
- **Yes** — process all detected agents
- **Claude Code only** — skip all additional agents
- **Select** — show a checklist and let user pick

#### Per-Agent File Generation

For each confirmed agent (excluding claude-code, already done):

**A. Write instruction file**

Create the agent's `instruction_dest` directory if needed (e.g., `mkdir -p .github` for `.github/copilot-instructions.md`, `mkdir -p .cursor/rules` for Cursor).

Check the agent's `instruction_format` field in `agent-registry.yaml`:

**If `instruction_format: mdc`** (Cursor): write a `.mdc` file with YAML frontmatter:

```markdown
---
description: Archflow phase-based development framework instructions
globs:
alwaysApply: true
---

# Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

**If no `instruction_format`** (standard Markdown): write a plain `.md` file:

```markdown
# [instruction_dest filename]

This file provides guidance to [Agent Name] when working with code in this repository.

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: 1 (Strategy & Planning) — see `.archflow/current-phase.yaml`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

If the file already exists, check whether it already contains an `## Archflow Framework` section (or the `# Archflow Framework` heading for `.mdc` files). If it does, skip the write entirely (idempotent). If it does not, append only the Archflow section.

**B. Copy Archflow skills**

Copy the archflow skill to the agent's `skills_dest` path from the project root. Skip files that already exist (no-clobber — do not overwrite existing customizations):
```bash
mkdir -p {agent.skills_dest}archflow
rsync -a --ignore-existing skills/archflow/. {agent.skills_dest}archflow/
```
If `rsync` is unavailable, use: `cp -r skills/archflow/. {agent.skills_dest}archflow/` (this will overwrite; inform the user).

**C. Hooks** — skip if `supports_hooks: false`. Only Claude Code writes hooks.

**D. MCP note** — if `mcp_method: manual`, record this agent for the summary (Step 6 will show manual setup instructions).

---

### Step 6: Print Summary

```
Archflow initialized at Phase 1 (Strategy & Planning).

Created:
  .archflow/current-phase.yaml
  AGENTS.md [created / updated with Archflow section]
  CLAUDE.md [created / updated with Archflow section]
  [For each additional detected agent:]
  {agent.instruction_dest} [created / updated with Archflow section]
  {agent.skills_dest}archflow/ [skills copied]

Next steps:
  - Run Phase 1 to define your product strategy
  - The product-strategist agent will create:
    → .archflow/project-context.md (business goals, tech stack, architecture)
    → .archflow/roadmap.yaml (feature roadmap and sprint planning)
```

If GitHub Copilot (or any `mcp_method: manual` agent) was detected, append:

```
MCP Setup for GitHub Copilot (VS Code):
  MCP servers must be added manually to .vscode/mcp.json.
  Run /archflow setup-mcp [tool] for step-by-step guidance with the exact JSON to add.
```

---

## Notes
- This command is idempotent — it won't overwrite existing `.archflow/current-phase.yaml`
- For existing codebases, always use `/archflow onboard` instead (it determines the correct phase via audit)
- The `project_type` field is left as `null` and will be set during Phase 1
