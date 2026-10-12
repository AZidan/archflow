VERDICT: FAIL

# S8-05 code review: framework-wide anonymous telemetry

Scope: `git diff v2.5.0-autopilot..HEAD -- plugin/ scripts/ tests/ SECURITY.md`. That covers
`plugin/lib/telemetry.mjs`, `plugin/hooks/telemetry.mjs`, the OpenCode comment in
`scripts/build-adapters.mjs`, `tests/test_telemetry.py` and `SECURITY.md`. I spot-checked the adapters:
`adapters/copilot/.github/archflow/lib/telemetry.mjs` and `adapters/gemini/hooks/telemetry.mjs` are
byte-identical to their plugin sources. S8-06 (the `/archflow:telemetry` command and the `--status`
wording) and the Copilot/Gemini `cat instructions.md` and check-upgrade SessionStart entries were out
of scope.

Checks:
- `python3 -m pytest -q tests/`: 407 passed.
- `node scripts/build-adapters.mjs --check`: all 6 adapters up to date.

Every manual run used `ARCHFLOW_TELEMETRY_SINK` with a temp `HOME` and `ARCHFLOW_CONFIG_DIR`. Nothing
was sent to PostHog.

## Design System Compliance

N/A. The diff has no UI.

## Code Review Summary

**Overall assessment:** The privacy core is sound. `capture()` builds the payload only from
`EVENT_PROPERTIES`. Unknown events are dropped, and so is a `command_run` that has no valid command.
Unknown keys are discarded. Enum fields fall back to null or `"other"`, and free-text fields are
checked against tight regexes. A project name typed into `phase:`, `mode:` or `project_type:` does not
get through. Command names must match the shipped list on every route: the prompt prefix, the Claude
`command_name`, and OpenCode's `command.executed`. The test seam returns before `spawn`.

One blocking gap remains in the notice. I-1 was marked fixed, but the case where Copilot loads the
Claude plugin directly was not covered.

## Critical Issues

### I-3 (blocking): on Copilot loading the Claude plugin directly, the notice is lost and marked shown

`plugin/hooks/telemetry.mjs:125-130, 137-147`. `formatNotice` decides the format from
`ARCHFLOW_HOST`, which defaults to `"claude"`. `plugin/hooks/hooks.json` never sets `ARCHFLOW_HOST`.
So when Copilot CLI runs the Claude plugin's hooks, the notice goes out as plain text. The QA report
cites Copilot's hook docs: SessionStart stdout that is not JSON counts as no output. `recordNoticeShown()`
still runs, and the notice is suppressed on every host on the machine from then on. The QA report's
I-1 named this case explicitly ("The same applies when Copilot loads the Claude plugin directly,
because `plugin/hooks/hooks.json` is also plain stdout"). The fix in 175bd6b handles only the Copilot
adapter, which sets `ARCHFLOW_HOST=copilot`. `lib/telemetry.mjs:186-192` already treats this as a real
deployment: "Copilot CLI can also load [the Claude plugin] directly ... a null [entrypoint] on
host=claude marks a session that was not Claude Code".

- Repro (sink only):
  `echo '{}' | env -u CLAUDE_CODE_ENTRYPOINT HOME=$T ARCHFLOW_CONFIG_DIR=$T/cfg ARCHFLOW_TELEMETRY_SINK=$T/sink.jsonl CLAUDE_PLUGIN_ROOT=plugin node plugin/hooks/telemetry.mjs`
- Expected: the notice is not marked shown unless it went out in a format the host surfaces.
- Actual: stdout is the plain-text notice, and `config.json` gets `noticeShownAt`.
- Suggested fix: Claude Code always sets `CLAUDE_CODE_ENTRYPOINT`; this session has `sdk-cli`. In
  `formatNotice`, treat `host === "claude"` with no `CLAUDE_CODE_ENTRYPOINT` as an unknown host and
  return `null`. The notice then stays pending, the same as the existing unknown-host path. Add a test
  next to `test_notice_not_marked_shown_when_host_format_is_unknown`.

## High Priority Issues

None.

## Medium Priority Issues

### I-4 (minor): an unreadable config is read as "telemetry on" and then overwritten

`plugin/lib/telemetry.mjs:107-113`. `loadConfig()` returns `{}` on any failure. A missing file
(ENOENT) and a file that exists but won't parse both end up as `{}`.

1. A hand-edited opt-out with a trailing comma, `{"telemetryEnabled": false, ...,}`, turns into "on".
   The hook prints the notice, sends `session_start`, and `saveConfig` replaces the file. The opt-out
   is gone for good. Reproduced with the sink: one event was written, and the file now holds only
   `noticeShownAt` and a new `distinctId`. Before this diff `recordNoticeShown` already overwrote the
   file. This diff adds a second writer, `ensureDistinctId` in `capture()`, on the same path.
2. A file that parses to a non-object (`null`, `[]`, `1`) is returned as-is. `isEnabled(null)` then
   throws. `--status` exits 1 with a stack trace. `npx archflow install` installs everything and then
   exits 1 with `archflow: Cannot read properties of null (reading 'noticeShownAt')`. The session hook
   survives only because of its outer try. The header's claim that any error here is swallowed is
   false for these paths.

Suggested fix: return `{}` only on ENOENT, and only when the parsed value is a plain object. For a
file that exists but can't be read, treat telemetry as disabled (fail closed) and never call
`saveConfig` over it.

### I-5 (minor): a malformed distinctId is never replaced

`plugin/lib/telemetry.mjs:208-214`. `ensureDistinctId` mints a new id only when `distinctId` is
falsy. If the stored value is not a UUID, the allow-list turns it into `distinct_id: null`, and that
is what gets sent. The identifier does not leak, which is correct. But PostHog rejects events that
have no distinct id, so that machine's telemetry is dropped with no error. Reproduced with
`"distinctId": "jane.doe@acme.com"`: the sink payload had `distinct_id: null`. Suggested fix: in
`ensureDistinctId`, re-mint whenever the stored value fails the same UUID regex `COMMON.distinct_id`
uses.

## Low Priority Issues

### I-6 (minor): the test docstring refers to a fixture that does not exist

`tests/test_telemetry.py:6` says "`no_network` additionally asserts the sender was never spawned".
There is no such fixture. The guarantee comes from a single test,
`test_capture_never_spawns_the_sender_when_the_sink_is_set` (line 571). Either reword the docstring,
or turn the spawn stub into an autouse fixture so every test asserts it.

### Observations (no issue recorded)

- `ARCHFLOW_TELEMETRY_SINK` is honoured in the shipped code. It can only redirect an allow-listed
  payload into an append-only local file, and it disables the network send. Anyone who can set the
  hook's environment can already run arbitrary hooks, so it gives them nothing new. It is acceptable
  as is. If a narrower seam is wanted, accept it only when `ARCHFLOW_CONFIG_DIR` is also set.
- `entrypoint` is checked against a 40-character alphanumeric pattern, not an enum. That is fine for
  Claude Code's own values (`cli`, `sdk-cli`, `sdk-ts`, `claude-vscode`). An enum with an `"other"`
  fallback would make the allow-list strict all the way through.
- The OpenCode plugin's `runTelemetry` uses `spawnSync`, with a 3 s timeout, inside an event handler.
  This was already there before the diff (only the comment changed). `telemetry.mjs` itself is fast,
  so in practice it is not a problem.

## Positive Observations

- The allow-list lives in one place (`EVENT_PROPERTIES`), is applied after the caller's properties are
  merged, and `distinct_id` is put in last. A caller cannot inject an extra key or override the id.
- The shipped-command check is applied the same way on all three detection routes.
  `archflow:telemetry` is never reported, so turning telemetry off sends no `command_run`.
- `showNoticeOnce` marks the notice shown only after `writeSync` succeeds, and only for a known
  format. That is the right order.
- The Copilot (`{"additionalContext": ...}`) and Gemini
  (`{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}}`) formats match
  the vendor shapes the QA report cited. Prompt hooks print nothing.
- Hooks fail open: everything is inside try, every path exits 0, there is no network in the hook
  process, and the sender is a detached child with `stdio: "ignore"` and a 5 s `AbortSignal` timeout.
- Config writes go to a per-pid temp file and are then renamed, so a reader never sees a torn file.
- The tests use a real secret-named project folder, check for leaks across every adapter root, and
  check that SECURITY.md stays in sync with the lib's allow-list. No other test file runs a telemetry
  path, so the suite cannot reach PostHog.

## Recommendations

1. (Blocking) I-3: gate the plain-text notice on `CLAUDE_CODE_ENTRYPOINT` when the host is `claude`,
   and add a test for it.
2. I-4: make `loadConfig` fail closed on a config file that exists but is unreadable, and never
   overwrite it.
3. I-5: re-mint a distinctId that is not a UUID.
4. I-6: fix the docstring, or make the no-spawn check an autouse fixture.
