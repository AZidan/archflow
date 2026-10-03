---
name: archflow-telemetry
description: "Use ONLY when the user asks for $archflow-telemetry or \"archflow telemetry\". Show or change anonymous usage telemetry (on by default; this is how to opt out)"
---

> Arguments are the text after the skill name.


# $archflow-telemetry — Show or change anonymous usage telemetry

Argument (`the text the user wrote after the skill name`): optional `on` or `off`. Empty → show the current setting.

Telemetry is **on by default**. The first time a session starts with no `~/.archflow/config.json` yet
(see `plugin/hooks/telemetry.mjs`), a one-time notice fires — not a question — saying telemetry is on
and how to turn it off; this command is that off switch, and the way to turn it back on later. The
setting lives in `~/.archflow/config.json`, one file shared by every Archflow project on this machine,
so an opt-out here holds everywhere, not just this project.

What is sent, while on: which command ran (`command_run`, just the command name — e.g. `archflow:status`
— never its arguments) and that a session started (`session_start`), each with the Archflow version,
current phase/mode, and a random id generated locally. Never a project name, a file path, file
contents, or anything from `project-context.md`.

## Show current setting (no argument)
```bash
node ".agents/archflow/hooks/telemetry.mjs" --status
```
Report it plainly: "on" or "off", and since when.

## Change it
```bash
node ".agents/archflow/hooks/telemetry.mjs" --enable    # on
node ".agents/archflow/hooks/telemetry.mjs" --disable   # off
```
Confirm the new setting back to the user in one line, including the script's note when turning it
off sent one final `telemetry_opted_out` event (counting opt-outs); nothing is sent after it. Turning it back
on sends `telemetry_opted_in`. Never run either without the user asking.
