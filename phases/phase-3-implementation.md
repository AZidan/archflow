# Phase 3: Implementation (Parallel Development)

## 🎯 Phase Objective
Build frontend and backend simultaneously using API contracts, then integrate and test each feature.

## 📋 Required Agents
- `ui-engineer` - All frontend (React, React Native, SwiftUI, Jetpack Compose, HTML/CSS)
- `api-engineer` - Backend services (NestJS, MySQL, REST APIs, authentication)
- `qa-engineer` - All testing (unit, integration, e2e, mobile, web)

## 📚 Prerequisites
- Phase 2.5 output: `docs/api-contract.md` (SACRED DOCUMENT)
- `design-artifacts/styled-dsl.yaml`
- `design-artifacts/hifi-screens/` (visual reference for ui-engineer)
- `current-feature.yaml` defining feature scope
- User approval from Phase 2.5

## 🚀 Execution Steps

### 🗺️ Pre-Implementation: Codemap Setup
Before writing any code, ensure Codemap is initialized and running:
```bash
# Verify codemap is active (should already be from phase-setup)
codemap stats

# If not initialized:
codemap init . && codemap watch . -q &
```

### ⚡ FEATURE-BY-FEATURE DEVELOPMENT (ONE AT A TIME)
For EACH feature in `roadmap.yaml`, execute this 3-step process:

### 🔄 Step 3A: PARALLEL DEVELOPMENT
**Run simultaneously - both agents work at same time:**

**Before writing code, BOTH agents must:**
```bash
# Check what already exists — avoid duplicating code
codemap find "[FeatureName]"
codemap find "related-symbol-name"

# Understand existing file structures before creating new ones
codemap show src/components/  # or relevant directory
codemap show backend/src/
```

```bash
# Frontend Development
ui-engineer: ref:design-artifacts/styled-dsl.yaml + docs/api-contract.md → src/components/[FeatureName]/
  - Use `codemap find` to check for existing shared components before creating new ones
  - Use `codemap show` to understand existing service layer patterns
  - Build frontend components using contract for API integration points
  - Create service layers that match contract endpoints exactly
  - Implement UI logic and user interactions
  - Add error handling for all contract-defined error codes

# Backend Development (CONTRACT SACRED!)
🚨 api-engineer: MUST READ + FOLLOW docs/api-contract.md EXACTLY → backend/src/[feature-name]/
   - Use `codemap find` to locate existing models, services, and utilities before creating new ones
   - Use `codemap show` on existing feature modules to follow established patterns
   - VERIFY: All endpoints match contract paths, methods, parameters
   - VERIFY: All response structures match contract schemas  
   - VERIFY: All error codes match contract specifications
   - VERIFY: Authentication matches contract requirements
   - NO DEVIATIONS from contract allowed - ZERO TOLERANCE
```

### 🔗 Step 3B: INTEGRATION
**After both frontend + backend are complete:**

```bash
ui-engineer: ref:docs/api-contract.md → connect frontend ↔ backend
  - Test API calls against actual backend endpoints
  - Verify data flow matches contract specifications
  - Handle all error scenarios as defined in contract
  - Ensure authentication integration works correctly
```

### ✅ Step 3C: FEATURE TESTING

```bash
qa-engineer: test integrated feature → tests/[feature-name]/
  - Unit tests for frontend components
  - Unit tests for backend endpoints
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

## 📤 Expected Outputs (Per Feature)
- `src/components/[FeatureName]/` - Complete frontend implementation
- `backend/src/[feature-name]/` - Complete backend implementation
- `tests/[feature-name]/` - Comprehensive test suite
- `docs/acceptance-reports/{story-id}-review.md` - Acceptance test report
- Working, integrated feature ready for demo

## ✅ Completion Criteria (Per Feature)
- [ ] Frontend components fully implemented per DSL specifications
- [ ] Backend endpoints match API contract exactly (100% compliance)
- [ ] Frontend-backend integration working flawlessly
- [ ] All test scenarios passing (unit, integration, e2e)
- [ ] Acceptance criteria validated by pm-maestro-reviewer (ACCEPTED verdict)
- [ ] Feature ready for user demo and approval

## 🚨 Critical Requirements

### API Contract Compliance (ZERO TOLERANCE)
- **api-engineer MUST follow `docs/api-contract.md` exactly**
- **NO deviations, modifications, or "improvements" allowed**
- **Every endpoint, parameter, response format must match contract**
- **Contract violations cause integration failures and project delays**

### Feature Isolation
- **ONE FEATURE AT A TIME** - never batch multiple features
- **Complete entire 4-step process before next feature**
- **Each feature must be fully integrated and tested**

### Mandatory Approval Gates
- **DEMO REQUIRED**: Working feature must be demonstrated to user
- **USER APPROVAL MANDATORY**: Wait for explicit approval before next feature
- **NO PROCEEDING**: Cannot start next feature without approval

## ⚠️ Common Pitfalls to Avoid
1. **API Contract Deviations** - Most common cause of integration failures
2. **Batching Features** - Leads to complexity and integration issues
3. **Skipping Integration Testing** - Results in broken user experiences
4. **Approval Bypass** - Creates misaligned expectations

## 🔄 Per-Feature Workflow
```yaml
For each feature in roadmap:
  Step 3A: ui-engineer + api-engineer (parallel)
  Step 3B: ui-engineer integration
  Step 3C: qa-engineer testing
  Step 3D: pm-maestro-reviewer acceptance testing
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
**Phase 3 Complete (All Features)** ✅ → **Phase 4: Quality** ➡️