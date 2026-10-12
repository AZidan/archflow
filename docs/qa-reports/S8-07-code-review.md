VERDICT: FAIL

# S8-07 code review — telemetry policy recorded (opt-out, framework-wide)

Reviewer: code-reviewer (story_review pass, autopilot)
Scope: `git diff v2.5.0-autopilot..HEAD -- SECURITY.md CHANGELOG.md docs/_config.yml`, the
uncommitted `docs/internal/decisions/005-framework-telemetry-opt-out.md`, and ADR 003's status line.
Checked against `plugin/lib/telemetry.mjs`, `plugin/hooks/telemetry.mjs`, `scripts/archflow.mjs`,
`plugin/hooks/check-upgrade.mjs`, `plugin/hooks/hooks.json`, `tests/test_site_publishing.py`.
Telemetry code defects are out of scope (S8-05/S8-06) and are not filed here.

## Design System Compliance

N/A. Documentation and site-config only; no UI code in the diff.

## Code Review Summary

**Overall assessment:** ADR 005 is accurate and well-bounded, ADR 003 is correctly marked
"Superseded by ADR 005 (2026-10-03)", and the `_config.yml` exclude change is safe. The verdict is
FAIL on one point: `SECURITY.md` still lists fewer properties than the code sends and uses the word
"only" for `cli_install`. That breaks the release exit criterion "SECURITY.md and CHANGELOG describe
the shipped telemetry behavior exactly". It is what's left of QA I-1, which was marked fixed.

## Critical Issues

None.

## High Priority Issues

### I-3 (blocking): the SECURITY.md property list is incomplete, and "carries only" is wrong for `cli_install`

- `SECURITY.md:94`: "`cli_install` carries only which hosts were installed and where the files
  came from". In `plugin/lib/telemetry.mjs:143`, `capture()` spreads `runtimeContext()` into every
  event. `scripts/archflow.mjs:573` overrides `host` with `"cli"`, but `cli_install` still sends
  `entrypoint` (raw `CLAUDE_CODE_ENTRYPOINT`, non-null when `npx archflow install` is run from inside
  Claude Code), `via_studio`, `studio_capture`, `archflow_version` and `distinct_id`.
- `studio_capture` appears nowhere in SECURITY.md, though it is on every event (ADR 005 lists it).
- `SECURITY.md:110-111`: `telemetry_opted_out` is said to carry "the host, the Archflow version,
  where the change was made and how many days after the first-run notice". It also carries
  `entrypoint`, `via_studio`, `studio_capture` and the random id.
- `CHANGELOG.md:20`: "`cli_install` carries the version and the installed hosts" leaves out
  `source` and the runtime-context fields, and the same entry says "(full list in `SECURITY.md`)",
  which is not yet true.

Expected: SECURITY.md lists every property ADR 005's allow-list names, per event, with no "only"
that the code contradicts. The simplest fix is one sentence: "every event also carries host,
entrypoint, via_studio and studio_capture". Keep the per-event extras as they are, and make the
CHANGELOG line agree. All of these values are non-identifying. The defect is that a security
document claims a narrower payload than the one that ships.

## Medium Priority Issues

### I-4 (minor): "It sends no project data anywhere" contradicts the payload

`SECURITY.md:4`. Session and command events send `has_project`, `project_type`, `phase` and
`mode`, all read from the project's own `.archflow/` files. Studio events send project type, phase
and mode as well. That is project metadata. Suggest "It sends no project content, names or paths
anywhere", which matches the "never sent" list in ADR 005.

### I-5 (minor): the env-var off switches are described more broadly than the code applies them

`SECURITY.md:106`: "It is off whenever `CI` is set", and `DO_NOT_TRACK=1`. At
`plugin/lib/telemetry.mjs:56`, a value of `0`, `false`, `no` or `off` counts as unset, so `CI=false`
or `DO_NOT_TRACK=0` leaves telemetry on. ADR 005 states this rule correctly. SECURITY.md should say
"set to anything except 0, false, no or off" so it matches the ADR.

## Low Priority Issues

### I-6 (minor): ADR 005 says the notice is recorded as shown only by code that printed it

`docs/internal/decisions/005-framework-telemetry-opt-out.md:98-99`. `setConsent()`
(`plugin/lib/telemetry.mjs:108`) also sets `noticeShownAt` on any explicit on/off, without
printing. The behaviour is reasonable, since an explicit choice implies the user knows. The ADR
should name that second writer so the record stays exact. (The file is in the archflow-internal
repo and is uncommitted on purpose.)

## Positive Observations

- ADR 005's allow-list matches the code: `runtimeContext()` fields, per-event extras, the
  `days_since_notice` / `via` opt-out fields, the 5-second detached sender, the
  `^archflow:.*` `UserPromptExpansion` matcher, OpenCode's `command.executed`, `/archflow:telemetry`
  never reported, and the opt-out captured before the setting is saved. The Open section admits that
  enum values are not enforced and that retention is undecided, which is better than overclaiming.
- ADR 003 status line: "Superseded by ADR 005 (2026-10-03)".
- The SECURITY.md GitHub-request sentence is accurate: `check-upgrade.mjs` fetches the releases page
  at most once a day per cache, and the installer resolves and downloads a release tag unless it is
  run `--bundled`. Neither request carries user data.
- `docs/_config.yml`: excluding `qa-reports` and `acceptance-reports` by directory follows the
  file's deny-by-default rule ("one entry, not a per-file list"). Jekyll copies front-matter-less
  `.md` files verbatim, so without this `docs/qa-reports/S8-07-qa.md` would have published to
  archflowai.dev. `tests/test_site_publishing.py` passes (10/10), and
  `test_only_the_guides_directory_publishes_markdown` now covers both directories.

## Recommendations

1. (I-3, blocking) Make the SECURITY.md payload description complete: state the four
   runtime-context fields once as "on every event", remove "only" from `cli_install`, and align
   the CHANGELOG `cli_install` line.
2. (I-4, I-5) Tighten the two overstated phrasings in SECURITY.md.
3. (I-6) Amend ADR 005's notice paragraph in the archflow-internal repo.
