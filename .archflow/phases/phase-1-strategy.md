# Phase 1: Strategy & Planning

## 🎯 Phase Objective
Define business strategy, user personas, and feature roadmap to establish project foundation.

## 📋 Required Agents
- `product-strategist` - Business strategy, user personas, KPIs, market positioning
- `feature-planner` - Feature roadmaps, user stories, epic breakdown, sprint planning

## 🚀 Execution Steps

### Parallel Development
Both agents work simultaneously to maximize efficiency.

```bash
# Run in parallel
product-strategist: define business goals + target personas + KPIs → project-context.md
feature-planner: create feature roadmap + user stories + sprint plan → roadmap.yaml
```

## 📤 Expected Outputs
- `.archflow/project-context.md` - Business goals, tech stack, target users, success metrics
- `.archflow/roadmap.yaml` - Prioritized feature list, development phases, timeline estimates

## ✅ Completion Criteria
- [ ] Business strategy clearly defined with target market
- [ ] User personas documented with pain points
- [ ] Success metrics and KPIs established  
- [ ] Feature roadmap prioritized and estimated
- [ ] Technical stack decisions documented
- [ ] All outputs validated and approved by stakeholders

## 🚨 Critical Requirements
- **USER APPROVAL MANDATORY**: Present all outputs to user and wait for explicit approval
- **NO PROCEEDING**: Do not move to Phase 2 without approval
- **DOCUMENTATION**: All decisions must be captured in specified output files

## ➡️ Phase Transition
Upon completion and approval:
1. Update `.archflow/current-phase.yaml` to `phase: 2`
2. Proceed to Design Phase
3. Load `.archflow/phases/phase-2-design.md` for next phase instructions

---
**Phase 1 Complete** ✅ → **Phase 2: Design** ➡️