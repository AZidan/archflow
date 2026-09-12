# Changelog

All notable changes to Archflow are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). "Breaking" means a project on the
previous version needs a migration or a manual edit, not merely that behaviour changed.

Entries before 2.2.1 were reconstructed from git history and are less detailed than what follows.

## [Unreleased]

Nothing yet.

## [2.4.0] — 2026-09-12

### Added

- **Archflow runs on hosts other than Claude Code.** `scripts/build-adapters.mjs` generates a
  host-native package from the plugin for OpenAI Codex, GitHub Copilot CLI, Cursor, Gemini CLI,
  OpenCode, and a generic `AGENTS.md` + Agent Skills package for anything else. Each lands in
  `adapters/<host>/` with its own README describing install steps and what that host cannot do.
  The `.archflow/` state files, schemas, phases, design systems and stack profiles are identical
  across hosts, so one project can be worked on from several tools. CI fails if the adapters drift
  from the plugin (`node scripts/build-adapters.mjs --check`).

  Codex and Copilot CLI also load the unmodified Claude Code plugin directly
  (`copilot --plugin-dir plugin`, Codex's plugin importer); the adapters exist for teams that want
  host-native, repo-committed configuration.

- **`npx archflow install`** (npm package `archflow`; `archflowai` is an alias) installs Archflow into a
  project for any of those hosts, and for Claude
  Code itself (`--host claude` installs the marketplace plugin at project scope through the `claude`
  CLI, or writes the same `.claude/settings.json` keys when the CLI is absent). It detects the hosts
  on the machine (or takes `--host`), copies the adapter in, merges the `AGENTS.md`
  block between `<!-- archflow:start/end -->` markers (one section per host when several share a
  project), merges Codex's `config.toml` flags without overriding a human's values, installs
  Gemini as an extension, and installs the git guard. Re-running upgrades in place and never
  deletes a user's file. `--dry-run` shows the plan. The root `package.json` publishes it with
  the adapters bundled.

  The adapters are fetched from the **latest GitHub release** by default and cached per tag under
  `~/.cache/archflow/`, so an npx-cached installer never installs stale files. `--version`
  pins a release, `--bundled` skips the network. The release workflow now attaches the packed
  installer to every release and checks `package.json` against the tag. Re-running the installer
  is the upgrade path on every host; on Claude Code it also runs `claude plugin update`.

- **A session-start notice when a newer Archflow release exists.** The upgrade hook compares the
  installed version with a cache of the latest GitHub release tag, refreshed by a detached child at
  most once a day, so nothing blocks on the network. On Claude Code it names the plugin update; on
  other hosts the installer. Off with `update_check: false` in `project-settings.yaml`.

- **A git `pre-push` guard** (`plugin/scripts/archflow-pre-push.sh`) gives hosts without a
  `PreToolUse` hook the same protection Claude Code has: no force-push to `main`/`master`, no push
  to `main` while an autopilot run is live. `/archflow:doctor --fix` offers to install it (Step 5d),
  chaining any existing hook. It also protects the human's own terminal.

### Changed

- `/archflow:init` and `/archflow:onboard` now write the Archflow section to `AGENTS.md` (read by
  every host) as well as `CLAUDE.md`, wrapped in `<!-- archflow:start/end -->` markers.
- `hooks/guard-git.mjs` accepts the shell tool names other hosts use (`bash`,
  `run_shell_command`) in addition to Claude Code's `Bash`.

### Not ported

- `/archflow:studio` stays Claude Code only: it drives the `claude` binary's session fork.
- `memory: user` agent memory has no equivalent elsewhere.
- OpenCode plugin hooks do not fire inside subagents (upstream #5894), so its git guard covers the
  primary agent only; use the `pre-push` guard as well.

## [2.3.2] — 2026-09-10

### Fixed

- **A project's framework files are kept in step with the plugin.** `.archflow/` is a copy made at
  setup, and the only reconciliation that existed copied files that were *absent* — which almost
  never happens, since every project gets the full set. The real drift was staleness, and it was
  invisible: a project onboarded months ago validated against last quarter's schemas, ran last
  quarter's phase files, and injected last quarter's `instructions.md` into every session.
  `/archflow:doctor --fix` now compares content across everything the plugin ships — `phases/`,
  `schemas/`, `design-systems/`, `stacks/`, `workflow.md`, `stack-detection.md`, `instructions.md`
  and `reference.md` — and refreshes what is behind, backing up each original first.

  Two things it will not do. A file the plugin does not ship is invisible to it, so a design system
  or stack profile you wrote is never touched. And when the project's `plugin_version` already
  matches the installed plugin, a difference is something a human did after the last upgrade: it is
  reported and left alone, because silently discarding a deliberate edit is the one outcome worse
  than staleness. Deleting a file is how you ask for it back.

## [2.3.1] — 2026-09-10

### Added

- **`/archflow:doctor --fix` completes the project's stack.** As its last repair, it detects the
  stack from the repo's own manifests and lockfiles and fills the `stack:` fields that are null,
  after showing the diff. A null `test.e2e` meant `pm-reviewer` returned BLOCKED on every acceptance
  run while `@playwright/test` sat in `package.json` the whole time; that question is now asked once.
  A field that is already set and disagrees with the evidence is a question, never an overwrite —
  asked one field at a time, because a value can be set deliberately against the manifests (a
  mid-migration project with both frameworks installed, a monorepo whose root manifest is not the
  app). `--fix` still installs nothing and still writes no value the repo does not evidence.

### Changed

- **Stack detection is defined once**, in `stack-detection.md`, and read by both `/archflow:onboard`
  and `/archflow:doctor --fix`. It was previously spelled out inside `onboard.md`, which is where a
  second copy would have gone.

### Fixed

- **Framework files the plugin ships now all reach existing projects.** `upgrade_archflow.py` copies
  from an explicit list, and a file added to the skill without being added to that list was shipped
  to new projects and silently never copied into old ones. A test now fails when the two disagree.

## [2.3.0] — 2026-09-10

### Security

- **Removed another project's admin credentials** from the acceptance agent's sample login flow.
  Test accounts now live in `.archflow/test-accounts.yaml`, gitignored, with a committed
  `.example` template.
- **Removed a hardcoded absolute home path** from the acceptance agent. The `memory: user`
  frontmatter already provisions that directory per machine.
- **Pinned both external installs.** codemap now pins to the `v1.3.1` release tag, and
  superdesign-mcp-claude-code to a commit, so a compromise upstream cannot reach users on their next
  install. Each site carries a comment saying why, and `SECURITY.md` records the commit each tag must
  resolve to.
- **Fenced untrusted external content.** `/archflow:onboard` ingests Jira, Notion, Confluence,
  GitHub, Drive, Slack, Trello and arbitrary URLs. That text is now wrapped in
  `<untrusted_external_content>` delimiters and every consuming prompt states it is data to
  summarize, never instructions to follow. Directives found inside are surfaced, not acted on.
- **Added `SECURITY.md`** covering the pinning policy, the untrusted-content convention, the shell
  surface, credential handling, and how to report a vulnerability.
- **Two guard hooks, scoped to Archflow projects.** In a directory with an `.archflow/`, a
  `PreToolUse` hook blocks a force-push to `main`, and any push, checkout or merge touching `main`
  while an unattended autopilot run is live. In any other repo it exits immediately. A `Stop` hook
  warns when state files have drifted from their schemas. Both fail open.

### Changed — schema v2.1

**`current-phase.yaml` split into a cursor and project settings.** It had accreted into two things
with change frequencies orders of magnitude apart: `phase` moves at every transition, `stack` moves
essentially never. Mixing them meant every phase transition dirtied the file holding the stack
config, so a real settings change was buried in phase churn, and the filename described eight of
seventeen fields.

`project_type`, `stack`, `api_contract_path` and `optional_agents` now live in
`.archflow/project-settings.yaml`. `mode` deliberately stayed in the cursor: it is read on nearly
every operation and is already mirrored in `roadmap.yaml`.

`schema_version` is `2.1`. `/archflow:doctor --fix` walks you through the split, reading the file and moving the keys itself
rather than running a script over it — `current-phase.yaml` is hand-editable and its shape varies
per project, so a script would either destroy its comments or eventually mis-parse it. `.archflow/design-system.yaml` was left alone — folding it in touches 88
references across 35 files, most of them a verbatim-quoted string agents are tested against, and
bundling that with a schema migration would tangle two risks.

### Upgrading from 2.2.0

This release changes the schema to 2.1. `/archflow:doctor` reports what needs doing and
`/archflow:doctor --fix` repairs everything except the settings split, which it walks you through
because `current-phase.yaml` is hand-editable and its shape varies per project.

You will be told. A `SessionStart` hook compares your project's `plugin_version` against the
installed plugin and prints what has drifted before your first command, so this does not surface
midway through a story. It stops once the project is repaired.

Run **`/archflow:doctor`** first. A project's `.archflow/` is a copy of framework files made when it
was set up and was never refreshed, so an existing project needs four things reconciled. `doctor`
reports them and **`/archflow:doctor --fix`** repairs the mechanical ones, backing up everything it
touches.

- **Release files naming `pm-maestro-reviewer` fail validation**, and a story assigned to it would
  dispatch an agent that no longer exists. `--fix` renames it.
- **No `stack:` block**, so every code-writing agent stops and asks on its first dispatch. Projects
  onboarded before this have a `tech_stack:` block holding most of the answer; `--fix` converts it.
  A project with neither needs `/archflow:onboard` detection, or a hand-written `stack:`.
- **No `design-systems/`**, so an agent told to read one stops rather than guessing. `--fix` copies
  the missing framework files.
- **No `plugin_version`**, so nothing could detect the drift. `--fix` stamps it.

### Added

- **Review findings are state, not chat.** A story gains an optional `issues[]`: `qa-engineer`,
  `pm-reviewer` and the `story_review` optional agents write what they found into the release file
  alongside their report, instead of handing it back as prose that the next compaction loses. Each
  entry carries `found_by`, `severity`, a location and a pointer to the report — never a copy of it.
  Two invariants are enforced by `validate_archflow.py` (and so by `/archflow:doctor`): a story
  cannot be `done` while it holds an open `blocking` issue, and a `deferred` issue must name the
  backlog stub it moved into. Existing projects need no migration; `issues` is optional and absent
  means none.
- **`/archflow:issue`** — the human's way into that array: record a defect on a story being built,
  list what is open across the active release, or `defer` a minor finding into the backlog. Deferral
  is reserved for a human, so this is the only verb for it. The command routes before it writes:
  anything that is not a defect in a story currently in the build loop goes to `/archflow:feature`,
  which is what keeps a release file from turning into a bug tracker.

- **`optional_agents`, a per-project setting for which non-core agents run automatically.**
  `code-reviewer`, `a11y-expert`, `ui-animation-designer` and `doc-writer` are always available on
  request; this says whether they also join automatically, and where, via four hook points:
  `design`, `story_review`, `release_quality`, `pre_ship`. An empty list means available but never
  automatic. Asked at `/archflow:init` and `/archflow:onboard`, pre-selected by mode, revisited by
  `/archflow:mode`, reported by `/archflow:doctor`.

  This closes two gaps. Three agents shipped referenced by no phase file, so nothing could dispatch
  them and nothing told users they existed. And `code-reviewer` ran only as a Phase 4 whole-codebase
  pass, so a story could be built, tested, accepted and merged with no code review at all — in
  autopilot too. Autopilot now runs the `story_review` hook as part of its loop.
- **`/archflow:contract`** — the release's API contract architecture, and per-story endpoint specs
  that clear a story's `needs_contract` gate. The contract architecture never had a verb.
- **`/archflow:doctor`** — checks tooling, e2e tooling, project state and repo hygiene, with
  `--validate` for schema validation. Reports only; never installs, never edits state.
- **`/archflow:design {story-id}`** — per-story screen design, clearing `needs_design`. The command
  now owns both halves of the split the design phase already defined.
- **Design systems** — shadcn, Material 3, Fluent 2, Liquid Glass and custom tokens, each with a
  binding component vocabulary, scales, rules and anti-patterns that qa-engineer and code-reviewer
  enforce as a blocking gate.
- **Stack profiles** (`stacks/*.yaml`) offered by `/archflow:init` as starting points.
- **`contract_endpoints`** on a story — the counterpart to `design_artifact`. Operation identifiers
  pointing into the contract, never a copy of the endpoint definitions.
- **`current-phase-schema.yaml`** — `current-phase.yaml` was the only state file with no schema.
- **A schema validator** (`plugin/scripts/validate_archflow.py`) with no dependency beyond PyYAML.
- **CI** — YAML and frontmatter parsing, a mirror check, a validator self-check, and 60 tests.

### Changed

- **BREAKING (agents): every agent is now technology-agnostic.** Ten of seventeen hardcoded a stack.
  They now read `stack:` from `.archflow/current-phase.yaml` and work in what it names. A null field
  is a question the agent asks, never a default it assumes, and no agent installs anything to close a
  gap. Projects that relied on the implicit NestJS/PostgreSQL/React defaults should run
  `/archflow:onboard` to populate `stack:`, or write it by hand.
- **BREAKING (agents): `pm-maestro-reviewer` is now `pm-reviewer`**, and no longer Maestro-specific.
  It discovers whatever e2e tooling the project has, uses it, and never installs one. Adds a
  `BLOCKED` verdict for "could not test at all", which halts a story rather than reading as a
  rejection. Anything referencing the old agent name needs updating.
- **All 17 agent descriptions rewritten** to one shape: what it does, when it runs, what it produces,
  what binds it. From 13,535 characters to 3,669, about 2,470 fewer tokens per session.
- **Onboarding split into a router and per-stage sections.** `/archflow:onboard` is the recommended
  entry for an existing codebase, so it is the first thing a new user loads, and it escaped the
  `instructions.md` split. It was 1,889 lines across two files before any agent ran. The always-loaded
  part is now 948, a 50% cut, with the audit checklist, the six agent prompt templates, the synthesis
  rules and the finalization shapes moved to `.archflow/phases/onboarding/` and read per stage. The
  untrusted-content security rule was also duplicated in full across both files; the phase file is now
  its single definition and the command carries the operative summary, so nobody has to fetch a
  security rule before obeying it.
- **`instructions.md` split into a core and a reference.** It is injected on every session start,
  resume and compact, so every line was paid for repeatedly by every user. The always-loaded core is
  now ~1,100 tokens instead of ~5,700, an 81% cut, with the detail moved to `.archflow/reference.md`
  and read on demand. A test enforces the budget so the core cannot quietly grow back, and another
  asserts that every agent, command and rule is still findable in one of the two.
- **codemap is now optional.** Every invocation is guarded and degrades to ordinary file search, and
  the watcher is opt-in. It was an undeclared hard dependency the README never mentioned.
- **The design-system path is threaded into every UI dispatch**, including Phase 3, where the rule
  had been stated but not applied.

### Fixed

- **Stories now walk their status ladder instead of jumping it.** Nothing in the framework said who
  writes `in_progress` or `review`: Phase 3 read `in_progress` in its serialization check but never
  wrote it, and `/archflow:autopilot` went straight to `done`. Overnight runs therefore produced
  stories that had never been observably in progress, and a run that died mid-story left one that
  looked untouched. Both now write each transition as it happens and commit it. A story being fixed
  after a REJECTED verdict stays at `review` rather than flapping back to `in_progress`, which
  would erase that it had already been through QA.
- **The autopilot morning report names what actually broke.** A failed story now lists its open
  blocking issues with file, line and report path, read from the release file — rather than only
  reporting that QA rejected it three times.

- **`api_contract_path` was only half a setting.** `ui-engineer` and `qa-engineer` resolved through
  it, while `api-engineer` and `api-contract-architect` hardcoded `docs/api-contract.md` in seven
  places between them. On a project with a configured path the architect wrote the contract where it
  was told and api-engineer read the default and found nothing — silently, on the one artifact the
  framework calls sacred. All four now resolve, and a test fails on a literal path used as an
  instruction.
- **The contract path was write-once.** Set at setup with no way to change it afterwards.
  `/archflow:contract path <path>` now relocates it, distinguishing pointing at an existing contract
  from moving one (which uses `git mv` so history follows), and reporting references outside
  Archflow that it will not touch.

- **Four commands shipped invalid YAML frontmatter** (`groom`, `mode`, `release`, `status`), each
  from an unquoted colon in the description.
- **The code-reviewer design-system gate was inert**, pasted inside the fenced output template, so it
  read as a section to print rather than a check to run.
- **dsl-generator wrote `styled-dsl.yaml` to a nested path no consumer reads**, breaking the handoff
  into Phase 2.25.
- **qa-engineer's design-system gate declared a failure its protocol never honoured**, so green tests
  reported success with violations outstanding.
- **ui-engineer had no mention of the API contract**, despite the framework binding it as firmly as
  api-engineer.
- **ui-engineer and api-engineer wrote subtask state to `roadmap.yaml`**, which is the release index.
  They now write the active release file and set `status: review` on handoff, which nothing did.
- **pm-reviewer read acceptance criteria from `roadmap.yaml`** rather than the active release file.
- **api-engineer taught MySQL** while the framework promised PostgreSQL. Now neither.
- **Removed the retired root `agents/` tree**, a duplicate of `plugin/agents/` that nothing shipped
  and that had silently drifted.

## [2.2.0] — 2026-08-31

### Added

- **Archflow Studio** as `/archflow:studio` — a local web workspace over the same `.archflow/` files,
  with onboarding and migration from the UI (beta).
- A Studio guide, and titles on every guide.

## [2.1.0] — 2026-08-24

### Added

- **`/archflow:autopilot`** — runs queued release stories unattended on one branch after a blocker
  interview. Pre-authorizes review gates but never the merge to `main`. Parks a story on an undecided
  question rather than guessing, and a parked story blocks the ship by default.

## [2.0.2] — 2026-08-17

### Changed

- **BREAKING: commands are namespaced** as `/archflow:<name>` and live in `plugin/commands/`. The
  argument style `/archflow <sub>` is retired.

## [2.0.1] — 2026-07-26

### Added

- **`/archflow:groom`** — details a backlog stub into a `ready` story with acceptance criteria,
  subtasks and gates.

## [2.0.0] — 2026-07-20

### Changed

- **BREAKING: schema v2.0.** Releases became the outer loop and replaced product "phases"; sprints
  were retired. `roadmap.yaml` became a small index, with detailed stories in
  `releases/{slug}.yaml`, unscheduled scope in `backlog.yaml`, and shipped intent in `history.yaml`.
  Adds the per-story readiness pipeline with `needs_design` and `needs_contract` gates, and
  `quick`/`full` ceremony modes.
- `/archflow:migrate` upgrades a v1.0 project.

## [1.x]

Pre-v2.0 releases used product phases and sprints. See git history for detail; `/archflow:migrate`
is the supported path forward from any of them.

[Unreleased]: https://github.com/AZidan/archflow/compare/2.3.0...HEAD
[2.3.0]: https://github.com/AZidan/archflow/compare/2.2.0...2.3.0
[2.2.0]: https://github.com/AZidan/archflow/compare/2.1.0...2.2.0
[2.1.0]: https://github.com/AZidan/archflow/compare/2.0.2...2.1.0
[2.0.2]: https://github.com/AZidan/archflow/compare/2.0.1...2.0.2
[2.0.1]: https://github.com/AZidan/archflow/compare/2.0...2.0.1
[2.0.0]: https://github.com/AZidan/archflow/releases/tag/2.0
