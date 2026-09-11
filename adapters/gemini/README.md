# Archflow for Gemini CLI

Generated from Archflow 2.3.2 by `scripts/build-adapters.mjs`. Do not edit here.

## Install

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
| `/archflow:studio` | Not available |
| `memory: user` | Not available |

Note: Gemini CLI's extension install location is per-user (`~/.gemini/extensions`), not per-project. Use `gemini extensions disable archflow --scope workspace` in repos that don't use it.
