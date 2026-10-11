# Archflow for Cursor

Generated from Archflow 2.4.0 by `scripts/build-adapters.mjs`. Do not edit here.

## Install

**One command:** `npx archflow install --host cursor` from your project root does every step below, and re-running it upgrades in place. By hand:

**As a project overlay:** copy `.cursor/` into your project root and restart Cursor.

**As a plugin:** the directory is a Cursor Plugin (`.cursor-plugin/plugin.json`); install it from Customize → Plugins, or publish it to a marketplace.

Node.js 18+ is required for the hooks.

## What is different on Cursor

| Claude Code | Cursor |
|---|---|
| `/archflow:<cmd>` | `/archflow-<cmd>` (`.cursor/commands/`) |
| `agents/*.md` sub-agents | `.cursor/agents/*.md` (`model: inherit`; reviewers `readonly: true`) |
| Plugin hooks | `.cursor/hooks.json` (`sessionStart` / `beforeSubmitPrompt` / `beforeShellExecution` / `stop`) via a small bridge script |
| `CLAUDE.md` section | `.cursor/rules/archflow.mdc` (`alwaysApply`) |
| Telemetry: `UserPromptExpansion` names the command | `beforeSubmitPrompt` counts a prompt that starts with `/archflow-<cmd>` |
| `/archflow:studio` | `/archflow-studio` in forward mode: Studio runs no agent, its chat composes the command and you paste it into this host's session. Its server bundle goes in `.cursor/archflow/server` and `.cursor/archflow/dist`: `npx archflow@latest install` puts it there, or by hand copy the Archflow package's `plugin/server/` and `plugin/dist/` |
| `memory: user` | Not available |

Project hooks also run in Cursor cloud agents.
