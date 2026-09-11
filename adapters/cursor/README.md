# Archflow for Cursor

Generated from Archflow 2.3.2 by `scripts/build-adapters.mjs`. Do not edit here.

## Install

**As a project overlay:** copy `.cursor/` into your project root and restart Cursor.

**As a plugin:** the directory is a Cursor Plugin (`.cursor-plugin/plugin.json`); install it from Customize → Plugins, or publish it to a marketplace.

Node.js 18+ is required for the hooks.

## What is different on Cursor

| Claude Code | Cursor |
|---|---|
| `/archflow:<cmd>` | `/archflow-<cmd>` (`.cursor/commands/`) |
| `agents/*.md` sub-agents | `.cursor/agents/*.md` (`model: inherit`; reviewers `readonly: true`) |
| Plugin hooks | `.cursor/hooks.json` (`sessionStart` / `beforeShellExecution` / `stop`) via a small bridge script |
| `CLAUDE.md` section | `.cursor/rules/archflow.mdc` (`alwaysApply`) |
| `/archflow:studio` | Not available |
| `memory: user` | Not available |

Project hooks also run in Cursor cloud agents.
