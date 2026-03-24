# Phase 3: Implementation (Parallel Development)

## 🎯 Phase Objective
Build frontend and backend simultaneously using API contracts, then integrate and test each feature.

## 📋 Required Agents (Project-Type Aware)

Read `.archflow/current-phase.yaml` to determine `project_type` and select appropriate agents:

| Agent | fullstack | frontend_only | backend_only | mobile |
|-------|-----------|---------------|--------------|--------|
| `ui-engineer` | Yes | Yes | No | Yes |
| `api-engineer` | Yes | No | Yes | Yes |
| `qa-engineer` | Yes | Yes | Yes | Yes |

## 📚 Prerequisites
- API contract at `.archflow/current-phase.yaml → api_contract_path` (SACRED DOCUMENT)
  - This may be `docs/api-contract.md`, `openapi.yaml`, `swagger.json`, or any path
  - If `api_contract_path` is null: skip API contract verification (frontend_only projects consuming no external APIs)
- `design-artifacts/styled-dsl.yaml` (for projects with UI — skip for backend_only)
- `design-artifacts/hifi-screens/` (visual reference — skip for backend_only)
- `.archflow/current-feature.yaml` defining feature scope
- User approval from previous phase

## 🚀 Execution Steps

### Step 0: Phase 3 Pre-Flight Validation (MANDATORY)

If ANY check fails, HALT and fix before proceeding.

#### 0.1 Git Repository
Run: `git status`
- NOT initialized → HALT: "Git is required. Run `git init && git add . && git commit -m 'Initial commit'`"
- Verify prior phase commits: `git log --oneline | head -5`

#### 0.2 Feature Branch
Check: `.archflow/current-feature.yaml` exists AND `branch` field is NOT "main"
- Missing/main → HALT: "Run `/archflow feature` first."

#### 0.3 API Contract (ALL project types that consume or serve APIs)
Check: API contract file exists at path from `.archflow/current-phase.yaml → api_contract_path`
- **fullstack / backend_only**: HALT if missing — "Complete Phase 2.5 first."
- **frontend_only / mobile**: If `api_contract_path` is set (i.e., the app consumes external APIs),
  HALT if the file is missing — "API contract required. Point to existing spec or generate one via `/archflow onboard`."
  If `api_contract_path` is null (no external APIs), skip this check.

Note: The onboarding wizard (Step A3) scans frontend/mobile client-side API calls,
service layers, and TypeScript interfaces to generate or locate the API contract.
Frontend/mobile projects that consume APIs MUST have a contract so ui-engineer
can build correct service layers and TypeScript interfaces.

#### 0.4 Design Artifacts (fullstack/frontend_only/mobile)
Check: `design-artifacts/styled-dsl.yaml` exists
- Missing → HALT: "Complete Phase 2 first."

#### 0.5 Codemap
- `.codemap/` missing → `codemap init .`
- Watcher: `pgrep -f "codemap watch" > /dev/null || codemap watch . -q &`

All checks passed → proceed to Step 3A.

---

### 🗺️ Pre-Implementation: Codemap Setup
Before writing any code, ensure Codemap is initialized and running:
```bash
# Verify codemap is active (should already be from phase-setup)
codemap stats

# If not initialized:
codemap init . && codemap watch . -q &
```

### 🔀 Git Workflow Integration
Each feature follows the branching strategy from `.archflow/workflow.md`:

1. Feature branch should already exist (created by `/archflow feature` command)
2. If not, create it:
   ```bash
   git checkout main && git pull origin main
   git checkout -b {feature-branch}
   git push -u origin {feature-branch}
   ```
3. Task branches are created from the feature branch per `.archflow/workflow.md`
4. All merges require explicit user approval

### ⚡ FEATURE-BY-FEATURE DEVELOPMENT (ONE AT A TIME)

- **ONE FEATURE AT A TIME**: Complete all stories in a feature before starting next
- **ONE STORY AT A TIME**: Complete full cycle (implement → test → accept → approve → merge) per story
- **PARALLEL WITHIN A STORY**: ui-engineer + api-engineer CAN run in parallel for SAME story only

For EACH feature in `.archflow/roadmap.yaml` (or `.archflow/current-feature.yaml`), execute the process below.

### Story Serialization Check

Before starting work on a new story:

1. Check roadmap.yaml: Any stories with `status: in_progress`?
   - YES, DIFFERENT story → HALT: "Story [X] still in progress. Complete it first."
   - YES, SAME story → Continue (resuming)
   - NO → Proceed

2. Only ONE story may be `in_progress` at a time within a feature.

3. Parallelism rules:
   - ALLOWED: ui-engineer + api-engineer for the SAME story (independent scopes)
   - NOT ALLOWED: agents for DIFFERENT stories in parallel
   - NOT ALLOWED: different features in parallel

### Pre-Dispatch Validation (BEFORE launching any agent)

1. `.archflow/current-feature.yaml` present?
   - NO → Run `/archflow feature` first

2. Task branch exists for this story?
   - NO → Create per workflow.md, update current-feature.yaml

3. Working tree clean? (`git status --porcelain`)
   - Dirty → Commit or stash first

ONLY THEN dispatch the agent with: "Work on branch [branch-name]"

### 🔄 Step 3A: DEVELOPMENT

**Before writing code, agents must:**
```bash
# Check what already exists — avoid duplicating code
codemap find "[FeatureName]"
codemap find "related-symbol-name"

# Understand existing file structures before creating new ones
codemap show src/components/  # or relevant directory
codemap show backend/src/
```

**Project-type-aware agent dispatch:**

#### fullstack (parallel)
```bash
# Frontend Development
ui-engineer: design-artifacts/styled-dsl.yaml + {api_contract_path} → src/components/[FeatureName]/
  - Build frontend components using contract for API integration points
  - Create service layers that match contract endpoints exactly
  - Implement UI logic and user interactions
  - Add error handling for all contract-defined error codes

# Backend Development (CONTRACT SACRED!)
api-engineer: MUST READ + FOLLOW {api_contract_path} EXACTLY → backend/src/[feature-name]/
  - VERIFY: All endpoints match contract paths, methods, parameters
  - VERIFY: All response structures match contract schemas
  - VERIFY: All error codes match contract specifications
  - VERIFY: Authentication matches contract requirements
  - NO DEVIATIONS from contract allowed - ZERO TOLERANCE
```

#### frontend_only
```bash
# Frontend Development Only
ui-engineer: design-artifacts/styled-dsl.yaml → src/components/[FeatureName]/
  - If consuming external APIs: read {api_contract_path} for integration
  - Build frontend components
  - Create service layers for API calls (if applicable)
  - Implement UI logic and user interactions
```

#### backend_only
```bash
# Backend Development Only (CONTRACT SACRED!)
api-engineer: MUST READ + FOLLOW {api_contract_path} EXACTLY → backend/src/[feature-name]/
  - VERIFY: All endpoints match contract paths, methods, parameters
  - VERIFY: All response structures match contract schemas
  - NO DEVIATIONS from contract allowed - ZERO TOLERANCE
```

#### mobile
```bash
# Same as fullstack but with mobile-specific ui-engineer instructions
ui-engineer: design-artifacts/styled-dsl.yaml + {api_contract_path} → mobile components
api-engineer: {api_contract_path} → backend/src/[feature-name]/
```

### 🔗 Step 3B: INTEGRATION
**After development is complete (skip for backend_only):**

```bash
ui-engineer: {api_contract_path} → connect frontend ↔ backend
  - Test API calls against actual backend endpoints
  - Verify data flow matches contract specifications
  - Handle all error scenarios as defined in contract
  - Ensure authentication integration works correctly
```

### ✅ Step 3C: FEATURE TESTING

```bash
qa-engineer: test integrated feature → tests/[feature-name]/
  - Unit tests for frontend components (skip for backend_only)
  - Unit tests for backend endpoints (skip for frontend_only)
  - Integration tests for API calls
  - End-to-end tests for complete user workflows
  - Error scenario testing
```

Gate: ALL tests must pass before Step 3D.
If tests FAIL:
  → Re-dispatch implementation agent with failure details
  → Re-run qa-engineer
  → Do NOT proceed to Step 3D

### 🎯 Step 3D: ACCEPTANCE TESTING (AUTO-TRIGGERED after 3C passes)

IMMEDIATELY after qa-engineer reports all tests passing:
  → Dispatch pm-maestro-reviewer with story ID + acceptance criteria
  → Output: `docs/acceptance-reports/{story-id}-review.md`

If REJECTED:
  → Re-dispatch implementation agent to fix blocking defects
  → Re-run Step 3C (qa-engineer)
  → Re-run Step 3D (pm-maestro-reviewer)
  → Do NOT proceed until ACCEPTED

If ACCEPTED:
  → Proceed to Step 3F (Approval Gate)

Step 3D is NOT optional. No story can be "done" without ACCEPTED verdict.

### Post-Agent Verification

After an agent returns from implementing a story:

1. Verify roadmap.yaml subtasks are updated:
   - Count subtasks with `completed: true` for the story
   - If count doesn't match agent's claimed completion, update manually

2. Only mark story `status: done` when ALL of:
   - ALL subtasks are `completed: true`
   - Tests pass (qa-engineer)
   - Acceptance verdict is ACCEPTED (pm-maestro-reviewer)
   - User has explicitly approved

3. NEVER mark a story "done" by only changing the status field.

### 🔀 Step 3E: GIT MERGE (Per Task)
After each task passes testing and acceptance:
1. Wait for explicit user approval
2. Merge task branch → feature branch (per `.archflow/workflow.md`)
3. Clean up task branch
4. Update `.archflow/current-feature.yaml`: mark task complete

### 🛑 Step 3F: APPROVAL GATE (MANDATORY — CANNOT BE SKIPPED)

After acceptance testing returns ACCEPTED:

1. Present to the user:
   ```
   ============================================
   APPROVAL REQUIRED: [Story ID] — [Story Title]
   ============================================
   Branch: [task-branch-name]
   Agent: [agent-name]

   Completed subtasks:
   - [x] Subtask 1
   - [x] Subtask 2

   Acceptance: ACCEPTED
   Test results: [X/Y tests passing]

   Files changed:
   - [list of created/modified files]

   Respond with:
   - "Approved" → merge to feature branch
   - "Changes needed: [feedback]" → agent will address
   ============================================
   ```

2. WAIT for user response. Do NOT proceed.

3. If "Approved":
   - Merge per workflow.md
   - Update roadmap.yaml: story `status: done`, all subtasks `completed: true`
   - Add `approved: true` and `approved_at: "[date]"` to the story
   - Update current-feature.yaml: task `status: complete`, `completed_at: "[date]"`

4. If "Changes needed":
   - Re-dispatch agent with feedback
   - Re-run qa-engineer → pm-maestro-reviewer → return to step 1

After ALL tasks for a feature are complete:
1. Wait for explicit user approval
2. Merge feature branch → main (per `.archflow/workflow.md`)
3. Clean up feature branch
4. Update `.archflow/roadmap.yaml`: feature status → `complete`
5. Update `.archflow/current-phase.yaml`: `current_feature` → `null`

## 📤 Expected Outputs (Per Feature)
- Frontend implementation (skip for backend_only)
- Backend implementation (skip for frontend_only)
- Comprehensive test suite
- `docs/acceptance-reports/{story-id}-review.md` - Acceptance test report
- Working, integrated feature ready for demo

## ✅ Completion Criteria (Per Feature)
- [ ] Implementation complete per project type
- [ ] API contract compliance (100% for endpoints that exist)
- [ ] Frontend-backend integration working (if applicable)
- [ ] All test scenarios passing (unit, integration, e2e)
- [ ] Acceptance criteria validated by pm-maestro-reviewer (ACCEPTED verdict)
- [ ] Git workflow completed (task branches merged, feature branch clean)
- [ ] Feature ready for user demo and approval

## 🚨 Critical Requirements

### API Contract Compliance (ZERO TOLERANCE)
- **api-engineer MUST follow `{api_contract_path}` exactly** (whatever format it's in)
- **NO deviations, modifications, or "improvements" allowed**
- **Every endpoint, parameter, response format must match contract**
- **Contract violations cause integration failures and project delays**

### Feature Isolation
- **ONE FEATURE AT A TIME** - never batch multiple features
- **Complete entire process before next feature**
- **Each feature must be fully integrated and tested**

### Git Workflow
- **All merges require explicit user approval** (per `.archflow/workflow.md`)
- **Never auto-merge** task or feature branches
- **Branch naming follows conventions** in `.archflow/workflow.md`

### Mandatory Approval Gates
- **DEMO REQUIRED**: Working feature must be demonstrated to user
- **USER APPROVAL MANDATORY**: Wait for explicit approval before next feature
- **NO PROCEEDING**: Cannot start next feature without approval

## 🔄 Per-Feature Workflow
```yaml
For each feature in roadmap:
  Step 3A: Development (agents based on project_type)
  Step 3B: Integration (skip for backend_only)
  Step 3C: qa-engineer testing
  Step 3D: pm-maestro-reviewer acceptance testing
  Step 3E: Git merge (with user approval)
  Demo: Present working feature + acceptance report to user
  Approval Gate: Wait for explicit user approval
  Next: Move to next feature OR proceed to Phase 4 if all complete
```

## ➡️ Phase Transition
When ALL features are implemented, integrated, tested, and approved:
1. Update `.archflow/current-phase.yaml` to `phase: 4`
2. Proceed to Quality Phase
3. Load `.archflow/phases/phase-4-quality.md` for next phase instructions

---
**Phase 3 Complete (All Features)** → **Phase 4: Quality**
