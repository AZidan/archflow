# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Archflow Framework

This repository uses [Archflow](https://github.com/AZidan/archflow), a phase-based development
framework with a release-driven outer loop (schema v2.0).

**The framework flow is defined in a single agent-neutral base file:**

📖 **`.archflow/instructions.md`** — read it first. It is the source of truth for how Archflow works:
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
- `/archflow:groom [story-id]` — detail a backlog stub into a `ready` story
- `/archflow:feature` — add a story to the backlog or active release
- `/archflow:setup-mcp [tool]` — connect an external tool via MCP

All commands are namespaced (`/archflow:<name>`) and live in `plugin/commands/*.md`. There is no
argument-style `/archflow <sub>` — never document or suggest that form.

## Repository-specific rules
- Commit ONLY the changes you made — never `git add .` / all files.
- This repo mirrors framework files across two trees: `plugin/skills/archflow/` (the shipped
  source) and `.archflow/` (this repo's own dogfood copy) — keep any edited framework file
  identical in both. (`plugin/.archflow/`, the root `skills/` tree, and `skills/archflow.zip` are
  retired — the plugin is the only distribution.)
