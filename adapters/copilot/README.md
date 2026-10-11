# Archflow for GitHub Copilot CLI

Generated from Archflow 2.4.0 by `scripts/build-adapters.mjs`. Do not edit here.

## Install

**One command:** `npx archflow install --host copilot` from your project root does every step below, and re-running it upgrades in place. By hand:

**Fastest: load the Claude Code plugin directly.** Copilot CLI reads `.claude-plugin/plugin.json` and Claude-shaped `hooks.json`, and sets `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PROJECT_DIR` for plugin hooks:

```
copilot --plugin-dir /path/to/archflow/plugin      # local checkout
copilot plugin install AZidan/archflow:plugin      # from GitHub (subdirectory form)
```

**Repo-scoped (this adapter), for teams that want it committed under .github/:**

1. Copy `.github/agents`, `.github/skills`, `.github/hooks` and `.github/archflow` into your repo (they merge alongside your workflows).
2. Merge `AGENTS.archflow.md` into `AGENTS.md`.
3. Restart Copilot CLI; ask for `/archflow-init` or `/archflow-onboard`.

Node.js 18+ is required for the hooks. The same `.github/` tree is read by VS Code agent mode and by Copilot cloud agent (hooks must be on the default branch for cloud agent).

## What is different on Copilot

| Claude Code | Copilot |
|---|---|
| `/archflow:<cmd>` | `archflow-<cmd>` skills (`.github/skills/`), invoked by name |
| `agents/*.md` sub-agents | `.github/agents/*.agent.md` custom agents (`disable-model-invocation: true`, so only Archflow dispatches them) |
| Plugin hooks | `.github/hooks/archflow.json` using PascalCase events, which give Claude-compatible payloads |
| Telemetry: `UserPromptExpansion` names the command | `UserPromptSubmit` counts a prompt that starts with `/archflow-<cmd>`. Loading the Claude plugin directly should report session starts only, as `host: claude` (Copilot lists no `UserPromptExpansion` event) |
| `/archflow:studio` | `/archflow-studio` in forward mode: Studio runs no agent, its chat composes the command and you paste it into this host's session. Its server bundle goes in `.github/archflow/server` and `.github/archflow/dist`: `npx archflow@latest install` puts it there, or by hand copy the Archflow package's `plugin/server/` and `plugin/dist/` |
| `memory: user` | Not available |
