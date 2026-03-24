# Phase 2: Design

## 🎯 Phase Objective
Create user flows, visual design system, wireframes, and component specifications.

## 📋 Required Agents
- `ux-designer` - User flows + visual design + themes + wireframes
- `dsl-generator` - Screen DSL creation + styling + component specs

## 📚 Prerequisites
- Phase 1 outputs: `.archflow/project-context.md`, `.archflow/roadmap.yaml`
- User approval from Phase 1

## 🚀 Execution Steps

### Sequential Development
UX Designer creates foundation, then DSL Generator builds on it.

```bash
# Step 2A: UX Foundation
ux-designer: .archflow/project-context.md → design-artifacts/user-flows.md + design-artifacts/theme.yaml + design-artifacts/wireframes/

# Step 2B: Component Specifications  
dsl-generator: design-artifacts/wireframes/ → design-artifacts/styled-dsl.yaml
```

## 📤 Expected Outputs
- `design-artifacts/user-flows.md` - Complete user journey documentation
- `design-artifacts/theme.yaml` - Design system tokens (colors, typography, spacing)
- `design-artifacts/wireframes/` - Screen layouts and mockups
- `design-artifacts/styled-dsl.yaml` - Component specifications with styling

## ✅ Completion Criteria
- [ ] User flows documented for all major features
- [ ] Design system established with consistent tokens
- [ ] Wireframes created for all screens in roadmap
- [ ] Component DSL specifications completed
- [ ] Design artifacts validated and approved by stakeholders
- [ ] All designs align with business goals from Phase 1

## 🚨 Critical Requirements
- **REFERENCE PHASE 1**: All design decisions must reference `.archflow/project-context.md`
- **USER APPROVAL MANDATORY**: Present design artifacts to user and wait for explicit approval
- **NO PROCEEDING**: Do not move to Phase 2.5 without approval
- **CONSISTENCY**: Maintain design system consistency across all artifacts

## Phase Completion: Commit Artifacts

Before transitioning to the next phase, commit all artifacts:
```bash
git add design-artifacts/
git commit -m "docs: complete Phase 2 - wireframes, theme, styled-dsl"
```

## Phase Transition Validation

Before updating `current-phase.yaml`, verify:

1. **Artifacts exist**:
   - [ ] `design-artifacts/styled-dsl.yaml` exists
   - [ ] Design system files exist (e.g., `design-artifacts/theme.yaml`)

2. **Git state**:
   - [ ] All artifacts committed (`git status` shows clean tree)

3. **Approval**:
   - [ ] User explicitly approved phase outputs

If ANY check fails → HALT: "Cannot transition. Missing: [list]"
If ALL pass → update `current-phase.yaml` to next phase.

## ➡️ Phase Transition
Upon completion and approval:
1. Update `.archflow/current-phase.yaml` to `phase: 2.25`
2. Proceed to High-Fidelity Design Phase
3. Load `.archflow/phases/phase-2.25-hifi-design.md` for next phase instructions

---
**Phase 2 Complete** ✅ → **Phase 2.25: High-Fidelity Design** ➡️