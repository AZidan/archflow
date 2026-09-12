# Archflow for OpenCode

Generated from Archflow 2.3.2 by `scripts/build-adapters.mjs`. Do not edit here.

## Install

**One command:** `npx archflow-install --host opencode` from your project root does every step below, and re-running it upgrades in place. By hand:

1. Copy `.opencode/` into your project root.
2. Merge `AGENTS.archflow.md` into `AGENTS.md`.
3. Restart OpenCode; run `/archflow-init` or `/archflow-onboard`.

Node.js 18+ (or Bun) is required for the plugin hooks.

## What is different on OpenCode

| Claude Code | OpenCode |
|---|---|
| `/archflow:<cmd>` | `/archflow-<cmd>` (OpenCode has no colon namespaces) |
| `agents/*.md` sub-agents | `.opencode/agents/*.md` with `mode: subagent` |
| Plugin hooks | `.opencode/plugins/archflow.ts` (`tool.execute.before`, system-prompt transform, `session.idle`) |
| `/archflow:studio` | Not available |
| `memory: user` | Not available |

Known limitation: OpenCode plugin hooks do not currently fire for tool calls made *inside* subagents (anomalyco/opencode#5894), so the git guard only covers the primary agent. The approval gates remain the real control.
