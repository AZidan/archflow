# Phase 3: Implementation (Parallel Development)

## 🎯 Phase Objective
Build frontend and backend simultaneously using API contracts, then integrate and test each feature.

## 📋 Required Agents (Project-Type Aware)

Read `current-phase.yaml` to determine `project_type` and select appropriate agents:

| Agent | fullstack | frontend_only | backend_only | mobile |
|-------|-----------|---------------|--------------|--------|
| `ui-engineer` | Yes | Yes | No | Yes |
| `api-engineer` | Yes | No | Yes | Yes |
| `qa-engineer` | Yes | Yes | Yes | Yes |

## 📚 Prerequisites
- API contract at `ref:current-phase.yaml → api_contract_path` (SACRED DOCUMENT)
  - This may be `docs/api-contract.md`, `openapi.yaml`, `swagger.json`, or any path
  - If `api_contract_path` is null: skip API contract verification (frontend_only projects consuming no external APIs)
- `design-artifacts/styled-dsl.yaml` (for projects with UI — skip for backend_only)
- `design-artifacts/hifi-screens/` (visual reference — skip for backend_only)
- `current-feature.yaml` defining feature scope
- User approval from previous phase

## 🚀 Execution Steps

### 🗺️ Pre-Implementation: Codemap Setup
Before writing any code, ensure Codemap is initialized and running:
```bash
# Verify codemap is active (should already be from phase-setup)
codemap stats

# If not initialized:
codemap init . && codemap watch . -q &
```

### 🔀 Git Workflow Integration
Each feature follows the branching strategy from `ref:workflow.md`:

1. Feature branch should already exist (created by `/feature` command)
2. If not, create it:
   ```bash
   git checkout main && git pull origin main
   git checkout -b {feature-branch}
   git push -u origin {feature-branch}
   ```
3. Task branches are created from the feature branch per `workflow.md`
4. All merges require explicit user approval

### ⚡ FEATURE-BY-FEATURE DEVELOPMENT (ONE AT A TIME)
For EACH feature in `roadmap.yaml` (or `current-feature.yaml`), execute the process below.

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
ui-engineer: ref:design-artifacts/styled-dsl.yaml + ref:{api_contract_path} → src/components/[FeatureName]/
  - Build frontend components using contract for API integration points
  - Create service layers that match contract endpoints exactly
  - Implement UI logic and user interactions
  - Add error handling for all contract-defined error codes

# Backend Development (CONTRACT SACRED!)
api-engineer: MUST READ + FOLLOW ref:{api_contract_path} EXACTLY → backend/src/[feature-name]/
  - VERIFY: All endpoints match contract paths, methods, parameters
  - VERIFY: All response structures match contract schemas
  - VERIFY: All error codes match contract specifications
  - VERIFY: Authentication matches contract requirements
  - NO DEVIATIONS from contract allowed - ZERO TOLERANCE
```

#### frontend_only
```bash
# Frontend Development Only
ui-engineer: ref:design-artifacts/styled-dsl.yaml → src/components/[FeatureName]/
  - If consuming external APIs: read ref:{api_contract_path} for integration
  - Build frontend components
  - Create service layers for API calls (if applicable)
  - Implement UI logic and user interactions
```

#### backend_only
```bash
# Backend Development Only (CONTRACT SACRED!)
api-engineer: MUST READ + FOLLOW ref:{api_contract_path} EXACTLY → backend/src/[feature-name]/
  - VERIFY: All endpoints match contract paths, methods, parameters
  - VERIFY: All response structures match contract schemas
  - NO DEVIATIONS from contract allowed - ZERO TOLERANCE
```

#### mobile
```bash
# Same as fullstack but with mobile-specific ui-engineer instructions
ui-engineer: ref:design-artifacts/styled-dsl.yaml + ref:{api_contract_path} → mobile components
api-engineer: ref:{api_contract_path} → backend/src/[feature-name]/
```

### 🔗 Step 3B: INTEGRATION
**After development is complete (skip for backend_only):**

```bash
ui-engineer: ref:{api_contract_path} → connect frontend ↔ backend
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

### 🎯 Step 3D: ACCEPTANCE TESTING

```bash
pm-maestro-reviewer: ref:roadmap.yaml → docs/acceptance-reports/{story-id}-review.md
  - Map acceptance criteria from roadmap.yaml to Maestro test flows
  - Execute Maestro tests against the running app
  - Produce pass/fail acceptance report
  - Verdict: ACCEPTED → proceed to demo | REJECTED → fix and re-run
```

### 🔀 Step 3E: GIT MERGE (Per Task)
After each task passes testing and acceptance:
1. Wait for explicit user approval
2. Merge task branch → feature branch (per `workflow.md`)
3. Clean up task branch
4. Update `current-feature.yaml`: mark task complete

After ALL tasks for a feature are complete:
1. Wait for explicit user approval
2. Merge feature branch → main (per `workflow.md`)
3. Clean up feature branch
4. Update `roadmap.yaml`: feature status → `complete`
5. Update `current-phase.yaml`: `current_feature` → `null`

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
- **api-engineer MUST follow `ref:{api_contract_path}` exactly** (whatever format it's in)
- **NO deviations, modifications, or "improvements" allowed**
- **Every endpoint, parameter, response format must match contract**
- **Contract violations cause integration failures and project delays**

### Feature Isolation
- **ONE FEATURE AT A TIME** - never batch multiple features
- **Complete entire process before next feature**
- **Each feature must be fully integrated and tested**

### Git Workflow
- **All merges require explicit user approval** (per `workflow.md`)
- **Never auto-merge** task or feature branches
- **Branch naming follows conventions** in `workflow.md`

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
1. Update `current-phase.yaml` to `phase: 4`
2. Proceed to Quality Phase
3. Load `ref:phases/phase-4-quality.md` for next phase instructions

---
**Phase 3 Complete (All Features)** → **Phase 4: Quality**
