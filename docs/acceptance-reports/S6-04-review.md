# Acceptance Review Report
## Release: v2-5-0 | Story: S6-04 | Date: 2026-10-11

### Verdict
**ACCEPTED**

All eight criteria pass, each checked by something that actually ran. Two P3 copy findings are filed as minor (I-9, I-10). Neither blocks the story.

### How this was tested
- **Tooling** (all already in the project, nothing installed): pytest (`tests/`), `node scripts/build-adapters.mjs --check`, `python3 plugin/scripts/validate_archflow.py`, the real installer `node scripts/archflow.mjs install --bundled`, `npm pack --dry-run`, and the chrome-devtools MCP (isolated browser contexts) to drive Studio's forward-mode chat.
- **Commands**:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -x` gave `957 passed in 168.18s`
  - `node scripts/build-adapters.mjs --check` reported all 6 adapters `up to date`, exit 0
  - `python3 plugin/scripts/validate_archflow.py` reported 11 state files valid, exit 0
  - `HOME=<tmp> node scripts/archflow.mjs install --bundled --host cursor,codex --yes --dir <tmp proj>`
  - `HOME=<tmp> node scripts/archflow.mjs install --bundled --host cursor --yes --no-guard --dir <tmp proj2>`
  - `HOME=<tmp> GEMINI_CLI_HOME=<tmp> ... --host gemini,copilot,opencode --dry-run`, `--host generic --dry-run`, and a real `--host gemini` with stdin closed (Gemini was never invoked)
  - The start, status and stop steps from the adapter's own `archflow-studio` command, run verbatim from the project root
- **Environment**: macOS, Node on PATH, temp HOME and temp git projects under the session scratchpad (all deleted afterwards). Ports 48713 and 48714, `STUDIO_AUTO_OPEN=0`. No user port, real HOME or real `~/.gemini` was touched.

### Summary
- **Total acceptance criteria**: 8
- **Passed**: 8 · **Failed**: 0 · **Blocked**: 0

### Criterion results

- **AC 1**: The rebuilt forward-mode bundle (plugin/server/server.mjs, plugin/dist/**, hooks.json) is committed
  - **Result**: PASS
  - **Evidence**: `git status` is clean apart from the two out-of-scope untracked files. `git diff --stat 408b49a..HEAD` covers `plugin/server/server.mjs` (2,508,836 to 2,593,460 bytes), the `plugin/dist` assets (58 files in total) and `plugin/hooks/hooks.json`. The hooks.json change is the SessionStart reorder: telemetry now runs before `studio-session-context.mjs`. The committed server carries the forward host ids (codex, gemini, copilot, cursor, opencode) and the `FORWARD_TO_TERMINAL` policy. It is also the server that ran in AC 3.

- **AC 2**: Every adapter ships /archflow:studio and the server bundle it needs; build-adapters.mjs no longer skips studio
  - **Result**: PASS
  - **Evidence**: Each of the six adapters has a studio command, and each points `BUNDLE` at its own root:
    - codex: `.codex/archflow/server/server.mjs`
    - gemini: `$HOME/.gemini/extensions/archflow/server/server.mjs`
    - copilot: `.github/archflow/...`
    - cursor: `.cursor/archflow/...`
    - opencode: `.opencode/archflow/...`
    - generic: `.agents/archflow/...`

    Each command also names its own host id. The only studio-specific skip left in build-adapters.mjs is the Claude-only `studio-session-context.mjs` hook, which is correct. Per the user's decision, the bundle is carried once in the npm package and placed per host by the installer. That placement is verified in AC 6.

- **AC 3**: /archflow:studio starts, reports status and stops Studio on a non-Claude host, launching the server from the adapter's own copy
  - **Result**: PASS
  - **Evidence**: Two runs, each launched from the installed host copy.
    - **Run 1, codex + cursor installed, launched from `.cursor/archflow/server/server.mjs`.**
      - Start: the probe showed FREE and `bundle=ok`, then the detached start ran. The server process was reparented (PPID 1), so it outlives the launching shell.
      - `/api/project`: `host":"codex","hostSource":"detected","detectedHosts":["codex","cursor"]`. This follows the documented ranking.
      - `/api/chat/session`: `reasonCode":"FORWARD_TO_TERMINAL"`, reason "Copy a message, then paste it into Codex.", `canSend:true`, `sendTarget:"terminal"`.
      - Log: `[host] host=codex source=detected ...` and `[mode] ... reasonCode=FORWARD_TO_TERMINAL`.
      - The UI is served (`/` returns 200 text/html and its JS asset returns 200).
      - In the browser, the chat says "Compose here, run it in Codex". Typing `/archflow:status` and pressing Copy for terminal put `$archflow-status` on the clipboard, which is Codex's spelling.
      - Stop: the pid was killed, and the re-probe showed `pids=[]`, `body=` (FREE). Running stop again is a no-op.
    - **Run 2, cursor-only project.**
      - `/api/chat/session` shows `host":"cursor"`, FORWARD_TO_TERMINAL, "paste it into Cursor".
      - The browser chat turned `/archflow:status` into `/archflow-status` and `/archflow:studio stop` into `/archflow-studio stop`.
      - Stopped cleanly.
    - **Gemini** (not launched): the real Gemini CLI install was exercised by QA with expect. Here, a no-terminal run correctly reported "Not fully installed", exited 1 and wrote nothing to `~/.gemini`.

- **AC 4**: studio.md describes forward mode and per-host behaviour accurately; no 'not built yet' or Claude-only claims remain
  - **Result**: PASS
  - **Evidence**:
    - `plugin/commands/studio.md`, and each adapter's rendering of it, has a "Hosts and chat" table: full / companion on `claude`, **forward** on every other host, **off** by policy. It also covers the chat line (`host <h>, chat <c>`), the detection order and the companion caveat (claude only).
    - The live behaviour in AC 3 matched what the doc says: the detected host, forward on codex and cursor, the "Studio resolved another host" case when codex outranks cursor, a detached launch, and stop by pid.
    - A grep for "not built yet", "Claude Code only" and "Claude-only" over the studio commands, the guide, the README and the site finds nothing about Studio. The remaining hits are the unrelated `CLAUDE.md (skip: Claude Code only)` lines in init and onboard. The test `test_no_studio_command_says_forwarding_is_unbuilt_or_claude_only` passes.

- **AC 5**: help, SKILL.md and reference.md list studio on every host, consistent with what each adapter ships
  - **Result**: PASS
  - **Evidence**: Each of the six adapters' help lists studio in that host's spelling (`$archflow-studio` for codex and generic, `/archflow-studio` for copilot, cursor and opencode, `/archflow:studio` for gemini). Each adapter's SKILL.md and reference.md list studio. `plugin/skills/archflow/reference.md` is identical to `.archflow/reference.md`. `test_help_command.py` passes.

- **AC 6**: npx archflow install copies the bundle for each host; the npm package stays a sensible size
  - **Result**: PASS
  - **Evidence**:
    - Real installs put `server` (2.5M) and `dist` (4.0M) in `.cursor/archflow/` and `.codex/archflow/`. The server is byte-identical to `plugin/server/server.mjs` (`cmp`). Each host gets a `.gitignore` there containing `/server/` and `/dist/`, so the bundle stays out of commits.
    - Dry runs plan the same copy for copilot (`.github/archflow`), opencode (`.opencode/archflow`), generic (`.agents/archflow`) and gemini (the staged extension under `~/.cache/archflow/gemini-extension/<v>/archflow`). None of them wrote anything.
    - `npm pack --dry-run`: 1 `server.mjs` in the package; unpacked 35.95 MB vs 28.91 MB for the published 2.4.0, so the bundle is added once (+7 MB unpacked).
    - Compressed, the bundle is 1,679,360 bytes, which matches CHANGELOG's "about 1.7 MB".
    - Per adapter, the size is dominated by pre-existing design-system PNGs, not by this story.

- **AC 7**: build-adapters.mjs --check passes and tests cover the shipped bundle per host
  - **Result**: PASS
  - **Evidence**: `--check` exits 0 with all six adapters up to date. `tests/test_studio_hosts.py` (542 lines) parametrizes over hosts and covers:
    - each adapter ships the command
    - it launches from the host's own root and names its host
    - no adapter carries a bundle copy, and the package ships it once
    - install places the bundle where the command launches it, and gitignores it
    - Gemini: staged extension, prune, declined upgrade and fresh install, no-terminal case, dry runs
    - the `@latest` remedy

    Full suite: 957 passed.

- **AC 8**: CHANGELOG supersedes the 2.4.0 'Claude Code only' line; the site's host claims match
  - **Result**: PASS
  - **Evidence**:
    - The CHANGELOG entry says, verbatim: "This supersedes 2.4.0's '`/archflow:studio` stays Claude Code only'". It lists each host's spelling, forward mode, the single-bundle placement and the Gemini consent flow.
    - `docs/index.html` (meta, JSON-LD, hero, Studio section, install section) now says Claude Code runs the agent in-panel and the other hosts compose prompts for you to paste. This matches the live behaviour.
    - Gemini is marked "(enterprise/API)" consistently across the site, README, guide and CHANGELOG.
    - The README explains the Antigravity move and says support is planned. The site and guide do not (see I-9).

### Blocking defects (must fix)
None.

### Non-blocking observations (filed as minor issues)
1. **I-9 (P3)**: The Antigravity note appears only in the README. The site (`docs/index.html`), the Studio guide (`docs/guides/studio.md`) and the CHANGELOG mark Gemini CLI "(enterprise/API)" but never say where individual Gemini users went or that Antigravity CLI support is planned. An individual Gemini user reading the site sees they are excluded and has no pointer to what comes next. Suggested fix: add one clause pointing to the README's Hosts note, or saying "Antigravity CLI support is planned", on the site's host line and in the guide.
2. **I-10 (P3)**: `docs/guides/studio.md:158-159` says that if you decline Gemini's trust or confirm prompts, "Studio's bundle is not installed". That understates the result. On a fresh install, declining means the whole Archflow extension is not installed; on an upgrade, the old extension stays, without Studio. The installer itself reports this accurately ("extension not installed ..."). Suggested fix: "Accept both, or the extension is not installed (an upgrade keeps the version you had); re-run the install to try again."

### Other notes (not filed)
- After a no-terminal Gemini run, the installer correctly prints "Not fully installed" and exits 1. It still lists "Next: Restart Gemini CLI / Run /archflow:init" under that. This is mild noise, but those steps do apply once the printed todo command has run.
- The installer banner says "Archflow 2.4.0 (bundled)" because `package.json` is still 2.4.0. The version bump belongs to the release ship, not this story.
- I-8 (Ctrl-C during a Gemini upgrade) remains deferred to S7-12 by the user. It was not re-tested.

### Product view of the non-Claude journey
Install, then `/archflow:studio`, then forward-mode chat, then stop: the journey holds together. The installer puts the bundle exactly where the host's command looks for it. Studio detects the host from the installs it finds. The chat clearly says "compose here, run in <Host>". Copy turns Claude-style commands into that host's spelling. Stop leaves the port free. The docs are honest that Gemini CLI is enterprise/API only. The pointer to Antigravity being planned should go beyond the README (I-9).

### Recommendation
Proceed. The story can be marked done. I-9 and I-10 are copy fixes; whether to fix them now or defer them to the backlog is the user's call.
