# Archflow for Gemini CLI

Generated from Archflow 2.4.0 by `scripts/build-adapters.mjs`. Do not edit here.

## Install

**One command:** `npx archflow install --host gemini` from your project root does every step below, and re-running it upgrades in place. By hand:

```
gemini extensions install https://github.com/AZidan/archflow --ref main   # once published under adapters/gemini
gemini extensions link ./adapters/gemini                                # local development
```

Restart Gemini CLI, then run `/archflow:init` or `/archflow:onboard`. Node.js 18+ is required for the hooks.

## What is different on Gemini CLI

| Claude Code | Gemini CLI |
|---|---|
| `/archflow:<cmd>` | `/archflow:<cmd>` (identical; TOML commands under `commands/archflow/`) |
| `agents/*.md` sub-agents | `agents/*.md` (`kind: local`) — sub-agents are a preview feature |
| `PreToolUse` / `Stop` hooks | `BeforeTool` / `AfterAgent` hooks (timeouts in ms) |
| Telemetry: `UserPromptExpansion` names the command | `BeforeAgent` counts a prompt that starts with `/archflow:<cmd>` or the command's marker line |
| `/archflow:studio` | `/archflow:studio` in forward mode: Studio runs no agent, its chat composes the command and you paste it into this host's session. Its server bundle goes in `~/.gemini/extensions/archflow/server` and `~/.gemini/extensions/archflow/dist`: `npx archflow install` puts it there, or by hand copy the Archflow package's `plugin/server/` and `plugin/dist/` |
| `memory: user` | Not available |

Note: Gemini CLI's extension install location is per-user (`~/.gemini/extensions`), not per-project. Use `gemini extensions disable archflow --scope workspace` in repos that don't use it.
