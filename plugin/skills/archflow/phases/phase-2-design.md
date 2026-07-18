# Phase 2: Design

## 🎯 Phase Objective
Design splits into TWO kinds of work (v2.0 — Pillar 2):

1. **Release foundation (once, at release start):** the design *system* — user flows, visual
   language, theme tokens, component library. Set up (or confirmed) once per release; informs every
   story. This is what the numbered Phase 2 pass below produces.
2. **Per-story design gate (continuous):** a specific story's *screens*, produced just-in-time one
   step ahead of its build. Writes the story's `design_artifact` and advances it to `design_ready`.
   This is the readiness-pipeline gate the engineer consumes in Phase 3 (see "Per-story design gate"
   below). Stories with `gates.needs_design: false` skip it entirely.

## 📋 Required Agents
- `ux-designer` - User flows + visual design + themes + wireframes (foundation) AND per-story screens (gate)
- `dsl-generator` - Screen DSL creation + styling + component specs

## 📚 Prerequisites
- Phase 1 outputs: `.archflow/project-context.md`, `.archflow/roadmap.yaml`, `.archflow/backlog.yaml`
- The active release (`.archflow/releases/{active_release}.yaml`) — its stories drive per-story design
- User approval from Phase 1

## 🚦 Per-story design gate (readiness pipeline)

For each story in the active release with `gates.needs_design: true`, run just-in-time (one step ahead
of that story's build):

```bash
ux-designer: {design-system} + story context → design-artifacts/{story-id}/
```
Then in the release file, set the story's `design_artifact: design-artifacts/{story-id}/` and advance
its `status` to `design_ready` (or `ready` if `needs_contract` is false / already met).

**Mode calibration:** in `quick` mode this gate auto-satisfies (no separate design step required); in
`full` mode it runs and produces the handoff. A designer can work these gates on a `ready` future
release's stories while an engineer builds the `in_progress` one.

## 🚀 Execution Steps

### Release foundation (once, at release start)
UX Designer creates the design-system foundation, then DSL Generator builds on it. This runs once per
release (or is confirmed unchanged when reusing an existing system).

```bash
# Step 2A: UX Foundation (design SYSTEM, not individual story screens)
ux-designer: .archflow/project-context.md → design-artifacts/user-flows.md + design-artifacts/theme.yaml + design-artifacts/wireframes/

# Step 2B: Component Specifications
dsl-generator: design-artifacts/wireframes/ → design-artifacts/styled-dsl.yaml
```

Per-*screen* design for individual stories does NOT happen here — it happens in the per-story design
gate above, just-in-time before each story's build.

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