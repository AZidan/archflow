# Archflow for OpenAI Codex

Generated from Archflow 2.3.2 by `scripts/build-adapters.mjs`. Do not edit here; edit `plugin/` and rebuild.

## Install

**One command:** `npx archflow-install --host codex` from your project root does every step below, and re-running it upgrades in place. By hand:

1. Copy `.agents/` and `.codex/` into your project root.
2. Merge `AGENTS.archflow.md` into your `AGENTS.md` (create it if absent).
3. Merge `.codex/config.archflow.toml` into `.codex/config.toml`.
4. Trust the project in Codex (project-scoped agents and hooks only load in trusted projects), then restart Codex.
5. Run `$archflow-init` (new project) or `$archflow-onboard` (existing codebase).

Node.js 18+ is required for the hooks.

## What is different on Codex

| Claude Code | Codex |
|---|---|
| `/archflow:<cmd>` slash commands | `$archflow-<cmd>` skills (explicit invocation only) |
| `agents/*.md` sub-agents | `.codex/agents/*.toml` custom agents via `spawn_agent` |
| Plugin hooks (`hooks.json`) | `.codex/hooks.json` — same events; needs the `hooks` feature (default on) |
| `SessionStart` injects `instructions.md` | Same hook, plus an AGENTS.md instruction as a fallback |
| `/archflow:studio` | Not available — Studio drives the `claude` binary |
| `memory: user` agent memory | Not available |

The `.archflow/` state files, schemas, phases, design systems and stack profiles are identical across hosts, so a project can be worked on from both Claude Code and Codex.
