# Archflow remediation backlog

One list. Every issue from the three source audits, deduplicated, with the file, the fix, and the
check that proves it closed.

## Sources

| Tag | Source document | Scope |
|---|---|---|
| `AGENT` | `docs/agent-definitions-audit.md` | All 17 files in `plugin/agents/` vs `.archflow/instructions.md` v2.0 |
| `SEC` | `docs/security-audit-remediation-prompt.md` | Socket / Snyk / Gen Agent Trust Hub scans, 2026-04-02, commit `e584c75` |
| `COMP` | `docs/archflow-remediation-prompt.md` | Source-level audit of v2.2.0 against BMAD-METHOD v6.12.0 |

Nine issues were raised by two sources and appear once here, with both tags. Nothing was dropped.
Where the sources disagree, the entry says so and names the decision.

## Status

**37 done · 1 partial · 1 won't fix · 1 deferred · 2 open.** 166 tests pass.

P1 is closed apart from AF-28, which is deferred pending a decision.

Verified against the code rather than trusting these markers — eight items had been fixed as side
effects of other work and were still marked open. The table itself had drifted from reality in a
single session, which is the same class of problem this backlog exists to fix.

What is left:

| ID | Why it is still open |
|---|---|
| AF-28 (deferred) | A `tools` allowlist may belong in project settings, like `stack` and `optional_agents`. Decide that first |
| AF-34 (partial) | 2,750 → ~2,400 lines. dsl-generator and ux-designer grew during the design-system work |
| AF-36 | Won't fix. The measurement showed the delivery mechanism dominates the bundle |
| AF-40, AF-41 | Product and positioning calls, not engineering |

P0 (AF-01 to AF-17) is **done**. All 20 acceptance checks pass. Two P0 fixes changed shape during the work and the entries below reflect the original
finding, not the final fix:

- **AF-16** became a redesign rather than a fallback ladder. `pm-maestro-reviewer` is now
  `pm-reviewer`: tool-agnostic, it discovers whatever e2e tooling the project already has, and it
  never installs anything without asking. The file dropped from 299 lines to 195 and Maestro is now
  one option in a table rather than a hard requirement. This also closed most of AF-34 for that file.
- **AF-12** is now decided and closed. The root `agents/` tree is deleted. Evidence: the marketplace
  ships `./plugin`, so the root tree was never packaged; Claude Code loads project agents from
  `.claude/agents/`, which this repo does not have; and no manifest, hook or script referenced it. It
  dated from the first commit, before the plugin layout existed. `CLAUDE.md` now records that agents
  live in `plugin/agents/` only and are deliberately not mirrored.

Follow-ups created by the P0 work:

- The Studio bundle (`plugin/dist/`, `plugin/server/server.mjs`) still contains the old agent name.
  It is compiled from the archflow-studio repo and needs a rebuild there.
- `.archflow/test-accounts.example.yaml` is new and gitignores `.archflow/test-accounts.yaml`.
- `/archflow:doctor` is written (`plugin/commands/doctor.md`) and registered in the instructions,
  SKILL.md, status, README, CLAUDE.md, init and onboard. This completes AF-15.
- The Studio rebuild is specified in `docs/studio-sync-prompt.md`, to be run in the archflow-studio
  repo. It also raises a product question: the assigned-agent control hardcodes only ten of the
  seventeen agents.
- **AF-29 is done.** All 17 descriptions rewritten to one shape: what it does, when it runs, what it
  produces, what binds it. Total went from 13,535 to 3,669 characters, about 2,470 tokens saved per
  session. The `<example>` blocks were removed because Archflow routes by phase file, not by matching
  a user utterance, so they were paying rent for a mechanism the framework does not use. Three
  descriptions say "on-demand, since no phase dispatches it yet" pending the AF-27 orphan decision.
- **Multi-harness portability** is written up as `docs/decisions/001-multi-harness-portability.md`,
  status Proposed, awaiting review. It has four open questions.

## How to use this

Work top down. AF-01 through AF-17 are the tier that either ships a defect to users today or makes
an agent do the wrong thing; nothing below them matters until they are closed. Each entry ends with
a **Check** that is either a command or a specific observable outcome. Do not mark an item done on
"should work".

The two audit prompts also asked for deliverables that span several entries: `SECURITY.md` covers
AF-03 through AF-05, and `docs/audits/remediation-<tier>.md` reports each tier. Both are noted at
the end.

---

## Summary

| ID | Issue | Sev | Source | Status |
|---|---|---|---|---|
| AF-01 | Another project's credentials ship in `pm-maestro-reviewer.md` | P0 | AGENT, COMP | ✅ done |
| AF-02 | Author's absolute home path ships in `pm-maestro-reviewer.md` | P0 | AGENT, COMP | ✅ done |
| AF-03 | Two runtime installs pull from unpinned Git refs | P0 | SEC | ✅ done |
| AF-04 | Fetched external content is not fenced as untrusted | P0 | SEC | ✅ done |
| AF-05 | Shell surface and background processes are undocumented | P0 | SEC | ✅ done |
| AF-06 | code-reviewer's design-system gate sits inside a fenced template | P0 | AGENT | ✅ done |
| AF-07 | dsl-generator writes `styled-dsl.yaml` where nothing reads it | P0 | AGENT | ✅ done |
| AF-08 | api-engineer teaches MySQL; the framework promises PostgreSQL | P0 | AGENT, COMP | ✅ done |
| AF-09 | ui-engineer never mentions the API contract | P0 | AGENT | ✅ done |
| AF-10 | Both engineers write subtask state to `roadmap.yaml` | P0 | AGENT, COMP | ✅ done |
| AF-11 | pm-maestro-reviewer reads acceptance criteria from `roadmap.yaml` | P0 | AGENT, COMP | ✅ done |
| AF-12 | Root `agents/` is a second, drifting copy of all 17 agents | P0 | AGENT, COMP | ✅ done |
| AF-13 | Design-system path missing from the Phase 3 dispatch templates | P0 | AGENT | ✅ done |
| AF-14 | qa-engineer's design-system FAIL is not wired to its protocol | P0 | AGENT | ✅ done |
| AF-15 | Undeclared hard dependency on codemap | P0 | COMP | ✅ done |
| AF-16 | Maestro is a silent hard stop with no fallback | P0 | COMP | ✅ done |
| AF-17 | Agent and phase counts disagree across manifests | P0 | AGENT, COMP | ✅ done |
| AF-18 | devops-engineer invents a competing release model | P1 | AGENT | ✅ done |
| AF-19 | dsl-generator carries a rival component vocabulary | P1 | AGENT | ✅ done |
| AF-20 | ux-designer's body overrides its own design-system block | P1 | AGENT | ✅ done |
| AF-21 | Phase 4 to 6 agents name no output files | P1 | AGENT | ✅ done |
| AF-22 | Agents have no stop conditions or approval-gate language | P1 | AGENT | ✅ done |
| AF-23 | Nothing advances a story to `review` | P1 | AGENT | ✅ done |
| AF-24 | performance-optimizer plans by calendar | P1 | AGENT | ✅ done |
| AF-25 | post-launch-analyst writes stories into the index | P1 | AGENT | ✅ done |
| AF-26 | i18n-engineer collides with the reserved term "Phase" | P1 | AGENT | ✅ done |
| AF-27 | Three agents are unreachable from any phase | P1 | AGENT, COMP | ✅ done |
| AF-28 | Frontmatter is unnormalized: no `tools`, almost no `model` | P1 | AGENT, COMP | deferred |
| AF-29 | Three description styles, some very large | P1 | AGENT | ✅ done |
| AF-30 | No CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, or tags | P1 | COMP | ✅ done |
| AF-31 | No CI, no mirror check, no schema validator, no migrate tests | P1 | COMP | ✅ done |
| AF-32 | Agents hardcode a technology stack; make them agnostic | P1 | COMP+ | ✅ done |
| AF-33 | The safety envelope is prompt-only | P1 | COMP | ✅ done |
| AF-34 | Roughly half the agent corpus is generic filler | P2 | AGENT | partial |
| AF-35 | Startup injects `instructions.md` whole | P2 | COMP | ✅ done |
| AF-36 | Studio ships 6 MB into every install | P2 | COMP | ⛔ won't fix |
| AF-37 | Phase 3 dispatches engineers with the full transcript | P2 | COMP | ✅ done (reduced) |
| AF-38 | `/archflow:groom` cannot refine an in-release story | P2 | COMP | ✅ done |
| AF-39 | `api_contract_path` is read but never written | P2 | COMP | ✅ done |
| AF-40 | Positioning, comparison page, and name collision | P3 | COMP | open |
| AF-41 | The agent-neutral portability claim is unshipped | P3 | COMP | open |
| AF-42 | Repo tidy: stale ignores, stray proposals, unbuilt flag | P3 | COMP | ✅ done |

---

# P0 — ships a defect today

## AF-01 Another project's credentials ship in the plugin
**Source:** AGENT, COMP P0-4 · **File:** `plugin/agents/pm-maestro-reviewer.md:126-127`

```
ADMIN_EMAIL: admin@aegis.ai
ADMIN_PASSWORD: "Admin12345!@"
```

They sit inside a 40-line sample Maestro login flow at lines 77 to 117, carried over from the
author's own project. Line 75 already tells the agent to read project credentials from its memory,
which is the pattern that should have been used.

**Fix:** Delete the sample flow. Document a gitignored `.archflow/test-accounts.yaml` with a
committed `.example` alongside it, and point line 75 at that. Remove the TOTP helper snippets from
the same block or move them to an optional reference doc. If those credentials are live anywhere,
rotate them.

**Check:** `grep -rn "aegis\|Admin12345" plugin/` returns nothing.

## AF-02 The author's absolute home path ships in the plugin
**Source:** AGENT, COMP P0-4 · **File:** `plugin/agents/pm-maestro-reviewer.md:275`

```
You have a persistent agent memory directory at `/Users/azidan/.claude/agent-memory/pm-maestro-reviewer/`.
```

The frontmatter already sets `memory: user`, which provisions this correctly on every machine. The
prose line is redundant here and wrong everywhere else.

**Fix:** Delete the line. If the memory directory genuinely needs naming, use the variable Claude
Code provides; if it cannot be made portable, drop `memory: user` instead.

**Check:** `grep -rn "/Users/azidan" plugin/` returns nothing.

## AF-03 Two runtime installs pull from unpinned Git refs
**Source:** SEC Finding 1 (Snyk W012, risk 0.80; Trust Hub REMOTE_CODE_EXECUTION + EXTERNAL_DOWNLOADS)

| Where | Install |
|---|---|
| `.archflow/phases/phase-setup.md:145` and its mirror | `pip install git+https://github.com/AZidan/codemap.git` |
| `plugin/skills/archflow/instructions.md:136`, `phase-2.25-hifi-design.md:23,29` | `npx -y github:AZidan/superdesign-mcp-claude-code` |

Both track a moving branch. If either upstream is compromised, every Archflow user executes whatever
is on `main`.

**Fix:** Pin both to a full commit SHA resolved from GitHub, not a placeholder. Make each install an
explicit prompted step that states what is being installed and from where, rather than a side effect
of entering a phase. Add a comment at each site saying why the ref is pinned, so a later edit does
not silently un-pin it. Add a "Supply chain" section to the README listing every external artifact
with its pinned ref.

Related but separate: AF-15 covers making codemap optional, and this entry covers making its install
safe. Do both.

**Propose, do not implement without asking:** publishing `codemap` to PyPI and
`superdesign-mcp-claude-code` to npm with semver, which turns both into ordinary versioned
dependencies. Report what that would take.

**Check:** No `git+https://` or `github:` install in the repo lacks a `@<sha>` or `#<sha>`.

## AF-04 Fetched external content is not fenced as untrusted
**Source:** SEC Finding 2 (Snyk W011, risk 1.00; Trust Hub PROMPT_INJECTION)

**Files:** `plugin/commands/onboard.md` step A2, `.archflow/phases/phase-onboarding.md` Phase B,
plus every other ingestion point.

`/archflow:onboard` pulls text from Jira, Notion, Confluence, GitHub, Google Drive, Slack, Trello
and arbitrary URLs, then hands it to downstream agents that synthesize project context and drive
follow-up actions. Nothing marks where fetched text begins and ends, and nothing tells the consuming
agent that it is data. A single poisoned ticket can steer the workflow, and AF-05's broad shell
surface is what makes that exploitable.

**Fix:** Wrap every fetched item in delimiters naming its source, for example
`<untrusted_external_content source="jira:PROJ-123"> … </untrusted_external_content>`. In every
prompt that consumes such content, state that text inside those delimiters is data to summarize and
never instructions to follow, and that any directive found inside must be surfaced to the user
rather than acted on. Any side-effectful action whose parameters derive from fetched content needs
explicit user confirmation first. Grep for every WebFetch and MCP doc-reading call and cover all of
them, not only the two files named above.

**Check:** Every ingestion site wraps its content, and a fixture document containing an embedded
instruction is reported to the user rather than executed.

## AF-05 The shell surface is undocumented
**Source:** SEC Finding 3 (Trust Hub COMMAND_EXECUTION)

Archflow runs git operations, directory management and long-lived background processes such as
`codemap watch`. That is not a flaw on its own. It is undisclosed, and it is the blast radius for
AF-04.

**Fix:** Add a "What Archflow runs on your machine" section to the README covering the categories of
shell command, which phases run them, and which spawn background processes. Make every long-lived
background process opt-in and document how to stop it.

**Check:** README lists each category, and `codemap watch` does not start without consent.

## AF-06 The code-reviewer design-system gate is inert
**Source:** AGENT · **File:** `plugin/agents/code-reviewer.md:32-51`

Line 32 is `**Output Format:**`, line 33 opens a fence, and line 72 closes it. The design-system
block was pasted at lines 34 to 51, inside that fence, directly above `## Code Review Summary` and
the rest of the fill-in-the-blank template. The model reads it as a section to print, not a check to
perform. The gate does not run.

**Fix:** Move the block above line 32 under its own `## Mandatory pre-review step` heading. Leave
only a `## 🎨 Design System Compliance` heading stub inside the template.

Second, smaller point: the block calls a missing `design-system.yaml` "a blocking finding" while
`.archflow/instructions.md:147` says MISSING FILE = STOP. For a reviewer the softer wording is
arguably correct, since a reviewer that halts reviews nothing. Make it a deliberate choice and say so
in the file, rather than leaving it as drift.

**Check:** The block sits outside every fence, and the only fenced content is the report template.

## AF-07 dsl-generator writes styled-dsl.yaml where nothing reads it
**Source:** AGENT · **File:** `plugin/agents/dsl-generator.md:249-251`

The declared output tree is `design-artifacts/dsl/styled-dsl.yaml`. Every consumer expects it flat
at `design-artifacts/styled-dsl.yaml`: `.archflow/instructions.md` lines 12, 21, 25, 143 and 184,
`phase-2.25-hifi-design.md` lines 13 and 83, and `phase-2.5-api-architecture.md` line 18. Phase 2.25
will not find the file.

**Fix:** Flatten the path. Drop the invented `analysis/` and `validation/` directories in the same
tree, which nothing reads either.

**Check:** `grep -rn "design-artifacts/dsl/" plugin/ .archflow/` returns nothing.

## AF-08 api-engineer teaches MySQL; the framework promises PostgreSQL
**Source:** AGENT, COMP P0-5 · **File:** `plugin/agents/api-engineer.md`

`.archflow/instructions.md:22` says NestJS/PostgreSQL. The agent says MySQL at line 3 twice in the
routing description, at line 7 in the opening persona line, and at line 43 in the schema section.
`grep -i postgres` on that file returns nothing, so the body teaches it, not only the description.
`performance-optimizer.md` and the onboarding templates already assume PostgreSQL.

**Fix:** Standardize on PostgreSQL, which is the majority in the repo. Three string edits. The ORM
line at 47 is already stack-neutral. This is a stop-gap. AF-32 removes the stack from the agent entirely.

**Check:** `grep -rniI "mysql" plugin/ --include=*.md` returns nothing.

## AF-09 ui-engineer never mentions the API contract
**Source:** AGENT · **File:** `plugin/agents/ui-engineer.md`

`grep -i "api.contract"` on that file returns nothing. `.archflow/instructions.md:129` binds the
contract to "api-engineer AND ui-engineer", and line 132 spells out the consumer side: interfaces
must match contract response schemas exactly, pages must call real API hooks, and mock data belongs
only in `design-artifacts/` prototypes and test files.

api-engineer carries three contract sections. Its counterpart carries none, and qa-engineer never
verifies the contract either, so it is enforced on exactly one side of the seam it exists to protect.
After the new design-system block landed, ui-engineer now has a rigorous design gate and no contract
gate at all.

**Fix:** Add a matching `## 🚨 API Contract (real app only)` block to ui-engineer stating the four
rules from line 132. Add a backend check to qa-engineer that verifies implemented endpoints against
`docs/api-contract.md` for path, method and response schema, and fails on drift.

**Check:** ui-engineer names `docs/api-contract.md`, and qa-engineer has a contract-drift check.

## AF-10 Both engineers write subtask state to the wrong file
**Source:** AGENT, COMP P0-3 · **Files:** `plugin/agents/api-engineer.md:92,103`,
`plugin/agents/ui-engineer.md:196,201`

Both say `Update .archflow/roadmap.yaml — set completed: true for each subtask you completed`, with
matching `git add .archflow/roadmap.yaml`. Under v2.0, `roadmap.yaml` is an index. Subtasks live in
`.archflow/releases/{active_release}.yaml`, and neither agent is told that `active_release` comes
from `.archflow/current-phase.yaml`.

**Fix:** Point both at the active release file, resolved through `current-phase.yaml`, per
`plugin/skills/archflow/schemas/release-schema.yaml`.

**Check:** `grep -rn "roadmap.yaml" plugin/agents` returns only index-level reads.

## AF-11 pm-maestro-reviewer reads acceptance criteria from the wrong file
**Source:** AGENT, COMP P0-3 · **File:** `plugin/agents/pm-maestro-reviewer.md`

`.archflow/instructions.md:24` and `:150` put acceptance criteria in the active release file. The
agent says `roadmap.yaml` at lines 9, 39 and 257, where line 257 states it as the source of truth
outright. Line 39 is the operative instruction that breaks runs.

Retired sprint vocabulary survives at lines 197, 253 and 269, and in four `<example>` blocks inside
the frontmatter description. Those four are the only genuine sprint residue left in the markdown;
every other hit in the repo is either intentional "sprints retired" prose or a Jira column label in
`setup-mcp.md`.

**Fix:** Repoint lines 9, 39 and 257 at `.archflow/releases/{active_release}.yaml`, resolved through
`current-phase.yaml`, which must be read first and unconditionally rather than "if it exists" as
line 40 currently says. Change line 197's report header from `Sprint` to `Release`, line 253 from
"Sprint Completion" to the release ship gate, and line 269 to "across releases". Rewrite the
description per AF-29, which removes the other four.

**Check:** `grep -rniI "sprint" plugin/agents plugin/commands plugin/skills --include=*.md` returns
only the intentional "sprints retired" statements and the Jira column label.

## AF-12 Root `agents/` is a second, drifting copy
**Source:** AGENT, COMP ground rules · **Files:** `agents/`, `plugin/agents/`, `CLAUDE.md:40-42`

The repo root has a tracked `agents/` directory holding all 17 files. It was byte-identical to
`plugin/agents/` at HEAD, and the current uncommitted design-system work has already broken that on
all seven edited files. There is no sync script and no CI check. The marketplace manifest points at
`./plugin`, so the root copy ships nothing.

**The two audits disagree and this needs your decision.** The agent audit recommends deleting the
root tree, since nothing ships from it. The competitive audit treats `plugin/agents` and `agents` as
a mirror pair that must stay byte-identical. `CLAUDE.md:40-42` documents only
`plugin/skills/archflow/` and `.archflow/` as mirrored and does not mention `agents/` at all, which
is why the drift went unnoticed.

**Fix, either way:** pick one. If deleting, remove the tree and say so in `CLAUDE.md`. If keeping,
add `agents/` to the mirror rule in `CLAUDE.md` and enforce it in CI under AF-31. Do not leave it
undocumented.

**Check:** Either `agents/` is gone, or `diff -rq agents plugin/agents` is clean and CI runs it.

## AF-13 The design-system path never reaches Phase 3
**Source:** AGENT · **Files:** `.archflow/phases/phase-3-implementation.md` and five others

`.archflow/instructions.md:185` requires the design-system path be written verbatim into every UI
subagent's dispatch prompt, explicitly warning against relying on the parent's context. Phase 2 was
updated. Phase 3, where ui-engineer is actually dispatched, was not: its templates at lines 185, 198,
210 and 216 pass `{design_artifact}` and `{api_contract_path}` and stop there.

Also missing it: `phase-2.25-hifi-design.md`, `phase-6-enhancement.md`, `phase-onboarding.md`,
`plugin/commands/feature.md`, `plugin/commands/autopilot.md`.

**Fix:** Add the sentence from `instructions.md:185` to every dispatch template in those six files.

**Check:** Every file that names a UI agent also names `design-system.yaml`.

## AF-14 qa-engineer's design-system FAIL is not wired to its protocol
**Source:** AGENT · **File:** `plugin/agents/qa-engineer.md:16-18, 282`

The new block says any anti-pattern violation fails the review. The completion protocol at line 282
still reads "If ALL pass", meaning tests only. An agent with green tests and three design-system
violations will read line 282 and report success. qa-engineer also writes no durable artifact, so
those findings evaporate when the subagent returns.

**Fix:** Amend line 282 to require both. Add a third branch for tests-pass-design-fails that returns
the story to ui-engineer and does not trigger acceptance testing. Give the agent a report path at
`docs/qa-reports/{story-id}-qa.md` and `git add` it alongside the tests.

**Check:** A fixture with passing tests and one anti-pattern violation does not report success.

## AF-15 Undeclared hard dependency on codemap
**Source:** COMP P0-1 · **Files:** `plugin/skills/archflow/instructions.md:159-165,211`,
`phase-3-implementation.md` pre-flight, `phase-setup.md`, `README.md`

The instructions say to always use codemap and to run `codemap init .` and `codemap watch . -q &` on
setup. `grep -ci codemap README.md` returns 0, and the only install mention is in `phase-setup.md`.
A user without it hits errors in the pre-flight.

**Fix:**
1. Add a Prerequisites section to the README listing Node 18 or newer, Python 3 with PyYAML for
   `/archflow:migrate`, codemap, and Maestro, each with a one-line why and used-by.
2. Make codemap optional with graceful degradation. Guard every invocation with
   `command -v codemap >/dev/null 2>&1` and fall back to Glob, Grep and Read. Change "ALWAYS use
   codemap" to "prefer codemap when installed".
3. Add `/archflow:doctor` as `plugin/commands/doctor.md`, checking git, node, python3 with a yaml
   import, codemap, maestro and the `.archflow/` schema version, printing PASS, WARN or FAIL per
   check with the install command for each failure. Reference it from `init.md`, `onboard.md` and
   the README quick start.

Pin the install itself under AF-03. Make `codemap watch` opt-in under AF-05.

**Check:** On a fresh clone with codemap uninstalled, `/archflow:init` and a Phase 3 pre-flight run
without error, and `/archflow:doctor` shows codemap as WARN with its install line.

## AF-16 Maestro is a silent hard stop
**Source:** COMP P0-2 · **Files:** `plugin/agents/pm-maestro-reviewer.md`,
`phase-3-implementation.md`, `phase-4-quality.md`

The agent forbids curl, Playwright and source reading as substitutes, allowing curl only for
backend-only projects. The README mentions Maestro five times and never says how to install it. With
Maestro absent, acceptance simply cannot complete.

**Fix:**
1. README Prerequisites: the install command, and which project types need it.
2. Add an explicit fallback ladder to the agent for when `maestro` is off PATH or the target is
   unreachable. For `backend_only`, use Supertest or curl against every acceptance criterion with
   response captures in place of screenshots. For web with Maestro missing, use a Playwright flow per
   criterion with the same ACCEPTED, REJECTED or PARTIAL report format. Otherwise return
   `BLOCKED: maestro not installed`, which is not REJECTED, and halt the story rather than skipping
   acceptance.
3. Phase 3 must treat `BLOCKED` as do-not-merge and surface it to the user.

**Check:** A `backend_only` project with Maestro absent still produces a report. A `fullstack`
project with Maestro absent halts with BLOCKED and an install instruction.

## AF-17 Agent and phase counts disagree
**Source:** AGENT, COMP P0-6

`plugin/.claude-plugin/plugin.json:3` says "16+ specialized agents". `.claude-plugin/marketplace.json`
lines 5 and 13, `README.md` lines 25, 213 and 380, and `docs/index.html` say 17. The real count is
17. Separately, the README and landing page say "6 phases" while
`plugin/skills/archflow/phases/` holds eight numbered stages (1, 2, 2.25, 2.5, 3, 4, 5, 6) plus
onboarding and setup.

**Fix:** Settle the agent count after AF-27 decides whether the three unreachable agents are kept,
then write one canonical number into `plugin.json`, `marketplace.json`, the README and the landing
page. For phases, either say "6 phases, with optional 2.25 hi-fi and 2.5 API-contract sub-phases"
everywhere or renumber.

**Check:** `grep -rn "16+\|17 agents\|6 phases\|8 phases" .` is internally consistent.

---

# P1 — correctness, consistency, rigor

## AF-18 devops-engineer invents a competing release model
**Source:** AGENT · **File:** `plugin/agents/devops-engineer.md`

No mention of `/archflow:release ship`, `.archflow/releases/archive/`, `history.yaml`, the `shipped[]`
ledger, or any of the nine ordered steps in `phase-5-launch.md:34-76`. Instead line 177 defines its
own `release-plan.yaml` with version, release date, features and rollback strategy, and line 221 an
`app-store-metadata.yaml`, neither with a path. That is a second source of truth for exactly the data
`/archflow:release` owns. Line 195 gives a release-notes template with no destination, though the
framework wants it at `docs/releases/{active_release}.md`.

It also omits `phase-5-launch.md:106`, "USER APPROVAL MANDATORY before actual production launch, NO
AUTONOMOUS LAUNCH". The closest thing is a checklist item at line 276, which is a checkbox, not a stop.

**Fix:** Replace lines 173 to 242 with the ship ritual as defined in `phase-5-launch.md`, reading
`active_release` from `current-phase.yaml`, and state that the release file is the only release
record. Add explicit stop conditions: no autonomous launch, and never merge to `main`.

**Check:** `grep -n "release-plan.yaml" plugin/agents/devops-engineer.md` returns nothing, and the
agent names the archive, history and shipped-ledger steps.

## AF-19 dsl-generator carries a rival component vocabulary
**Source:** AGENT · **File:** `plugin/agents/dsl-generator.md:99-127, 129-169`

Lines 129 to 169 hardcode `VStack`, `HStack`, `ZStack`, `TextField`, `Picker`, `TabView` and
`NavigationView`, while the new block at line 14 says names come from the design system's vocabulary
table. shadcn has neither `VStack` nor `Picker`. Two catalogs, and the longer example-backed one
tends to win.

Worse, the flagship styled-DSL example at lines 99 to 127 emits `gray_900`, `gray_300` and
`primary_500`. The shadcn design-system file lists raw palette classes as both a Rules violation and
a review-failing anti-pattern, so the agent's own example fails the gate the agent now enforces.

**Fix:** Delete the hardcoded catalog, or demote it explicitly to a fallback used only when no design
system is set. Rewrite the example to draw token names from the chosen system's theme entry point.

**Check:** The example passes the anti-pattern list in `.archflow/design-systems/shadcn.md`.

## AF-20 ux-designer's body overrides its own design-system block
**Source:** AGENT · **File:** `plugin/agents/ux-designer.md:82-182, 193, 213-225`

Lines 82 to 182 instruct the agent to invent a design system from scratch: a 70-line `theme.yaml`
with hardcoded hex ramps such as `primary.500: "#3b82f6"` at line 96, its own radius, shadow and
animation scales, and a Brand Discovery step at line 193. `phase-2-design.md:78` says `theme.yaml`
must be derived from the chosen system's scales, not invented. The agent reads the block, then
follows 100 lines of worked example that ignore it.

The output tree at lines 213 to 225 is also wrong. It declares `design-artifacts/flows/` and
`design-artifacts/themes/`, while phase 2 expects flat `user-flows.md` and `theme.yaml`. Nothing
reads the nested paths.

**Fix:** Reframe the visual-design section as token derivation from the chosen system, leaving only
brand hues as a project choice. Flatten the output tree to match phase 2, and add the two paths the
agent does not know about: per-story output under `design-artifacts/{story-id}/` and
`design-artifacts/component-gaps.md`. Add a handoff naming dsl-generator as the consumer.

**Check:** The declared paths match `phase-2-design.md:77-81`.

## AF-21 The Phase 4 to 6 agents name no output files
**Source:** AGENT · **Files:** `code-reviewer.md`, `performance-optimizer.md`, `devops-engineer.md`,
`post-launch-analyst.md`, `i18n-engineer.md`

Between them they produce a code review, a performance report, deployment config, an analytics setup
doc and locale files. None states a path, though the phase files name every one:
`docs/code-review-report.md`, `docs/performance-report.md`, `docs/analytics-setup.md`,
`i18n-config/`. This violates `.archflow/instructions.md:168`, "MANDATORY FILE NAMING".

Note the framework itself is inconsistent here: `phase-4-quality.md:75` wants
`docs/performance-report.md` and `phase-6-enhancement.md:34` wants
`docs/performance-improvements.md`. Settle that while fixing this.

**Fix:** Give each agent an `## 📤 Outputs` section with the exact path.

**Check:** Every agent names at least one output path that a phase file also names.

## AF-22 Agents have no stop conditions or approval-gate language
**Source:** AGENT

`.archflow/instructions.md:155-158` declares approval gates universal, and line 185 warns explicitly
against relying on the parent's context to carry a rule. None of product-strategist,
api-contract-architect, doc-writer, code-reviewer, performance-optimizer, devops-engineer,
post-launch-analyst or i18n-engineer mentions one. Four of them end on a self-congratulatory sentence
instead: `devops-engineer.md:285`, `i18n-engineer.md:393`, `performance-optimizer.md:111`,
`code-reviewer.md:74`.

None of the five Phase 4 to 6 agents mentions the git workflow either, though three of them write
code or push tags.

Two agents also tell a subagent to ask the user clarifying questions, which a dispatched subagent
cannot do: `ui-animation-designer.md:65` and `post-launch-analyst.md:47`.

**Fix:** Replace each closing sentence with an explicit stop. Add one line about working on the
current task branch and never merging. Replace both ask-the-user instructions with "state the
assumption in the report".

**Check:** Every agent's last section is a stop condition, not a summary of its own virtues.

## AF-23 Nothing advances a story to `review`
**Source:** AGENT

The v2.0 ladder is `backlog → spec_ready → design_ready → contract_ready → ready → in_progress →
review → done`, plus `parked`. It appears in none of the engineer or reviewer agents. Each only
carries the negative rule "do not set done", at `api-engineer.md:121` and `ui-engineer.md:218`. The
state machine therefore has no writer at the exact point where these agents hand off, and
qa-engineer, which produces the review, updates nothing.

**Fix:** State the ladder once in the agents that move a story, and have ui-engineer and api-engineer
set `review` when they hand off. This is the same edit as AF-10 and should land with it.

**Check:** Running a story end to end leaves it at `review`, not `in_progress`.

## AF-24 performance-optimizer plans by calendar
**Source:** AGENT · **File:** `plugin/agents/performance-optimizer.md:92-96`

An `## Implementation Roadmap` with "Quick wins (1-2 days)", "Medium-term (1-2 weeks)" and "Strategic
(1+ months)". This predates the release model and collides with `roadmap.yaml`, which under v2.0 is
an index the agent must not touch.

The file is also ambiguous about whether it edits code: `phase-4-quality.md:75` says analyze and
optimize, `phase-6-enhancement.md:34` says implement, and the agent itself only ever writes a report.

**Fix:** Replace the calendar tiers with backlog stubs written via `/archflow:feature`. State plainly
whether the agent may apply optimizations, and if so, that it works on the current task branch and
never merges.

**Check:** No calendar-based planning remains, and the edit-or-report question is answered in the file.

## AF-25 post-launch-analyst writes stories into the index
**Source:** AGENT · **File:** `plugin/agents/post-launch-analyst.md:27`

"Suggest roadmap updates based on user behavior patterns and engagement data". Under v2.0 that would
put stories into an index file. Findings should become backlog stubs, or a candidate goal for the
next release per `phase-5-launch.md:85`.

**Fix:** Repoint at `/archflow:feature` and the backlog. Add the output paths from AF-21.

**Check:** The agent never names `roadmap.yaml` as a write target.

## AF-26 i18n-engineer collides with the reserved term "Phase"
**Source:** AGENT · **File:** `plugin/agents/i18n-engineer.md:356-380`

It labels its own five internal steps `### 1. Text Extraction Phase` through `### 5. Validation
Phase`. In a framework where Phase is reserved for the 1 to 6 lifecycle, an agent reading "Phase 5"
against `current-phase.yaml → phase: 6` is ambiguous.

The agent is also a repo-wide refactor, which `.archflow/instructions.md:183` explicitly warns
against ("Never give an agent a cross-cutting concern"), and it has no handoff to qa-engineer to
re-run the suite afterwards.

**Fix:** Rename the five headings to Step. Add the task-branch and never-merge line from AF-22 and a
handoff to qa-engineer.

**Check:** `grep -n "Phase" plugin/agents/i18n-engineer.md` returns only lifecycle references.

## AF-27 Three agents are unreachable from any phase
**Source:** AGENT, COMP P1-4

`a11y-expert`, `doc-writer` and `ui-animation-designer` appear zero times in
`.archflow/instructions.md` and zero times across every file in `.archflow/phases/`. For comparison,
`ux-designer` appears 18 times and `qa-engineer` 15. Two of the three just received the new
design-system block, so effort is going into agents nothing dispatches.

Two of them also have a specific problem if kept. `doc-writer` is told to write `docs/API.md`
alongside `docs/api-contract.md`, which is two owners for one subject and a direct violation of
`instructions.md:186`, "Only ONE agent may modify a given file". `ui-animation-designer` received the
producer variant of the design-system block, but the design-system files have no motion section at
all, so its durations and easing remain unbound.

**Fix:** Either wire them in, with a11y-expert into the Phase 4 quality set, doc-writer into Phase 5
before the ship ritual, and ui-animation-designer as an optional Phase 2 step behind a `needs_motion`
flag, or move them to `plugin/agents/optional/` and exclude them from the headline count. If
doc-writer is kept, repoint it at a human-facing `docs/api-reference.md` that links to the contract
rather than restating it. If ui-animation-designer is kept, add a `## Motion` section to the
design-system file schema, which `design-systems/CONTRIBUTING.md` governs. Then close AF-17.

**Check:** `grep -rln "a11y-expert\|doc-writer\|ui-animation-designer" .archflow/phases` is non-empty
for every agent that was kept.

## AF-28 Frontmatter is unnormalized
**Source:** AGENT, COMP P3-3

| Field | Coverage across the 17 |
|---|---|
| `model` | 2 (api-contract-architect sonnet, pm-maestro-reviewer opus) |
| `tools` | 0 |
| `color` | 15 (missing on product-strategist, ui-animation-designer) |

No `tools` declaration means every agent gets full access, including write and web tools that
read-only reviewers never need. The sharpest illustration: pm-maestro-reviewer spends ten prose lines
at 13 to 23 banning chrome-devtools, Playwright and curl, which a `tools` allowlist would make
structurally impossible.

**Fix:** Add `tools` allowlists, starting with the read-only agents: code-reviewer,
performance-optimizer, post-launch-analyst, a11y-expert. Pin a model on at least the two gate agents,
code-reviewer and pm-maestro-reviewer, since a zero-tolerance gate that inherits whatever the caller
is running is not a gate. Add the two missing colors.

**Check:** Every agent declares `tools`, and both gate agents declare `model`.

**Deferred, deliberately.** A `tools` allowlist may belong in project settings rather than
hardcoded per agent — the same shape as `stack` and `optional_agents`, where the framework declares
the field and the project fills it. A team on a locked-down setup may want a narrower allowlist than
a solo developer. Decide the configurability question before hardcoding anything, or the hardcoded
version becomes the thing that has to be undone.

## AF-29 Three description styles, some very large
**Source:** AGENT

Tagged `<example>` blocks, untagged "Examples:" prose, and bare one-liners are all in circulation.
Descriptions load into every session's agent index, and the legacy blobs are large: pm-maestro-reviewer's
is roughly 2,400 characters, api-engineer's 1,200. They are also where stale vocabulary survives best:
four of pm-maestro-reviewer's sprint references and api-engineer's MySQL claim all live inside
description strings.

Several also fail at the one job a description has. `qa-engineer.md:3` is a tooling inventory that
never says it runs after the feature agents and before acceptance. `ui-engineer.md:3` ends on
"Replaces 6 specialized agents", which is a changelog note. Neither mentions the contract or the
design system, the two things that most constrain them.

**Fix:** Standardize on one line saying what the agent does, when it runs, and what binds it. Delete
the `<example>` blocks.

**Check:** No description exceeds roughly 300 characters, and each names its position in the sequence.

## AF-30 No release hygiene files
**Source:** COMP P1-1

**Fix:** Add `CHANGELOG.md` in Keep-a-Changelog format, backfilling 2.0, 2.1 and 2.2 from
`docs/archflow-releases-v2-proposal.md` and file dates. Add `CONTRIBUTING.md` covering how to add an
agent and wire it into a phase, the mirrored-tree rule as settled in AF-12, and commit conventions.
Add `CODE_OF_CONDUCT.md`. Tag `v2.2.1` and add a release workflow triggered on tags.

**Check:** The files exist and `git tag` shows the version in `plugin.json`.

## AF-31 No CI, no mirror check, no schema validator
**Source:** COMP P1-2 · `.github/workflows/` currently holds only `traffic-metrics.yml`

**Fix:**
1. `ci.yml` on push and PR: markdownlint, a script asserting `plugin/skills/archflow` equals
   `.archflow` and, per the AF-12 decision, `plugin/agents` equals `agents`, YAML lint on all schemas
   and examples, and `python -m pytest`.
2. `plugin/scripts/validate_archflow.py` validating `roadmap.yaml`, `backlog.yaml`, `releases/*.yaml`,
   `history.yaml`, `current-phase.yaml` and autopilot ledgers against the schemas in
   `plugin/skills/archflow/schemas/`. Expose it as `/archflow:doctor --validate` and run it in CI
   against fixture projects.
3. Tests for `plugin/scripts/migrate.py`: at least one v1 fixture to v2 golden output, plus the
   deploy-evidence reconstruction path.
4. Run `claude plugin validate` in CI if available.

**Check:** CI is green on a PR, and deliberately breaking a schema field fails it.

## AF-32 Make the agents technology-agnostic
**Source:** COMP P1-3, extended · **Severity: P1, promoted** · Supersedes the AF-08 stop-gap

Ten of the seventeen agents hardcode a technology stack.

| Agent | Distinct technologies named |
|---|---|
| qa-engineer | 20 |
| i18n-engineer, pm-reviewer | 13 |
| devops-engineer | 12 |
| ui-engineer | 10 |
| ui-animation-designer | 6 |
| api-engineer, dsl-generator | 4 |
| performance-optimizer, ux-designer | 3 |

Two different problems are mixed together here, and only one is a defect.

**Prescriptive coupling is the defect.** The agent decides the stack. api-engineer fixes NestJS,
PostgreSQL and TypeORM or Prisma. ui-engineer fixes React with TypeScript and Tailwind, React Native
with Styled Components, SwiftUI on iOS 16+, Compose with Material 3. devops-engineer fixes GitHub
Actions, Docker, Firebase Hosting and Fastlane. qa-engineer fixes Jest for web and Detox for React
Native. A team on a different stack gets a prompt shaped around someone else's.

**Descriptive naming is fine and should be kept.** pm-reviewer names Playwright, Cypress, Detox and
the rest as options to *detect*, not to impose. That is the target behavior, not the problem.

### Why "configurable" is not enough

The original brief proposed a `stack:` block that agents read, with "the hard-coded text becomes the
default profile." That is configurable-with-defaults, and it moves the coupling rather than removing
it. An agent that says "NestJS unless told otherwise" still reaches for NestJS whenever the config is
absent, thin, or half-populated by detection. The default leaks at exactly the moments it matters.

**Target: the agent carries no technology at all.** It reads the stack profile and works in whatever
that names. Where no profile exists it discovers from the project and asks rather than assuming.

### The precedent already exists

`pm-reviewer` was rewritten this way in the P0 pass. It checks the project's manifests, looks for an
existing test directory, checks binaries on PATH, matches what it finds against the project type,
and returns `BLOCKED` with the options rather than installing or assuming. Generalize that.

### This is the same separation as ADR 001

`docs/decisions/001-multi-harness-portability.md` argues that behavior belongs in the skill and
harness specifics belong in thin bindings. Technology is the third thing to pull out of the same
files. What api-engineer *does* — build endpoints from the contract, follow it exactly, hand off to
qa-engineer — is technology-neutral. The stack is a profile exactly as the harness is a binding.

Doing AF-32 and ADR 001 step 0 together is cheaper than doing either alone, since both are the same
edit to the same seventeen files.

**Fix:**

1. Add a `stack:` block to `current-phase.yaml` and extend the schemas: `backend.framework`,
   `backend.database`, `backend.orm`, `web.framework`, `web.styling`, `mobile.framework`, `ci`,
   `hosting`, `test.unit`, `test.e2e`.
2. `/archflow:init` asks for it. `/archflow:onboard` populates it by detection from `package.json`,
   `go.mod`, `pyproject.toml`, `Podfile`, `build.gradle` and `Dockerfile`. `/archflow:doctor` reports
   it and flags an unset stack on a project past Phase 1.
3. **Strip every prescriptive technology name from the agents.** They read `stack:` and work in what
   it names. No agent carries a default. Keep descriptive enumerations only where the agent's job is
   to detect, as pm-reviewer does.
4. Where the stack is unset and cannot be detected, the agent states what it found, names the
   candidates, and asks. It never assumes and never installs.
5. Ship named profiles under `plugin/skills/archflow/stacks/` as starting points for `init`, not as
   fallbacks agents silently inherit.

**Check:** `grep -riE "nestjs|postgres|tailwind|firebase|fastlane" plugin/agents/` returns only
detection lists, never an instruction to use one. Initializing with a non-default profile makes
api-engineer's plan reference that framework. Initializing with **no** stack set makes api-engineer
ask rather than reach for NestJS.

## AF-33 The safety envelope is prompt-only
**Source:** COMP P1-5 · `plugin/hooks/hooks.json` has only SessionStart hooks

"Never merge to main", the phase gates and the one-agent-per-file rule are all prompt text with no
mechanical backing.

**Fix:** Add `PreToolUse` hooks on Bash that block `git merge` and `git push` targeting `main` or
`master` while an autopilot run is active in `.archflow/autopilot/*.yaml`, and block
`git checkout main && git merge` outside the ship ritual unless `current-phase.yaml` records an
explicit approval token. Add a `Stop` hook running `validate_archflow.py` that warns on schema drift.
Keep hooks under 2 seconds and fail open with a visible warning if the validator itself errors.

**Check:** During an autopilot run, `git push origin main` is refused with a clear message; the same
command outside autopilot with approval recorded is allowed.

---

# P2 — cost and inner-loop quality

## AF-34 Roughly half the agent corpus is generic filler
**Source:** AGENT

| Agent | Lines | Estimated cuttable |
|---|---|---|
| i18n-engineer | 393 | ~230 |
| devops-engineer | 286 | ~150 |
| qa-engineer | 295 | ~200 |
| ui-engineer | 219 | ~110 |
| pm-maestro-reviewer | 299 | ~75 |

The pattern is consistent: four near-identical platform cheat-sheets, textbook example tests,
Dockerfiles, GitHub Actions YAML, a 24-line Maestro command reference, and bullet lists reading
"write clean maintainable code". ui-engineer enumerates the same five platforms three separate times;
api-engineer states the contract rule three times.

The project-specific rules are the minority, and they are the parts that drift. Cutting the filler
makes the gates likelier to fire.

**Fix:** Delete the tutorial content, keeping short pointers. Preserve what is genuinely policy:
coverage thresholds, the Maestro-only constraint, key-naming conventions, directory layouts,
completion protocols.

**Check:** No agent exceeds roughly 150 lines, and every remaining section is Archflow-specific.

## AF-35 Startup injects instructions.md whole
**Source:** COMP P2-1

`hooks.json` runs `cat .archflow/instructions.md` on startup, resume and compact, which is 235 lines.
Phase files of 314 to 974 lines are loaded whole.

**Fix:** Split `instructions.md` into a roughly 60-line core covering the rules, the state-file map
and the current-phase pointer, injected by the hook, with per-phase detail loaded lazily by the
command that needs it. Measure tokens before and after for a startup plus one Phase 3 story and
record the numbers in the changelog.

**Check:** Startup injection is 80 lines or fewer, and `feature`, `groom` and `release ship` still
find their guidance.

## AF-36 Studio ships 6 MB into every install
**Source:** COMP P2-2 · **Status: won't fix — the premise was wrong**

The concern was that `plugin/server/` (2.3 MB) and `plugin/dist/` (3.7 MB) reach every user,
including those who never open Studio. That is true and it is not the dominant cost.

### What install actually does

Measured on a real machine, not inferred:

| Location | Size | What it is |
|---|---|---|
| `~/.claude/plugins/marketplaces/archflow` | **22 MB** | A full `git clone` of the whole repo, `.git` history included |
| `~/.claude/plugins/cache/archflow/archflow/2.2.0` | 6.6 MB | The extracted `./plugin` directory |

A marketplace entry is cloned as a git repository. The user therefore receives `docs/`, `metrics/`,
every retired tree and the entire history regardless of what the plugin manifest points at. Studio's
bytes arrive in that clone and are then extracted again into the cache: downloaded once, stored
twice.

Framework content — every agent, command, phase, schema and design system — is under 1 MB of it.

### Why splitting Studio out does not help

Moving Studio to a second plugin **in the same marketplace** saves nothing. The clone is repo-wide,
so both plugins land whatever the user installs. The core install still costs 22 MB and Studio's
bytes still hit the disk. The only saving is one cache entry not being extracted: roughly 6 MB of
local disk, and zero download.

Actually saving the download would require Studio to move to a **separate repository**, which is a
far larger change than this item described, and it separates a codebase that currently benefits from
living together.

Downloading the bundle on first `/archflow:studio` was the other option and is worse. It adds a
supply-chain surface — a pinned source, a checksum, an offline story, a prompt — immediately after
`SECURITY.md` was written to pin and document exactly that surface. Paying that to save a step is a
bad trade.

### One real cost, unrelated to size

The cache keeps every installed version. Five versions currently total 14 MB, of which 12.7 MB is
the two that contain Studio. That grows per release rather than being a one-time cost.

### What IS worth acting on

Not the megabytes. Studio living in the same repo is what couples the release trains: a framework
fix cannot ship without reshipping Studio, and a Studio fix cannot ship without a framework release.
The v2.1 schema bump made that concrete — see `docs/studio-v2.1-prompt.md`, where Studio needs a
coordinated release before 2.3.0 can go out.

That coupling is the real problem this item was gesturing at. It is a repository-boundary decision,
not a bundle-size one, and it should be raised as its own question rather than as an optimization.

## AF-37 Phase 3 dispatches engineers with the full transcript
**Source:** COMP P2-3

**Fix:** For each story, generate a token-budgeted `story-spec.md` of roughly 900 to 1,600 tokens
holding an immutable intent block, the relevant contract excerpt, acceptance criteria in
Given/When/Then, and the files the agent may touch. Dispatch the engineer context-free with the spec
and contract only. Add one cheap adversarial review pass per story before qa-engineer, capped at 10
findings with no minimum, with triage recorded in the story. Do not import BMAD's forced finding floor.

**Check:** A story runs end to end, the engineer's input is the spec rather than the transcript, and
the review log shows triage decisions.

## AF-38 groom cannot refine an in-release story
**Source:** COMP P2-4 · `plugin/commands/groom.md` notes the gap itself

**Fix:** `/archflow:groom <story-id>` on a story already in a release file edits it in place,
covering acceptance criteria, subtasks and gates, and re-runs gate derivation.

**Check:** Grooming an in-release story updates the release file, and status regresses to
`spec_ready` if gates changed.

## AF-39 api_contract_path is read but never written
**Source:** COMP P2-5

`phase-3-implementation.md` references it. `grep -n "api_contract_path" plugin/commands/init.md`
returns nothing, so the template never writes it.

**Fix:** `init` and `onboard` write it, defaulting to `docs/api-contract.md`. Phase 2.5 updates it.
The Phase 3 pre-flight fails loudly if the file is missing. Note that
`api-contract-architect.md` also hardcodes `docs/api-contract.md` and will ignore an override, so fix
that at the same time.

**Check:** A fresh init produces a `current-phase.yaml` containing `api_contract_path`.

---

# P3 — positioning and cleanup

## AF-40 Positioning, comparison, and name collision
**Source:** COMP P3-1

Add a "How Archflow compares" page under `docs/guides/` covering BMAD, Superpowers, Spec Kit and
OpenSpec, positioned as the delivery layer: releases, contract-first parallel build, acceptance
evidence, ship ritual, history, Studio. Add a compatibility note and, if cheap, an importer accepting
a BMAD `SPEC.md` or `prd.md` as Phase 1 input to `/archflow:feature`. Address the name collision with
`rafaelolsr/archflow` through consistent naming in package metadata, the README title and the landing
page title. Add Discord or Discussions links and a CONTRIBUTING pointer.

## AF-41 The portability claim is unshipped
**Source:** COMP P3-2 · `CLAUDE.md`

It calls `instructions.md` agent-neutral and mentions Cursor and Windsurf rules files that do not
ship. Either ship generators that point at `.archflow/instructions.md`, or drop the claim. Do not
leave it aspirational.

## AF-42 Repo tidy
**Source:** COMP P3-3

Remove `.gitignore` and `_config.yml` entries for files that do not exist. Move
`docs/archflow-skill-scaffolding-proposal.md` to `docs/proposals/` with a status header, or implement
it. Hide `--chat-policy forward` in `studio.md` until it is built.

Add while you are here: the working tree currently carries untracked `.DS_Store` files at the repo
root, `plugin/`, `plugin/skills/` and `plugin/skills/archflow/`. Add the pattern to `.gitignore`.

---

## Cross-cutting deliverables

- **`SECURITY.md`** at the repo root, covering the supply-chain pinning policy from AF-03, the
  untrusted-content convention from AF-04, the shell surface from AF-05, and how to report a
  vulnerability.
- **`docs/audits/remediation-<tier>.md`** after each tier, listing every item, the commits that
  closed it, the verification output, and anything left open with the reason.
- **Re-scan** on skills.sh once AF-03 through AF-05 land, so the badges reflect the current tree.
  Flag anything likely to be caught next time that was not in the original audit.

## Constraints carried from the source prompts

- Do not change user-facing behavior or phase structure beyond what a fix requires.
- Do not weaken or delete functionality to make a finding disappear.
- Preserve the existing prompt style and voice of the skill files.
- Socket currently passes on excessive autonomy. Keep it that way.
- Verify each finding still exists before changing anything; several were written against older
  commits. Report anything already resolved and skip it.

## Open decisions

1. **AF-12** — delete the root `agents/` tree, or promote it to a documented, CI-enforced mirror.
   The two source audits disagree.
2. **AF-27** — wire the three unreachable agents into phases, or move them to `optional/`. This gates
   the agent count in AF-17.
3. **AF-06** — for a reviewer, does a missing `design-system.yaml` stop the run or become a blocking
   finding? The instructions say stop; the new block says report.
4. **AF-21** — `docs/performance-report.md` or `docs/performance-improvements.md`. The phase files
   disagree with each other.
