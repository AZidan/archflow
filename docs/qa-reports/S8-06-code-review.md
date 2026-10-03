VERDICT: FAIL

# Code Review: S8-06 `/archflow:telemetry` and `npx archflow telemetry`

- **Release:** v2-5-0 · **Branch:** `telemetry/opt-out-command` · **Diff:** `v2.5.0-autopilot..HEAD`
  (plugin/, scripts/, tests/, SECURITY.md, CHANGELOG.md, CLAUDE.md, .archflow/reference.md; the
  generated adapters were spot-checked on all six hosts)
- **Date:** 2026-10-03 · **Reviewer:** code-reviewer (unattended autopilot)
- **Result:** 1 blocking (I-2), 1 minor (I-3)

## Design System Compliance

Not applicable. The change is a CLI and hook script with no UI (`project_type: backend_only`), so the
missing `.archflow/design-system.yaml` is not a finding.

## Checks run

| Check | Result |
|---|---|
| `python3 -m pytest -q tests/` | 498 passed (62s) |
| `node scripts/build-adapters.mjs --check` | all 6 adapters up to date |
| `plugin/skills/archflow/reference.md` vs `.archflow/reference.md` | identical |
| Manual runs (temp `HOME`, `ARCHFLOW_CONFIG_DIR`, `ARCHFLOW_TELEMETRY_SINK`; nothing sent to PostHog) | see I-2 |

## Code Review Summary

**Overall assessment:** small, focused, well-tested change. State transitions are right in the normal
case: `consentChangedAt` moves only when the stored choice flips, `noticeShownAt` keeps its meaning,
`telemetry_opted_out` goes out once and repeating `off` sends nothing. The env-disabled messages are now
truthful. `--host` attribution is safe. One path breaks the main promise of the story: if the opt-out
cannot be saved, the user is told nothing more will be sent, and events keep going.

## Critical Issues

### I-2 (blocking): an opt-out that fails to save reports success, and telemetry keeps sending
`plugin/lib/telemetry.mjs:230-237`, with the confirmations at `plugin/hooks/telemetry.mjs:196` and
`scripts/archflow.mjs:486`.

`setConsent(false)` sends `telemetry_opted_out` first and then calls `saveConfig()`. `saveConfig()`
swallows every write error and returns nothing, so `setConsent` returns `sentOptOut: true` either way.
Both callers then print *"Anonymous usage telemetry is now OFF. One final event recorded the opt-out;
nothing else will be sent."*

Repro (temp HOME and sink):
```
mkdir $T/.archflow; echo '{"noticeShownAt":"2026-01-01T00:00:00.000Z","distinctId":"1111…"}' > $T/.archflow/config.json
chmod 555 $T/.archflow
node scripts/archflow.mjs telemetry off      # prints "now OFF … nothing else will be sent", exit 0
node scripts/archflow.mjs telemetry          # "on (since 2026-01-01…)"
node plugin/hooks/telemetry.mjs --command-run <<< '{"command_name":"archflow:status",…}'
# sink: 1 line (telemetry_opted_out) → 2 lines (command_run sent after the "opt-out")
```
Expected: the opt-out takes effect, or the user is told it did not and nothing is sent (the AC says
"After opt-out no further events are sent"). Actual: a false confirmation, exit 0, and later events are
still sent. Opt-out analytics also count a user who is still sending.

Fix direction (for api-engineer): have `saveConfig` report success. In `setConsent`, check the write
before reporting `sentOptOut`, or before sending the event. One way: write the temp file first, capture
the opt-out, then rename and check the result. Another: save first, then send the final event through
a path that skips the `isEnabled` check. If the save fails, print a "could not save; nothing was
changed" line, like the unreadable-config path, and exit non-zero from the CLI. Add a test with a
read-only config dir.

## High Priority Issues

None.

## Medium Priority Issues

None.

## Low Priority Issues

### I-3 (minor): two `status` hints are still missing
- `CHANGELOG.md:27` still reads `/archflow:telemetry [on|off]`. Every other surface (CLAUDE.md, SKILL.md,
  reference.md x2, the command's `argument-hint`, all adapters) says `[on|off|status]`.
  `test_argument_hints_list_status` does not cover CHANGELOG.md, so the test suite missed it.
- `plugin/commands/telemetry.md:9`, the bad-argument reply, says "the options are `on`, `off`, or nothing".
  It leaves out `status`, though the line above accepts it. This reaches every host's generated copy.

### Note (not filed): `--host` with no value
`node telemetry.mjs --disable --host` (no value) gives `host = undefined`, which falls back to
`ARCHFLOW_HOST || "claude"`, so it is attributed to `claude` rather than `other`. Every generated command
line passes a literal value, so only a hand-typed command hits this. It is harmless.

## Focus areas checked, no finding

- **Consent transitions.** `consentChangedAt` is set only when `(telemetryEnabled !== false) !== enabled`,
  so a first-ever `on` leaves it unset and status shows the notice time. `noticeShownAt ||= now` never
  overwrites. `off` while off sends nothing, because `wasEnabled` is false. `on`/`off` while an env var
  is set stores the choice and sends nothing, because `capture()` re-checks `isEnabled`. After a saved
  opt-out, session-start, command-run and prompt hooks all send nothing, and tests cover this.
- **`--host` injection.** The value only reaches `capture()` through `allowedProperties`, where
  `host: oneOf(HOSTS, "other")` maps any unknown string (including `__proto__`-style keys) to `other`.
  The test case `nonsense → other` covers this.
- **Shell safety of generated lines.** The build-time vocab rewrite inserts `--host ${host}` from the
  fixed build-target keys, never user input. All six adapters have it on `--enable`/`--disable` and
  not on `--status`. Gemini's path is `"$HOME/.gemini/extensions/archflow/hooks/telemetry.mjs"`:
  double-quoted, so `$HOME` expands, and there is no `~`. `test_host_command_lines_work_when_run`
  runs each line under `bash -c` from the project root.
- **Env-disabled messaging.** `statusLine()` names the variable before any date. `optInConfirmation()`
  says the choice is saved but stays OFF. The CLI hides the "turn it on" hint while a variable is set.
  QA I-1 is fixed.
- **CLI parsing and exit codes.** `telemetry`, `telemetry status`, `on`, `off` → 0. Any other argument →
  stderr and exit 2. Extra arguments after the first are ignored. Telemetry is dispatched before
  install-argument parsing.
- **Mirror rule.** The two `reference.md` copies are byte-identical.

## Positive Observations

- `statusLine()` and `optInConfirmation()` move the wording into the shared lib, so the CLI and all seven
  hosts print the same text, and tests assert the exact strings.
- The tests run each host's command lines from the generated files, in a real shell, with the tree laid
  out as installed. That catches path and quoting regressions that a string match would miss.
- Every test goes through the sink, a temp HOME and a temp config dir, so none can reach PostHog.

## Recommendations

1. (Blocking, I-2) Make the opt-out confirmation depend on a successful write, and add a read-only
   config-dir test.
2. (Minor, I-3) Fix the CHANGELOG hint and the bad-argument reply, and extend
   `test_argument_hints_list_status` to CHANGELOG.md.
