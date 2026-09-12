# Archflow for any Agent-Skills host

Generated from Archflow 2.3.2 by `scripts/build-adapters.mjs`. Do not edit here.

This is the lowest-common-denominator package: `AGENTS.md` + Agent Skills (agentskills.io). It works in any host that reads those, including Cline, Roo, Kilo, Windsurf, Zed, Amp and Copilot/Codex/OpenCode/Cursor without their native adapters.

## Install

**One command:** `npx archflow-install --host generic` from your project root does every step below, and re-running it upgrades in place. By hand:

1. Copy `.agents/` into your project root.
2. Merge `AGENTS.archflow.md` into `AGENTS.md`.
3. Install the git guard: `sh .agents/archflow/scripts/archflow-install-git-guard.sh`
4. Ask your agent to run `$archflow-init` or `$archflow-onboard`.

## What you give up

- No sub-agents: roles run serially inside the main context (bigger context use, slower Phase 3).
- No lifecycle hooks: instructions load via AGENTS.md; upgrade and schema-drift checks run inside `$archflow-doctor` instead of automatically.
- The git guard is a real `pre-push` hook, so it also protects you from your own terminal.
