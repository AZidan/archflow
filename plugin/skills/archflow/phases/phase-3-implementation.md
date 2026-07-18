# Phase 3: Implementation (Build the Active Release)

## 🎯 Phase Objective
Build the stories of the ONE active release, one story at a time, honoring each story's readiness
pipeline. Frontend and backend build in parallel within a story via the API contract.

## 📋 Required Agents (Project-Type Aware)

Read `.archflow/current-phase.yaml` to determine `project_type` and select appropriate agents:

| Agent | fullstack | frontend_only | backend_only | mobile |
|-------|-----------|---------------|--------------|--------|
| `ui-engineer` | Yes | Yes | No | Yes |
| `api-engineer` | Yes | No | Yes | Yes |
| `qa-engineer` | Yes | Yes | Yes | Yes |

## 🧭 Work source (v2.0) — the ACTIVE RELEASE only

All build work comes from the one release currently `in_progress`:

- `.archflow/current-phase.yaml → active_release` = slug of the in_progress release.
- Stories live in `.archflow/releases/{active_release}.yaml` (see `release-schema.yaml`).
- `roadmap.yaml` is only the index — you never read `backlog.yaml` or other release files to select
  build work. An agent scoped to the active release file literally cannot see backlog / draft-release
  stories; that is the soft release boundary made structural.
- **If `active_release` is null** → HALT: "No release is being built. Transition a `ready` release to
  `in_progress` first (see Release start), or create one via feature-planner."

### Release start (transition ready → in_progress)
Before Phase 3 can run, exactly one release must be `in_progress`:
1. Pick a `ready` release from `roadmap.yaml → releases`.
2. **Gate: at most one `in_progress`.** If another release is already `in_progress`, HALT — finish or
   park it first.
3. Optional re-validation: reconcile the release against what has shipped since it was drafted (via
   `history.yaml`).
4. Set its `status: in_progress` in both the release file and the `releases` index; set
   `current-phase.yaml → active_release` to its slug.

## 🚦 Readiness pipeline (Pillar 2) — which stories are buildable

A story's `status` IS its readiness state. Phase 3 builds a story only once it is `ready` — all
*applicable* upstream gates satisfied:

- `gates: {needs_design, needs_contract}` (derived from scope).
- `needs_design: true` → requires `design_ready` (designer produced `design_artifact`) before build.
- `needs_contract: true` → requires `contract_ready` (architect specified endpoints) before build.
- `ready` = `spec_ready` AND (`design_ready` OR not needs_design) AND (`contract_ready` OR not needs_contract).

### Mode calibration
- **quick mode** → gates auto-satisfy. A story promoted into the release is buildable immediately; no
  gate prompts.
- **full mode** → gates enforced **advisory-recorded**. To build a story that is not yet `ready`:
  1. Warn which gate is unmet (e.g. "S2-07 needs_design but is only `spec_ready` — no design artifact").
  2. Ask to proceed anyway.
  3. If yes, stamp the story `started_ungated: {gate, by, reason, at: <iso8601>}` and proceed. The
     skip is recorded so review/QA can catch it. **Never a hard block** — the human keeps control.

## 📚 Prerequisites
- `active_release` set and its release file present.
- API contract at `.archflow/current-phase.yaml → api_contract_path` (SACRED DOCUMENT) for stories
  with `needs_contract`. May be `docs/api-contract.md`, `openapi.yaml`, etc. Null → no external APIs.
- `design-artifacts/` handoff for stories with `needs_design` (per-story `design_artifact`).
- User approval from the previous phase.

## 🚀 Execution Steps

### Step 0: Phase 3 Pre-Flight Validation (MANDATORY)

If ANY check fails, HALT and fix before proceeding.

#### 0.1 Git Repository
Run: `git status`
- NOT initialized → HALT: "Git is required. Run `git init && git add . && git commit -m 'Initial commit'`"
- Verify prior phase commits: `git log --oneline | head -5`

#### 0.2 Active Release
Check: `.archflow/current-phase.yaml → active_release` is set AND `.archflow/releases/{active_release}.yaml` exists
- Missing → HALT: "No active release. Start one (ready → in_progress) first."

#### 0.3 Feature Branch
Check: `.archflow/current-feature.yaml` exists AND `branch` field is NOT "main"
- Missing/main → HALT: "Run `/archflow feature` first."

#### 0.4 API Contract (stories with needs_contract)
Check: contract file exists at `api_contract_path`
- **fullstack / backend_only**: HALT if missing — "Complete Phase 2.5 (contract architecture) first."
- **frontend_only / mobile**: if `api_contract_path` is set, HALT if missing; if null, skip.

#### 0.5 Codemap
- `.codemap/` missing → `codemap init .`
- Watcher: `pgrep -f "codemap watch" > /dev/null || codemap watch . -q &`

All checks passed → proceed.

---

### 🔀 Git Workflow Integration
Each story follows the branching strategy in `.archflow/workflow.md` (feature → task → subtask
branches). Feature branch should already exist (from `/archflow feature`). All merges require
explicit user approval.

### ⚡ STORY-BY-STORY DEVELOPMENT (ONE AT A TIME)

- **ONE STORY AT A TIME**: complete the full cycle (build → test → accept → approve → merge) per story.
- **PARALLEL WITHIN A STORY**: ui-engineer + api-engineer CAN run in parallel for the SAME story only
  (independent scopes from the contract).

For EACH `ready` story in `.archflow/releases/{active_release}.yaml`, execute the process below.

### Story Serialization Check

Before starting a new story:
1. Read the active release file: any story with `status: in_progress`?
   - YES, DIFFERENT story → HALT: "Story [X] still in progress. Complete it first."
   - YES, SAME story → continue (resuming).
   - NO → proceed.
2. Only ONE story may be `in_progress` in the active release at a time.
3. Parallelism: ALLOWED — ui-engineer + api-engineer for the SAME story. NOT ALLOWED — agents for
   DIFFERENT stories in parallel.

### 🔁 Pull-forward (scope change mid-build)

If the work needs a story that is NOT in the active release (it's a stub in `backlog.yaml` or lives in
a draft release file):

1. STOP — the active release file doesn't contain it, and a release-scoped agent can't see it.
2. ASK: "S2-11 is in {backlog | q3-launch (draft)}, not this release. Pull it in?"
3. On approval, **MOVE** it into the active release (never copy):
   - from backlog → promote: remove the stub from `backlog.yaml`, add it to the release file, detail
     ACs + subtasks, derive `gates` from scope.
   - from a draft release → relocate the story block out of that file into the active release file.
   - annotate `pulled_from: {backlog | <release-id>}` on the story.
4. A story is never in two releases at once. Advisory, not a hard block.

### 🔎 Pre-modification history check (institutional memory)

Before an agent modifies an existing file, check `.archflow/history.yaml`:
1. Look up the concrete file path in the `touched.files` of any history entry.
2. If found, surface it: "`PaymentForm.tsx` last shipped for S3-04 (release checkout-redesign); its
   AC was 'declined payment shows inline error'. Confirm your change preserves that."
3. **Advisory** — confirm and proceed; never blocks. Purpose: stop silently breaking a shipped
   guarantee, or re-solving something already built.

`history.yaml` is loaded ONLY for this lookup, never scanned per step. codemap answers *where* the
code is; history answers *why it exists and what it was supposed to do*.

### 🔄 Step 3A: DEVELOPMENT

#### Mandatory Agent Delegation

The orchestrator (main Claude session) MUST NOT write application code directly. For every story:

1. **Read the `assigned` field** from the story in the active release file (e.g. `assigned: ui-engineer`).
2. **Launch that agent via the Agent tool** with story context (story ID, description, acceptance
   criteria, subtasks, `design_artifact` path if present, relevant file paths).
3. **Orchestrator role = coordination only**: dispatch agents, verify outputs, update the release
   file, manage git workflow.

**Exception — orchestrator may act directly when:** the work is interactive infrastructure (Docker,
live API calls, env setup, DB migrations needing shell interaction), or purely file-tracking updates
(release file status, current-feature.yaml). Document the reason in the commit if the orchestrator
writes application code.

**Enforcement:** if `assigned` names a specialized agent, delegation via the Agent tool is mandatory.
The orchestrator must NOT copy-paste or rewrite agent output. If an agent fails, re-launch with a
corrected prompt — do not take over.

---

**Before writing code, agents must** (run the pre-modification history check above, then):
```bash
# Check what already exists — avoid duplicating code
codemap find "[FeatureName]"
codemap find "related-symbol-name"
codemap show src/components/   # or relevant directory
```

**Project-type-aware agent dispatch:**

#### fullstack (parallel within the story)
```bash
# Frontend (uses the story's design_artifact + contract integration points)
ui-engineer: {design_artifact} + {api_contract_path} → src/components/[FeatureName]/
  - Build components using the contract for API integration points
  - Service layers matching contract endpoints exactly
  - Error handling for all contract-defined error codes

# Backend (CONTRACT SACRED!)
api-engineer: MUST READ + FOLLOW {api_contract_path} EXACTLY → backend/src/[feature-name]/
  - VERIFY endpoints, response structures, error codes, auth all match the contract
  - NO DEVIATIONS — ZERO TOLERANCE
```

#### frontend_only
```bash
ui-engineer: {design_artifact} → src/components/[FeatureName]/
  - If consuming external APIs: read {api_contract_path} for integration
```

#### backend_only
```bash
api-engineer: MUST READ + FOLLOW {api_contract_path} EXACTLY → backend/src/[feature-name]/
  - VERIFY endpoints + response structures match the contract — ZERO TOLERANCE
```

#### mobile
```bash
ui-engineer: {design_artifact} + {api_contract_path} → mobile components
api-engineer: {api_contract_path} → backend/src/[feature-name]/
```

### 🔗 Step 3B: INTEGRATION (skip for backend_only)
```bash
ui-engineer: {api_contract_path} → connect frontend ↔ backend
  - Test API calls against actual endpoints; verify data flow matches the contract
  - Handle all error scenarios; verify auth integration
```

### ✅ Step 3C: STORY TESTING
```bash
qa-engineer: test the integrated story → tests/[feature-name]/
  - Unit (frontend/backend per project type), integration, e2e, error scenarios
```
Gate: ALL tests must pass before Step 3D. If tests FAIL → re-dispatch the implementation agent with
details → re-run qa-engineer. Do NOT proceed.

### 🎯 Step 3D: ACCEPTANCE TESTING (auto-triggered after 3C passes)
IMMEDIATELY after qa-engineer reports all tests passing:
  → Dispatch pm-maestro-reviewer with story ID + acceptance criteria (from the release file)
  → Output: `docs/acceptance-reports/{story-id}-review.md`

If REJECTED → re-dispatch implementation agent → re-run 3C → re-run 3D. Do NOT proceed until ACCEPTED.
Step 3D is NOT optional. No story is "done" without an ACCEPTED verdict.

### Post-Agent Verification
After an agent returns:
1. Verify subtasks in the **active release file** are updated (count `completed: true`); if the count
   doesn't match the agent's claim, correct it.
2. Mark a story `status: done` only when ALL of: all subtasks `completed: true`; tests pass; acceptance
   ACCEPTED; user approved.
3. NEVER mark a story done by only changing the status field.
4. If the story carries `started_ungated`, call it out in the acceptance/approval summary so the skipped
   gate is reviewed before done.

### 🔀 Step 3E: GIT MERGE (per task)
After a task passes testing + acceptance:
1. Wait for explicit user approval.
2. Merge task branch → feature branch (per `.archflow/workflow.md`); clean up the task branch.
3. Update `.archflow/current-feature.yaml`: mark task complete.

### 🛑 Step 3F: APPROVAL GATE (MANDATORY — CANNOT BE SKIPPED)

After acceptance returns ACCEPTED, present to the user:
```
============================================
APPROVAL REQUIRED: [Story ID] — [Story Title]   (release: [active_release])
============================================
Branch: [task-branch-name]        Agent: [agent-name]
Readiness: [ready | started_ungated: <gate>]

Completed subtasks:
- [x] Subtask 1
- [x] Subtask 2

Acceptance: ACCEPTED        Tests: [X/Y passing]

Files changed:
- [list]

Respond with:
- "Approved" → merge to feature branch
- "Changes needed: [feedback]" → agent will address
============================================
```

WAIT for the user. Do NOT proceed.

If "Approved":
- Merge per workflow.md.
- Update the **active release file**: story `status: done`, all subtasks `completed: true`,
  `approved: true`, `approved_at: "[date]"`.
- Update current-feature.yaml: task `status: complete`, `completed_at: "[date]"`.

If "Changes needed": re-dispatch agent with feedback → re-run 3C → 3D → back to the gate.

## 📤 Expected Outputs (per story)
- Implementation per project type; comprehensive tests
- `docs/acceptance-reports/{story-id}-review.md`
- Working, integrated story ready for demo

## ✅ Completion Criteria (per story)
- [ ] Built by the assigned agent; readiness gates honored (or override recorded)
- [ ] API contract compliance (100% for endpoints that exist)
- [ ] Integration working (if applicable); all tests passing
- [ ] Acceptance ACCEPTED by pm-maestro-reviewer
- [ ] Git workflow completed; user approved

## 🚨 Critical Requirements
- **API Contract (ZERO TOLERANCE)**: api-engineer follows `{api_contract_path}` exactly — no deviations.
- **One story at a time**; complete the full cycle before the next.
- **All merges require explicit user approval** (per `.archflow/workflow.md`); never auto-merge.
- **Readiness gates are advisory-recorded in full mode**; auto-satisfied in quick mode.

## ➡️ Phase Transition
When ALL stories in the active release are `done` (tested + accepted + approved):
1. Update `.archflow/current-phase.yaml` to `phase: 4` (still scoped to the active release).
2. Load `.archflow/phases/phase-4-quality.md`.
(The release itself SHIPS in Phase 5 — mark released, tag, archive, append history, then prompt for
the next release.)

---
**Phase 3 Complete (active release built)** → **Phase 4: Quality**
