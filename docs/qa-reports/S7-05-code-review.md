VERDICT: FAIL

# S7-05 code review: Gemini $HOME paths and Cursor workspace-root fixes

Reviewer: code-reviewer (autopilot story_review pass), 2026-10-03
Scope: `git diff v2.5.0-autopilot..HEAD -- scripts/build-adapters.mjs tests/test_host_paths.py CHANGELOG.md`,
the regenerated `adapters/cursor/.cursor/archflow/hooks/cursor-bridge.mjs`, and the regenerated Gemini
`.toml`/`.md` files.

## Design System Compliance

Not applicable. The change is build tooling, a hook bridge and tests. It has no UI.

## Verification run

- `python3 -m pytest -q tests/`: **634 passed** in 98s.
- `node scripts/build-adapters.mjs --check`: all six adapters up to date (exit 0).
- Manual bridge probes, with HOME, telemetry sink and process cwd all in `/tmp/s705cr`:
  - root with a space and a trailing slash (`"/tmp/s705cr/proj dir/"`): resolves, instructions loaded.
  - `["/tmp/.../else", "/tmp/.../proj dir"]`: picks the second root. This is the new behavior and it is correct.
  - `file://` URI root, `"notarray"`, `[{"path": ...}]`: each returns `{}` with exit 0 and does not throw.
  - `beforeShellExecution` with `cwd` set to a **subdirectory** of the project: returns `{}`, and the git guard is
    **not run**. See I-1.

## Code Review Summary

**Overall assessment**: The Gemini half is correct and well tested. The Cursor root-selection logic
handles every Cursor payload that has no `cwd`. The defect is that Cursor's documented
`beforeShellExecution` payload does carry `cwd`, and that value is the shell's working directory, not
the project root. The bridge still lets the payload's `cwd` win over everything else, so the safety
guard is skipped whenever that directory is not the project root. The CHANGELOG line "Cursor does not
send cwd" and the test fixture that models every event without `cwd` encode the same wrong assumption.

## Critical Issues

### I-1 (blocking): Git guard bypassed when Cursor's shell `cwd` is a project subdirectory
`scripts/build-adapters.mjs:277` (generated `cursor-bridge.mjs:17`)

```js
const cwd = input.cwd || roots.find((r) => existsSync(join(r, ".archflow"))) || roots[0] || process.cwd();
```

The Cursor hooks documentation (cursor.com/docs/agent/hooks) lists
`"cwd": "<current working directory>"` in the `beforeShellExecution` input. That value is where the
shell command runs. In a monorepo the agent often works from `packages/api` or a similar subdirectory.
`input.cwd` wins, `existsSync(join(cwd, ".archflow"))` is false, `isArchflow` becomes false, and the bridge
returns `{}` before it calls `guard-git.mjs`.

Reproduction (same project, same command `git push --force origin main`, branch `main`):

| payload | bridge output |
|---|---|
| `workspace_roots` only | `{"permission":"deny", ...}` |
| `cwd` = project root | `{"permission":"deny", ...}` |
| `cwd` = `<project>/sub` | `{}` (guard skipped) |

This is the root-resolution path this story rewrote, and the project's own claim about the payload is
wrong. Related problems:
- CHANGELOG: "The Cursor hook bridge used `cwd`, which Cursor does not send." That is true for
  sessionStart, beforeSubmitPrompt and stop. It is false for beforeShellExecution.
- `tests/test_host_paths.py`: `EVENT_FIELDS["beforeShellExecution"]` and
  `test_cursor_payloads_carry_no_cwd` describe a payload without `cwd`, which does not match the
  documentation. No test covers a `cwd` below the root.

Expected: resolve the project as the nearest ancestor of `input.cwd` that contains `.archflow/`, or as
the workspace root that contains `input.cwd`, and only then fall back to the root scan. Pass the shell
`cwd` to guard-git as the command's directory if guard-git needs it. Add tests where `cwd` is a
subdirectory and where `cwd` is outside every root. Fix the CHANGELOG wording.

## High Priority Issues

None.

## Medium Priority Issues

### I-2 (minor): Stop relay drops stdout when stderr is non-empty
`scripts/build-adapters.mjs:314`. `const msg = (r.stderr || r.stdout || "").trim();` relays only one of
the two streams. If check-state ever writes to both, or if Node prints a warning such as
`ExperimentalWarning` or a deprecation notice to stderr, the stdout advisory is lost and the noise is
shown in its place. Relay both, for example `[r.stderr, r.stdout].map(s => s?.trim()).filter(Boolean).join("\n")`.

## Low Priority Issues

### I-3 (minor): Unquoted `$HOME` path in Gemini migrate command
`adapters/gemini/commands/archflow/migrate.toml:30,44` (source `plugin/commands/migrate.md:30,44`):
`python3 $HOME/.gemini/extensions/archflow/scripts/migrate.py ...`. With a HOME that contains a space,
the shell splits the path into separate words. Every other shell use (doctor's four lines) is quoted.
The fix is to quote the path in the source (`"${CLAUDE_PLUGIN_ROOT}/scripts/migrate.py"`). That also
fixes Claude Code for a plugin root that contains spaces. The shell-safety tests check only for quoted
tilde paths. They could also flag an unquoted `$HOME/` in shell blocks.

### Notes (no issue recorded)
- `file://` URIs in `workspace_roots` make the bridge do nothing quietly. The documentation shows plain
  absolute paths, so this is acceptable. Windows paths and trailing slashes are handled correctly by
  `path.join`.
- Gemini's `read_file` tool does not expand `$HOME`, so the new "read `$HOME/.../design.toml`"
  references rely on the model resolving the variable itself. This approach predates S7-05 (the old
  `commands/<n>.md` references used it too). Not counted against this story.

## Gemini reference rewrite rule

`[/\$\{CLAUDE_PLUGIN_ROOT\}\/commands\/([a-z-]+|<name>)\.md/g, ".../commands/archflow/$1.toml"]` is placed
before the generic `${CLAUDE_PLUGIN_ROOT}` rule, so the order is correct. It is anchored on the
`${CLAUDE_PLUGIN_ROOT}/commands/` prefix and the `.md` suffix, so it cannot over-match. All 12 source
occurrences (design ×4, groom ×4, onboard, setup-mcp, status, `<name>`) map to `.toml` files that exist.
One theoretical gap: a future command name containing a digit or underscore would not match and would
fall through to a dead `commands/x.md` path. `test_every_extension_path_in_the_package_exists` would
catch that, so the risk is covered.

## Positive Observations

- The root filter drops non-string and empty entries and tolerates non-array `workspace_roots`. The
  bridge never throws, always exits 0, and keeps the stdout JSON shape for every event. The
  6-payload × 4-event no-op matrix shows this.
- The Gemini tests copy the extension into a throwaway HOME and run the doctor's real shell lines in
  bash. They also include a test showing that the tilde form would have failed.
- The tests are isolated properly: HOME, the config dir, the cache dir, the telemetry sink and the
  update check are all redirected, and the gemini binary is never run.
- The CHANGELOG entries describe the user-visible symptom, not the implementation.

## Recommendations

1. (I-1, blocking) Resolve the project from the payload's `cwd` by walking up to its `.archflow/`
   ancestor or its containing root, and add subdirectory-cwd tests. Correct the CHANGELOG and the
   no-cwd test premise for beforeShellExecution.
2. (I-2) Relay both stdout and stderr on stop.
3. (I-3) Quote the migrate.py path in the source command.
