# Acceptance Review Report
## Release: v2-5-0 | Story: S8-05 "Framework-wide anonymous telemetry" | Date: 2026-10-03

### Verdict
**ACCEPTED** (with three minor, non-blocking issues: I-7, I-8, I-9)

All four acceptance criteria pass when you run each host's real hook wiring. No event carried a
project name, path, file contents, prompt or argument. DO_NOT_TRACK and CI suppressed every event
and the notice on all eight surfaces. Telemetry is on by default everywhere, and the notice
appeared exactly once, in the format each host reads. Prior issues I-1..I-6 are fixed. The three
new findings concern the notice's wording and doc accuracy, not the ACs themselves.

### How this was tested
- **Tooling**: the project's own pytest suite (already in the repo) plus a throwaway Node probe
  harness (`/tmp/s805/probe.mjs`, `/tmp/s805/probe2.sh`). The harness runs the *real* generated
  hook wiring. Nothing was installed.
- **Commands**:
  - `python3 -m pytest -q tests/` → `432 passed in 71.19s`; second run `432 passed in 100.19s`.
    I also ran `test_cursor_bridge_sends_by_default` on its own three more times: passed every
    time. The reported flake did not reproduce.
  - `node scripts/build-adapters.mjs --check` → all 6 adapters up to date.
  - `node /tmp/s805/probe.mjs {sink|wire|dnt|ci|dnt-wire|ci-wire}` and `/tmp/s805/probe2.sh`.
- **Environment / isolation**:
  - Every hook process ran under `sandbox-exec` with outbound IP/TCP/UDP denied. I confirmed
    the sandbox works first: curl and Node `fetch` to us.i.posthog.com both failed (EPERM).
  - Each run had a clean `env -i`-style environment: a fresh temp `HOME`, a temp
    `ARCHFLOW_CONFIG_DIR`, and a PATH with no `claude`, `gemini` or `copilot`.
  - Two capture seams:
    - *sink* mode: `ARCHFLOW_TELEMETRY_SINK`.
    - *wire* mode: no sink. The real detached `--send` child ran with
      `NODE_OPTIONS=--import=fetchpatch.mjs`, which records the exact POST body to
      `https://us.i.posthog.com/capture/` and returns a synthetic 200.
  - Nothing reached PostHog. The real `~/.archflow/config.json` was untouched (mtime is still
    2026-09-19).
- **Surfaces driven, using each host's shipped wiring command**:
  - **Claude Code**: `plugin/hooks/hooks.json`, SessionStart and UserPromptExpansion, run via
    `sh -c` with `CLAUDE_PLUGIN_ROOT`.
  - **Codex**: `.codex/hooks.json`.
  - **Copilot**: `.github/hooks/archflow.json`, with its `env` block and `cwd`.
  - **Cursor**: `.cursor/hooks.json` → `cursor-bridge.mjs` (`sessionStart` and
    `beforeSubmitPrompt`, payload with `workspace_roots` and no `cwd`).
  - **Gemini**: the extension's `hooks/hooks.json` with `${extensionPath}`/`${workspacePath}`
    substituted (SessionStart and BeforeAgent, including the `<!-- archflow-command: -->`
    expansion marker).
  - **OpenCode**: the generated `.opencode/plugins/archflow.ts` loaded under
    `node --experimental-strip-types`, driving `session.created`, `command.executed` and
    `experimental.chat.system.transform`.
  - **Generic**: the exact AGENTS.md command,
    `ARCHFLOW_HOST=generic node .agents/archflow/hooks/telemetry.mjs </dev/null`.
  - **CLI**: `node scripts/archflow.mjs --host … --bundled --dir <tmp> --yes --no-guard`.
    All adapters were installed into temp projects this way; Gemini went into the temp
    `HOME/.gemini/extensions`.
- **Fixtures**: every project path contains `ZEBRASECRET_DIR`. `.archflow/` holds
  `ZEBRASECRET_*` in the project name, release, phase name, context file and instructions. Prompts
  and arguments carry `ZEBRASECRET_ARG` and `/Users/someone/ZEBRASECRET_PATH/file.txt`. A
  *hostile* variant puts secret strings directly into `phase:`, `mode:` and `project_type:`.

### Summary
- **Total acceptance criteria**: 4
- **Passed**: 4 · **Failed**: 0 · **Blocked**: 0

### Criterion results

- **AC 1**: No event carries project names, paths, file contents, prompts or arguments
  - **Result**: PASS
  - **Evidence**:
    - The leak scan covered all 43 captured events in sink mode and 43 in wire mode, across 8
      surfaces × normal/hostile fixtures. It looked for `ZEBRA`, `/Users`, `/private`, `/var/`,
      `/tmp`, `.archflow`, `instructions`, `please`, `file.txt` and `s805`. Result: 0 hits.
    - No event had a property outside `EVENT_PROPERTIES`, and no top-level key other than
      api_key, event, properties and timestamp.
    - Hostile YAML values come out as `project_type/phase/mode: null`.
    - Hostile env values also leak nothing. `CLAUDE_CODE_ENTRYPOINT=/Users/ZEBRA/path`,
      `ARCHFLOW_HOST=ZEBRAHOST`, `STUDIO_PROJECT_PATH=/Users/ZEBRA/proj` and a source of
      `/Users/ZEBRA/secret` produced `entrypoint:"other"`, `host:"other"`, `via_studio:true` and
      `session_source:"other"`. ZEBRA count in the payload: 0.
    - The Copilot SessionStart `initialPrompt` (which held the secret) was not sent.
    - These are dropped and send no event: `/archflow-telemetry off`, `/archflow-statusZEBRA`,
      `please /archflow-status`, `archflow:mything` and `archflow:status extra`.
    - `/archflow-status ZEBRA /Users/x` sends only `"command":"archflow:status"`.
  - Sample wire payload (Codex):
    `{"distinct_id":"<uuid>","archflow_version":"2.4.0","host":"codex","entrypoint":null,"via_studio":false,"studio_capture":false,"has_project":true,"project_type":"backend_only","phase":"3","mode":"full","command":"archflow:status","detected_by":"prompt_prefix","$process_person_profile":false}`

- **AC 2**: DO_NOT_TRACK and CI disable telemetry and send nothing
  - **Result**: PASS
  - **Evidence**:
    - With `DO_NOT_TRACK=1` or `CI=true`, I re-ran every surface above in both sink and wire mode.
      PostHog events: 0 on all 8 surfaces. Notice printed: 0 times. No `--send` child posted
      anything.
    - Each value was then checked against the claude hook:

      | Value | Events |
      |---|---|
      | `DO_NOT_TRACK=1` / `true` / `yes` | 0 |
      | `CI=1` / `true` | 0 |
      | `ARCHFLOW_TELEMETRY_DISABLED=1` | 0 |
      | `DO_NOT_TRACK=0` / `false` / empty | 1 |
      | `CI=false` / `off` | 1 |

      Telemetry stays on for the last two rows, which matches what SECURITY.md documents.
    - With the variables set, no config file is written.
    - The only network calls in wire mode with DNT or CI set were check-upgrade's GET to
      `github.com/AZidan/archflow/releases/latest`, from the Cursor bridge and the OpenCode
      plugin. That is the upgrade check, which SECURITY.md discloses separately. It is not
      telemetry.

- **AC 3**: Telemetry is on by default (opt-out) on every host, per S8-07
  - **Result**: PASS
  - **Evidence**: with a fresh HOME, no config and no env vars, every surface sent events:
    - claude: 2 × session_start + 2 × command_run (`detected_by: command_hook`)
    - codex, copilot, cursor: 2 + 2 each (`prompt_prefix`)
    - gemini: 2 + 4 (prompt plus expansion marker)
    - opencode: 2 + 2 (`command_hook`)
    - generic: 2 × session_start
    - CLI: 1 × cli_install (`installed_hosts:["cursor"]`, `source:"bundled with this package"`)

    Each host reports its own `host` value. `npx archflow install --dry-run` sends nothing and
    writes no config.

- **AC 4**: A one-time notice announces telemetry
  - **Result**: PASS (see I-7 and I-9)
  - **Evidence**:
    - Each surface printed the notice on its first session start, in that host's format:
      - claude, codex, generic: plain text
      - Copilot: `{"additionalContext":…}`
      - Gemini: `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":…}}`
      - Cursor: inside the bridge's `{"additional_context":…}`
      - OpenCode: pushed into `system[]` on the next transform
      - CLI: in the terminal
    - On a second session it was absent everywhere, and `noticeShownAt` was recorded.
    - On prompt-hook hosts, a command typed before any session start sends one `command_run`
      with no notice. The next session start then prints it. This is exactly what SECURITY.md
      documents (old I-2).

### Prior issues re-verified
- **I-1** (Copilot drops plain text): the Copilot adapter emits JSON `additionalContext`, and
  `noticeShownAt` is set only after it is written. Fixed.
- **I-2** (doc claimed the notice came first): SECURITY.md now documents that one `command_run`
  can precede the notice. Observed behaviour matches. Fixed.
- **I-3** (Copilot loading the Claude plugin directly): with neither `CLAUDECODE` nor
  `CLAUDE_CODE_ENTRYPOINT` set, stdout is empty and no `noticeShownAt` is written. A later real
  Claude Code session (`CLAUDECODE=1`) still prints the notice. Fixed as designed, but see I-9.
- **I-4** (unreadable config): I tested four configs: `{"telemetryEnabled": false,}`, `null`,
  `[]` and `1`. In every case:
  - the hook sends 0 events and exits 0
  - the file's checksum is unchanged
  - `--status` prints `off (… could not be read …)` and exits 0
  - `--enable` prints "Nothing was changed" and exits 0
  - the CLI install exits 0

  Fixed.
- **I-5** (non-UUID id): `"distinctId":"bogus-id"` is re-minted to a UUID, and the event carries
  the new UUID. Fixed.
- **I-6** (docstring): `tests/test_telemetry.py` no longer mentions a `no_network` fixture. It now
  names `test_capture_never_spawns_the_sender_when_the_sink_is_set`, and that test exists. Fixed.

### SECURITY.md "## Telemetry" vs behaviour
Most of it matches what I observed:
- the event list and the per-event property list
- the env-variable semantics
- the unreadable-config behaviour
- the generic package reporting a session start only when its script is run
- the prompt being read only locally

Two statements are inaccurate: "Every event carries … the Archflow version" (false on generic,
see I-8), and the notice paragraph (silent on the Copilot-loads-Claude-plugin path, see I-9).

### Blocking defects (must fix)
None.

### Non-blocking observations (recorded as issues, status open)
1. **I-7 (minor, P2): the notice names the wrong opt-out command on 5 of 7 hosts.**
   - `plugin/hooks/telemetry.mjs:31`: `OPT_OUT_LINE` is always
     "…/archflow:telemetry off turns it off."
   - The shipped command is `/archflow-telemetry` on Copilot, Cursor and OpenCode, and
     `$archflow-telemetry` on Codex and generic. It is correct only on Claude Code and Gemini.
   - Repro: the Codex SessionStart hook on a fresh HOME prints
     "Tell the user this once, and that /archflow:telemetry off turns it off."
   - Expected: the opt-out command named in the host's own syntax, as SECURITY.md promises the
     notice says "how to turn it off".
   - Suggested fix: choose the line by `noticeHost()`.
2. **I-8 (minor, P3): generic `session_start` always has `archflow_version: null`.**
   - The AGENTS.md command (`scripts/build-adapters.mjs:781`) does not set `CLAUDE_PLUGIN_ROOT`,
     so `pluginVersion()` looks in `<project>/plugin`.
   - `.agents/archflow/.claude-plugin/plugin.json` exists, but it is never read.
   - Contradicts SECURITY.md: "Every event carries … the Archflow version".
   - Suggested fix: add `CLAUDE_PLUGIN_ROOT=.agents/archflow` to the generated command, or fall
     back to the script's own `../.claude-plugin/plugin.json`.
3. **I-9 (minor, P2): telemetry is sent without any notice on one path.**
   - When Copilot loads the Claude plugin directly (no Claude Code markers), every session sends
     `session_start` (`host:"claude"`, `entrypoint:null`). The notice is never printed, so the
     user is never told.
   - SECURITY.md's notice paragraph does not mention this path.
   - The I-3 fix correctly stopped marking the notice as shown, but events still go out with no
     notice.
   - Suggested options, for the user to choose:
     - (a) on an unknown host, send nothing until the notice has been shown
     - (b) emit one JSON object that both hosts read: Claude Code's `hookSpecificOutput`
       *and* Copilot's top-level `additionalContext`
     - (c) at minimum, document the gap in SECURITY.md.

   I rated this minor because it is not a supported install path (the Copilot adapter is), but
   the user should decide.

### Recommendation
Proceed. S8-05 meets its acceptance criteria. Fix I-7 and I-8 when convenient, since both are
small. I-9 is a policy call for the user: either suppress events until the notice has been
shown, or document the gap.
