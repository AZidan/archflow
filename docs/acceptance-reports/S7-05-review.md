# Acceptance Review Report
## Release: v2-5-0 | Story: S7-05 | Date: 2026-10-04

### Verdict
**ACCEPTED**

Both criteria pass on automated evidence. Under the story's binding verification plan, that evidence is
what acceptance requires. The live on-host checks (Gemini CLI, Cursor) are the user's, after the run, and
do not gate this verdict. One minor finding was filed (I-4). It does not block.

### How this was tested
- **Tooling**: the project's own stack, which was already in the repo: pytest (Python 3.10.10), Node v22.12.0, bash.
  The project is `backend_only` with no e2e runner. The "user" of this story is a host CLI running shell lines
  and hook payloads, so I drove those surfaces directly. Nothing was installed.
- **Commands**:
  - `python3 -m pytest -q tests/` → **718 passed** in 108.79s, exit 0
  - `python3 -m pytest -q tests/test_host_paths.py` → 213 passed
  - `node scripts/build-adapters.mjs --check` → all six adapters up to date, exit 0
  - Hand-run probes, described below
- **Environment**: scratch dir `/tmp/s705pm.*`. The temp HOME is `.../home with space`, which has a space in it. Every run used `env -i`
  with `HOME=<temp>`, `ARCHFLOW_CONFIG_DIR=<temp>`, `ARCHFLOW_TELEMETRY_SINK=<temp file>` and `ARCHFLOW_NO_UPDATE_CHECK=1`.
  The real `~/.gemini`, the real HOME and all global host config were left untouched. No network was used.

### Summary
- **Total acceptance criteria**: 2
- **Passed**: 2 · **Failed**: 0 · **Blocked**: 0

### Criterion results

- **AC 1**: Gemini /archflow:doctor resolves the plugin path (automated test; live check by user)
  - **Result**: PASS
  - **Evidence**: I copied `adapters/gemini` to `<temp HOME with space>/.gemini/extensions/archflow`, the
    layout `gemini extensions install` produces. The fixture project was a git repo holding a copy of this repo's `.archflow/`.
    I extracted every `$HOME` bash block from `adapters/gemini/commands/archflow/doctor.toml` and ran each one
    exactly as written in bash, from the project:
    - `python3 "$HOME/.gemini/extensions/archflow/scripts/validate_archflow.py" .` → "12 state file(s) valid", exit 0
    - `python3 "$HOME/.../upgrade_archflow.py" . --plugin-root "$HOME/.gemini/extensions/archflow"` → full drift
      report, exit 1. Exit 1 means drift was found. The plugin path resolved.
    - the same line with `--apply` (on a copy of the project) → exit 0
    - `sh "$HOME/.../archflow-install-git-guard.sh"` → "Archflow pre-push guard installed", exit 0
    - `/archflow:migrate`'s quoted `migrate.py --dry-run` line → ran, "Already schema v2.x", in a HOME with a space
  - **Negative controls**: the pre-fix form `python3 "~/.gemini/..."` → "can't open file '<cwd>/~/.gemini/...'",
    exit 2. The unquoted `$HOME/...` form → word-split at the space, exit 2. Both show that the fix
    (`$HOME`, quoted) is the reason the lines work.
  - **Automated test**: `tests/test_host_paths.py` (Gemini half) runs the doctor's lines in a throwaway HOME, including a
    spaced HOME. It also checks that every extension path exists and that no command uses tilde or an unquoted path. Passes.

- **AC 2**: Cursor hooks find the project without cwd (automated test; live check by user)
  - **Result**: PASS
  - **Evidence**: the generated `adapters/cursor/.cursor` was copied into a fixture project at a path with a space
    (`cursor proj`, git on `main`). The bridge was run by absolute path from an unrelated process cwd. Payloads
    follow the documented shapes that `tests/test_host_paths.py` cites (cursor.com/docs/agent/hooks: common
    fields plus `workspace_roots`, with `cwd` only on `beforeShellExecution`):

    | event / payload | bridge stdout | expected |
    |---|---|---|
    | sessionStart, roots=[project], no cwd | `additional_context` contains the project's `instructions.md` text and the upgrade notice | project resolved |
    | beforeSubmitPrompt `/archflow:status`, no cwd | `{"continue":true}`; telemetry `command_run` has_project=true, project_type=backend_only, host=cursor | project resolved |
    | beforeShellExecution force-push main, cwd=root | `permission: deny` ("...in cursor proj") | deny |
    | beforeShellExecution force-push main, **cwd=`<project>/packages/api`** | `permission: deny` | deny (this was I-1) |
    | beforeShellExecution `ls`, cwd=subdir | `permission: allow` | allow |
    | beforeShellExecution force-push main, no cwd | `permission: deny` | deny |
    | sessionStart, roots=[unrelated, project] | the project's instructions are loaded | the second root is picked |
    | stop, clean state | `{}`, empty stderr | `{}` |
    | stop, current-phase.yaml broken | stdout `{}`; stderr "state files have drifted from their schemas..." | drift advisory relayed (this was I-2) |

    All runs exit 0.
  - **Negative control**: I ran the pre-story bridge (`6e84419`) on the same fixture. With the subdirectory cwd and a force push, it returned `{}`,
    so the guard was skipped. With multiple roots and the project second, sessionStart did not load the instructions. The
    current bridge denies the push and loads the instructions.
  - **Automated test**: `tests/test_host_paths.py` (Cursor half) covers a single root without cwd,
    multi-root ordering, subdirectory cwd, a non-Archflow root, cwd outside every root, HOME never treated as a
    project, a malformed payload as a no-op, and stop relaying both streams. Passes.

### Code-review issues I-1..I-3
- **I-1 (blocking)**: fixed. A subdirectory cwd now resolves to the project and the guard denies (table row 4; negative control above).
- **I-2 (minor)**: fixed. On stop the bridge relays stderr and stdout together, and the drift advisory reaches stderr (last table row).
- **I-3 (minor)**: fixed. `plugin/commands/migrate.md:30,44` quotes the path, and so do the regenerated migrate
  commands on Gemini, Codex, Copilot, Cursor and OpenCode. The Gemini dry-run line works in a HOME with a space.

### CHANGELOG (Unreleased → Fixed)
Checked against the 2.4.0 tag, the baseline users have. 2.4.0's bridge used `input.cwd || process.cwd()` and relayed only
stdout on stop. The five entries are accurate (Gemini `$HOME`, Gemini `.toml` references, Cursor project
resolution, Cursor stop stderr, quoted migrate path), with one exception. The sentence "A shell in a workspace root that is not
an Archflow project is left alone" does not hold when that root is nested inside an Archflow project. See I-4.

### Blocking defects (must fix)
None.

### Non-blocking observations
1. **I-4 (minor, P2)**: the bridge's ancestor walk (`scripts/build-adapters.mjs:288`) does not stop at the
   workspace root. Reproduction: an Archflow project `cursor proj/` (on main) contains a separate git repo
   `vendor/nested/` (on `feature-x`, no `.archflow/`). Open `vendor/nested` as the only workspace root and send
   `beforeShellExecution` with cwd=`vendor/nested/src` and `git push --force origin main`.
   - Expected, per the CHANGELOG and matching Claude Code, whose guard uses the session cwd without walking up: the
     nested repo never opted in, so `{"permission":"allow"}`.
   - Actual: `{"permission":"deny","user_message":"Blocked: force-push to a protected branch in cursor proj."}`.
     The guard runs with the outer project as its cwd and names the wrong project. Meanwhile sessionStart in the same
     workspace treats it as a plain workspace and loads no instructions.
   - The failure is over-protective, not unsafe. Suggested fix: limit the walk to the workspace root that contains cwd, or
     reword the CHANGELOG sentence and record the behavior as deliberate.
2. Cursor's `hooks.json` invokes the bridge by a relative path (`node .cursor/archflow/hooks/...`). So in real
   Cursor the process cwd is the project root, and the payload-only resolution tested here is defense in depth.
   The live check by the user will confirm this.
3. `upgrade_archflow.py` on the fixture reported 4 framework files that differ from the Gemini extension's copies
   (`phase-2-design.md` and others). The cause is the fixture: this repo's `.archflow/` is the Claude-path mirror, not a
   Gemini-initialized project. It is not a defect.

### Recommendation
Proceed. AC `met` flags are left to the orchestrator. The live on-host checks on Gemini CLI and Cursor remain with the
user. I-4 is open as minor, for the user to fix or defer.
