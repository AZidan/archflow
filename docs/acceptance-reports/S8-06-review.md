# Acceptance Review Report
## Release: v2-5-0 | Story: S8-06 "/archflow:telemetry and npx archflow telemetry" | Date: 2026-10-03

### Verdict
**ACCEPTED**

Both criteria pass end to end on all 7 hosts and the CLI. Each host's own command lines were run as written against a real install. Each host's real hooks sent events while telemetry was on, sent nothing after opt-out, and sent again after opt-in. One minor wording issue (I-4) is filed. It does not block.

### How this was tested
- **Tooling**: the project's own stack: Python 3 + pytest (already in the repo), plus throwaway Python/bash probes under `/tmp/s806/` that drive the installed host files. No new tool was installed. `sandbox-exec` (macOS built-in) denied network egress.
- **Commands**:
  - `python3 -m pytest -q tests/` → `505 passed in 94.28s` (run with `CLAUDECODE` / `CLAUDE_CODE_ENTRYPOINT` unset)
  - `node scripts/build-adapters.mjs --check` → all 6 adapters "up to date"; every adapter `lib/telemetry.mjs` is byte-identical to `plugin/lib/telemetry.mjs`
  - `python3 /tmp/s806/probe.py` (per-host matrix), `probe2.py` (CLI, unwritable config, env-disabled, unreadable config), `probe3.py` (re-check of two harness races)
- **Environment**: every child ran with `env -i`, a temp `HOME=/tmp/s806/h`, `ARCHFLOW_CONFIG_DIR=/tmp/s806/h/.archflow`, and `sandbox-exec` with outbound ip/tcp/udp denied. The sandbox was proven first: curl and node fetch to PostHog both failed with EPERM. `NODE_OPTIONS=--import=fetchpatch.mjs` replaced `fetch` in every node process, including the detached `--send` child. It logged the real wire body and returned a synthetic 200, so these results come from the real send path and not just the `ARCHFLOW_TELEMETRY_SINK` seam. No event reached PostHog.
- **Install, as a user would**: `node scripts/archflow.mjs install --bundled --no-guard --yes --host codex,copilot,cursor,gemini,opencode --dir /tmp/s806/p`, then `--host generic --dir /tmp/s806/p2` (the installer refuses generic alongside codex because they share `.agents/`). PATH had no `gemini`, so the Gemini extension was copied to `$HOME/.gemini/extensions/archflow`, which here is the temp HOME. The Claude plugin was copied to `/tmp/s806/claudeplugin` and run via `CLAUDE_PLUGIN_ROOT`.

**How each host's hooks were fired** (the real wiring, with the commands taken from the installed files):
| Host | Session start | Command / prompt |
|---|---|---|
| claude | `hooks.json` `node "${CLAUDE_PLUGIN_ROOT}/hooks/telemetry.mjs"` (CLAUDECODE=1) | `--command-run` with `command_name: archflow:status` |
| codex | `.codex/hooks.json` SessionStart command verbatim | UserPromptSubmit `--prompt` with `$archflow-status` |
| copilot | `.github/hooks/archflow.json` `bash` + its `env` block | UserPromptSubmit `--prompt` with `/archflow-status` |
| cursor | `cursor-bridge.mjs sessionStart` with a `workspace_roots`-only payload | `beforeSubmitPrompt` with `/archflow-status` |
| gemini | extension `hooks.json` with `${extensionPath}` / `${workspacePath}` substituted | BeforeAgent `--prompt` with `/archflow:status` |
| opencode | the installed `.opencode/plugins/archflow.ts` imported under `node --experimental-strip-types`, `event({type:"session.created"})` | `event({type:"command.executed", name:"archflow-status"})` |
| generic | the AGENTS.md line `ARCHFLOW_HOST=generic node .agents/archflow/hooks/telemetry.mjs </dev/null` | (generic has no prompt hook) |

**Command lines run per host**, extracted with a regex from each host's installed command/skill file and run in `bash -c` from the project root:
`.../telemetry.mjs --status`, `--disable --host <h>`, `--enable --host <h>` (Claude: no `--host`; Gemini: `$HOME/.gemini/extensions/archflow/hooks/telemetry.mjs`).

### Summary
- **Total acceptance criteria**: 2
- **Passed**: 2 · **Failed**: 0 · **Blocked**: 0

### Criterion results
- **AC 1**: /archflow:telemetry [on|off] works on every host
  - **Result**: PASS
  - **Evidence** (`probe.py`, 0 FAILS). For all 7 hosts, the sequence was: status → `on (since 2026-01-01…)`; off → `Anonymous usage telemetry is now OFF. One final event recorded the opt-out; nothing else will be sent.`; status → `off (since 2026-10-03T20:…Z)`; on → `Anonymous usage telemetry is now ON.` The opt events on the wire were attributed correctly: `('telemetry_opted_out', <host>, 'command')` and `('telemetry_opted_in', <host>, 'command')` for claude, codex, copilot, cursor, gemini, opencode and generic. A repeated `off` sends nothing.
  - CLI `node scripts/archflow.mjs telemetry` (no arg, `status`, `off`, `on`, `bogus`): status line with hint; `off` → one `('telemetry_opted_out','cli','cli')`; `on` → one `('telemetry_opted_in','cli','cli')`; `bogus` → exit 2, `Unknown telemetry option: bogus. Try "on", "off" or "status".`

- **AC 2**: After opt-out no further events are sent
  - **Result**: PASS
  - **Evidence**: before opt-out, each host's hooks sent `session_start` + `command_run` (generic: `session_start`). This is the positive control in the same harness. After each host's own `off`, the hooks of all 7 hosts were fired, and the wire log was `[]` all 7 times. After `on`, the same hooks sent again. After the CLI's `off`, firing all 7 hosts' hooks also gave `[]` (probe3, waited 2 s for the detached child to settle).
  - **Negative controls** (mutating only the temp plugin copy, restored and diffed afterwards):
    - Mutant A, `isEnabled` ignoring `telemetryEnabled`: the Claude hooks after `off` sent `session_start, command_run`. The harness catches a broken opt-out.
    - Mutant B, emit regardless of a failed save: unwritable `off` sent `telemetry_opted_out`. The harness catches the I-2 regression.

**Failure path: unwritable config dir** (`chmod 0500` on `$ARCHFLOW_CONFIG_DIR`, starting from both on and off):
- CLI: exit 1, stderr `Nothing was changed: could not write /tmp/s806/h/.archflow/config.json.`; no event.
- claude, codex, gemini command lines: exit 0, same line; no event.
- The config file was byte-identical afterwards and no `.tmp` file was left. Status still reported the old state. After a failed `off` the hooks still sent events, which is correct because telemetry really is still on, so the "nothing was changed" message is truthful.

**Env-disabled path** (`DO_NOT_TRACK=1`, `CI=1`, `ARCHFLOW_TELEMETRY_DISABLED=1` each, CLI and the Cursor command):
- status → `off (DO_NOT_TRACK is set in the environment; nothing is sent while it is)`. The CLI prints no "turn it on" hint.
- `on` → `Your choice (on) is saved, but anonymous usage telemetry stays OFF while DO_NOT_TRACK is set; nothing is sent.`
- `off` → `now OFF.` with no "final event" claim. Zero events on every line, and the session hook also sent nothing.

**Unreadable config** (`{corrupt`): CLI status/off and the Copilot `--disable` / `--enable` lines all say `Nothing was changed. … could not be read …`, send nothing, and leave the file as is.

### Prior issues
- **I-1** (env-disabled `on` claimed "now ON"; CLI hinted `on`): fixed. See the env-disabled path above.
- **I-2** (failed opt-out write still claimed OFF and sent): fixed. The save happens before the send, the failure message is truthful, and nothing is sent (mutant B shows the check binds).
- **I-3** (CHANGELOG / bad-arg reply omitted `status`): fixed. `CHANGELOG.md:27` reads `[on|off|status]`, every command file's bad-argument rule lists `on`, `off`, or `status`, and the CLI's unknown-option reply names all three.

### Blocking defects (must fix)
None.

### Non-blocking observations
1. **I-4 (minor)**: the CLI status hint says `` `archflow telemetry off` to turn it off `` (`scripts/archflow.mjs:496`). A user who ran `npx archflow telemetry`, which is the documented form at `scripts/archflow.mjs:15` and `:237`, gets `command not found` if they type the hint as printed. The hint should read `npx archflow telemetry off|on`, to match the install notice.
2. Two harness races showed up in the first `probe2.py` pass: the detached sender of the previous step wrote to the wire log after it had been truncated. `probe3.py` re-checked both with settle waits and both came out clean. They are recorded here so they are not mistaken for defects.

### Recommendation
Proceed. Mark S8-06 done once the orchestrator records it. I-4 is minor and the user can fix it or defer it.
