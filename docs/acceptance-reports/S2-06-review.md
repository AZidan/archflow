# Acceptance Review Report
## Release: v2-5-0 | Story: S2-06 | Date: 2026-10-10

### Verdict
**ACCEPTED**

### How this was tested
- **Tooling**: pytest (the repo's declared unit runner, `stack.test.unit`), `node scripts/build-adapters.mjs --check`,
  the telemetry hook (`plugin/hooks/telemetry.mjs`) driven through the existing `test_telemetry.py` sink helpers
  (nothing reaches PostHog). All already in the project; nothing installed.
- **Commands**:
  - `python3 -m pytest -q` → `763 passed in 81.71s`
  - `node scripts/build-adapters.mjs --check` → all six adapters `is up to date`, exit 0
  - Mutation probes run in a detached worktree at HEAD (6303800), removed afterwards
- **Environment**: macOS, Node + Python 3 as installed; branch `help/help-command`, diff `7f65432..HEAD`.
  The project is a backend_only framework repo, so "end to end" here means exercising the shipped
  command markdown, generated adapters and hook, and reading help/status as a user's agent would.

### Summary
- **Total acceptance criteria**: 7
- **Passed**: 7 · **Failed**: 0 · **Blocked**: 0

### Criterion results
- **AC 1**: plugin/commands/help.md lists every command in plugin/commands/ with a one-line usage note, plus a short primer on how Archflow works
  - **Result**: PASS
  - **Evidence**: 17 files in `plugin/commands/`; help's fenced block has exactly one line per command, each
    with a usage note, grouped by purpose. The primer covers phases, releases, the story pipeline (all
    nine schema states incl. `parked`, matching `release-schema.yaml:91`), gates, modes and a typical
    flow. Fact-checked against source: `/archflow:feature S2-11` is a real form (`feature.md:3,18`);
    quick is init's default and "at most one release in progress" (`reference.md:35,43-44`); done needs
    qa + pm-reviewer ACCEPTED (`reference.md:156-157`); autopilot wording fixed per I-4. `argument-hint:
    "[command]"` present (I-3). One imprecision filed as minor I-8 (below).
- **AC 2**: /archflow:status no longer prints the command list; it ends with the suggested next command(s) and a pointer to /archflow:help
  - **Result**: PASS
  - **Evidence**: Old "Step 2 — Available commands" block gone; Step 2 is now a priority-ordered next-step
    list closing with `All commands, and how Archflow works: /archflow:help` and an explicit "Do not print
    the command list". Walked against this repo's real state (Phase 3, backend_only, full, v2-5-0 with 6/7
    done, no open blocking issues, S2-06 in `review`): the first matching case is 5 → "finish its gate:
    qa-engineer, then pm-reviewer, then the user's approval", which is the correct next step. Pointer renders
    with each host's syntax (`$archflow-help` codex, `/archflow-help` cursor/opencode, `/archflow:help` gemini).
- **AC 3**: A test checks that help lists exactly the commands in plugin/commands/, so the list cannot drift
  - **Result**: PASS
  - **Evidence**: `tests/test_command_registration.py::test_help_lists_exactly_the_shipped_commands`, plus
    per-host `test_each_adapters_help_lists_exactly_what_that_host_ships`. Mutation results (control passes first):
    | Mutation | Result |
    |---|---|
    | add `plugin/commands/zzz.md` | FAIL: `Missing from help: ['zzz']` |
    | delete help's `/archflow:mode` line | FAIL: `Missing from help: ['mode']` |
    | duplicate the `mode` line | FAIL: `help lists a command twice` |
    | add stale `/archflow:sprint` line | FAIL: `In help with no command file: ['sprint']` |
    | re-add a 2-command list to status.md | status test FAIL |
    | delete status's help pointer | status test FAIL |
- **AC 4**: Every place that lists commands includes help: CLAUDE.md, README.md, instructions.md, reference.md, SKILL.md (mirrored in .archflow/), docs guides, site
  - **Result**: PASS
  - **Evidence**: help present in CLAUDE.md:26, README.md:338/355/438, instructions.md:42/45, reference.md:247,
    SKILL.md:20, docs/guides/new-project.md:85, existing-codebase.md:103, docs/index.html:967.
    `.archflow/instructions.md` and `.archflow/reference.md` are byte-identical to the plugin copies
    (`diff -q`). There is no tracked `.archflow/SKILL.md`, so that mirror does not apply. Sweep of every
    tracked md/html naming 8+ distinct commands without help found only `.archflow/project-context.md`
    (persona touchpoints, not a command list). Other guides (studio, prototype-to-product, compare) mention
    single commands in prose, not lists.
- **AC 5**: Gemini adapters regenerate with help.toml and build-adapters.mjs --check passes
  - **Result**: PASS
  - **Evidence**: `adapters/gemini/commands/archflow/help.toml` exists ("Generated from plugin/commands/help.md");
    `--check` exit 0 across all six adapters; every adapter ships its help (test_every_adapter_ships_help).
- **AC 6**: Telemetry's command allowlist (plugin/lib/telemetry.mjs) recognises help, if it keeps one
  - **Result**: PASS
  - **Evidence**: No hand-kept allowlist; `plugin/hooks/telemetry.mjs:91 knownCommands()` reads the shipped
    command files (and each adapter's `commands.json`, which includes help). Hook test reports
    `command_run` with `archflow:help`; negative control (help.md removed in the worktree) makes it fail,
    so the recognition binds to the file.
- **AC 7**: CHANGELOG has an entry for the change
  - **Result**: PASS
  - **Evidence**: CHANGELOG.md [Unreleased] lines 36-45: the help command and the status trim.

### Blocking defects (must fix)
None.

### Non-blocking observations
1. **I-8 (P3, minor)**: help's primer, `plugin/commands/help.md:65`, says "2.25 and 2.5 are skipped when they do
   not apply". Phase 2 (Design) is also wholly not applicable to backend_only projects
   (`phases/phase-2-design.md:32`; this repo records `phases_not_applicable: [2, 2.25]`). A backend user
   reading help would expect a design phase. Suggested: "2, 2.25 and 2.5 are skipped when they do not apply
   (e.g. no UI, no API)."
2. status's design-system line does not say what to print for a no-UI project with no design-system file
   (omit it?). Pre-existing wording, not touched by this story; noted only.

### Recommendation
Proceed. All seven criteria are verified by runs that executed. I-8 is cosmetic and can be fixed or deferred
at the user's discretion.
