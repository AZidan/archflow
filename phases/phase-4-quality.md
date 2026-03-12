# Phase 4: Quality Assurance

## 🎯 Phase Objective
Comprehensive quality review, performance optimization, and final testing across all implemented features.

## 📋 Required Agents (Project-Type Aware)

Read `current-phase.yaml` to determine `project_type` and select appropriate agents:

| Agent | fullstack | frontend_only | backend_only | mobile |
|-------|-----------|---------------|--------------|--------|
| `qa-engineer` | Yes | Yes | Yes | Yes |
| `code-reviewer` | Yes | Yes | Yes | Yes |
| `performance-optimizer` | If needed | If needed | If needed | If needed |
| `pm-maestro-reviewer` | Yes | Yes | Yes | Yes |

**Agent scope adjustments by project type:**
- **backend_only**: code-reviewer skips UI review, qa-engineer skips frontend tests, performance-optimizer focuses on API/DB
- **frontend_only**: code-reviewer skips backend review, qa-engineer skips backend tests, performance-optimizer focuses on bundle/render
- **fullstack/mobile**: all agents review their full scope

## 📚 Prerequisites
- All Phase 3 features implemented, integrated, and individually approved
- API contract at `ref:current-phase.yaml → api_contract_path` (for contract compliance verification)
- Individual feature tests passing
- User approval for all individual features

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
  - API contract compliance verification (ref:{api_contract_path})
  - Documentation completeness
  - Maintainability assessment

# Acceptance Regression Suite
pm-maestro-reviewer: ref:roadmap.yaml → docs/acceptance-reports/regression-report.md
  - Re-run ALL acceptance tests from Phase 3 as regression
  - Verify no cross-feature regressions introduced
  - Produce consolidated acceptance regression report

# Performance Analysis (If Issues Found)
performance-optimizer: analyze and optimize → docs/performance-report.md
  - Frontend performance optimization (skip for backend_only)
  - Backend API performance tuning (skip for frontend_only)
  - Database query optimization (skip for frontend_only)
  - Bundle size optimization (skip for backend_only)
  - Memory usage analysis
```

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
  - pm-maestro-reviewer: acceptance regression suite
  - performance-optimizer: optimization (if needed, scope based on project_type)

Review & Approval:
  - Present all reports to user
  - Address any critical issues found
  - Wait for explicit user approval

Outcome:
  - PASS: Proceed to Phase 5 (Launch)
  - ISSUES FOUND: Fix issues and repeat Phase 4
```

## ➡️ Phase Transition
When all quality gates pass and user approves:
1. Update `current-phase.yaml` to `phase: 5`
2. Proceed to Launch Phase
3. Load `ref:phases/phase-5-launch.md` for next phase instructions

---
**Phase 4 Complete** → **Phase 5: Launch**
