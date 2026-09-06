# Changelog

All notable changes to Archflow are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). "Breaking" means a project on the
previous version needs a migration or a manual edit, not merely that behaviour changed.

Entries before 2.2.1 were reconstructed from git history and are less detailed than what follows.

## [Unreleased]

Nothing yet.

## [2.3.0] — 2026-09-06

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
