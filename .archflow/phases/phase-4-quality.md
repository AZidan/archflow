# Phase 4: Quality Assurance

> Framework detail (release model, rules in full, agent roster): `.archflow/reference.md`.

## 🎯 Phase Objective
Comprehensive quality review, performance optimization, and final testing across the **active
release's** implemented stories, before it ships in Phase 5.

## 📋 Required Agents (Project-Type Aware)

Read `.archflow/project-settings.yaml` to determine `project_type` and select appropriate agents:

| Agent | fullstack | frontend_only | backend_only | mobile |
|-------|-----------|---------------|--------------|--------|
| `qa-engineer` | Yes | Yes | Yes | Yes |
| `code-reviewer` | Yes | Yes | Yes | Yes |
| `performance-optimizer` | If needed | If needed | If needed | If needed |
| `pm-reviewer` | Yes | Yes | Yes | Yes |

**Agent scope adjustments by project type:**
- **backend_only**: code-reviewer skips UI review, qa-engineer skips frontend tests, performance-optimizer focuses on API/DB
- **frontend_only**: code-reviewer skips backend review, qa-engineer skips backend tests, performance-optimizer focuses on bundle/render
- **fullstack/mobile**: all agents review their full scope

## 📚 Prerequisites
- All stories in the active release (`.archflow/releases/{active_release}.yaml`) are `done` (Phase 3)
- API contract, at the path in `.archflow/project-settings.yaml` → `api_contract_path` (for contract compliance verification)
- Individual story tests passing
- User approval for all individual stories

## 🚀 Execution Steps

### Pre-Review: Codebase Overview with Codemap
Before any agent starts reviewing, get the lay of the land:
```bash
# Codebase overview — size, languages, coverage
codemap stats

# Understand project structure
codemap show src/
codemap show backend/src/
```
All review agents should use `codemap find` to trace dependencies and `codemap show` to navigate files efficiently instead of reading entire files.

### Parallel Quality Assessment
All agents work simultaneously for comprehensive review:

```bash
# Comprehensive Testing
qa-engineer: comprehensive testing across all features → tests/reports/test-results.md
  - Cross-feature integration testing
  - Full user journey testing (skip for backend_only)
  - Performance testing under load
  - Security testing
  - Browser/device compatibility testing (skip for backend_only)
  - Regression testing

# Code Quality Review
code-reviewer: complete codebase review → docs/code-review-report.md
  - Code quality assessment
  - Security vulnerability analysis
  - Best practices compliance
  - Architecture review
  - API contract compliance verification ({api_contract_path})
  - Documentation completeness
  - Maintainability assessment

# Acceptance Regression Suite (scoped to the ACTIVE RELEASE)
pm-reviewer: .archflow/releases/{active_release}.yaml → docs/acceptance-reports/regression-report.md
  - Re-run ALL acceptance tests for THIS release's stories as regression
  - Verify no cross-story regressions within the release
  - Produce a consolidated acceptance regression report for the release
  - Record every regression against the story that regressed, as an `issues[]` entry on it
    (`found_by: pm-reviewer`, `severity: blocking`) — a release-level report alone leaves the
    orchestrator to remember which story each finding belongs to
  - (Cross-release regression against prior shipped releases is a separate, optional full-regression
    suite — run it before a high-risk release, sourced from history.yaml + archived releases.)

# Performance Analysis (If Issues Found)
performance-optimizer: analyze and optimize → docs/performance-report.md
  - Frontend performance optimization (skip for backend_only)
  - Backend API performance tuning (skip for frontend_only)
  - Database query optimization (skip for frontend_only)
  - Bundle size optimization (skip for backend_only)
  - Memory usage analysis
```

## 🐞 Issues in Phase 4

Phase 4 reviewers write findings the same way Phase 3's do: into the `issues[]` of the story the
finding belongs to, in the active release file, alongside the report that holds the evidence. The
same rules apply — sequential dispatch, ids `I-{n}` per story, the implementation agent closes them,
`blocking` findings are never deferred by an agent, and a `minor` one leaves the release only as a
backlog stub with `deferred_to` set. See Phase 3's *Issues — review findings as state*.

A finding that belongs to no single story — an architecture concern, a release-wide performance
regression — stays in its report and becomes a backlog stub. `issues[]` is story-scoped by design.

## 📤 Expected Outputs
- `tests/reports/test-results.md` - Comprehensive test results and coverage
- `docs/code-review-report.md` - Code quality assessment and recommendations
- `docs/acceptance-reports/regression-report.md` - Full acceptance regression results
- `docs/performance-report.md` - Performance analysis and optimizations (if needed)

## ✅ Completion Criteria
- [ ] All cross-feature integrations working correctly
- [ ] Complete user journeys tested and passing (if applicable)
- [ ] Code quality meets production standards
- [ ] Security vulnerabilities addressed
- [ ] Performance meets acceptable thresholds
- [ ] All tests passing (unit, integration, e2e, cross-feature)
- [ ] API contract compliance verified (if applicable)
- [ ] Documentation complete and accurate
- [ ] Acceptance regression suite passes (all stories ACCEPTED)
- [ ] No story in the active release carries an open blocking issue
      (`python3 plugin/scripts/validate_archflow.py .` reports clean)
- [ ] Codebase ready for production deployment

## 🚨 Critical Requirements

### Quality Standards
- **NO FAILING TESTS**: All tests must pass before proceeding
- **SECURITY COMPLIANCE**: All security issues must be resolved
- **PERFORMANCE THRESHOLDS**: App must meet defined performance criteria
- **CODE STANDARDS**: Code must pass quality review

### Comprehensive Coverage
- **ALL FEATURES**: Every implemented feature must be thoroughly tested
- **ALL PLATFORMS**: Testing across all target platforms/browsers (project-type appropriate)
- **ALL SCENARIOS**: Happy path, error scenarios, edge cases

### User Approval
- **PRESENT REPORTS**: All quality reports must be presented to user
- **USER APPROVAL MANDATORY**: Wait for explicit approval before Phase 5
- **NO PROCEEDING**: Cannot move to Launch without quality approval

## 🔍 Quality Gates Checklist
- [ ] **Functionality**: All features work as designed
- [ ] **Integration**: Cross-feature workflows function correctly
- [ ] **Performance**: Meets or exceeds performance requirements
- [ ] **Security**: No critical security vulnerabilities
- [ ] **Usability**: User experience is polished and intuitive (if applicable)
- [ ] **Reliability**: System handles errors gracefully
- [ ] **Maintainability**: Code is clean, documented, and maintainable
- [ ] **Compatibility**: Works across all target platforms/browsers (if applicable)

## ⚠️ Potential Issues & Resolutions
- **Test Failures**: Fix issues and re-run quality phase
- **Performance Problems**: Use performance-optimizer to resolve
- **Security Vulnerabilities**: Address security issues before proceeding
- **Code Quality Issues**: Refactor code to meet standards

## 🔄 Phase Workflow
```yaml
Quality Assessment:
  - qa-engineer: comprehensive testing (scope based on project_type)
  - code-reviewer: quality assessment (scope based on project_type)
  - pm-reviewer: acceptance regression suite
  - performance-optimizer: optimization (if needed, scope based on project_type)

Review & Approval:
  - Present all reports to user
  - Address any critical issues found
  - Wait for explicit user approval

Outcome:
  - PASS: Proceed to Phase 5 (Launch)
  - ISSUES FOUND: Fix issues and repeat Phase 4
```

## Phase Transition Validation

Before updating `current-phase.yaml`, verify:

1. **Artifacts exist**:
   - [ ] `docs/acceptance-reports/` contains reports for all stories
   - [ ] All tests passing (qa-engineer report confirms)
   - [ ] Every issue raised in this phase is `fixed`, or `deferred` with a backlog stub

2. **Git state**:
   - [ ] All artifacts committed (`git status` shows clean tree)

3. **Approval**:
   - [ ] User explicitly approved phase outputs

If ANY check fails → HALT: "Cannot transition. Missing: [list]"
If ALL pass → update `current-phase.yaml` to next phase.

## ➡️ Phase Transition
When all quality gates pass and user approves:
1. Update `.archflow/current-phase.yaml` to `phase: 5`
2. Proceed to ship the active release (Phase 5 — ship ritual + deploy)
3. Load `.archflow/phases/phase-5-launch.md` for next phase instructions

---
**Phase 4 Complete (active release quality-passed)** → **Phase 5: Ship the Release**

## 🔌 Optional agents at this hook point

Read `optional_agents` from `.archflow/project-settings.yaml`. Dispatch every agent whose list contains
**`release_quality`**, with the same payload discipline as any other dispatch.

An agent with an empty list is NOT dispatched here. It is still available on request — if the user
asks for it, run it. Absent from the block entirely means the same thing.

`code-reviewer` and `performance-optimizer` are core to this phase and run regardless. This block
adds anything else the project opted into.
