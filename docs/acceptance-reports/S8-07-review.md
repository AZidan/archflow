# Acceptance Review Report
## Release: v2-5-0 | Story: S8-07 | Date: 2026-10-03

### Verdict
**ACCEPTED**

All three acceptance criteria are met. Every mechanically checkable claim in the ADR and SECURITY.md
was driven through the shipped code with the network stubbed. One new minor finding (I-7) is a
public doc outside this story's three artifacts, so it does not block.

### How this was tested
- **Tooling**: this is a documentation story. Acceptance means reading each artifact as a user would
  and checking every claim it makes against the running code. The project's own suite is
  `python3 -m pytest` (already in the repo). The behavioural claims were checked with a throwaway
  Node 22.12.0 harness in `/tmp/s807/`, outside the repo, and nothing was added to the project.
- **Network stub**: `/tmp/s807/stub.mjs` is loaded with `NODE_OPTIONS=--import`. It replaces
  `child_process.spawn` (then `syncBuiltinESMExports()`) so any `telemetry.mjs --send <payload>`
  child is recorded to a log file and never started, and it replaces `globalThis.fetch` with a
  rejecting stub. **No event reached PostHog.** Every run used a temporary `HOME` and
  `ARCHFLOW_CONFIG_DIR`, and the harness unset `CI`, `DO_NOT_TRACK`, `ARCHFLOW_TELEMETRY_DISABLED`,
  `STUDIO_*`, `CLAUDE_CODE_ENTRYPOINT` and `ARCHFLOW_HOST` unless a case set them.
- **Negative control**: a baseline `session_start` with no disabling variable recorded exactly one
  payload, so the stub does catch sends. Every "0 events" result below is meaningful.
- **Commands**:
  - `python3 -m pytest -q tests/` gave **288 passed in 17.75s**
  - `node plugin/hooks/telemetry.mjs [--command-run | --prompt | --status | --enable | --disable]`
    with JSON on stdin
  - `node scripts/archflow.mjs telemetry [on|off|maybe]`
  - `node scripts/archflow.mjs install --host codex --dir <tmp> --bundled --no-guard --yes [--dry-run]`
- **Environment**: macOS, branch `telemetry/policy-adr` at `fcccfb1`, a scratch project with
  `phase: 3`, `mode: quick` and `project_type: fullstack`.

### Summary
- **Total acceptance criteria**: 3
- **Passed**: 3 · **Failed**: 0 · **Blocked**: 0

### Criterion results

- **AC 1**: A new ADR records opt-out, framework-wide telemetry (scope, event allow-list,
  DO_NOT_TRACK/CI disable, notice, opt-out command) and marks ADR 003 superseded.
  - **Result**: PASS
  - **Evidence**:
    - `docs/internal/decisions/005-framework-telemetry-opt-out.md` exists. It is untracked in
      archflow-internal (`?? decisions/005-...`), as the story intends. It has Scope (l.32-43),
      the allow-list (l.45-71), Never sent (l.73-77), Turning it off (l.79-91), The notice
      (l.93-101) and Delivery, and it marks itself as superseding ADR 003 (l.7).
    - ADR 003 l.3 reads `Status: Superseded by ADR 005 (2026-10-03)`. `git diff` shows that the
      status line is the only change.
    - **The allow-list matches the payloads exactly.** The recorded key sets are:
      - every event: `host, entrypoint, via_studio, studio_capture, distinct_id, $process_person_profile`
      - `session_start`: plus `archflow_version, has_project, project_type, phase, mode, session_source`
      - `command_run`: plus the same fields with `command, detected_by` (`command_hook` or `prompt_prefix`)
      - `cli_install`: plus `archflow_version, installed_hosts:["codex"], source:"bundled with this package"`
      - `telemetry_opted_out`/`_in`: plus `via, archflow_version, days_since_notice`

      No event carried any property that is not listed.
    - **Scope**: `plugin/hooks/hooks.json` has a SessionStart hook and `UserPromptExpansion` with
      matcher `^archflow:.*`. OpenCode handles `command.executed`. Codex, Copilot, Cursor and
      Gemini wire `--prompt`. Generic `AGENTS.archflow.md` tells the agent to run the script.
      `--dry-run` sent 0 events and a real install sent 1 `cli_install`. `archflow:telemetry`
      sent 0 events through both `--command-run` and `--prompt`.
    - **Disable**: `DO_NOT_TRACK`, `CI` and `ARCHFLOW_TELEMETRY_DISABLED`, each set to `1`,
      `true`, `yes` and `anything`, sent 0 events (12 of 12 cases). Each set to `0`, `false`,
      `no`, `off`, `OFF`, an empty value or ` 0 ` sent 1 event (21 of 21 cases). An install with
      `CI=true` sent 0 events and wrote no config file.
    - **Notice**: a fresh session printed the notice and recorded `noticeShownAt` and
      `distinctId`. The second session printed nothing. A fresh machine with `DO_NOT_TRACK=1`
      printed nothing and created no config file. A real install printed it with
      `npx archflow telemetry off`. A dry run did not print it.
    - **Opt-out command**: `--disable` sent exactly 1 `telemetry_opted_out`. A second `--disable`
      sent 0. After that, session, command and prompt hooks all sent 0. `--enable` sent 1
      `telemetry_opted_in`, and a repeat sent 0. `--disable` and `--enable` under `DO_NOT_TRACK=1`
      sent 0 but still persisted the choice. The CLI `telemetry off`/`on` behaved the same with
      `host:"cli", via:"cli"`.
    - The fix for I-6 is present: ADR l.99-100 names `setConsent()` as a second writer of
      `noticeShownAt`, which matches `plugin/lib/telemetry.mjs:108`.

- **AC 2**: SECURITY.md states that anonymous telemetry is on by default, what is sent, what is
  never sent, and how to turn it off.
  - **Result**: PASS
  - **Evidence**:
    - `SECURITY.md` Telemetry section: "**on by default** (opt-out)" (l.3). It lists every
      common property, including `entrypoint`, `via_studio` and `studio_capture`. It gives the
      per-event additions, with `cli_install` described separately from session and command
      events. It lists what is never sent. It covers the four off switches and the falsy-value
      rule, which matches the 33 env-var cases above. It covers the final `telemetry_opted_out`
      and the env vars sending nothing.
    - **A probe for "never sends arguments or prompts"**: `command_input:"SECRET-ARG"` and the
      prompt `/archflow-status my secret project` produced payloads with neither string. A prompt
      with the command mid-sentence (`please run /archflow-status`) sent nothing.
    - **Opening paragraph**: "never sends project content, names or paths", plus telemetry and
      two GitHub requests. A grep of `plugin/hooks`, `plugin/lib` and `scripts/archflow.mjs` for
      `fetch(` finds only PostHog, `check-upgrade.mjs`, which is gated by a one-day cache
      (`DAY`, l.103), and the installer's release lookup and download. That matches.
    - Fixes I-1 through I-5 are present. The property list is complete. `cli_install` is no
      longer implied to carry project fields. GitHub requests are disclosed. The "only" claim and
      "no project data anywhere" are gone. Falsy values are documented and behave as documented.

- **AC 3**: CHANGELOG [Unreleased] describes the same default and opt-out.
  - **Result**: PASS
  - **Evidence**: `CHANGELOG.md` [Unreleased] → Added says "on by default (opt-out), on every
    host". It covers the events, what is never sent (pointing to SECURITY.md for the full list),
    the one-time notice, `/archflow:telemetry [on|off]` and `npx archflow telemetry [on|off]`, the
    final opt-out event, `telemetry_opted_in`, the three env vars sending nothing, and
    `~/.archflow/config.json`. All of it agrees with SECURITY.md and with the observed behaviour.

### Blocking defects (must fix)
None.

### Non-blocking observations
1. **I-7 (minor, filed)**: `docs/compare/archflow-vs-gstack.md:232` gives Archflow's telemetry as
   **"None"**. After this release that public comparison page contradicts the decision this story
   records. The fix is to change the cell to something like "Anonymous, on by default (opt-out);
   `DO_NOT_TRACK`/CI honoured".
2. **Prompt hook first on a fresh machine (code, S8-05 territory; not filed here)**: if a Codex,
   Copilot, Cursor or Gemini prompt hook fires before any session-start hook has run, `command_run`
   is sent with `distinct_id: "anonymous"` and no notice is printed. This was observed with a fresh
   config dir. The ADR's "random UUID, minted once per machine" and "the first surface to run
   prints a notice" hold only because every one of those hosts also wires a session-start hook
   that normally runs first. Worth a guard in S8-05: mint the id in `capture()`, or skip the send
   until the notice has been shown.
3. **Status timestamp (S8-06 territory)**: after an opt-out, `--status` prints
   `off (since <noticeShownAt>)`. That is the notice time, not the time telemetry was turned off,
   so "since when" can mislead.
4. The CHANGELOG's per-event property summary is abbreviated ("host, entrypoint, Studio, …").
   That is acceptable because it points to SECURITY.md for the full list.

### Recommendation
Proceed. S8-07 can be marked done. I-7 is a one-line doc fix that should land before v2-5-0 ships
alongside release criterion 2, or the user can defer it. Reminder for the user: ADR 005 and the
ADR 003 status change are uncommitted in the archflow-internal repo by design, and they need
committing there.
