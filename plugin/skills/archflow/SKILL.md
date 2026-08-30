---
name: archflow
description: Phase-based development workflow manager that guides projects through structured phases from strategy and design through implementation, quality assurance, and launch. Manages roadmaps, releases, feature branches, agent orchestration, and MCP server configuration. Load when the user talks about Archflow phases, releases, the backlog, or asks what to do next in an Archflow project.
---

# Archflow — Phase-Based Development Workflow

Archflow manages the full software development lifecycle through structured phases, from onboarding
existing codebases to launching production software. Releases are the outer loop (schema v2.0);
phases are the inner loop.

## Commands

Every Archflow action is a namespaced slash command — there is no argument-style `/archflow <sub>`.

```
/archflow:status                    → Where the project stands: phase, mode, active release, what's next
/archflow:init                      → Set up a NEW, empty project (creates .archflow/, Phase 1)
/archflow:onboard                   → Set up an EXISTING codebase (audit, import context, pick phase)
/archflow:migrate                   → Upgrade a v1.0 archflow-onboarded project (sprints) → v2.0 (releases); dry-run then apply
/archflow:mode [quick|full]         → Show/switch ceremony mode: quick (solo) or full (team)
/archflow:release [new|start|ship]  → Release pipeline: status, cut, start building, ship
/archflow:setup-mcp [tool]          → Connect an external tool via MCP (Jira, Notion, Linear, ...)
/archflow:groom [story-id]          → Turn a backlog stub into a ready story (ACs, subtasks, gates)
/archflow:feature [name/description|story-id] → Add a story, or pull one into the active release
/archflow:autopilot [story-id ...]  → Run queued stories unattended on one branch (interview, then silent)
/archflow:studio [stop|status|port n] → Local web workspace over the same files; onboards and migrates from the UI (beta)
```

Command bodies live in `${CLAUDE_PLUGIN_ROOT}/commands/<name>.md`. When you need to run one from
inside another flow (e.g. onboarding calls setup-mcp), read that file and follow it inline.

## Framework files (shipped with the plugin)

- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/instructions.md` — agent-neutral base instructions
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/phases/` — per-phase instruction files
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/schemas/` — roadmap / release / backlog / history schemas
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/workflow.md` — git branching strategy
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/base-dsl-structure.yaml` — DSL template for design artifacts
- `${CLAUDE_PLUGIN_ROOT}/skills/archflow/mcp-registry.yaml` — curated MCP server registry
- `${CLAUDE_PLUGIN_ROOT}/scripts/migrate.py` — v1.0 → v2.0 migration engine

`init` / `onboard` copy `instructions.md`, `phases/`, `schemas/`, and `workflow.md` into the
project's `.archflow/`. Paths beginning with `.archflow/` are always **project-local**.

## When this skill is invoked directly

If the user runs this skill on its own (`/archflow:archflow`), behave exactly like
`/archflow:status`: read and follow `${CLAUDE_PLUGIN_ROOT}/commands/status.md`.

## Working in an Archflow project

1. Read `.archflow/current-phase.yaml` → `phase_file`, then follow
   `.archflow/phases/phase-{current}-{name}.md`.
2. `.archflow/instructions.md` (loaded by the SessionStart hook) is the source of truth for agents
   per phase, the release model, and the critical rules — do not restate it here.
3. Stop for explicit user approval at every phase gate.
