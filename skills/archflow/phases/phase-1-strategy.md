# Phase 1: Strategy & Planning

## 🎯 Phase Objective
Define business strategy, user personas, and the product **backlog** to establish project foundation.
(Releases are carved from the backlog just-in-time, later — Phase 1 does NOT plan every release up front.)

## 📋 Required Agents
- `product-strategist` - Business strategy, user personas, KPIs, market positioning
- `feature-planner` - Backlog (full scope as stubs), epic labels, story breakdown

## 🚀 Execution Steps

### Parallel Development
Both agents work simultaneously to maximize efficiency.

```bash
# Run in parallel
product-strategist: define business goals + target personas + KPIs → project-context.md
feature-planner (Mode A): create the backlog stubs + epic labels → backlog.yaml + roadmap.yaml
```

## 📤 Expected Outputs
- `.archflow/project-context.md` - Business goals, tech stack, target users, success metrics
- `.archflow/roadmap.yaml` - Index: project meta, `mode`, epic labels, empty `releases:` pipeline
- `.archflow/backlog.yaml` - Full product scope as prioritized stubs (no ACs/subtasks yet)

## ✅ Completion Criteria
- [ ] Business strategy clearly defined with target market
- [ ] User personas documented with pain points
- [ ] Success metrics and KPIs established  
- [ ] Backlog captured as prioritized stubs; epics registered as labels in the index
- [ ] Technical stack decisions documented
- [ ] All outputs validated and approved by stakeholders

## 🚨 Critical Requirements
- **USER APPROVAL MANDATORY**: Present all outputs to user and wait for explicit approval
- **NO PROCEEDING**: Do not move to Phase 2 without approval
- **DOCUMENTATION**: All decisions must be captured in specified output files

## Phase Completion: Commit Artifacts

Before transitioning to the next phase, commit all artifacts:
```bash
git add .archflow/project-context.md .archflow/roadmap.yaml .archflow/backlog.yaml
git commit -m "docs: complete Phase 1 - strategy and backlog"
```

## Phase Transition Validation

Before updating `current-phase.yaml`, verify:

1. **Artifacts exist**:
   - [ ] `.archflow/project-context.md` exists
   - [ ] `.archflow/roadmap.yaml` exists (schema_version 2.0, has `mode` + epic labels)
   - [ ] `.archflow/backlog.yaml` exists (stubs)

2. **Git state**:
   - [ ] All artifacts committed (`git status` shows clean tree)

3. **Approval**:
   - [ ] User explicitly approved phase outputs

If ANY check fails → HALT: "Cannot transition. Missing: [list]"
If ALL pass → update `current-phase.yaml` to next phase.

## ➡️ Phase Transition
Upon completion and approval:
1. Update `.archflow/current-phase.yaml` to `phase: 2`
2. Proceed to Design Phase
3. Load `.archflow/phases/phase-2-design.md` for next phase instructions

---
**Phase 1 Complete** ✅ → **Phase 2: Design** ➡️