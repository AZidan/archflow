# /archflow onboard — Existing Codebase Onboarding Wizard

Onboard an existing codebase to the phase-based development framework. Three-phase orchestration: gather user input upfront, dispatch specialized agents for deep analysis, then synthesize and present results.

## Usage
```
/archflow onboard          → Start or resume the onboarding wizard
```

## Prerequisites
- Must be run from the project's root directory
- The project should have existing source code (otherwise use Phase 1 setup normally)

## Detailed Rules
Load `.archflow/phases/phase-onboarding.md` for audit logic, project type detection, extraction rules, structured output schemas, agent prompt templates, and synthesis rules.

---

## Entry Check — ALWAYS RUN FIRST

**Before writing any response**, execute these steps in order using your tools:

### Step E1: Check for in-progress wizard
```bash
# Tool call: check if .onboard-progress.yaml exists
```
- EXISTS → skip to **Resume Check** section below
- MISSING → continue to Step E2

### Step E2: Read roadmap.yaml NOW (mandatory tool call)

**Use the Read tool** to read `.archflow/roadmap.yaml`. Do this immediately — do not skip or defer.

- If the file does not exist → continue to Step E3 (new onboarding)
- If it exists → run Step E2a before doing anything else

### Step E2a: Validate roadmap.yaml format (inline — no external file needed)

Parse the content you just read and check every rule below. Collect **all** violations.

**Top-level:** `project`, `project_type`, `epics`, `phases` must all be present. `project_type` must be `fullstack|frontend_only|backend_only|mobile`.

**Epics:** each must have `id` (matches `^E[0-9]+$`), `name`, `scope` (`backend|frontend|mobile|both|unknown`), `stories`.

**Stories:** each must have `id` (matches `^S[0-9]+-[0-9]+$`, epic-number prefix matches parent epic), `title`, `priority` (`Critical|High|Medium|Low`), `status` (`backlog|in_progress|review|done`), `assigned`, `description`, `acceptance_criteria`, `subtasks`.
- `acceptance_criteria` items must be objects with `text` + `met` (boolean). Plain strings = violation.
- `subtasks` items must be objects with `text` + `completed` (boolean). Plain strings = violation.

**Sprints:** each must have `id` (matches `^sprint-[0-9]+$`), `name`, `status` (`backlog|in_progress|review|done`), `goal`, `stories`.
- `stories` must be an array of **strings** (ID references). Embedded objects = violation.
- Every referenced story ID must exist under an epic. Missing = violation.
- No story ID may appear in more than one sprint. Duplicates = violation.

### Step E3: Check onboarded status
```bash
# Tool call: read .archflow/current-phase.yaml, check onboarded field
```
- `onboarded: true` AND roadmap has **no violations** → show status summary (see below), then stop
- `onboarded: true` AND roadmap has **violations** → show violations report (see below), then stop
- Not onboarded → proceed to **Step 0** (new onboarding)

---

## Already Onboarded — No Violations

```
This project is already onboarded. ✅

  [show current status: project type, phase, artifacts, gaps]

Run /archflow feature to kick off work, or tell me what you'd like to do.
```

---

## Already Onboarded — Violations Found

```
This project is already onboarded, but roadmap.yaml has [N] format violations
that are incompatible with the canonical schema.

  ⚠ [YAML path] — [rule broken]
     found: [found value]
  ⚠ ...

Fix these automatically? [Yes / Show me each one / Skip]
```

- **Yes** — auto-fix all violations (see fix rules below), write corrected `roadmap.yaml`, report what changed, then show status summary
- **Show me each one** — walk through each violation interactively, apply or skip fixes one at a time
- **Skip** — exit without changes

**Auto-fix rules:**
- Plain-string `acceptance_criteria` item → `{text: "<string>", met: false}`
- Plain-string `subtasks` item → `{text: "<string>", completed: false}`
- Embedded sprint story object → replace with its `id` string
- Invalid `status` value → map: `planned`→`backlog`, `completed`→`done`, `wip`→`in_progress`
- Missing epic `scope` → infer from stories or default to `unknown`
- Sprint references non-existent story ID → remove from sprint, warn

---

## Resume Check

Before starting a new wizard, check for interrupted progress:
```bash
if [[ -f ".onboard-progress.yaml" ]]; then
  # Read wizard_phase and agent_outputs
  # Phase A: re-ask from last incomplete step
  # Phase B: re-dispatch incomplete agents (skip completed ones)
  # Phase C: re-run synthesis
fi
```

If `.onboard-progress.yaml` exists, read it and resume from the saved `wizard_phase`. Present what was already completed.

---

### Step 0: Verify Git

1. Check: Is this a git repository? (`git rev-parse --is-inside-work-tree`)
   - If YES: Continue
   - If NO: Ask user "Initialize git? [Yes / No]"
     - Yes: `git init && git add . && git commit -m "chore: initial commit before archflow onboarding"`
     - No: WARN and continue

2. After onboarding creates `.archflow/` files (end of Step C5), commit:
   ```bash
   git add .archflow/
   git commit -m "chore: onboard to archflow (Phase [N])"
   ```

---

## PHASE A: Interactive Collection (main agent, user present)

All user input gathered in one pass. No heavy analysis, no agent dispatch.

### STEP A1: Project Detection

**Actions:**
1. Scan directory for code indicators:
   - `package.json` (read dependencies for framework detection)
   - `src/`, `backend/`, `frontend/`, `ios/`, `android/` directories
   - Config files: `next.config.*`, `vite.config.*`, `nest-cli.json`, `angular.json`
   - Database: `prisma/`, `typeorm`, `sequelize` in deps, `*.entity.ts`
   - CI/CD: `.github/workflows/`, `.gitlab-ci.yml`, `Dockerfile`
2. Detect tech stack from dependencies and file patterns
3. Detect project type using rules from `.archflow/phases/phase-onboarding.md`:
   - `fullstack` | `frontend_only` | `backend_only` | `mobile`
4. Run `codemap init .` and `codemap stats` for codebase metrics

**Present to user:**
```
STEP A1: PROJECT DETECTION

Detected project:
 - Type: [Fullstack / Frontend Only / Backend Only / Mobile]
 - Frontend: [framework] ([N] components in [path])
 - Backend: [framework] ([N] modules in [path])
 - Database: [type] ([ORM/schema tool])
 - Tests: [framework] ([N] test files)
 - CI/CD: [tool] ([N] workflows)

Is this correct?
```

Wait for confirmation before proceeding.

---

### STEP A2: Context Source Selection

**Ask the user:**
```
STEP A2: CONTEXT SOURCE SELECTION

Where does your project strategy and roadmap live?
```

Present options:
- **Jira** — Fetch epics/stories by link
- **Notion** — Fetch pages by link
- **Linear** — Fetch issues by link
- **GitHub Issues** — Fetch issues by link
- **Google Drive** — Fetch docs by link
- **Trello** — Fetch cards by link
- **Slack** — Fetch context from threads
- **Confluence** — Fetch documentation by link
- **Local files** — Point to existing docs
- **I'll describe it** — Answer questions conversationally
- **Skip** — No context import

**For external tools (Jira, Notion, Linear, etc.):**

1. Check if the tool's MCP is configured:
   ```bash
   claude mcp list
   ```
2. If NOT configured:
   - Run `/archflow setup-mcp [tool]` inline (load `skills/archflow/commands/setup-mcp.md`)
   - If MCP setup requires restart: save progress to `.onboard-progress.yaml`, instruct user to restart Claude Code, then run `/archflow onboard` again
3. Once MCP is available, collect links:
   ```
   Paste the links to the epics/stories you want to import:
   (one per line, press Enter twice when done)
   ```
4. **THEN explicitly prompt for additional documentation:**
   ```
   Paste any additional documentation links that describe requirements,
   architecture, or design decisions (Confluence pages, PRDs, wiki pages,
   Google Docs). The more links, the better the analysis.
   (one per line, press Enter twice when done, or type "skip")
   ```

**For "Local files":**
```
Point me to the files (paths or paste content):
```

**For "I'll describe it":**
Record: `import_source: "conversational"`. Conversational input will be collected in Step A4.

Do NOT fetch or process any links during Phase A. Just collect them.

---

### STEP A3: Design & API Preferences

**For fullstack / frontend_only / mobile:**
```
STEP A3: DESIGN & API PREFERENCES

Extract design system from existing components?
(Scans for Tailwind config, CSS variables, theme files, component patterns)
[Yes / Skip]
```

**For ALL project types with API interaction:**
```
Generate API contract from existing code? Or point to existing spec?
```
Options:
- **Generate** — Reverse-engineer from existing routes/API calls
- **Point to file** — User provides path to existing OpenAPI/Swagger spec
- **Skip** — No API contract generation

Clarify extraction mode by project type:
- `fullstack` / `backend_only`: "Will scan server-side routes, controllers, and decorators"
- `frontend_only` / `mobile`: "Will scan client-side API calls, service layers, and TypeScript interfaces"

**Also ask:**
```
Any corrections to the detected tech stack? [Confirm / Edit]
```

---

### STEP A4: Roadmap Preferences

```
STEP A4: ROADMAP PREFERENCES

Any vision for the product beyond what's in [selected source]?
Planned features not yet tracked?
```

Record response as `user_vision_notes`.

```
Any features to explicitly mark as completed or deprioritized?
(List feature names, or type "none")
```

Record as `completed_features_override`.

**If import_source is "conversational":** Ask the structured questions here:
1. "What does your application do?"
2. "Who are the target users?"
3. "What are the main features? List them briefly."
4. "Which features are complete / in-progress / planned?"
5. "Any KPIs or goals you're tracking?"

Record all answers in `user_vision_notes`.

---

### STEP A5: Confirmation & Handoff

**Present summary of everything collected:**
```
STEP A5: CONFIRMATION

Project: [Type] — [Tech Stack]
Import source: [source] ([N] links + [M] doc links)
Design extraction: [Yes/No]
API contract: [Generate/Existing/Skip]
Vision notes: [summary]
Feature overrides: [list or none]

This analysis will take several minutes. Specialized agents will
deeply analyze your codebase, imported documents, and generate
production-quality artifacts. You can work on other tasks and
come back to check results.

Proceed? [Yes / Edit]
```

If "Edit": go back to the relevant step.

**Save all state to `.onboard-progress.yaml`** using the schema from `phase-onboarding.md`.

---

## PHASE B: Autonomous Agent Dispatch (main agent orchestrates, user can leave)

Load the execution dependency graph and agent filtering table from `.archflow/phases/phase-onboarding.md`.

### Layer 1: No Dependencies (dispatch all in parallel)

**1a. Codebase Audit (inline — NOT a subagent)**
- Run the full audit checklist from `phase-onboarding.md`, filtered by `project_type`
- For each audit check: scan for listed file patterns, record found/missing
- **Format validation**: if `.archflow/roadmap.yaml` is found, run the full Roadmap Format Validation defined in `phase-onboarding.md` — check every rule (top-level structure, epic/story fields, patterns, enum values, acceptance_criteria/subtasks item shapes, sprint ID format, sprint story references as strings, referential integrity, no duplicate story references across sprints). Record `format_valid` and all `format_violations` in the audit report.
- Special: if swagger/openapi found, record path for `api_contract_path`
- Count source files, components, routes, modules, test files
- Output: `.onboard-audit-report.yaml` (use structured schema from `phase-onboarding.md`)

**1b. Doc Deep-Dive (Task subagent, `run_in_background: true`)**
- Skip if `import_source` is "skip" or "conversational" with no links
- Use prompt template from `phase-onboarding.md` → "Doc Deep-Dive Agent"
- Subagent type: `general-purpose`
- Output: `.onboard-imported-context.md`

**1c. Design Extraction (Task subagent, `run_in_background: true`)**
- Skip if `extract_design_system` is false OR project type is `backend_only`
- Use prompt template from `phase-onboarding.md` → "Design Extraction Agent"
- Subagent type: `Explore`
- Output: `design-artifacts/theme.yaml` + `design-artifacts/extracted-components.yaml`

**1d. Route/API Extraction (Task subagent, `run_in_background: true`)**
- Skip if `generate_api_contract` is false
- Choose server-side or client-side prompt based on project type
- Use prompt template from `phase-onboarding.md` → "Route/API Extraction Agent"
- Subagent type: `Explore`
- Output: `.onboard-extracted-routes.yaml`

**After dispatching Layer 1:** Update `.onboard-progress.yaml` with agent statuses. Wait for all Layer 1 agents to complete before proceeding.

### Layer 2: Depends on Layer 1 (dispatch in parallel where possible)

**2a. product-strategist (Task subagent)**
- Waits for: Codebase Audit + Doc Deep-Dive
- Use prompt template from `phase-onboarding.md` → "product-strategist (Onboarding Mode)"
- Subagent type: `product-strategist`
- Output: `.archflow/project-context.md` + `.onboard-roadmap-draft.yaml`

**2b. ux-designer (Task subagent)**
- Skip if project type is `backend_only`
- Waits for: Design Extraction + product-strategist (needs project-context.md)
- Use prompt template from `phase-onboarding.md` → "ux-designer (Onboarding Mode)"
- Subagent type: `ux-designer`
- Output: `design-artifacts/theme.yaml` (refined) + `design-artifacts/user-flows.md` + `design-artifacts/wireframes/`

**2c. api-contract-architect (Task subagent)**
- Skip if `generate_api_contract` is false
- Skip if existing spec was pointed to (use as-is)
- Waits for: Route/API Extraction + product-strategist (needs project-context.md)
- Use prompt template from `phase-onboarding.md` → "api-contract-architect (Onboarding Mode)"
- Subagent type: `api-contract-architect`
- Output: `docs/api-contract.md`

**Note:** product-strategist runs first in Layer 2. ux-designer and api-contract-architect both depend on its output. If product-strategist completes, dispatch ux-designer and api-contract-architect in parallel.

**After Layer 2:** Update `.onboard-progress.yaml`. Wait for all to complete.

### Layer 3: Depends on Layer 2 (dispatch in parallel)

**3a. dsl-generator (Task subagent)**
- Skip if project type is `backend_only`
- Waits for: ux-designer
- Use prompt template from `phase-onboarding.md` → "dsl-generator (Onboarding Mode)"
- Subagent type: `dsl-generator`
- Output: `design-artifacts/styled-dsl.yaml`

**3b. feature-planner (Task subagent)**
- Waits for: product-strategist
- Use prompt template from `phase-onboarding.md` → "feature-planner (Onboarding Mode)"
- Subagent type: `feature-planner`
- Output: `.archflow/roadmap.yaml`

**After Layer 3:** Update `.onboard-progress.yaml`. All agents complete. Proceed to Phase C.

---

## PHASE C: Synthesis & Presentation (main agent, user returns)

### STEP C1: Roadmap Reconciliation

Read `.archflow/roadmap.yaml` + `.onboard-audit-report.yaml` + user overrides from `.onboard-progress.yaml`:
- If feature-planner marks `backlog` but audit shows code exists → upgrade to `in_progress` or `done`
- If user explicitly overrode a story status → use user's status
- Stories not assigned to any sprint are forward-looking and should remain `backlog` under their epic
- Write reconciled `roadmap.yaml`

### STEP C2: Phase Determination

Use the Recommended Phase Logic from `phase-onboarding.md` with enriched audit data.

### STEP C3: Gap Report

Generate gap report using the format from `phase-onboarding.md` (Phase C section), based on real agent outputs.

### STEP C4: Presentation

Present using the format from `phase-onboarding.md`:
```
ONBOARDING COMPLETE

Project: [Name] ([Type]: [Tech Stack])
Recommended Phase: [N] ([Phase Name])

Generated Artifacts:
  ✅ project-context.md (by product-strategist — domain research + [source] synthesis)
  ✅ roadmap.yaml ([N] epics, [M] stories: [X] done, [Y] in-progress, [Z] backlog)
  ...

Review each artifact? [Yes / Trust the agents]
```

If "Yes": present each artifact for approval/editing, one at a time.

**For failed agents:** Show which artifacts were not generated and offer fallback options:
```
⚠️ [artifact] — Agent failed. Options:
  - Import from file
  - Describe manually
  - Skip (record as gap)
```

### STEP C5: Finalize & Cleanup

1. **Create `.archflow/current-phase.yaml`:**
```yaml
phase: {recommended_phase}
phase_name: "{phase_name}"
phase_file: "phases/phase-{N}-{name}.md"

# Project metadata
project_type: "{detected_type}"
onboarded: true
onboarded_at: "{ISO timestamp}"
tech_stack:
  language: "{language}"
  frontend: "{framework}"    # omitted for backend_only
  backend: "{framework}"     # omitted for frontend_only
  database: "{database}"

# API contract (flexible path — any format)
api_contract_path: "{found_path_or_null}"

# Phase tracking
phases_completed: [...]
phases_partial: [...]
phases_skipped: [...]
phases_not_applicable: [...]

# Gaps user chose to skip
gaps: [...]

# Git workflow
git_workflow: "workflow.md"

# Feature tracking
current_feature: null
feature_status: "ready"
status: "onboarded"
```

2. **Create or update `CLAUDE.md` with Archflow section:**

If `CLAUDE.md` does NOT exist in the project root, create it with global project instructions derived from the onboarding analysis:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

[Brief description from project-context.md — what the app does, tech stack summary]

## Common Commands

[Detected from package.json scripts, Makefile, or common patterns for the tech stack]

## Architecture

[Key architectural patterns, directory structure, path aliases — derived from audit]

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: [N] ([Phase Name]) — see `.archflow/current-phase.yaml`
- **Project Context**: `.archflow/project-context.md`
- **Roadmap**: `.archflow/roadmap.yaml` ([N] epics, [M] proposed features)
- **API Contract**: `docs/api-contract.md`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

If `CLAUDE.md` ALREADY exists, append the Archflow section to the end:

```markdown

## Archflow Framework

This project uses the [Archflow](https://github.com/AZidan/archflow) phase-based development framework.

- **Current Phase**: [N] ([Phase Name]) — see `.archflow/current-phase.yaml`
- **Project Context**: `.archflow/project-context.md`
- **Roadmap**: `.archflow/roadmap.yaml` ([N] epics, [M] proposed features)
- **API Contract**: `docs/api-contract.md`

Commands:
- `/archflow` — Show status and available commands
- `/archflow feature` — Start a new feature from the roadmap
```

Fill in the actual values from `current-phase.yaml` and the generated artifacts. Only list artifacts that were actually created (e.g., skip API contract line if none was generated, skip design system lines for backend_only).

3. **MCP cleanup** (if any onboarding-only MCPs were added):
```
These MCPs were added for import and aren't needed for development:
  - [list of onboarding_only MCPs]
Remove to save context window? [Yes / Keep]
```
If yes, run `claude mcp remove [name]` for each.

4. **Clean up ALL temporary onboarding files:**
```bash
rm .onboard-*
```
This removes every `.onboard-*` file (progress, audit report, imported context, extracted routes, roadmap draft, and any other temp files created during onboarding). Do NOT leave any behind.

5. **Print summary:**
```
ONBOARDING COMPLETE

Project: [Name] ([Type]: [Tech Stack])
Current Phase: [N] ([Phase Name])

Created:
  ✅ CLAUDE.md [created / updated with Archflow section]
  ✅ project-context.md
  ✅ roadmap.yaml ([N] features)
  ✅ API contract: [path]
  ✅ Design system: design-artifacts/theme.yaml
  ✅ styled-dsl.yaml ([N] screens)
  ✅ User flows: design-artifacts/user-flows.md

Skipped:
  ⏭️ [artifact] ([reason])

Next steps:
  - /archflow feature to add a new feature to the roadmap
  - Review roadmap.yaml, then start current phase
```

---

## Error Handling

### Agent Failure
- Record failure in `.onboard-progress.yaml` under the agent's status
- Continue dispatching non-dependent agents
- In Phase C, report failed artifacts with manual fallback options

### MCP Unavailable
- Use WebFetch as fallback for documentation pages
- If auth required: ask user to paste content manually in Phase A
- Product-strategist runs with reduced context (user_vision_notes only)

### MCP Restart Required
If an MCP needs to be configured and requires a Claude Code restart:
1. Save all progress to `.onboard-progress.yaml`
2. Tell the user: "Please restart Claude Code, then run `/archflow onboard` to resume."
3. On resume, skip completed steps and continue from where we left off.

### Design Extraction Fails
- ux-designer receives empty extraction
- Falls back to creating fresh theme from project-context.md

### No Source Code Found
If no source code indicators are found:
> "This doesn't appear to be an existing codebase. Use the normal Phase 1 setup instead."
> Exit the wizard.

### Resume After Interruption
`.onboard-progress.yaml` tracks `wizard_phase` (A/B/C) and per-agent status:
- **Phase A interrupted:** Re-ask from the last incomplete step
- **Phase B interrupted:** Re-dispatch agents with `status: "pending"` or `status: "running"`, skip `status: "completed"`
- **Phase C interrupted:** Re-run synthesis from Step C1

---

## Notes
- Phase A is interactive — wait for user input at every decision point
- Phase B is autonomous — user can leave, agents work in background
- Phase C is interactive — present results for user approval
- All generated artifacts must be shown to the user for approval in Phase C (unless they choose "Trust the agents")
- The wizard can be re-run safely; it will detect existing artifacts and skip them
