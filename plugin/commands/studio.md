---
description: "[Beta] Start (or stop) Archflow Studio for the current project and open it in the browser"
argument-hint: "[stop | status | port <n>]"
allowed-tools: Bash(curl:*), Bash(lsof:*), Bash(kill:*), Bash(node:*), Bash(nohup:*), Bash(mkdir:*), Bash(cat:*), Bash(tail:*), Bash(open:*), Bash(xdg-open:*), Bash(sleep:*), Bash(nc:*), Bash(printf:*)
disable-model-invocation: true
---

# Archflow Studio companion

Arguments: `$ARGUMENTS`

You manage a local Archflow Studio server for the project in the current working directory. Run
**the probe** first, classify the port with the table below, then follow the branch for the verb.
All three verbs are idempotent: running one twice must produce the same end state and the same
report, never a second server and never an error for work already done.

Keep the conversation short: one status line per step, then the URL.

## Settings

- `PORT` = the number after `port` in the arguments, otherwise `3456`.
- `URL` = `http://localhost:${PORT}`
- Server bundle: `${CLAUDE_PLUGIN_ROOT}/server/server.mjs`
- `LOG` = `$HOME/.archflow/studio/logs/studio-${PORT}.log` — where a detached server's output
  goes, since a detached process cannot write to this session's terminal.
- Session context: `${STUDIO_SESSION_CONTEXT:-$HOME/.archflow/studio/session-context.json}` —
  written by this plugin's `SessionStart` hook. See [Companion mode](#companion-mode).
- Project root: the current working directory of this session (`$PWD` in Bash).

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
(`lsof -iTCP:${PORT} -sTCP:LISTEN` names the process) and suggest `/archflow:studio port <n+1>`.

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
   `/archflow:studio port <n+1>` would start one for this project.
5. **FOREIGN** → `Port ${PORT} is held by another program, not Archflow Studio.`

For STUDIO-HERE or STUDIO-ELSEWHERE, also run
`curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/chat/session"` and report the `mode`
(`companion` or `full`) in the same line, so the user can see whether the handoff worked without
opening the browser.

## start (no arguments, or `port <n>`)

1. **Probe.**
   - **STUDIO-HERE** → it is already running. Print the URL (step 5) and skip to step 6. **Do not
     start a second server.** This is the idempotent case and it must be silent about having done
     nothing new beyond one line.
   - **STUDIO-ELSEWHERE** → tell the user that port is serving `<name>` at `<path>` and suggest
     `/archflow:studio port <n+1>`. Stop; do not start anything on this port.
   - **FOREIGN** → say another program owns the port, name it, suggest `/archflow:studio port
     <n+1>`. Stop; **never kill it**.
   - **FREE** → continue.
2. **Bundle present?** If `${CLAUDE_PLUGIN_ROOT}/server/server.mjs` does not exist, stop and tell
   the user to run `npm run build:plugin && npm run sync:plugin` in the archflow-studio repo. Do
   not try to build it from here.
3. **Start it DETACHED.** Not with the Bash tool's `run_in_background`: that keeps the server a
   child of this session, so it dies when the session does. The studio has to outlive the
   conversation that started it — that is the whole point of a companion studio you can leave open.

   ```bash
   mkdir -p "$HOME/.archflow/studio/logs"
   STUDIO_PROJECT_PATH="$PWD" STUDIO_PORT=${PORT} STUDIO_AUTO_OPEN=0 \
     nohup node "${CLAUDE_PLUGIN_ROOT}/server/server.mjs" \
     --session-context "${STUDIO_SESSION_CONTEXT:-$HOME/.archflow/studio/session-context.json}" \
     > "$HOME/.archflow/studio/logs/studio-${PORT}.log" 2>&1 < /dev/null &
   ```

   Run it as an ORDINARY foreground Bash call — it returns immediately because of the trailing `&`.
   Each part earns its place:

   - `nohup` — ignores the `SIGHUP` sent when the session's terminal goes away.
   - `> "$LOG" 2>&1` — a detached process has no terminal to write to, and an inherited pipe with
     nobody reading it will eventually block the server on its own log output.
   - `< /dev/null` — nothing to read, so it cannot be stopped waiting on a stdin that has gone.
   - `&` — the launching shell exits immediately and the server is reparented to `init`/`launchd`.

   `--session-context` is what makes this a *companion* studio rather than an unrelated one — see
   below. Passing it explicitly is deliberate: it is the same path the server would have guessed,
   but stating it means the handoff is visible in the command line and can be pointed elsewhere by
   setting `STUDIO_SESSION_CONTEXT` in the session.

4. **Wait for it.** Poll until the port answers (up to ~10 s):

   ```bash
   for i in $(seq 1 20); do
     curl -s --max-time 1 "http://127.0.0.1:${PORT}/api/project" >/dev/null && break
     sleep 0.5
   done
   curl -s --max-time 2 "http://127.0.0.1:${PORT}/api/project"
   ```

   If it never answers, `cat "$LOG"` and stop — that file is the only place a detached server's
   output goes. The startup log's `[mode]` line says which mode it resolved and, when it degraded,
   why.

5. **Report.** Print exactly one line: `Archflow Studio is running at ${URL}` followed by the
   project name from `/api/project`. If `/api/chat/session` reports `mode: "full"` when you
   expected companion, add the degrade reason from `tail -5 "$LOG"`'s `[mode]` line — a degrade is
   normal and explained, not a fault to debug.
6. **Open it.** Ask the user whether to open it in the browser. If yes (or if the user's request
   already said "open"), run `open "${URL}"` on macOS (`xdg-open` on Linux). Mention that
   `/archflow:studio stop` shuts it down.

## Companion mode

This plugin ships a `SessionStart` hook — `hooks/studio-session-context.mjs`, registered alongside
archflow's existing instructions hook — that writes the current session's id, transcript path and
cwd to:

```
${STUDIO_SESSION_CONTEXT:-~/.archflow/studio/session-context.json}
```

Step 3 hands that file to the server with `--session-context`, and the server resolves **companion
mode** from it: Studio's chat then talks to *this* session rather than an unrelated one.

- The file is rewritten on every session start, resume, clear and compact.
- Nothing deletes it when a session ends. The server ignores it once it is more than 12 hours old,
  so yesterday's session cannot capture today's Studio.
- It is one file per machine, so the most recently started session owns it. Two sessions that both
  want their own Studio must each set `STUDIO_SESSION_CONTEXT` to a different path before running
  this command.
- Missing, stale or malformed: the server says so in its `[mode]` startup line and runs in **full**
  mode instead. That is a degrade, never a crash — Studio still works, its chat just isn't wired to
  your terminal's session.

## Notes for you

- Never start a second server on the same port; the probe in step 1 is what prevents it, so never
  skip it — not even when you started the server yourself a moment ago.
- **The server outlives this session, by design.** Step 3 detaches it, so ending the conversation
  — or closing the terminal — leaves Studio running. That is deliberate: a studio that vanished
  with the session could not be left open beside it. `/archflow:studio stop` is how it ends, and
  `stop` works from any session because it kills by the pid the probe finds, not by parentage.
- A consequence worth stating rather than discovering: a studio from an EARLIER session is
  STUDIO-HERE to this one, and step 1 will adopt it silently rather than start a second. That is
  the idempotent case working, not a stale server. Its chat is still wired to whichever session
  owned `session-context.json` when it started — `/api/chat/session` says which.
- **What Studio's chat panel does depends on the mode it resolved**, and Studio reports it at
  `/api/chat/session`:
  - **companion** — chat runs `claude --resume <session-id> --fork-session` against *this* session.
    You get this conversation's history on a **branch**; nothing you type in Studio lands back in
    this terminal. Studio states that itself, so there is no need to warn the user separately.
  - **full** (the default, and where companion degrades to) — chat spawns its own `claude` process,
    unrelated to this session. This is the case worth a one-line mention if the user expected
    continuity with this conversation.
  - **no chat** — with `--chat-policy off`, or `--chat-policy forward` in companion mode
    (forwarding to your terminal is not built yet). Studio reports the reason rather than failing.
