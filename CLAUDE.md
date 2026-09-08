# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Archflow Framework

This repository uses [Archflow](https://github.com/AZidan/archflow), a phase-based development
framework with a release-driven outer loop (schema v2.0).

**The framework flow is defined in a single agent-neutral base file:**

📖 **`.archflow/instructions.md`** — read it first. It is the always-injected CORE, deliberately
small. **`.archflow/reference.md`** holds the detail (release model, agent roster, rules in full) and
is read on demand rather than carried all session. It is the source of truth for how Archflow works:
core agents per phase, the release model (releases as the outer loop, backlog stubs, the per-story
readiness pipeline, quick/full modes), the command surface, the universal context files, and the
critical rules. Other coding-agent instruction files (this `CLAUDE.md`, a Cursor `.cursorrules`, a
Windsurf rules file, etc.) all point at `.archflow/instructions.md` rather than duplicating it — one
source, no drift.

Then load the current phase: read `.archflow/current-phase.yaml` → `phase_file`, and follow
`.archflow/phases/phase-{current}-{name}.md`.

## Commands
- `/archflow:status` — status + available commands
- `/archflow:init` / `/archflow:onboard` — set up a new / existing project
- `/archflow:migrate` — upgrade a v1.0 project to schema v2.0
- `/archflow:mode [quick|full]` — show/switch ceremony mode
- `/archflow:release [new|start|ship]` — manage releases
- `/archflow:groom [story-id]` — detail or refine a story (a backlog stub, or one already in a release)
- `/archflow:feature` — add a story to the backlog or active release
- `/archflow:autopilot` — run queued release stories unattended on one branch (interview, then silent)
- `/archflow:design [pick|list|name|story-id]` — the project's design system, and per-story screen design
- `/archflow:contract [story-id]` — the API contract architecture, and per-story endpoint specs
- `/archflow:issue [story-id] ["summary"]` — record a defect on a story in the active release,
  list open issues, or `defer <story-id> <issue-id>` a minor one into the backlog
- `/archflow:doctor [--validate] [--fix]` — check environment + project state; `--fix` repairs drift
  between the project and an upgraded plugin
- `/archflow:studio [stop|status|port <n>]` — open Archflow Studio, a local web workspace (beta)
- `/archflow:setup-mcp [tool]` — connect an external tool via MCP

All commands are namespaced (`/archflow:<name>`) and live in `plugin/commands/*.md`. There is no
argument-style `/archflow <sub>` — never document or suggest that form.

## Repository-specific rules
- Commit ONLY the changes you made — never `git add .` / all files.
- This repo mirrors framework files across two trees: `plugin/skills/archflow/` (the shipped
  source) and `.archflow/` (this repo's own dogfood copy) — keep any edited framework file
  identical in both. This includes `design-systems/`. (`plugin/.archflow/`, the root `skills/` and
  `agents/` trees, and `skills/archflow.zip` are retired — the plugin is the only distribution.)
- Agents live in **`plugin/agents/` only** and are deliberately NOT mirrored. The marketplace ships
  `./plugin`, so that is the single copy that reaches users, and Claude Code loads project agents
  from `.claude/agents/`, which this repo does not use. Never recreate a second agents tree.
