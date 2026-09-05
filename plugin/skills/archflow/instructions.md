# Archflow — Phase-Based Development Instructions
Dynamic phase-based instruction loading for token-efficient development.

## 🎯 Core Agents (Always Available)

**Phase 1: Strategy & Planning**
- `product-strategist` - Business strategy, personas, KPIs → .archflow/project-context.md
- `feature-planner` - Backlog stubs + epic labels (Mode A) → .archflow/backlog.yaml + roadmap.yaml; promotes stubs into release files (Mode B)

**Phase 2: Design**
- `ux-designer` - User flows, design systems, themes, wireframes → design-artifacts/
- `dsl-generator` - Component specifications with styling → design-artifacts/styled-dsl.yaml

**Phase 2.25: High-Fidelity Design**
- SuperDesign MCP - Hi-fi screen generation from styled-dsl.yaml → design-artifacts/hifi-screens/

**Phase 2.5: API Architecture**
- `api-contract-architect` - API contracts from wireframes → docs/api-contract.md (single source of truth)

**Phase 3: Implementation**
- `ui-engineer` - All frontend (React, React Native, SwiftUI, Jetpack Compose) + integration with backend APIs. Also updates screens after ux-designer changes `styled-dsl.yaml`
- `api-engineer` - NestJS/PostgreSQL backends, MUST follow docs/api-contract.md exactly (zero tolerance)
- `qa-engineer` - Comprehensive testing (unit, integration, e2e) across all platforms. Runs AFTER feature agents complete
- `pm-reviewer` - Acceptance testing with the project's existing e2e tooling; asks before
  installing any tool. Runs AFTER qa-engineer, validates acceptance criteria from the active release file (.archflow/releases/{active_release}.yaml) → docs/acceptance-reports/
- `ux-designer` - Design updates on specific screens. Updates `styled-dsl.yaml` file

**Phase 4: Quality & Optimization**
- `code-reviewer` - Code quality, security, best practices analysis + improvement reports
- `performance-optimizer` - Performance bottleneck identification and optimization
- `pm-reviewer` - Acceptance regression suite scoped to the active release's stories

**Phase 5: Launch & Operations**
- `devops-engineer` - CI/CD pipelines, deployment infrastructure, app store preparation
- `post-launch-analyst` - Analytics implementation, user insights, performance monitoring

**Phase 6: Enhancement (On-Demand)**
- `i18n-engineer` - Internationalization for web/iOS/Android platforms

## 📌 Available Commands (Archflow)
- `/archflow:status` — Show current project status and available commands
- `/archflow:init` — Initialize Archflow in a new project (creates `.archflow/` state files, sets Phase 1, mode: quick)
- `/archflow:onboard` — Onboard existing codebase (interactive wizard: audit, import context, backfill artifacts, set phase + mode)
- `/archflow:migrate` — Migrate a v1.0 project to schema v2.0 (releases replace phases, sprints retired, multi-file split)
- `/archflow:mode [quick|full]` — Show or switch the ceremony mode
- `/archflow:release [new|start|ship]` — Inspect / manage releases (status, create, start, ship)
- `/archflow:setup-mcp` — Configure an MCP server for external tools (Jira, Notion, Linear, GitHub, SuperDesign, etc.)
- `/archflow:groom [story-id]` — Detail a backlog stub into a `ready` story (acceptance criteria, subtasks, gates); stays in the backlog
- `/archflow:feature` — Add a story to the backlog or the active release and start the git development workflow
- `/archflow:design [pick|list|name|story-id]` — The project's design system (chosen once, followed by
  every UI agent), and per-story screen design that clears a story's `needs_design` gate
- `/archflow:contract [story-id]` — The release's API contract architecture, and per-story endpoint
  specs that clear a story's `needs_contract` gate
- `/archflow:autopilot` — Run queued release stories unattended on one branch (blocker interview first,
  then silent; parks undecided stories; one report at the end)
- `/archflow:doctor [--validate]` — Check the environment and project state: what Archflow needs,
  what is missing, and the exact command to fix each gap. Report only; installs nothing
- `/archflow:studio [stop|status|port <n>]` — Start (or stop) Archflow Studio, a local web workspace
  over the same `.archflow/` files; runs onboarding and migration from the UI (beta)

## 🚀 Release Model (v2.0 — the outer loop)

Archflow has TWO axes. **Lifecycle phases (1–6)** are the inner process loop (strategy → design →
API → implement → quality → ship). **Releases** are the first-class OUTER loop — the shippable
increments a product is built in. (v2.0 renamed the old product "phases" to `releases:` and **retired
sprints**; a release is the story container.)

- **Files** (multi-file split keeps context bounded): `roadmap.yaml` is the small INDEX (meta, mode,
  epic LABELS, `releases[]` pipeline, `shipped[]` ledger); `backlog.yaml` holds unscheduled scope as
  STUBS; `releases/{slug}.yaml` holds one release's detailed stories; `releases/archive/` holds shipped
  releases; `history.yaml` is the shipped-story intent layer. A story lives in exactly ONE place
  (move, never copy). Schemas in `.archflow/schemas/{roadmap,release,backlog,history,current-phase}-schema.yaml`.
- **Loop:** Strategy (once) → **create + start a release** → inner phases 2–5 scoped to it → **ship
  ritual** (mark released, tag, archive, append history, roll off the index) → prompt for the next
  release. At most ONE release is `in_progress`; many may be `planning`/`ready` concurrently.
- **Readiness pipeline (per story):** `backlog → spec_ready → design_ready → contract_ready → ready →
  in_progress → review → done`, with per-story `gates {needs_design, needs_contract}`. Design/contract
  gates run just-in-time, one step ahead of build. One side status: `parked` — stopped on an open
  question only the human can answer (written by `/archflow:autopilot`; blocks the ship by default).
- **Modes:** `mode: quick | full` (in `roadmap.yaml` + `current-phase.yaml`). quick = single implicit
  release, gates auto-satisfied, one lane (default for `/archflow:init`). full = explicit release
  pipeline + enforced advisory gates + role lanes. Switch with `/archflow:mode`.

## 🌐 Project Types
The framework detects and adapts to project type: `fullstack`, `frontend_only`, `backend_only`, `mobile`.
- Stored in `.archflow/current-phase.yaml` as `project_type`
- Phases, agents, and audit checks are filtered by project type
- Release/backlog story fields are tailored to project type (backend = endpoints/services, frontend = pages/components)
- Set automatically by `/archflow:onboard` or can be set manually in `.archflow/current-phase.yaml`

## 🔀 Git Workflow
All feature development follows `.archflow/workflow.md` branching strategy:
- Feature branches from main
- Task branches from feature
- Subtask branches from task
- Merge only after explicit user approval
- Use `/archflow:feature` to create feature branches and track tasks in `.archflow/current-feature.yaml`

## 🔄 Dynamic Phase Loading

**Current Phase Detection:**
```yaml
# Read .archflow/current-phase.yaml to determine active phase
phase: 1  # Current phase number
phase_file: ".archflow/phases/phase-1-strategy.md"  # Load this file for detailed instructions
```

**Phase Instruction Loading:**
```bash
# Check for existing phase tracker
if [[ -f ".archflow/current-phase.yaml" ]]; then
  # Normal operation - use existing tracker
  Current Phase: .archflow/current-phase.yaml → phase_file
  Detailed Instructions: .archflow/phases/phase-{current}-{name}.md
else
  # Project setup needed - load setup system
  Setup Required: .archflow/phases/phase-setup.md → detect and initialize phase
fi
```

## 📋 Universal Context Files (Always Required)
- `.archflow/project-context.md` - Business goals, tech stack, architecture decisions
- `.archflow/roadmap.yaml` - v2.0 INDEX: mode, epic labels, `releases[]` pipeline, `shipped[]` ledger
- `.archflow/backlog.yaml` - Unscheduled scope as stubs
- `.archflow/releases/{slug}.yaml` - Detailed stories for a release (source of truth for story status)
- `.archflow/history.yaml` - Shipped-story intent layer (loaded only on lookup)
- `.archflow/current-feature.yaml` - Active development scope (git task/subtask tracking)
- `.archflow/current-phase.yaml` - Phase + mode + active_release tracker (PROJECT-SCOPED, auto-created)
- `.archflow/design-system.yaml` - The project's chosen design system (PROJECT-SCOPED; absent only for `backend_only`). Names the file to follow: `.archflow/design-systems/{design_system}.md`
- `.archflow/autopilot/{run-id}.yaml` - Unattended run ledger (only when `/archflow:autopilot` is used)

## 💡 Universal Critical Rules (Apply to ALL Phases)

### 🚨 API Contract Compliance (Phases 2.5-4)
- **API CONTRACT IS SACRED**: api-engineer AND ui-engineer MUST follow docs/api-contract.md exactly
- **ZERO TOLERANCE**: No deviations from contract specifications allowed
- **CONTRACT VERIFICATION**: Must confirm understanding before implementation
- **ui-engineer (real app only)**: When building the actual frontend app (`frontend/`), ui-engineer MUST read the API contract for every endpoint it integrates with. All TypeScript interfaces for API data MUST match the contract response schemas (field names, enum values, shapes). Pages MUST use real API hooks — no hardcoded mock data in page components. Mock data is only acceptable in HTML prototypes (`design-artifacts/`) and test files.
- **Prototype exception**: When building HTML prototypes/screens in `design-artifacts/`, static mock data is expected and correct.

### 🎨 SuperDesign MCP (Phase 2.25)
- **MCP SETUP**: Projects using Phase 2.25 require the SuperDesign MCP server:
  `npx -y github:AZidan/superdesign-mcp-claude-code#1bd2d1766b1e4d9a5828cd553da0f4e67e5a3ffe`
  The `#<sha>` is an immutable pin, not decoration — an unpinned `github:` ref runs whatever is on
  `main` at install time. Never replace it with a branch name. See SECURITY.md
- **ASK BEFORE INSTALLING**: Never install this (or any other tool) silently. Say what it is and
  where it comes from, and let the user decide
- **OPTIONAL PHASE**: If SuperDesign MCP is unavailable, Phase 2.25 can be skipped (Phase 2 → 2.5 directly)
- **VISUAL APPROVAL**: Hi-fi screens must be approved before API architecture begins

### 🎨 Design System Compliance (Phases 2-4)
- **CHOSEN ONCE**: The design system is picked at `/archflow:init` or `/archflow:onboard` and stored in `.archflow/design-system.yaml`. It is NOT a per-feature decision. Change it only via `/archflow:design`
- **READ BEFORE ANY UI OUTPUT**: Every agent that produces wireframes, screens, UI code, or reviews UI MUST read `.archflow/design-system.yaml`, then read and follow `.archflow/design-systems/{design_system}.md`, before producing output
- **VOCABULARY IS BINDING**: Component names in wireframes, `styled-dsl.yaml`, and every handoff file come from that file's `## Component vocabulary` table. Never a generic term where a system name exists
- **LIBRARY IS BINDING**: Import from the `library` named in `design-system.yaml`. A second UI kit in the dependency list is a violation
- **ANTI-PATTERNS ARE A GATE**: `qa-engineer` and `code-reviewer` treat the `## Anti-patterns` section as a mandatory checklist and FAIL the review on any violation, reporting file, line, and the vocabulary term that should have been used
- **GAPS ARE LOGGED**: A component the system genuinely lacks is composed from its primitives and recorded in `design-artifacts/component-gaps.md` — never silently invented
- **MISSING FILE = STOP**: If `.archflow/design-system.yaml` is absent on a project with a UI, stop and run `/archflow:design` before any UI work

### 🚦 Readiness Gates (the two just-in-time gates)
- **EVERY GATE HAS A VERB**: `gates.needs_design` is cleared by `/archflow:design {story-id}`;
  `gates.needs_contract` is cleared by `/archflow:contract {story-id}`. Both run just-in-time, one
  step ahead of that story's build
- **THE PHASE FILE OWNS THE TRANSITION**: the commands are entry points, not second definitions.
  `phase-2-design.md` § "Per-story design gate" and `phase-2.5-api-architecture.md` § "Per-story
  contract gate" define what each writes and how the status advances. Never restate them elsewhere
- **FOUNDATION vs PER-STORY**: both commands own both halves. Bare `/archflow:design` is the project
  design system; bare `/archflow:contract` is the release contract architecture. A story-id argument
  selects the per-story gate
- **HUMAN ACCEPTS**: the agent produces the artifact, the user accepts it. Neither command advances a
  status before that

### 🧱 Technology Agnosticism (ALL Phases)
- **AGENTS CARRY NO STACK**: no agent names a framework, database, ORM, styling library, test runner
  or CI system as *what to use*. They read `stack:` from `.archflow/current-phase.yaml` and work in
  what it names. Naming candidates to *detect among* is correct; naming one to impose is not
- **NULL MEANS ASK**: an unset field is a question, never a default. The agent states what it found
  in the repo, names the realistic candidates, and asks. It never assumes and never installs
- **THE REPO OUTRANKS THE FIELD ON FACT**: `stack:` records intent; the manifests record reality.
  When they disagree, say so rather than silently following either
- **PROFILES ARE SEEDS**: `.archflow/stacks/*.yaml` are starting points offered by `/archflow:init`,
  never fallbacks an agent inherits when the field is empty
- **NEVER INSTALL TO CLOSE A GAP**: a missing framework, runtime, simulator or test runner is
  named and asked about, never installed to make the task proceed

### 🔒 Mechanical Safety Envelope (enforced by hooks, not prompts)
Two hooks back the rules that cannot be undone by an apology. They are a floor under the prompt
rules, never a replacement for them.

- **`PreToolUse` on Bash — `guard-git.mjs`**: **inside an Archflow project only** (a directory with
  an `.archflow/`), blocks a force-push to `main`/`master`, and during an ACTIVE
  `/archflow:autopilot` run also blocks pushing to, checking out, or merging into those branches.
  Elsewhere it exits immediately: installing a framework is not consent to a global git policy.
  Outside a run it blocks nothing but the force-push, because the approval gates are the control
  there and a guard that fights ordinary merges gets switched off
- **`Stop` — `check-state.mjs`**: runs the schema validator and warns when a session leaves
  `.archflow/` state drifted. ADVISORY: it prints and exits 0, because a story is often half-written
  when a turn ends
- **BOTH FAIL OPEN**: a guard that breaks the session when its own parsing is wrong is worse than the
  risk it removes. Any internal error allows the command and prints a warning
- **A BLOCK IS NOT A PUZZLE**: when the guard blocks, it names the run and the ledger file. Resolve
  it by finishing the run, or by setting the run's `status` to `finished`/`aborted` if it is
  genuinely over. Never work around it

### ✅ Acceptance Testing (Phases 3-4)
- **ACCEPTANCE GATE**: After qa-engineer completes, launch `pm-reviewer` to validate acceptance criteria from the active release file (`.archflow/releases/{active_release}.yaml`)
- **VERDICT REQUIRED**: Feature is not complete until pm-reviewer returns ACCEPTED verdict
- **REJECTION FLOW**: If REJECTED, fix blocking defects and re-run pm-reviewer — do not proceed
- **REPORTS**: Acceptance reports saved to `docs/acceptance-reports/{story-id}-review.md`

### ⚠️ Mandatory Approval Gates (ALL Phases)
- **USER APPROVAL REQUIRED**: Stop and wait for explicit user approval after EVERY phase
- **NO PHASE SKIPPING**: Complete every phase in exact sequence
- **DEMO REQUIRED**: Working features must be demonstrated before approval
- **THE ONE EXCEPTION — `/archflow:autopilot`**: an unattended run pre-authorizes these gates in a
  single up-front interview. It relaxes *synchronous* review, never review itself: everything lands
  on one branch, and **merging to `main` stays the user's**. An undecided question parks the story
  (`status: parked`) instead of being guessed, and a parked story blocks the release by default.
  Nothing else in the framework may skip an approval gate.

### 🎯 Agent Selection Rules (ALL Phases)
- **SPECIALIZED AGENTS ONLY**: Always use sub-agents when possible. Never use `general-purpose` agent
- **PHASE-APPROPRIATE AGENTS**: Only use agents listed for current phase
- **MANDATORY FILE NAMING**: Follow exact output naming conventions

### 🗺️ Codemap Navigation (ALL Phases — optional, for token optimization)
Codemap is a token optimization. It is RECOMMENDED, not required: Archflow works without it, and
every rule below degrades to ordinary Glob/Grep/Read when it is absent.

- **CHECK FIRST**: `command -v codemap >/dev/null 2>&1` before invoking it. If it is not installed,
  use Glob/Grep and targeted reads instead, and do not prompt the user about it mid-story
- **PREFER CODEMAP WHEN INSTALLED**: `codemap find` before reading full files or using grep/glob
- **TARGETED READS**: Use `codemap show` to get file structure, then read only the relevant line ranges
- **INIT ON SETUP**: When installed, run `codemap init .` on a new project. `codemap watch . -q &` is
  a long-lived background process — start it only with the user's agreement, and tell them
  `pkill -f "codemap watch"` stops it
- **VALIDATE BEFORE TRUSTING**: Run `codemap validate` before using cached line numbers after compaction
- **See `.claude/skills/codemap/SKILL.md`** for full usage guide

### 🔍 Subagent Codebase Navigation
- When launching **Explore** or **Plan** agents, ALWAYS include this in the prompt: "Use the `/codemap` skill to navigate the codebase structurally. Never read full files — use codemap indexes to find symbols, then read only the specific line ranges you need. At the end of your response, state how many files you read fully vs. how many you navigated via codemap line ranges (e.g. 'Codemap: 5 files via line ranges, 1 full read')."

### ⚡ Development Efficiency (ALL Phases)
- **AGENT TEAMS**: For Phase 3+ features, launch ui-engineer and api-engineer simultaneously when both have clear, independent scopes from the API contract
- **SEQUENTIAL DEPENDENCY**: qa-engineer runs AFTER feature agents complete, never in parallel. pm-reviewer runs AFTER qa-engineer
- **AGENT SCOPING**: Each agent works on ONE feature boundary. Never give an agent a cross-cutting concern
- **HANDOFF VIA FILES**: Agents communicate through files, not messages. api-engineer produces endpoints; ui-engineer consumes docs/api-contract.md and styled-dsl.yaml
- **DESIGN SYSTEM IN THE PROMPT, NOT THE CONTEXT**: Every subagent that touches UI gets the path written into its dispatch prompt verbatim — `Design system: read .archflow/design-system.yaml, then read and follow .archflow/design-systems/{design_system}.md before producing any output.` Never rely on the parent's context carrying it
- **CONFLICT PREVENTION**: Only ONE agent may modify a given file. If two agents need the same file, sequence them
- **TOKEN EFFICIENCY**: Use codemap find + targeted line reads instead of full file scans
- **ONE STORY AT A TIME**: In Phase 3, complete one story's full cycle (build → test → accept → approve → merge) before the next. Only one story `in_progress` in the active release at a time.

## 🔄 Phase Navigation System

### Phase Transition Workflow
```yaml
Current Phase Complete:
  1. Validate all completion criteria met
  2. Present outputs to user
  3. Wait for explicit user approval
  4. Update .archflow/current-phase.yaml to next phase
  5. Load .archflow/phases/phase-{next}.md for next instructions

Phase Files Available:
  - .archflow/phases/phase-onboarding.md    # For existing codebases (via /archflow:onboard)
  - .archflow/phases/phase-1-strategy.md
  - .archflow/phases/phase-2-design.md
  - .archflow/phases/phase-2.25-hifi-design.md
  - .archflow/phases/phase-2.5-api-architecture.md
  - .archflow/phases/phase-3-implementation.md
  - .archflow/phases/phase-4-quality.md
  - .archflow/phases/phase-5-launch.md
  - .archflow/phases/phase-6-enhancement.md
```

### Project Setup (When Needed)
For projects without `.archflow/current-phase.yaml`:
- **Load Setup System**: `.archflow/phases/phase-setup.md`
- **Phase Detection**: Automatic inference from project state
- **Initialization**: Create phase tracker and load instructions

## 🚀 Getting Started

**On Every New Session:**
```bash
# Optional token optimization. Skips silently when codemap is not installed.
# The watcher is a long-lived background process — only start it if the user has agreed to it.
command -v codemap >/dev/null 2>&1 && pgrep -f "codemap watch" > /dev/null || true
```

**Normal Operation (.archflow/current-phase.yaml exists):**
1. Start codemap watch if installed and agreed (above)
2. Load current phase from `.archflow/current-phase.yaml`
3. Load detailed instructions from `.archflow/phases/phase-{current}.md`
4. Follow phase-specific execution steps
5. Complete approval gates before proceeding to next phase

**Project Setup (.archflow/current-phase.yaml missing):**
1. Start codemap watch if installed and agreed (above)
2. Load setup system from `.archflow/phases/phase-setup.md`
3. Auto-detect phase from project state or start Phase 1
4. Create `.archflow/current-phase.yaml` and continue with normal operation

**File Structure:**
- `.archflow/current-phase.yaml` - Project phase state (auto-created if missing)
- `.archflow/phases/phase-setup.md` - Setup system (loaded only when needed)
- `.archflow/phases/phase-*.md` - Phase-specific instructions (loaded based on current phase)

---
**📍 Current Phase Instructions: Load .archflow/current-phase.yaml → phase_file**
- You always commit ONLY the changes you did not all the files.
