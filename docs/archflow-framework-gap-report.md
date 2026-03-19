# Archflow Framework Gap Report

**Date**: 2026-03-16
**Auditor**: Claude Opus 4.6 (manual audit of framework files + real-world failure analysis)
**Project Audited**: archflow-studio (Drop 1 implementation)
**Archflow Version**: 1.0.0 (installed at `~/.claude/plugins/cache/archflow/archflow/1.0.0/`)

---

## Executive Summary

The Archflow framework has **8 structural gaps** that allowed a complete bypass of git workflow, subtask tracking, approval gates, and acceptance testing during the archflow-studio Phase 3 implementation. The root cause is systemic: **governance rules are documented as aspirational text but have no enforcement mechanism**. Agents receive no end-of-task responsibilities, phase transitions have no validation checklists, and critical workflows (git branching, acceptance testing) are only triggered by optional commands.

**Compliance score for archflow-studio Phase 3**: 6.25% (1 of 8 requirements met)

**Files audited**:
- `~/.claude/CLAUDE.md` (main framework instructions)
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/skills/archflow/SKILL.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/skills/archflow/commands/feature.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/.archflow/phases/phase-3-implementation.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/.archflow/workflow.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/agents/ui-engineer.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/agents/api-engineer.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/agents/qa-engineer.md`
- `~/.claude/plugins/cache/archflow/archflow/1.0.0/agents/pm-maestro-reviewer.md`

---

## Gap 1: Git Not Initialized at Project Start

### Severity: CRITICAL

### What happened
The entire project went from Phase 1 through Phase 3 (75% of Drop 1 implemented) with zero git infrastructure. No repository was initialized, no commits were made. Strategy documents, design artifacts, API contracts, roadmaps — none of it was version-controlled. The entire branching strategy from `workflow.md` was silently bypassed.

### Where the rule exists
- **`phase-3-implementation.md` lines 37-49**: "Git Workflow Integration: Each feature follows the branching strategy from `.archflow/workflow.md`"
- **`feature.md` lines 180-245**: Step 3 creates feature branches, Step 4 creates task branches
- **`workflow.md` lines 28-48**: Complete branching hierarchy (feature → task → subtask branches)

### Why it failed
1. Git initialization is NOT part of `/archflow init` or `/archflow onboard` — it should be
2. Phases 1-2.5 produce critical artifacts (project-context.md, roadmap.yaml, styled-dsl.yaml, api-contract.md, hi-fi screens) that are never committed
3. Phase 3 instructions **assume** git exists but **never verify** it
4. No phase — including Phase 1 — has a "Step 0: Initialize git" instruction
5. If a user starts a project without git, the framework silently continues through ALL phases without version control

### Core principle
**Git must be initialized at the very beginning of the Archflow workflow — during `/archflow init` or `/archflow onboard`.** ALL artifacts from ALL phases should be tracked in git, not just Phase 3 implementation code. Phases 1-2.5 work directly on `main` (no branching needed for planning/design). Phase 3+ uses the feature branch workflow from `workflow.md`.

### What needs to be fixed

#### In `/archflow init` (commands/init.md)
Add git initialization as the FIRST step, before creating `.archflow/`:

```markdown
## Step 0: Initialize Git (MANDATORY)

Before creating any Archflow files:

1. Check if git is already initialized:
   ```bash
   git rev-parse --is-inside-work-tree 2>/dev/null
   ```

2. If NOT initialized:
   ```bash
   git init
   ```
   Ask user: "Initialize git repository? [Yes / No]"
   - If Yes: `git init` (already done above)
   - If No: WARN "Archflow strongly recommends git for tracking all phase artifacts.
     Proceeding without git — you can initialize later with `git init`."

3. After `.archflow/` files are created, make the initial commit:
   ```bash
   git add .archflow/
   git commit -m "chore: initialize archflow (Phase 1)"
   ```

4. If git remote exists, push:
   ```bash
   git remote -v && git push origin main
   ```
```

#### In `/archflow onboard` (commands/onboard.md)
Add the same git check at the start of the onboarding wizard:

```markdown
## Step 0: Verify Git

1. Check: Is this a git repository?
   - If YES: Good, continue
   - If NO: Initialize git:
     ```bash
     git init
     git add .
     git commit -m "chore: initial commit before archflow onboarding"
     ```

2. After onboarding creates `.archflow/` files:
   ```bash
   git add .archflow/
   git commit -m "chore: onboard to archflow (Phase [N])"
   ```
```

#### In ALL phase files (phase-1 through phase-5)
Add a commit step at the END of each phase, before transition:

```markdown
## Phase Completion: Commit Artifacts

Before transitioning to the next phase, commit all artifacts produced:

### Phase 1 (Strategy):
```bash
git add .archflow/project-context.md .archflow/roadmap.yaml
git commit -m "docs: complete Phase 1 - strategy and roadmap"
```

### Phase 2 (Design):
```bash
git add design-artifacts/
git commit -m "docs: complete Phase 2 - wireframes, theme, styled-dsl"
```

### Phase 2.25 (Hi-Fi Design):
```bash
git add superdesign/
git commit -m "docs: complete Phase 2.25 - hi-fi design screens"
```

### Phase 2.5 (API Architecture):
```bash
git add docs/api-contract.md
git commit -m "docs: complete Phase 2.5 - API contract"
```

### Phase 3 (Implementation):
Git branching workflow per workflow.md — feature/task/subtask branches

### Phase 4+ (Quality/Launch):
Continue on feature branch or main per workflow
```

#### In `~/.claude/CLAUDE.md`
Add to the "Universal Critical Rules" section:

```markdown
### Git Version Control (ALL Phases)
- **GIT FROM DAY ONE**: `/archflow init` and `/archflow onboard` MUST initialize git
- **COMMIT AFTER EVERY PHASE**: All artifacts committed before phase transition
- **Phases 1-2.5**: Work directly on `main` branch (planning/design artifacts)
- **Phase 3+**: Feature branch workflow per `.archflow/workflow.md`
- **FEATURE BRANCH REQUIRED (Phase 3+)**: Implementation must happen on a feature branch, never on main
- **VALIDATE BEFORE STARTING Phase 3**: Run `git status` before any agent dispatch
```

#### In `phase-3-implementation.md`
Add pre-flight validation at the top:

```markdown
## Step 0: Phase 3 Pre-Flight Validation (MANDATORY)

Before ANY implementation work begins, validate these prerequisites.
If ANY check fails, HALT and fix before proceeding.

### 0.1 Git Repository
Run: `git status`
- If git is NOT initialized:
  HALT: "Git is required. Run `git init && git add . && git commit -m 'Initial commit'`"
- Verify main branch has commits from Phases 1-2.5:
  `git log --oneline | head -5` should show strategy/design/contract commits

### 0.2 Feature Branch
Check: `.archflow/current-feature.yaml` exists AND `branch` field is NOT "main"
- If missing or branch is "main":
  HALT: "Run `/archflow feature` to create the feature branch before implementing."

### 0.3 API Contract (fullstack/backend_only projects)
Check: `docs/api-contract.md` exists
- If missing: HALT: "Complete Phase 2.5 first."

### 0.4 Design Artifacts (fullstack/frontend_only/mobile projects)
Check: `design-artifacts/styled-dsl.yaml` exists
- If missing: HALT: "Complete Phase 2 first."

### 0.5 Codemap
Check: `.codemap/` directory exists
- If missing: Run `codemap init .`
- Start watcher: `pgrep -f "codemap watch" > /dev/null || codemap watch . -q &`

All checks passed → proceed to Step 1.
```

#### In `feature.md` Step 3 (Git Workflow Setup)
Add git validation:

```markdown
### Step 3: Git Workflow Setup

**Pre-check: Verify git is available**
```bash
# Verify git is initialized (should be from /archflow init)
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  echo "ERROR: Git not initialized. Run 'git init' first."
  exit 1
fi

# Verify we're on main before creating feature branch
git checkout main
git pull origin main 2>/dev/null || true
```

If git is not initialized, HALT — do not proceed without git.
```

---

## Gap 2: Subtask Completion Not Tracked

### Severity: HIGH

### What happened
6 stories were marked `status: done` in `roadmap.yaml`, but 5 of them had ALL subtasks still showing `completed: false`. Only D1-01 had subtasks properly marked. The roadmap showed 0% subtask completion for stories that were 100% implemented.

### Where the rule exists
- **`workflow.md` lines 105-108**: "Step 8: Update tracking documentation — Mark subtask as 'Complete'"
- **`phase-3-implementation.md` lines 144-157**: "Update `.archflow/current-feature.yaml`: mark task complete"
- **`feature.md` lines 249-293**: Task-level git workflow references updating tracking

### Why it failed
1. `workflow.md` says "mark subtask as complete" but doesn't specify WHERE — `roadmap.yaml`? `current-feature.yaml`? Both?
2. `current-feature.yaml` schema (defined in `feature.md` lines 217-228) has NO subtask tracking — only task-level status
3. `roadmap.yaml` HAS subtask fields (`completed: true/false`) but NO instruction tells agents to update them
4. Agent specs (ui-engineer, api-engineer) contain ZERO references to updating roadmap.yaml subtasks
5. When the orchestrator marks a story "done", it only changes `status: done` — it doesn't iterate through subtasks

### What needs to be fixed

#### In `workflow.md`
Replace the vague "Step 8: Update tracking documentation" with explicit instructions:

```markdown
## Step 8: Update Tracking Documentation

After completing a subtask, update BOTH files:

### 8.1 Update roadmap.yaml
Find your story → subtasks array → your subtask:
```yaml
subtasks:
  - text: "Your subtask description"
    completed: true    # ← Change from false to true
```

### 8.2 Update current-feature.yaml
Find your task → update status and progress:
```yaml
tasks:
  - id: "1"
    name: "Your task"
    status: "in_progress"  # or "complete" if ALL subtasks done
    completed_subtasks: 5   # increment this counter
    total_subtasks: 7
```

### 8.3 Commit the tracking update
```bash
git add .archflow/roadmap.yaml .archflow/current-feature.yaml
git commit -m "docs: mark subtask complete - [subtask description]"
```

IMPORTANT: Do this AFTER each subtask, not at the end of the story.
```

#### In `current-feature.yaml` schema (feature.md lines 217-228)
Extend the schema to include subtask tracking:

```yaml
# Current schema (feature.md line 217-228):
tasks:
  - id: "1"
    name: "{task_1}"
    type: "{frontend|backend}"
    status: pending
    branch: null

# PROPOSED schema:
tasks:
  - id: "1"
    name: "{task_1}"
    type: "{frontend|backend}"
    status: pending           # pending | in_progress | complete
    branch: null
    subtasks_completed: 0     # NEW: count of completed subtasks
    subtasks_total: 0         # NEW: total subtasks from roadmap
    started_at: null          # NEW: ISO timestamp
    completed_at: null        # NEW: ISO timestamp
```

#### In agent specs
Add to EVERY implementation agent (ui-engineer.md, api-engineer.md):

```markdown
## Tracking Responsibilities

After completing your implementation work:

1. Update `.archflow/roadmap.yaml`:
   - Find your story by ID
   - Mark each subtask you completed as `completed: true`
   - Do NOT change the story `status` field (the orchestrator does that)

2. Commit the tracking update:
   ```bash
   git add .archflow/roadmap.yaml
   git commit -m "docs: mark subtasks complete for [story-id]"
   ```

3. Report your subtask completion in your response:
   "Subtasks completed: [list]. Remaining: [list]."
```

#### In `phase-3-implementation.md`
Add after the agent dispatch section:

```markdown
### Post-Agent Verification

After an agent returns from implementing a story:

1. Verify roadmap.yaml subtasks are updated:
   - Count subtasks with `completed: true` for the story
   - If count doesn't match agent's claimed completion, update manually

2. Only mark story `status: done` when:
   - ALL subtasks are `completed: true`
   - Tests pass (qa-engineer)
   - Acceptance verdict is ACCEPTED (pm-maestro-reviewer)
   - User has explicitly approved

3. NEVER mark a story "done" by only changing the status field.
   The subtasks must reflect reality.
```

---

## Gap 3: Git Workflow Only Triggered by `/archflow feature`

### Severity: HIGH

### What happened
The user said "implement D1-04" and the orchestrator launched a ui-engineer agent directly — without running `/archflow feature` first. No task branch was created. The agent wrote code directly in the working directory with no git branch isolation.

### Where the rule exists
- **`CLAUDE.md` line 45**: "Use `/archflow feature` to create feature branches and track tasks"
- **`feature.md` lines 180-245**: Step 3-4 define the full branching workflow
- **`phase-3-implementation.md` lines 37-49**: "Feature branch should already exist (created by `/archflow feature` command)"

### Why it failed
1. Git branching is ONLY implemented inside the `/archflow feature` skill command
2. Phase 3 instructions say to use `/archflow feature` but don't ENFORCE it
3. If a user asks to implement a story directly (without the command), agents start coding immediately
4. No check in agent dispatch that verifies: "Is there a branch for this task?"

### What needs to be fixed

#### In `phase-3-implementation.md`
Add to the agent dispatch section:

```markdown
### Pre-Dispatch Validation (BEFORE launching any agent)

Before dispatching ui-engineer, api-engineer, or any implementation agent:

1. Check: Is `.archflow/current-feature.yaml` present?
   - If NO: Run `/archflow feature` first to set up the feature

2. Check: Does a task branch exist for this story?
   ```bash
   TASK_BRANCH=$(grep "branch:" .archflow/current-feature.yaml | grep "[story-id]")
   ```
   - If NO branch: Create it per workflow.md:
     ```bash
     git checkout [feature-branch]
     git checkout -b [feature]/[task-name]
     ```
   - Update current-feature.yaml with the branch name

3. Check: Is the working tree clean?
   ```bash
   git status --porcelain
   ```
   - If dirty: Commit or stash before switching branches

ONLY THEN dispatch the agent with: "Work on branch [branch-name]"
```

#### In `CLAUDE.md`
Add to Universal Critical Rules:

```markdown
### Branch-Before-Code (Phase 3+)
- **NEVER write implementation code without a task branch**
- Before dispatching ANY implementation agent, verify:
  1. Feature branch exists in current-feature.yaml
  2. Task branch exists for the story being implemented
  3. Working tree is on the correct branch
- If any of these fail: run `/archflow feature` or create branches manually
```

---

## Gap 4: Approval Gates Are Documented But Not Enforced

### Severity: CRITICAL

### What happened
Stories D1-01 through D1-06 were marked "done" without formal user approval. No demos were presented. No approval was recorded. The orchestrator changed `status: done` in roadmap.yaml as a unilateral action.

### Where the rule exists
- **`CLAUDE.md` lines 109-112**: "USER APPROVAL REQUIRED: Stop and wait for explicit user approval after EVERY phase... DEMO REQUIRED... NO PHASE SKIPPING"
- **`workflow.md` lines 84-89**: "Step 5: Wait for EXPLICIT user approval — CRITICAL: Do NOT merge until user EXPLICITLY approves"
- **`phase-3-implementation.md` lines 174-195**: "DEMO REQUIRED: Working feature must be demonstrated... USER APPROVAL MANDATORY"

### Why it failed
1. These rules are written as documentation — there is no MECHANISM to enforce them
2. Agents have no instruction saying "STOP after your work and present for approval"
3. The orchestrator can mark stories done without a blocking approval step
4. No field in roadmap.yaml or current-feature.yaml records whether approval was given
5. Phase 3 says "Wait for explicit user approval" but doesn't define WHAT the agent should DO — should it pause? Ask a question? Output a specific format?

### What needs to be fixed

#### In `phase-3-implementation.md`
Add a new mandatory step between implementation and merge:

```markdown
## Step 3F: APPROVAL GATE (MANDATORY — CANNOT BE SKIPPED)

After an agent completes a story AND acceptance testing passes:

1. Present the following to the user:
   ```
   ============================================
   APPROVAL REQUIRED: [Story ID] — [Story Title]
   ============================================

   Branch: [task-branch-name]
   Agent: [agent-name]

   Completed subtasks:
   - [x] Subtask 1
   - [x] Subtask 2
   - [x] Subtask 3

   Acceptance: [ACCEPTED / verdict from pm-maestro-reviewer]
   Test results: [X/Y tests passing]

   Files changed:
   - src/components/NewComponent.tsx (new)
   - src/store/studioStore.ts (modified)

   Please review and respond with:
   - "Approved" → merge to feature branch
   - "Changes needed: [feedback]" → agent will address
   ============================================
   ```

2. WAIT for the user to respond. Do NOT proceed.

3. If user says "Approved":
   - Merge per workflow.md Step 6-7
   - Update roadmap.yaml: story status → done, ALL subtasks → completed: true
   - Update current-feature.yaml: task status → complete
   - Commit: "feat: complete [story-id] - [title]"

4. If user says "Changes needed":
   - Parse feedback
   - Re-dispatch agent with feedback
   - Re-run acceptance testing
   - Return to step 1

5. Record approval in roadmap.yaml:
   ```yaml
   - id: D1-04
     status: done
     approved_by: user          # NEW FIELD
     approved_at: "2026-03-16"  # NEW FIELD
   ```
```

#### In agent specs (ALL implementation agents)
Add to the END of every agent spec:

```markdown
## End-of-Task Protocol

When you have completed your implementation:

1. DO NOT mark any story as "done" — only the orchestrator does this after user approval
2. Present a completion summary:
   - What you built
   - Files created/modified
   - Tests you ran
   - Any issues or notes
3. State: "Ready for review. Awaiting user approval."
4. STOP — do not proceed to the next task
```

#### In `roadmap.yaml` story schema
Add approval tracking fields:

```yaml
# Add to the story schema documentation:
stories:
  - id: D1-01
    title: "..."
    status: done
    approved: true              # NEW: was this explicitly approved?
    approved_at: "2026-03-16"   # NEW: when was it approved?
```

---

## Gap 5: "ONE FEATURE AT A TIME" Rule Has No Enforcement

### Severity: HIGH

### What happened
D1-05 (Chat Panel) and D1-06 (Markdown Viewer) were launched in parallel as simultaneous background agents. This violated the "ONE FEATURE AT A TIME" rule.

### Where the rule exists
- **`CLAUDE.md` line 136**: "ONE FEATURE AT A TIME: Never batch features in Phase 3"
- **`phase-3-implementation.md` lines 182-185**: "Feature Isolation: ONE FEATURE AT A TIME — never batch multiple features"

### Why it failed
1. The rule exists as text but has no enforcement mechanism
2. `CLAUDE.md` also says (line 130): "AGENT TEAMS: For Phase 3+ features, launch ui-engineer and api-engineer simultaneously when both have clear, independent scopes"
3. These two rules CONTRADICT each other — one says "one at a time", the other says "launch simultaneously"
4. The orchestrator interpreted "one feature at a time" as "one FEATURE" but treated stories within a feature as parallelizable
5. No validation prevents multiple stories from being `in_progress` simultaneously

### What needs to be fixed

#### In `CLAUDE.md`
Clarify the contradiction between parallel agents and sequential features:

```markdown
### Feature and Story Execution Rules (Phase 3+)

**FEATURE level**: ONE feature at a time. Complete all stories in a feature
before starting the next feature.

**STORY level**: ONE story at a time within a feature. Complete the full cycle
(implement → test → accept → approve → merge) before starting the next story.

**AGENT level within a story**: ui-engineer and api-engineer CAN run in
parallel IF the story has independent frontend and backend scopes defined
in the API contract. This is parallelism WITHIN a single story, not across stories.

Examples:
- ALLOWED: D1-04 frontend + D1-04 backend agents in parallel (same story)
- NOT ALLOWED: D1-05 + D1-06 agents in parallel (different stories)
- NOT ALLOWED: Feature A + Feature B in parallel (different features)
```

#### In `phase-3-implementation.md`
Add validation before story dispatch:

```markdown
### Story Serialization Check

Before starting work on a new story:

1. Check roadmap.yaml: Are there any stories with `status: in_progress`?
   - If YES and it's a DIFFERENT story: HALT
     "Story [X] is still in progress. Complete it before starting [Y]."
   - If YES and it's the SAME story: Continue (resuming work)
   - If NO: Proceed

2. Only ONE story may have `status: in_progress` at a time within a feature

3. Exception: Frontend + backend tasks of the SAME story may run in parallel
   if they have independent scopes per the API contract
```

---

## Gap 6: Acceptance Testing Not Auto-Triggered

### Severity: HIGH

### What happened
Only 3 of 6 done stories received acceptance testing (D1-01, D1-02, D1-04 — and that was a manual curl-based report, not Maestro). Stories D1-05, D1-06 had no acceptance testing at all. pm-maestro-reviewer was only invoked when explicitly requested.

### Where the rule exists
- **`CLAUDE.md` lines 103-107**: "ACCEPTANCE GATE: After qa-engineer completes, launch pm-maestro-reviewer"
- **`phase-3-implementation.md` lines 134-142**: "Step 3D: ACCEPTANCE TESTING"
- **`CLAUDE.md` line 105**: "VERDICT REQUIRED: Feature is not complete until pm-maestro-reviewer returns ACCEPTED verdict"

### Why it failed
1. Acceptance testing is listed as "Step 3D" but nothing in the orchestration flow TRIGGERS it automatically
2. pm-maestro-reviewer agent has to be manually invoked — there's no hook that says "after qa-engineer → dispatch pm-maestro-reviewer"
3. The `CLAUDE.md` says "After qa-engineer completes, launch pm-maestro-reviewer" but this is in a reference section, not in the agent dispatch logic
4. qa-engineer itself has no instruction to trigger pm-maestro-reviewer after tests pass
5. No blocking gate prevents marking a story "done" without an acceptance report

### What needs to be fixed

#### In `phase-3-implementation.md`
Make the acceptance flow explicit and sequential:

```markdown
## Step 3C-3D: Testing Pipeline (SEQUENTIAL — CANNOT SKIP STEPS)

### Step 3C: Quality Testing
Dispatch qa-engineer:
- Scope: The story just implemented
- Output: Test files in tests/ or __tests__/
- Gate: ALL tests must pass before Step 3D

If tests FAIL:
  → Re-dispatch implementation agent with failure details
  → Re-run qa-engineer
  → Do NOT proceed to Step 3D

### Step 3D: Acceptance Testing (AUTO-TRIGGERED after Step 3C passes)

IMMEDIATELY after qa-engineer reports all tests passing:
  → Dispatch pm-maestro-reviewer with:
    - Story ID from roadmap.yaml
    - Acceptance criteria from the story
    - Running app URL (if applicable)
  → Output: docs/acceptance-reports/{story-id}-review.md

If verdict is REJECTED:
  → Parse blocking defects from the report
  → Re-dispatch implementation agent to fix
  → Re-run qa-engineer (Step 3C)
  → Re-run pm-maestro-reviewer (Step 3D)
  → Do NOT proceed until ACCEPTED

If verdict is ACCEPTED:
  → Proceed to Step 3F (Approval Gate)
  → Include acceptance report in the approval presentation

IMPORTANT: Step 3D is NOT optional. A story cannot be marked "done"
without an ACCEPTED verdict in docs/acceptance-reports/.
```

#### In qa-engineer agent spec
Add:

```markdown
## Integration with Acceptance Testing

After your test suite is complete and ALL tests pass:

1. Report: "All [X] tests passing. Ready for acceptance testing."
2. The orchestrator will automatically dispatch pm-maestro-reviewer next.
3. Do NOT mark the story as "done" — acceptance testing must pass first.

If tests fail:
1. Report which tests fail and why
2. Do NOT trigger acceptance testing
3. Wait for implementation agent to fix the issues
```

#### In `CLAUDE.md` Universal Critical Rules
Add:

```markdown
### Testing Pipeline (Phase 3+)
- **SEQUENTIAL**: qa-engineer → pm-maestro-reviewer → approval gate
- **NO SKIPPING**: Cannot skip qa-engineer or pm-maestro-reviewer
- **AUTO-TRIGGER**: pm-maestro-reviewer launches automatically after qa-engineer passes
- **BLOCKING**: Story cannot be "done" without ACCEPTED verdict in docs/acceptance-reports/
```

---

## Gap 7: Phase Transition Has No Validation Checklist

### Severity: HIGH

### What happened
Phase 2.5 → Phase 3 transition happened without verifying prerequisites. The `api_contract_path` field was never set in `current-phase.yaml`. Phase files in `.archflow/phases/` didn't exist in the project (only in the plugin directory).

### Where the rule exists
- **`CLAUDE.md` lines 138-159**: "Phase Transition Workflow: 1. Validate all completion criteria met"
- **Each phase file has a "Completion Criteria" section** but no mechanism to CHECK them

### Why it failed
1. "Validate all completion criteria met" is a one-liner with no specification of WHAT criteria or HOW to validate
2. Each phase file defines completion criteria, but the transition logic doesn't READ those criteria
3. No automated check compares "what exists" against "what's required"
4. The current-phase.yaml update is a simple field change with no validation

### What needs to be fixed

#### Create phase transition validation files
Add to each phase instruction file a machine-readable completion checklist:

```markdown
## Phase Completion Checklist (Machine-Readable)

```yaml
phase_completion:
  phase: 2.5
  next_phase: 3
  required_artifacts:
    - path: "docs/api-contract.md"
      description: "API contract document"
      check: "file_exists"
    - path: ".archflow/roadmap.yaml"
      description: "Roadmap with stories defined"
      check: "file_exists"
  required_state:
    - field: "current_phase.yaml → phases_completed"
      must_include: [1, 2, 2.25, 2.5]
    - field: "current_phase.yaml → status"
      must_equal: "completed"
  required_approvals:
    - "User approved Phase 2.5 outputs"
  git_requirements:
    - "git repository initialized"
    - "main branch exists"
```
```

#### In `CLAUDE.md` Phase Navigation System
Replace the current transition workflow with:

```markdown
### Phase Transition Workflow (ENFORCED)

1. Read current phase's completion checklist (from phase file)
2. For each required artifact: verify file exists
3. For each required state: verify field values
4. For each required approval: verify user gave explicit approval
5. If ANY check fails:
   HALT: "Cannot transition to Phase [N]. Missing: [list of failures]"
6. If ALL checks pass:
   - Present completion summary to user
   - Wait for explicit "Approved, advance to Phase [N]"
   - Update current-phase.yaml
   - Load next phase instructions
```

---

## Gap 8: Agent Specs Have No End-of-Task Responsibilities

### Severity: HIGH

### What happened
Implementation agents (ui-engineer, api-engineer) wrote code and returned results, but never:
- Updated subtask completion in roadmap.yaml
- Committed to a task branch (no git)
- Presented work for user approval
- Triggered the next step in the pipeline (qa-engineer)

### Where the rule exists
- Agent specs describe WHAT to build but not what to do AFTER building
- `workflow.md` Step 5-8 describe post-implementation steps but agents don't read workflow.md
- Phase 3 orchestration (lines 144-157) describes the merge flow but from the ORCHESTRATOR's perspective, not the AGENT's

### Why it failed
1. Agent specs (ui-engineer.md, api-engineer.md) end with implementation instructions — no "after you finish" section
2. Agents don't know about workflow.md, current-feature.yaml, or the approval gate
3. The orchestrator dispatches agents with implementation prompts but doesn't include "and then update tracking files"
4. Result: agents write code → return → orchestrator moves on without tracking

### What needs to be fixed

#### Add to EVERY implementation agent spec

Add a new section at the END of each agent spec file:

**For `agents/ui-engineer.md`** — append:

```markdown
## Phase 3 Completion Protocol

When you finish implementing a story or task during Phase 3:

### 1. Update Subtask Tracking
For each subtask you completed, update `.archflow/roadmap.yaml`:
```yaml
subtasks:
  - text: "The subtask you completed"
    completed: true     # ← Set this to true
```

### 2. Git Commit (if git is available)
```bash
# Stage your implementation files
git add src/ [other directories you modified]

# Stage tracking update
git add .archflow/roadmap.yaml

# Commit with descriptive message
git commit -m "feat([story-id]): [brief description of what you built]"
```

### 3. Present Completion Summary
Include in your response:
```
IMPLEMENTATION COMPLETE

Story: [ID] — [Title]
Files created: [list]
Files modified: [list]
Subtasks completed: [X/Y]
  - [x] Subtask 1
  - [x] Subtask 2
  - [ ] Subtask 3 (not in scope for this agent)

Ready for: qa-engineer testing → acceptance testing → user approval
```

### 4. Do NOT:
- Mark the story status as "done" (orchestrator does this after approval)
- Merge branches (requires user approval first)
- Start the next story (one at a time)
- Skip the completion summary
```

**For `agents/api-engineer.md`** — append the same protocol, adapted:

```markdown
## Phase 3 Completion Protocol

[Same structure as ui-engineer but with backend-specific file paths]

### 2. Git Commit
```bash
git add server/ [backend directories]
git add .archflow/roadmap.yaml
git commit -m "feat([story-id]): [backend implementation description]"
```

### Additional: API Contract Verification
Before presenting completion, verify:
- All endpoints match docs/api-contract.md exactly
- Response shapes match TypeScript interfaces
- Error codes match the contract's error table

Include in summary: "API contract compliance: [X/Y endpoints verified]"
```

**For `agents/qa-engineer.md`** — append:

```markdown
## Phase 3 Completion Protocol

### After Tests Complete
If ALL tests pass:
1. Report: "All [X] tests passing across [Y] test files."
2. State: "Ready for acceptance testing (pm-maestro-reviewer)."
3. The orchestrator should automatically dispatch pm-maestro-reviewer next.

If tests FAIL:
1. Report which tests fail, with error messages
2. State: "Tests failing. Implementation agent needs to fix [list of issues]."
3. Do NOT trigger acceptance testing.
4. Wait for implementation fix, then re-run.

### Git Commit
```bash
git add src/__tests__/ server/__tests__/ [test directories]
git commit -m "test([story-id]): add test suite - [X] tests"
```
```

**For `agents/pm-maestro-reviewer.md`** — append:

```markdown
## Phase 3 Completion Protocol

### After Acceptance Testing
1. Write report to: `docs/acceptance-reports/{story-id}-review.md`
2. Include VERDICT: ACCEPTED or REJECTED
3. If ACCEPTED: "Story [ID] is ready for user approval."
4. If REJECTED: List blocking defects that must be fixed.

### Git Commit
```bash
git add docs/acceptance-reports/
git commit -m "docs([story-id]): acceptance report - [ACCEPTED/REJECTED]"
```
```

---

## Gap Summary: Fix Priority Matrix

| Priority | Gap | Files to Modify | Effort |
|----------|-----|-----------------|--------|
| **P0** | Gap 1: Git from day one | init.md, onboard.md, ALL phase files, phase-3-implementation.md, feature.md, CLAUDE.md | Large |
| **P0** | Gap 4: Approval gates | phase-3-implementation.md, ALL agent specs, CLAUDE.md | Large |
| **P1** | Gap 8: Agent responsibilities | ui-engineer.md, api-engineer.md, qa-engineer.md, pm-maestro-reviewer.md | Medium |
| **P1** | Gap 2: Subtask tracking | workflow.md, feature.md, phase-3-implementation.md, agent specs | Medium |
| **P1** | Gap 7: Phase transition | CLAUDE.md, ALL phase files | Medium |
| **P2** | Gap 5: Feature serialization | CLAUDE.md, phase-3-implementation.md | Small |
| **P2** | Gap 3: Git workflow enforcement | phase-3-implementation.md, CLAUDE.md | Small |
| **P2** | Gap 6: Acceptance auto-trigger | phase-3-implementation.md, qa-engineer.md, CLAUDE.md | Medium |

---

## Files That Need Changes

### Plugin Files (Framework Level)
These files define the Archflow framework itself:

```
~/.claude/plugins/cache/archflow/archflow/1.0.0/
├── .archflow/
│   ├── phases/
│   │   ├── phase-1-strategy.md          ← Gaps 1 (git commit), 7 (completion checklist)
│   │   ├── phase-2-design.md            ← Gaps 1 (git commit), 7 (completion checklist)
│   │   ├── phase-2.25-hifi-design.md    ← Gaps 1 (git commit), 7 (completion checklist)
│   │   ├── phase-2.5-api-architecture.md← Gaps 1 (git commit), 7 (completion checklist)
│   │   ├── phase-3-implementation.md    ← Gaps 1 (pre-flight), 3, 4, 5, 6, 7
│   │   ├── phase-4-quality.md           ← Gap 7 (completion checklist)
│   │   ├── phase-5-launch.md            ← Gap 7 (completion checklist)
│   │   └── [all phase files]            ← Gap 1 (commit artifacts before transition)
│   └── workflow.md                      ← Gap 2 (explicit subtask tracking)
├── skills/archflow/
│   ├── commands/
│   │   ├── init.md                      ← Gap 1 (initialize git as FIRST step)
│   │   ├── onboard.md                   ← Gap 1 (verify/initialize git)
│   │   └── feature.md                   ← Gaps 1, 2, 3, 5
│   └── SKILL.md                         ← No changes needed
├── agents/
│   ├── ui-engineer.md                   ← Gaps 4, 8
│   ├── api-engineer.md                  ← Gaps 4, 8
│   ├── qa-engineer.md                   ← Gaps 6, 8
│   └── pm-maestro-reviewer.md           ← Gap 8
└── [other files — no changes]
```

### Global Instructions
```
~/.claude/CLAUDE.md                      ← Gaps 1, 3, 4, 5, 6, 7
```

### Schema Changes
```
.archflow/current-feature.yaml schema   ← Gap 2 (add subtask tracking fields)
.archflow/roadmap.yaml story schema     ← Gap 4 (add approved/approved_at fields)
```

---

## Validation: How to Verify Fixes Work

After implementing these fixes, run this scenario to verify:

1. Create a new test project with `/archflow init`
   → Should initialize git automatically (`git init` + initial commit)
   → `.archflow/` files committed on main
2. Complete Phase 1 (Strategy)
   → `project-context.md` and `roadmap.yaml` committed on main
   → Phase transition commits: `docs: complete Phase 1`
3. Complete Phase 2 (Design)
   → `design-artifacts/` committed on main
   → Phase transition commits: `docs: complete Phase 2`
4. Complete Phase 2.5 (API Architecture)
   → `docs/api-contract.md` committed on main
   → `git log --oneline` should show commits from every phase
5. Run `/archflow feature` to start Phase 3
   → Creates feature branch from main
   → `current-feature.yaml` has branch != "main"
6. Attempt Phase 3 without feature branch → Should HALT with clear message
7. Implement ONE story → Agent should update subtasks, commit on task branch, present for approval
8. Attempt to start second story before first is approved → Should HALT
9. Approve first story → Should merge task branch to feature branch, update tracking
10. Implement second story → qa-engineer should auto-trigger pm-maestro-reviewer
11. Acceptance REJECTED → Should block progression, require fix
12. Acceptance ACCEPTED → Should allow approval gate
13. All stories done → Merge feature branch to main (with user approval)
14. Attempt Phase 4 transition → Should validate all stories done + all reports exist + all merged

If all 14 steps work correctly, the gaps are fixed.
