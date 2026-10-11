---
name: archflow-studio
description: "[Beta] Start (or stop) Archflow Studio for the current project and open it in the browser"
---

> Invoke with `$archflow-studio`. Arguments are the text after the mention.

Arguments: `[stop | status | port <n>]`


# Archflow Studio

Arguments: `the text the user wrote after the skill mention`

You manage a local Archflow Studio server for the project in the current working directory. Run
**the probe** first, classify the port with the table below, then follow the branch for the verb.
All three verbs are idempotent: running one twice must produce the same end state and the same
report, never a second server and never an error for work already done.

Keep the conversation short: one status line per step, then the URL.

Studio runs on every host Archflow supports. What its chat panel does depends on the host it
resolves for the project; see [Hosts and chat](#hosts-and-chat). This command is the same
everywhere: it starts, reports on and stops the server.

## Settings

- `PORT` = the number after `port` in the arguments, otherwise `3456`.
- `URL` = `http://localhost:${PORT}`
- `BUNDLE` = `.codex/archflow/server/server.mjs`, the server, with the web UI it serves in
  `.codex/archflow/dist` beside it. Both ship with this host's Archflow install.
- `LOG` = `$HOME/.archflow/studio/logs/studio-${PORT}.log`, where a detached server's output
  goes, since a detached process cannot write to this session's terminal.
- Session context: `${STUDIO_SESSION_CONTEXT:-$HOME/.archflow/studio/session-context.json}`.
  Always handed to the server; it only matters for companion mode on the `claude` host. See
  [Companion mode](#companion-mode).
- Project root: the current working directory of this session (`$PWD` in Bash). Run every command
  below from it.
- This host's id, `codex`: how Studio names the host this command is running in.

## The probe

Every verb starts here. One command, two facts:

```bash
printf 'pids=[%s]\n' "$(lsof -tiTCP:${PORT} -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')"
printf 'body=%s\n' "$(curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/project" || true)"
```

Classify the port into exactly one of four states:

| `pids` | `body` | State | Meaning |
|---|---|---|---|
| empty | — | **FREE** | nothing is listening |
| non-empty | JSON object with a `path` field | **STUDIO-HERE** | …and `path` equals `$PWD` |
| non-empty | JSON object with a `path` field | **STUDIO-ELSEWHERE** | …and `path` is a different directory |
| non-empty | empty, or not JSON, or JSON without `path` | **FOREIGN** | some other program owns the port |

`/api/project` answering with a `path` is what identifies a Studio; a bare listener is not one.
Compare `path` to `$PWD` literally after resolving symlinks if they differ only by `/private`
(macOS `/tmp`). Never assume — always read `path` out of the probe body you just ran.

**FOREIGN is never killed.** Not by `start`, not by `stop`. Report what is there
(`lsof -iTCP:${PORT} -sTCP:LISTEN` names the process) and suggest `$archflow-studio port <n+1>`.

## The chat line

`status` and `start` both report which host Studio resolved and what its chat does. Read it from
one call:

```bash
curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/chat/session"
```

- `host` — the host Studio resolved for this project.
- `chat` — derived, never guessed:
  - `chatPolicy.reasonCode` is `FORWARD_TO_TERMINAL` → **forward**
  - `chatPolicy.reasonCode` is `CHAT_DISABLED` → **off**
  - otherwise → the `mode` field: **full** or **companion**

Report them as `host <host>, chat <chat>`. If `host` is not this host's id (see
[Settings](#settings)), add one line: Studio resolved another host for this project, and the host
picker in Studio's settings changes it (the choice is saved per project), or setting
`STUDIO_HOST=<id>` before starting forces it for that launch.

## `stop`

1. Probe.
2. **FREE** → say `Archflow Studio is not running on port ${PORT}.` and stop. This is success, not
   an error: stopping something already stopped is a no-op, so do not retry and do not report a
   failure.
3. **FOREIGN** → say the port is held by another program, name it, and stop **without killing it**.
4. **STUDIO-HERE** or **STUDIO-ELSEWHERE** → `kill ${pids}`, `sleep 1`, re-probe. If it is now
   FREE, confirm it stopped. If it is still there, `kill -9` those pids, re-probe once more, and
   report the outcome either way.

## `status`

1. Probe. Report exactly one of:
2. **FREE** → `Archflow Studio is not running on port ${PORT}.`
3. **STUDIO-HERE** → `Archflow Studio is running at ${URL} — <name> (this project).`
4. **STUDIO-ELSEWHERE** → `Port ${PORT} is serving another project: <name> at <path>.` Add that
   `$archflow-studio port <n+1>` would start one for this project.
5. **FOREIGN** → `Port ${PORT} is held by another program, not Archflow Studio.`

For STUDIO-HERE or STUDIO-ELSEWHERE, append [the chat line](#the-chat-line) to the same report, so
the user can see what the chat panel will do without opening the browser.

## start (no arguments, or `port <n>`)

1. **Probe.**
   - **STUDIO-HERE** → it is already running. Print the URL (step 5) and skip to step 6. **Do not
     start a second server.** This is the idempotent case and it must be silent about having done
     nothing new beyond one line.
   - **STUDIO-ELSEWHERE** → tell the user that port is serving `<name>` at `<path>` and suggest
     `$archflow-studio port <n+1>`. Stop; do not start anything on this port.
   - **FOREIGN** → say another program owns the port, name it, suggest `$archflow-studio port
     <n+1>`. Stop; **never kill it**.
   - **FREE** → continue.
2. **Bundle present?**

   ```bash
   test -f ".codex/archflow/server/server.mjs" && echo bundle=ok || echo bundle=missing
   ```

   If it is missing, stop and tell the user the Studio bundle did not reach this install: running
   `npx archflow@latest install` from the project root puts it where this command looks
   (`@latest`, because a cached older installer brings the adapters without the bundle). Do not
   try to build or fetch it from here.
3. **Start it DETACHED.** Not as a background task of this session: that keeps the server a child
   of the session, so it dies when the session does. The studio has to outlive the conversation
   that started it — that is the whole point of a studio you can leave open.

   ```bash
   mkdir -p "$HOME/.archflow/studio/logs"
   STUDIO_PROJECT_PATH="$PWD" STUDIO_PORT=${PORT} STUDIO_AUTO_OPEN=0 \
     nohup node ".codex/archflow/server/server.mjs" \
     --session-context "${STUDIO_SESSION_CONTEXT:-$HOME/.archflow/studio/session-context.json}" \
     > "$HOME/.archflow/studio/logs/studio-${PORT}.log" 2>&1 < /dev/null &
   ```

   Run it as an ORDINARY foreground shell command — it returns immediately because of the trailing
   `&`. Each part earns its place:

   - `nohup` — ignores the `SIGHUP` sent when the session's terminal goes away.
   - `> "$LOG" 2>&1` — a detached process has no terminal to write to, and an inherited pipe with
     nobody reading it will eventually block the server on its own log output.
   - `< /dev/null` — nothing to read, so it cannot be stopped waiting on a stdin that has gone.
   - `&` — the launching shell exits immediately and the server is reparented to `init`/`launchd`.

   The command passes no host. Studio resolves it itself, in this order: `--host` or
   `STUDIO_HOST`, then the choice saved from Studio's host picker for this project, then detection
   of the Archflow installs it finds (this host's install is one of them). Leaving the host off is
   what keeps a choice made in the picker in force on the next launch.

   `--session-context` hands the server the companion handoff file. It is harmless everywhere and
   only read for companion mode; see [Companion mode](#companion-mode).

4. **Wait for it.** Poll until the port answers (up to ~10 s):

   ```bash
   for i in $(seq 1 20); do
     curl -s --max-time 1 "http://127.0.0.1:${PORT}/api/project" >/dev/null && break
     sleep 0.5
   done
   curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/project"
   ```

   If it never answers, `cat "$LOG"` and stop — that file is the only place a detached server's
   output goes. The startup log's `[host]` line says which host it resolved and from where, and its
   `[mode]` line says which mode it resolved and, when it degraded, why.

   **Sandboxed shells.** Some hosts run commands in a sandbox (Codex's `workspace-write`, for
   one) that can block what steps 1–4 need: writing under `$HOME/.archflow`, listening on and
   curling `127.0.0.1`, or a detached child outliving its command. A failed `mkdir`, no log file,
   or `bundle=ok` with a port that never answers on such a host points at the sandbox, not Studio.
   Re-run the start and probe with the host's approval to run outside the sandbox (or with network
   and write access granted), or give the user step 3's command, values filled in, to run in their
   own terminal from the project root.

5. **Report.** Print one line: `Archflow Studio is running at ${URL}`, the project name from
   `/api/project`, and [the chat line](#the-chat-line). Only if the session set
   `STUDIO_MODE=companion` and the chat is not `companion`, add the reason from `tail -5 "$LOG"`'s
   `[mode]` line — a degrade is normal and explained, not a fault to debug.
6. **Open it.** Ask the user whether to open it in the browser. If yes (or if the user's request
   already said "open"), run `open "${URL}"` on macOS (`xdg-open` on Linux). Mention that
   `$archflow-studio stop` shuts it down.

## Hosts and chat

The board, releases, stories, files and design views work the same on every host: they read the
project's `.archflow/` files. What differs is the chat panel, which depends on the host Studio
resolved (`host` in the chat line):

| Host Studio resolved | Chat | What the panel does |
|---|---|---|
| `claude` | **full** (the default) | Runs its own `claude` process, unrelated to this session. Needs the `claude` binary on `PATH`. |
| `claude`, with `STUDIO_MODE=companion` | **companion** | Runs `claude --resume <session-id> --fork-session` against the session that wrote the handoff file. See [Companion mode](#companion-mode). |
| `codex`, `copilot`, `cursor`, `gemini`, `opencode`, `generic` | **forward** | Studio runs no agent. You compose in the panel, Studio spells the command the way that host expects, and Send copies it for you to paste into your own terminal session. No permission prompts, interrupt or session switching in the panel: the terminal owns the session. |
| any, with `--chat-policy off` or `STUDIO_CHAT_POLICY=off` | **off** | No chat panel. Studio reports the reason rather than failing. |

`--chat-policy forward` (or `STUDIO_CHAT_POLICY=forward`) puts the `claude` host in forward mode
too, for a user who would rather paste into the session they already have than have Studio run a
second one. Forward mode needs nothing beyond Node: no hook, no handoff file, no `claude` binary.

Studio detects a host by its Archflow install: `.claude/settings.json` (or the user-level one)
enabling the plugin for `claude`; `.codex/archflow`, `.cursor/archflow`, `.opencode/archflow` or
`.github/archflow` in the project for `codex`, `cursor`, `opencode` and `copilot`;
`$HOME/.gemini/extensions/archflow` for `gemini`; `.agents/archflow` for `generic`. When several are
installed, detection ranks them: the `claude` plugin enabled in the project, then the project's own
`codex`, `cursor`, `opencode` or `copilot` install, then the `claude` plugin enabled for the user,
then `gemini`, then `generic`. The host picker in Studio switches between the detected hosts.

## Companion mode

Companion applies only when Studio's host is `claude`. On every other host there is no session for
Studio to fork, so a companion request runs in forward mode, and Studio says so.

The Archflow plugin for the `claude` host ships a `SessionStart` hook,
`hooks/studio-session-context.mjs`, that writes the current session's id, transcript path and cwd
to:

```
${STUDIO_SESSION_CONTEXT:-~/.archflow/studio/session-context.json}
```

No other host's install has that hook, so nothing else writes the file.

Start hands that file to the server with `--session-context`. **Full is the default:** the server
reads the file and keeps it, but its presence does not select companion, so a fresh file still
starts a full-mode studio whose chat spawns its own `claude`. Companion — Studio's chat starting
from *this* session's history rather than an unrelated one — is **opt-in**. To get it, set
`STUDIO_MODE=companion` in the session *before* running this command:

```bash
export STUDIO_MODE=companion
```

The server's own precedence is `--mode` flag, then `STUDIO_MODE`, then the default `full`, and
step 3 inherits the session's environment, so the exported variable is honoured without any change
to the command line above.

- The file is rewritten on every session start, resume, clear and compact.
- Nothing deletes it when a session ends. The server ignores it once it is more than 12 hours old,
  so yesterday's session cannot capture today's Studio.
- It is one file per machine, so the most recently started session owns it. Two sessions that both
  want their own Studio must each set `STUDIO_SESSION_CONTEXT` to a different path before running
  this command.
- Missing, stale or malformed when companion was opted into: the server says so in its `[mode]`
  startup line and runs in **full** mode instead. That is a degrade, never a crash — Studio still
  works, its chat just isn't wired to your terminal's session. Without the opt-in the file's state
  is irrelevant: full was chosen, nothing degraded, and the `[mode]` line names source `default`.
- In companion mode you get this conversation's history on a **branch**: nothing you type in
  Studio lands back in this terminal. Studio states that itself, so there is no need to warn the
  user separately.

## Notes for you

- Never start a second server on the same port; the probe in step 1 is what prevents it, so never
  skip it — not even when you started the server yourself a moment ago.
- **The server outlives this session, by design.** Step 3 detaches it, so ending the conversation
  — or closing the terminal — leaves Studio running. That is deliberate: a studio that vanished
  with the session could not be left open beside it. `$archflow-studio stop` is how it ends, and
  `stop` works from any session, on any host, because it kills by the pid the probe finds, not by
  parentage.
- A consequence worth stating rather than discovering: a studio from an EARLIER session is
  STUDIO-HERE to this one, and step 1 will adopt it silently rather than start a second. That is
  the idempotent case working, not a stale server. Its host and chat are the ones it resolved when
  it started; [the chat line](#the-chat-line) says which. Stop and start it to pick up a new
  `STUDIO_HOST`, `STUDIO_MODE` or chat policy.
- In forward mode a command copied from Studio and pasted into this session is an ordinary prompt
  here: run it as you would any other.
