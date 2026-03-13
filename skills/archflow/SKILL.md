# /archflow — Phase-Based Development Workflow

Archflow manages the full software development lifecycle through structured phases, from onboarding existing codebases to launching production software.

## Usage
```
/archflow                → Show available subcommands
/archflow onboard        → Onboard an existing codebase (interactive wizard)
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

  /archflow onboard       Onboard an existing codebase to the phase framework
                          (detect project type, import context, audit, set phase)

  /archflow setup-mcp     Configure MCP servers for external tools
                          (Jira, Notion, Linear, GitHub, SuperDesign, etc.)

  /archflow feature       Add a new feature to the roadmap and start development
                          (from description, external tool link, or existing roadmap)

Current project status:
  → Read .archflow/current-phase.yaml if it exists, show phase + project type
  → If missing: "No project onboarded. Run /archflow onboard to get started."
```

### `onboard` → Load onboarding wizard
Read and follow `skills/archflow/commands/onboard.md`

### `setup-mcp` → Load MCP setup helper
Read and follow `skills/archflow/commands/setup-mcp.md`
Pass any additional arguments (e.g., `jira`, `notion`) as the tool name.

### `feature` → Load feature command
Read and follow `skills/archflow/commands/feature.md`
Pass any additional arguments (e.g., `login`) as the feature name for quick-add.

### Unknown subcommand
```
Unknown subcommand: [arg]

Available: onboard, setup-mcp, feature
Run /archflow for help.
```
