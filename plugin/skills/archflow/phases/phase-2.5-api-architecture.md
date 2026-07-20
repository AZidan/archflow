# Phase 2.5: API Architecture

## 🎯 Phase Objective
API architecture splits into TWO kinds of work (v2.0 — Pillar 2), mirroring the design split:

1. **Release foundation (once, at release start):** the contract *architecture* — auth patterns,
   conventions, error-response format, pagination, versioning. The shared rules every endpoint obeys.
2. **Per-story contract gate (continuous):** a specific story's *endpoints*, specified just-in-time
   against the architecture, one step ahead of that story's build. Advances the story to
   `contract_ready`. Stories with `gates.needs_contract: false` skip it entirely.

The contract remains the single source of truth for frontend/backend integration (SACRED DOCUMENT).

## 📋 Required Agents
- `api-contract-architect` - Contract architecture (foundation) AND per-story endpoint specs (gate)

## 📚 Prerequisites
- Phase 2 outputs: `design-artifacts/wireframes/`, `design-artifacts/styled-dsl.yaml`
- Phase 2.25 outputs: `design-artifacts/hifi-screens/` (visual reference for API design)
- The active release (`.archflow/releases/{active_release}.yaml`) — its stories drive per-story specs
- User approval from Phase 2.25

## 🚦 Per-story contract gate (readiness pipeline)

For each story in the active release with `gates.needs_contract: true`, run just-in-time (one step
ahead of that story's build):

```bash
api-contract-architect: {contract-architecture} + story context → docs/api-contract.md (this story's endpoints)
```
Then in the release file, advance the story's `status` to `contract_ready` (or `ready` if
`needs_design` is false / already met). Endpoints MUST conform to the contract architecture.

**Mode calibration:** in `quick` mode this gate auto-satisfies; in `full` mode it runs and appends the
story's endpoints to the contract.

## 🚀 Execution Steps

### Release foundation: contract architecture (once, at release start)
Define the shared contract rules before per-story endpoints are specified.

```bash
api-contract-architect: design-artifacts/wireframes/ + active release → docs/api-contract.md (architecture section)
```
Per-*endpoint* specs for individual stories happen in the per-story contract gate above, not here.

## 📤 Expected Outputs
- `docs/api-contract.md` - Complete API specifications including:
  - All endpoint definitions (paths, methods, parameters)
  - Request/response schemas and examples
  - Authentication requirements
  - Error response formats and codes
  - Data validation rules

## ✅ Completion Criteria
- [ ] All API endpoints defined for current feature scope
- [ ] Request/response schemas documented with examples
- [ ] Authentication and authorization specified
- [ ] Error handling patterns established
- [ ] API contracts align with wireframes and DSL specifications
- [ ] Frontend and backend teams can work independently using contracts

## 🚨 Critical Requirements
- **CONTRACT COMPLETENESS**: Every frontend data need must have corresponding API endpoint
- **SCHEMA PRECISION**: All request/response formats must be explicitly defined
- **ERROR SPECIFICATIONS**: All possible error scenarios must be documented
- **USER APPROVAL MANDATORY**: Present API contracts to user and wait for explicit approval
- **NO PROCEEDING**: Do not move to Phase 3 without approval
- **RELEASE SCOPE**: Only specify endpoints for stories in the active release
  (`.archflow/releases/{active_release}.yaml`) with `gates.needs_contract: true`

## 💡 Why This Phase Is Critical
- Enables **parallel development** in Phase 3
- Eliminates **integration issues** and back-and-forth
- Provides **single source of truth** for both frontend and backend
- Reduces **development time** by 40-50%

## Phase Completion: Commit Artifacts

Before transitioning to the next phase, commit all artifacts:
```bash
git add docs/api-contract.md
git commit -m "docs: complete Phase 2.5 - API contract"
```

## Phase Transition Validation

Before updating `current-phase.yaml`, verify:

1. **Artifacts exist**:
   - [ ] `docs/api-contract.md` exists (or equivalent at `api_contract_path`). For `frontend_only`/`mobile`: required if app consumes external APIs (`api_contract_path` is set)

2. **Git state**:
   - [ ] All artifacts committed (`git status` shows clean tree)

3. **Approval**:
   - [ ] User explicitly approved phase outputs

If ANY check fails → HALT: "Cannot transition. Missing: [list]"
If ALL pass → update `current-phase.yaml` to next phase.

## ➡️ Phase Transition
Upon completion and approval:
1. Update `.archflow/current-phase.yaml` to `phase: 3`
2. Proceed to Implementation Phase (Parallel Development)
3. Load `.archflow/phases/phase-3-implementation.md` for next phase instructions

---
**Phase 2.5 Complete** ✅ → **Phase 3: Implementation (Parallel)** ➡️