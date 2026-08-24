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
- `pm-maestro-reviewer` - Acceptance testing via Maestro. Runs AFTER qa-engineer, validates acceptance criteria from the active release file (.archflow/releases/{active_release}.yaml) → docs/acceptance-reports/
- `ux-designer` - Design updates on specific screens. Updates `styled-dsl.yaml` file

**Phase 4: Quality & Optimization**
- `code-reviewer` - Code quality, security, best practices analysis + improvement reports
- `performance-optimizer` - Performance bottleneck identification and optimization
- `pm-maestro-reviewer` - Acceptance regression suite scoped to the active release's stories

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
- `/archflow:autopilot` — Run queued release stories unattended on one branch (blocker interview first,
  then silent; parks undecided stories; one report at the end)

## 🚀 Release Model (v2.0 — the outer loop)

Archflow has TWO axes. **Lifecycle phases (1–6)** are the inner process loop (strategy → design →
API → implement → quality → ship). **Releases** are the first-class OUTER loop — the shippable
increments a product is built in. (v2.0 renamed the old product "phases" to `releases:` and **retired
sprints**; a release is the story container.)

- **Files** (multi-file split keeps context bounded): `roadmap.yaml` is the small INDEX (meta, mode,
  epic LABELS, `releases[]` pipeline, `shipped[]` ledger); `backlog.yaml` holds unscheduled scope as
  STUBS; `releases/{slug}.yaml` holds one release's detailed stories; `releases/archive/` holds shipped
  releases; `history.yaml` is the shipped-story intent layer. A story lives in exactly ONE place
  (move, never copy). Schemas in `.archflow/schemas/{roadmap,release,backlog,history}-schema.yaml`.
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
- `.archflow/autopilot/{run-id}.yaml` - Unattended run ledger (only when `/archflow:autopilot` is used)

## 💡 Universal Critical Rules (Apply to ALL Phases)

### 🚨 API Contract Compliance (Phases 2.5-4)
- **API CONTRACT IS SACRED**: api-engineer AND ui-engineer MUST follow docs/api-contract.md exactly
- **ZERO TOLERANCE**: No deviations from contract specifications allowed
- **CONTRACT VERIFICATION**: Must confirm understanding before implementation
- **ui-engineer (real app only)**: When building the actual frontend app (`frontend/`), ui-engineer MUST read the API contract for every endpoint it integrates with. All TypeScript interfaces for API data MUST match the contract response schemas (field names, enum values, shapes). Pages MUST use real API hooks — no hardcoded mock data in page components. Mock data is only acceptable in HTML prototypes (`design-artifacts/`) and test files.
- **Prototype exception**: When building HTML prototypes/screens in `design-artifacts/`, static mock data is expected and correct.

### 🎨 SuperDesign MCP (Phase 2.25)
- **MCP SETUP**: Projects using Phase 2.25 require the SuperDesign MCP server: `npx -y github:AZidan/superdesign-mcp-claude-code`
- **OPTIONAL PHASE**: If SuperDesign MCP is unavailable, Phase 2.25 can be skipped (Phase 2 → 2.5 directly)
- **VISUAL APPROVAL**: Hi-fi screens must be approved before API architecture begins

### ✅ Acceptance Testing (Phases 3-4)
- **ACCEPTANCE GATE**: After qa-engineer completes, launch `pm-maestro-reviewer` to validate acceptance criteria from the active release file (`.archflow/releases/{active_release}.yaml`)
- **VERDICT REQUIRED**: Feature is not complete until pm-maestro-reviewer returns ACCEPTED verdict
- **REJECTION FLOW**: If REJECTED, fix blocking defects and re-run pm-maestro-reviewer — do not proceed
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

### 🗺️ Codemap Navigation (ALL Phases)
- **CODEMAP FIRST**: Always use `codemap find` before reading full files or using grep/glob
- **TARGETED READS**: Use `codemap show` to get file structure, then read only the relevant line ranges
- **INIT ON SETUP**: Run `codemap init .` when starting any new project, then `codemap watch . -q &`
- **VALIDATE BEFORE TRUSTING**: Run `codemap validate` before using cached line numbers after compaction
- **See `.claude/skills/codemap/SKILL.md`** for full usage guide

### 🔍 Subagent Codebase Navigation
- When launching **Explore** or **Plan** agents, ALWAYS include this in the prompt: "Use the `/codemap` skill to navigate the codebase structurally. Never read full files — use codemap indexes to find symbols, then read only the specific line ranges you need. At the end of your response, state how many files you read fully vs. how many you navigated via codemap line ranges (e.g. 'Codemap: 5 files via line ranges, 1 full read')."

### ⚡ Development Efficiency (ALL Phases)
- **AGENT TEAMS**: For Phase 3+ features, launch ui-engineer and api-engineer simultaneously when both have clear, independent scopes from the API contract
- **SEQUENTIAL DEPENDENCY**: qa-engineer runs AFTER feature agents complete, never in parallel. pm-maestro-reviewer runs AFTER qa-engineer
- **AGENT SCOPING**: Each agent works on ONE feature boundary. Never give an agent a cross-cutting concern
- **HANDOFF VIA FILES**: Agents communicate through files, not messages. api-engineer produces endpoints; ui-engineer consumes docs/api-contract.md and styled-dsl.yaml
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

**On Every New Session (ALWAYS do this first):**
```bash
# Start codemap watch if not already running
pgrep -f "codemap watch" > /dev/null || codemap watch . -q &
```

**Normal Operation (.archflow/current-phase.yaml exists):**
1. Start codemap watch (above)
2. Load current phase from `.archflow/current-phase.yaml`
3. Load detailed instructions from `.archflow/phases/phase-{current}.md`
4. Follow phase-specific execution steps
5. Complete approval gates before proceeding to next phase

**Project Setup (.archflow/current-phase.yaml missing):**
1. Start codemap watch (above)
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
