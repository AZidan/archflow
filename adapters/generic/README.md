# Archflow for any Agent-Skills host

Generated from Archflow 2.4.0 by `scripts/build-adapters.mjs`. Do not edit here.

This is the lowest-common-denominator package: `AGENTS.md` + Agent Skills (agentskills.io). It works in any host that reads those, including Cline, Roo, Kilo, Windsurf, Zed, Amp and Copilot/Codex/OpenCode/Cursor without their native adapters.

## Install

**One command:** `npx archflow install --host generic` from your project root does every step below, and re-running it upgrades in place. By hand:

1. Copy `.agents/` into your project root.
2. Merge `AGENTS.archflow.md` into `AGENTS.md`.
3. Install the git guard: `sh .agents/archflow/scripts/archflow-install-git-guard.sh`
4. Ask your agent to run `$archflow-init` or `$archflow-onboard`.

## What you give up

- No sub-agents: roles run serially inside the main context (bigger context use, slower Phase 3).
- No lifecycle hooks: instructions load via AGENTS.md, and the upgrade check and session telemetry run because AGENTS.md asks the agent to run them, not because the host does. Per-command telemetry is not available.
- The git guard is a real `pre-push` hook, so it also protects you from your own terminal.

## Archflow Studio

| Claude Code | Here |
|---|---|
| `/archflow:studio` | `$archflow-studio` in forward mode: Studio runs no agent, its chat composes the command and you paste it into this host's session. Its server bundle goes in `.agents/archflow/server` and `.agents/archflow/dist`: `npx archflow@latest install` puts it there, or by hand copy the Archflow package's `plugin/server/` and `plugin/dist/` |
