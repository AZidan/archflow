---
description: "Show or change anonymous usage telemetry (on by default; this is how to opt out)"
argument-hint: "[on|off|status]"
---

# /archflow:telemetry — Show or change anonymous usage telemetry

Argument (`$ARGUMENTS`): optional `on` or `off`. Empty or `status` → show the current setting.
Anything else → run nothing; tell the user the options are `on`, `off`, or `status` (or nothing)
to see the setting.

Telemetry is **on by default**. The first time a session starts on a machine whose
`~/.archflow/config.json` has not yet recorded the notice as shown (no `noticeShownAt` in it; see
`plugin/hooks/telemetry.mjs`), a one-time notice fires — not a question — saying telemetry is on
and how to turn it off; this command is that off switch, and the way to turn it back on later. The
setting lives in `~/.archflow/config.json`, one file shared by every Archflow project on this machine,
so an opt-out here holds everywhere, not just this project.

What is sent, while on: which command ran (`command_run`, just the command name — e.g. `archflow:status`
— never its arguments) and that a session started (`session_start`), each with the Archflow version,
current phase/mode, and a random id generated locally. Never a project name, a file path, file
contents, or anything from `project-context.md`.

Run exactly one of the commands below, then relay the line it prints to the user **verbatim** — do
not reword, summarise or add to it. It already says the setting (for status, since when), and when
turning it off, whether one final `telemetry_opted_out` event recorded the opt-out (nothing is sent
after it).

## Show current setting (no argument)
```bash
node "${CLAUDE_PLUGIN_ROOT}/hooks/telemetry.mjs" --status
```
If it says the config file could not be read, telemetry stays off and nothing is changed until the
user fixes or deletes that file. If turning it on or off says the file could not be written, nothing
was changed and nothing was sent; telemetry is as it was.

## Change it
```bash
node "${CLAUDE_PLUGIN_ROOT}/hooks/telemetry.mjs" --enable    # on
node "${CLAUDE_PLUGIN_ROOT}/hooks/telemetry.mjs" --disable   # off
```
Turning it back on sends `telemetry_opted_in`. Never run either without the user asking.
