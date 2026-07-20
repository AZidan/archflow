---
name: archflow
description: Phase-based development workflow manager that guides projects through structured phases from strategy and design through implementation, quality assurance, and launch. Manages roadmaps, feature branches, agent orchestration, and MCP server configuration.
---

# /archflow — Phase-Based Development Workflow

Archflow manages the full software development lifecycle through structured phases, from onboarding existing codebases to launching production software.

## Usage
```
/archflow                → Show available subcommands
/archflow init           → Initialize Archflow in a new project
/archflow onboard        → Onboard an existing codebase (interactive wizard)
/archflow migrate        → Migrate a v1.0 project to schema v2.0 (releases)
/archflow mode [quick|full] → Show or switch the ceremony mode
/archflow release        → Inspect / manage releases (status, new, start, ship)
/archflow setup-mcp      → Configure MCP servers for external tools
/archflow setup-mcp jira → Configure a specific MCP server
/archflow feature        → Add a new feature to the roadmap
/archflow feature login  → Quick-add a feature by name
```

## Subcommand Router

When the user runs `/archflow`, check the argument to determine which subcommand to execute:

### No arguments → Show help
```
Archflow — Phase-Based Development Workflow

Available subcommands:

  /archflow init          Initialize Archflow in a new project
                          (creates .archflow/ state files, sets Phase 1)

  /archflow onboard       Onboard an existing codebase to the phase framework
                          (detect project type, import context, audit, set phase)

  /archflow migrate       Migrate a v1.0 project to schema v2.0
                          (releases replace phases, sprints retired, multi-file split)

  /archflow mode          Show or switch the ceremony mode (quick | full)

  /archflow release       Inspect / manage releases (status, new, start, ship)

  /archflow setup-mcp     Configure MCP servers for external tools
                          (Jira, Notion, Linear, GitHub, SuperDesign, etc.)

  /archflow feature       Add a new feature to the roadmap and start development
                          (from description, external tool link, or existing roadmap)

Current project status:
  → Read .archflow/current-phase.yaml if it exists, show phase + project type + mode + active_release
  → If .archflow/roadmap.yaml is v1.0 (has phases:/no schema_version): suggest "/archflow migrate"
  → If missing: "No project onboarded. Run /archflow onboard to get started."
```

### `init` → Load project initializer
Read and follow `skills/archflow/commands/init.md`

### `onboard` → Load onboarding wizard
Read and follow `skills/archflow/commands/onboard.md`

### `migrate` → Load v1.0 → v2.0 migration
Read and follow `skills/archflow/commands/migrate.md`

### `mode` → Load mode show/switch
Read and follow `skills/archflow/commands/mode.md`
Pass any additional argument (`quick` / `full`) as the target mode.

### `release` → Load release management
Read and follow `skills/archflow/commands/release.md`
Pass any additional arguments (`new [name]` / `start [slug]` / `ship`) through.

### `setup-mcp` → Load MCP setup helper
Read and follow `skills/archflow/commands/setup-mcp.md`
Pass any additional arguments (e.g., `jira`, `notion`) as the tool name.

### `feature` → Load feature command
Read and follow `skills/archflow/commands/feature.md`
Pass any additional arguments (e.g., `login`) as the feature name for quick-add.

### Unknown subcommand
```
Unknown subcommand: [arg]

Available: init, onboard, migrate, mode, release, setup-mcp, feature
Run /archflow for help.
```
