VERDICT: PASS

# S7-04 code review: build-adapters HOOK_SCRIPTS helper

Reviewer: code-reviewer (autopilot story_review)
Scope: `git diff v2.5.0-autopilot..HEAD -- scripts/build-adapters.mjs tests/test_build_adapters.py`

## Design System Compliance
N/A. No UI in the diff (a Node build script and a pytest module).

## Verification
- `python3 -m pytest -q tests/` gives 296 passed.
- `node scripts/build-adapters.mjs --check` reports all six adapters up to date, exit 0.

## Code Review Summary
**Overall assessment:** Good. The production change is small and safe. `--list-hooks` exits before any
build and is introspection only, `CLAUDE_ONLY_HOOKS` puts the exclusion in the code instead of
leaving it implicit, and the doc comment says plainly what one HOOK_SCRIPTS entry gives you and what
it does not. The tests close the gap QA raised in I-1. A new `plugin/hooks/*.mjs` cannot be dropped
silently (it must sit in exactly one list). A listed hook cannot be missing from any adapter's hook
root. A hook that is copied but never run on a host now fails with the host name and the file to
edit, and the `NOT_WIRED` allow-list must give a reason per exception. Three minor gaps remain. None
blocks the story.

## Critical Issues
None.

## High Priority Issues
None.

## Medium Priority Issues
None.

## Low Priority Issues

### I-2 (minor): Claude Code's own wiring is not covered by the "every hook is wired" check
`tests/test_build_adapters.py:78` (HOOK_WIRING). The wiring test covers the six adapter hosts only.
For Claude Code, `plugin/hooks/hooks.json` is checked only by hard-coded per-hook asserts in
`tests/test_hooks.py:237` and `:338`. Those asserts name guard-git, check-state and check-upgrade.
They do not name telemetry, and they do not iterate over HOOK_SCRIPTS.
**Failure scenario:** someone adds `foo.mjs` to plugin/hooks and HOOK_SCRIPTS and wires it on every
adapter, but forgets `plugin/hooks/hooks.json`. Every test passes, and the hook never runs on the
primary host.
**Suggestion:** add a `"claude": (["../plugin/hooks/hooks.json"], ...)` style row, or a separate
loop asserting that every HOOK_SCRIPTS and CLAUDE_ONLY_HOOKS entry is named in
`plugin/hooks/hooks.json`.

### I-3 (minor): The wiring check matches script names as plain text, so a comment or dead code counts as "wired"
`tests/test_build_adapters.py:97` (`_names`) and `:114`. The check is a regex search for the
filename anywhere in the concatenated generated files. That includes the Cursor bridge and the
OpenCode plugin source, and a mention inside a comment counts.
**Failure scenario:** the OpenCode plugin gains a comment such as `// TODO: run foo.mjs on idle`.
The test passes and `foo.mjs` is never spawned. For the JSON hosts (codex, gemini, copilot, the
cursor hooks.json) this is low risk, because the name appears only in `command` strings.
**Suggestion:** for the JSON hosts, parse the file and match `command` values. For the
cursor-bridge and OpenCode sources, match the call shape (`run("foo.mjs"` and `runHook(cwd, "foo.mjs"`)
or strip comments first. At minimum, note the limitation in the HOOK_WIRING comment.

### I-4 (minor): Host discovery and the copy-outside-helper check depend on the layout of the source text
`tests/test_build_adapters.py:29` (`_hosts`) and `:140`
(`test_hook_scripts_are_copied_only_by_the_helper`).
- `_hosts()` regex-scans from `const HOSTS = {` to EOF for `^  [a-z]+: {`. A host key with a digit,
  a hyphen or quotes (`"vscode-x": {`), or a different indent, is not seen. The call-count assert
  currently backstops this, because copyHookRuntime would be called once more than `_hosts()`
  reports, but that error message would mislead.
- The offender scan flags only `cpSync` lines that contain the literal `"hooks"` or a script name.
  `copyTree(join(PLUGIN, "hooks"), ...)`, or `cpSync(hookDir, ...)` through a variable, gets past it.
  `test_every_host_ships_the_full_hook_runtime` would still pass in that case, so the drift S7-04
  removed could come back unnoticed.
- `end = src.index("\n}\n", start)` assumes the helper's closing brace is at column 0 with no
  trailing comment.
**Suggestion:** have `--list-hooks` (or a `--introspect` flag) also emit `Object.keys(HOSTS)`, and
drop the regex. For the copy check, widen the scan to any `copyTree`/`cpSync` whose arguments
mention `PLUGIN` and `hooks`. Alternatively, rely on the artifact-level assertion: each adapter's
`hooks/` contains exactly HOOK_SCRIPTS plus host-emitted files (such as cursor-bridge.mjs).

## Positive Observations
- `--list-hooks` returns the lists from the running module, so the tests do not drift from
  the code through a second, parsed copy of the list.
- The failure messages can be acted on: each names the host, the script, the build-adapters
  location to edit, and the generated file.
- `NOT_WIRED` requires a reason per exception and fails on stale entries. That keeps the escape hatch
  from turning into a dumping ground.
- `test_adapters_match_the_plugin` ties the assertions about generated files back to the generator,
  so passing artifact tests cannot hide a stale build.
- `_hook_roots` keys off `lib/commands.json`, which only copyHookRuntime writes. That is a
  precise marker.

## Recommendations
1. (I-2) Assert that every hook is wired in `plugin/hooks/hooks.json` too.
2. (I-4) Expose HOSTS through the introspection flag instead of regex-scanning the source.
3. (I-3) Tighten the wiring match to call sites and command strings.
