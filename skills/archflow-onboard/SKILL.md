# /archflow-onboard — Existing Codebase Onboarding Wizard

Onboard an existing codebase to the phase-based development framework. Interactive wizard that audits code, imports context, backfills artifacts, and sets the development phase.

## Usage
```
/archflow-onboard          → Start or resume the onboarding wizard
```

## Prerequisites
- Must be run from the project's root directory
- The project should have existing source code (otherwise use Phase 1 setup normally)

## Detailed Rules
Load `ref:phases/phase-onboarding.md` for audit logic, project type detection rules, backfill rules, and gap report format.

---

## Wizard Flow (5 Steps)

### Resume Check

Before starting, check for interrupted progress:
```bash
# Check for saved progress
if [[ -f ".onboard-progress.yaml" ]]; then
  # Read saved state and resume from wizard_step
  # Inform user: "Resuming onboarding from Step [N]..."
fi
```

If `.onboard-progress.yaml` exists, read it and skip to the saved `wizard_step`. Present what was already completed.

---

### STEP 1 of 5: PROJECT DETECTION

**Actions:**
1. Scan directory for code indicators:
   - `package.json` (read dependencies for framework detection)
   - `src/`, `backend/`, `frontend/`, `ios/`, `android/` directories
   - Config files: `next.config.*`, `vite.config.*`, `nest-cli.json`, `angular.json`
   - Database: `prisma/`, `typeorm`, `sequelize` in deps, `*.entity.ts`
   - CI/CD: `.github/workflows/`, `.gitlab-ci.yml`, `Dockerfile`
2. Detect tech stack from dependencies and file patterns
3. Detect project type using rules from `phases/phase-onboarding.md`:
   - `fullstack` | `frontend_only` | `backend_only` | `mobile`
4. Run `codemap init .` and `codemap stats` for codebase metrics

**Present to user:**
```
STEP 1 of 5: PROJECT DETECTION

Detected project:
 - Type: [Fullstack / Frontend Only / Backend Only / Mobile]
 - Frontend: [framework] ([N] components in [path])
 - Backend: [framework] ([N] modules in [path])
 - Database: [type] ([ORM/schema tool])
 - Tests: [framework] ([N] test files)
 - CI/CD: [tool] ([N] workflows)

Is this correct?
```

Ask user to confirm or correct. Wait for confirmation before proceeding.

**Save progress** after confirmation:
```yaml
# .onboard-progress.yaml
wizard_step: 2
completed_steps: [1]
detected_tech:
  language: "TypeScript"
  frontend: "React"
  backend: "NestJS"
  database: "PostgreSQL"
project_type: "fullstack"
mcps_added: []
```

---

### STEP 2 of 5: CONTEXT IMPORT

**Ask the user:**
```
STEP 2 of 5: CONTEXT IMPORT

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
   - Run `/archflow-setup-mcp [tool]` inline (load `ref:skills/archflow-setup-mcp/SKILL.md`)
   - If MCP setup requires restart: save progress to `.onboard-progress.yaml`, instruct user to restart Claude Code, then run `/archflow-onboard` again
3. Once MCP is available:
   ```
   Paste the links to the epics/stories you want to import:
   (one per line, press Enter twice when done)
   ```
4. For each link:
   - Fetch via MCP (the item + its children/sub-tasks)
   - Extract: title, description, acceptance criteria, status, priority
   - Translate to `project-context.md` + `roadmap.yaml` format
5. Present extracted data to user for approval/editing
6. Write approved files

**For "Local files":**
```
Point me to the files (paths or paste content):
```
- Read the files
- Translate to framework format (`project-context.md` + `roadmap.yaml`)
- Present for approval

**For "I'll describe it":**

Ask conversationally, one question at a time:
1. "What does your application do?"
2. "Who are the target users?"
3. "What's the tech stack?" (pre-fill from Step 1 detection)
4. "What are the main features? List them briefly."
5. "Which features are complete / in-progress / planned?"
6. "Any KPIs or goals you're tracking?"

Generate `project-context.md` + `roadmap.yaml` from answers. Present for approval.

**IMPORTANT**: Roadmap structure must match project type (see `phases/phase-onboarding.md`):
- Backend-only: features are endpoints, modules, integrations (no screens)
- Frontend-only: features are pages, components, flows (no API endpoints unless consuming external)
- Fullstack: both frontend and backend aspects per feature

**Save progress** after this step completes.

---

### STEP 3 of 5: CODEBASE AUDIT

**Actions:**
1. Run the full audit checklist from `phases/phase-onboarding.md`, filtered by `project_type`
2. For each audit check:
   - Scan for the listed file patterns
   - Record found/missing status
3. Special handling:
   - If swagger/openapi found: record path, mark as API contract (use as-is)
   - Count source files, components, routes, modules, test files
4. Determine phase status for each applicable phase
5. Calculate recommended starting phase (see phase-onboarding.md rules)

**Present the gap report** using the format from `phases/phase-onboarding.md`:

```
STEP 3 of 5: CODEBASE AUDIT

+--------------------------------------------------+
|           PROJECT ONBOARDING AUDIT               |
+--------------------------------------------------+
|                                                  |
|  Project Type: [type] ([tech])                   |
|  Files: [N] source files, [M] test files         |
|                                                  |
|  Phase 1 (Strategy):     [status]                |
|    [details per artifact]                        |
|                                                  |
|  Phase 2 (Design):       [status or N/A]         |
|  ...                                             |
|                                                  |
|  Recommended starting phase: Phase [N]           |
+--------------------------------------------------+

Agree with Phase [N]? [Yes / Prefer Phase X]
```

Wait for user confirmation on the recommended phase.

**Save progress** after confirmation.

---

### STEP 4 of 5: ARTIFACT BACKFILL

For each **missing CORE artifact** (one at a time, in phase order):

#### project-context.md (if missing)
```
No project context found. How to provide it?
```
Options:
- **Import from tool** — link-based fetch (same pattern as Step 2)
- **Local file** — point to existing documentation
- **Describe it** — structured questions
- **Skip** — record as gap

#### roadmap.yaml (if missing)
Same options as above. If importing from a tool:
```
Paste links to the epics/stories for this project's roadmap:
```
Fetch, translate, present, approve.

#### API contract (if missing AND project type needs one)

Check first: if swagger/openapi was found in audit, it's already handled:
> "Found [openapi.yaml] — using as API contract. No action needed."

If NOT found:
```
No API spec found. Generate from existing routes?
```
Options:
- **Yes** — Launch `api-contract-architect` to scan existing controllers/routes
- **I'll provide one** — User points to their spec file
- **Skip** — Record as gap

#### Nice-to-have artifacts (design system, wireframes)
Only shown for applicable project types. Brief mention:
> "Optional: Extract design tokens from your existing components? [Yes / Skip]"

**Present each generated artifact.** User approves before moving to the next.

**Save progress** after each artifact is handled.

---

### STEP 5 of 5: FINALIZE & CLEANUP

**Actions:**

1. **Create `current-phase.yaml`:**
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

2. **MCP cleanup** (if any onboarding-only MCPs were added):
```
These MCPs were added for import and aren't needed for development:
  - [list of onboarding_only MCPs]
Remove to save context window? [Yes / Keep]
```
If yes, run `claude mcp remove [name]` for each.

3. **Clean up progress file:**
```bash
rm .onboard-progress.yaml  # No longer needed
```

4. **Print summary:**
```
ONBOARDING COMPLETE

Project: [Name] ([Type]: [Tech Stack])
Current Phase: [N] ([Phase Name])

Created:
  [checkmark] project-context.md
  [checkmark] roadmap.yaml ([N] features)
  [checkmark] API contract: [path] (existing)

Skipped:
  [skip] [artifact] ([reason])

Next steps:
  - /archflow-feature to add a new feature to the roadmap
  - Review roadmap.yaml, then start current phase
```

---

## Error Handling

### MCP Restart Required
If an MCP needs to be configured and requires a Claude Code restart:
1. Save all progress to `.onboard-progress.yaml`
2. Tell the user: "Please restart Claude Code, then run `/archflow-onboard` to resume."
3. On resume, skip completed steps and continue from where we left off.

### MCP Fetch Failure
If fetching a link fails:
- Show the error
- Ask: "Try another link, or skip this import? [Try again / Skip]"

### No Source Code Found
If no source code indicators are found:
> "This doesn't appear to be an existing codebase. Use the normal Phase 1 setup instead."
> Exit the wizard.

---

## Notes
- This wizard is interactive — wait for user input at every decision point
- Never auto-skip steps or make assumptions about what the user wants
- All generated artifacts must be shown to the user for approval before writing
- The wizard can be re-run safely; it will detect existing artifacts and skip them
