# Acceptance Review Report
## Release: v2-5-0 | Story: S7-04 | Date: 2026-10-03

### Verdict
**ACCEPTED**

### How this was tested
- **Tooling**: the project's own tooling, nothing installed. That is pytest (`tests/test_build_adapters.py`), Node v22.12.0 and `scripts/build-adapters.mjs` (`--check`, `--list-hooks`, full regeneration).
- **Commands (real tree, branch `adapters/hook-scripts-helper` @ 04ef978)**:
  - `python3 -m pytest -q tests/` gave **296 passed in 22.31s**
  - `node scripts/build-adapters.mjs --check` reported all six adapters (codex, gemini, opencode, generic, cursor, copilot) "is up to date", **exit 0**
  - `node scripts/build-adapters.mjs --list-hooks` printed `{"hook_scripts":["check-upgrade.mjs","check-state.mjs","guard-git.mjs","telemetry.mjs"],"claude_only_hooks":["studio-session-context.mjs"],"hosts":["codex","gemini","opencode","generic","cursor","copilot"]}`
- **Environment**: a scratch worktree, `git worktree add --detach /tmp/s704-accept HEAD`, which was removed afterwards with `git worktree remove --force` and `prune`. The real working tree stayed clean the whole time.

### Summary
- **Total acceptance criteria**: 2
- **Passed**: 2 · **Failed**: 0 · **Blocked**: 0

### Criterion results

- **AC 1**: Adding a hook requires only a HOOK_SCRIPTS entry
  - **Interpretation**: this AC was judged against the story description: "copies the hook runtime through one helper, so a new hook is one entry in HOOK_SCRIPTS". QA and code review accepted that wiring a hook to a host event stays a per-host edit by design. The tests have to name every host and file that still needs that edit.
  - **Result**: PASS
  - **Evidence** (scratch worktree):
    1. Added `plugin/hooks/probe-hook.mjs` and a single edit: `"probe-hook.mjs"` appended to `HOOK_SCRIPTS`. `git diff --stat` showed only `scripts/build-adapters.mjs | 2 +-`.
    2. Before regenerating, `--check` failed with exit 1 (`Only in .../.codex/archflow/hooks: probe-hook.mjs`, "adapters/codex is stale"). So `--check` catches the stale adapters.
    3. `node scripts/build-adapters.mjs` then shipped the hook to **all six** adapters: `adapters/{codex/.codex/archflow,copilot/.github/archflow,cursor/.cursor/archflow,generic/.agents/archflow,opencode/.opencode/archflow,gemini}/hooks/probe-hook.mjs`. The rerun of `--check` exited 0.
    4. `pytest tests/test_build_adapters.py` gave 1 failed, 7 passed. The only failure was `test_every_hook_script_is_wired_on_every_host`, and it listed exactly 7 lines. That is claude (`plugin/hooks/hooks.json`) plus one line per adapter host, each naming the file to edit and the emit site in `build-adapters.mjs`. Cursor's line names both `.cursor/hooks.json` and the CURSOR_BRIDGE. Each line also offers the `NOT_WIRED` escape hatch.
    5. Positive control: I wired the probe for real on codex only (a Stop handler in `HOSTS.codex.emit`) and regenerated. Codex dropped off the list and the other 6 remained.
    6. A hook file in `plugin/hooks/` with no list entry fails `test_no_plugin_hook_is_silently_left_out`: "plugin/hooks/ has ['probe-hook.mjs'] in neither HOOK_SCRIPTS nor CLAUDE_ONLY_HOOKS".

- **AC 2**: build-adapters.mjs --check passes
  - **Result**: PASS
  - **Evidence**: in the real tree, `--check` prints "is up to date" for all six hosts and exits 0. `test_adapters_match_the_plugin` is green inside the 296-pass run. Step 2 above shows `--check` fails when an adapter is stale, so its pass carries meaning. It left no `.check` temp directories behind in `adapters/`.

### Prior issues I-1..I-4: each fix verified by mutation
| Issue | Mutation in scratch tree | Result |
|---|---|---|
| I-1: an entry ships the hook but nothing tests the wiring | probe hook with entry only | wiring test fails and names all 7 hosts. **Fixed** |
| I-2: Claude Code wiring not covered | same run; then a `"description": "also see probe-hook.mjs"` key added to `plugin/hooks/hooks.json` | `claude: probe-hook.mjs is never run` appears both times. A non-command JSON field does not count as wiring. **Fixed** |
| I-3: comments or prose count as wired | `// runHook(cwd, "probe-hook.mjs", {})` in OPENCODE_PLUGIN, `/* run("probe-hook.mjs", {}); */` in CURSOR_BRIDGE, prose "(probe-hook.mjs is optional)" in the generic AGENTS.md. All of these landed in the regenerated adapters (grep count 1 each) | opencode, cursor and generic are all still reported unwired. **Fixed** |
| I-4: hosts regex-scanned; indirect copies slip past | hosts now come from `Object.keys(HOSTS)` through `--list-hooks` (line 991). Three outside-helper copies injected: `copyTree(PLUGIN, ...)`, `const hk = join(PLUGIN, "hooks"); cpSync(hk, ...)`, `cpSync(PLUGIN, ...)` | each one fails `test_hook_scripts_are_copied_only_by_the_helper` and names the offending line. **Fixed** |

Negative control: the unmodified tree passes all 8 adapter tests (inside the 296), so each failure above comes from its mutation and not from the harness.

### Blocking defects (must fix)
None.

### Non-blocking observations
1. The copy-outside-helper guard is still a source-text regex. It would miss a path built some other way, such as `` `${PLUGIN}/hooks` `` or `PLUGIN + "/hooks"`. No such code exists, and I-4's scope (indirect `copyTree` and `cpSync` of the plugin root or hooks dir) is closed. I am noting it here and not filing it as an issue.

### Recommendation
Proceed. Both ACs pass under the accepted interpretation, and I-1..I-4 are fixed.
