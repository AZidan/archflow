# Phase: Onboarding (Existing Codebase)

This phase is loaded by `/onboard`. It contains audit logic, project type detection, backfill rules, and gap analysis for onboarding existing codebases into the phase-based framework.

---

## Project Type Detection

Detect the project type by scanning for structural indicators. Store the result in `current-phase.yaml` as `project_type`.

### Detection Rules

**fullstack**
- Indicators: `frontend/ + backend/`, `src/ + api/`, `package.json` with both React and Express/NestJS deps
- Applicable phases: 1, 2, 2.25, 2.5, 3, 4, 5, 6
- Agents: ui-engineer, api-engineer, qa-engineer, ux-designer, all others

**frontend_only**
- Indicators: `src/components/` without `backend/`, `next.config.*`, `vite.config.*`, only React/Vue/Angular deps
- Applicable phases: 1, 2, 2.25, 3, 4, 5, 6 (no 2.5 unless consuming external APIs)
- Agents: ui-engineer, qa-engineer, ux-designer
- Notes: api-engineer not used; skip backend audit checks

**backend_only**
- Indicators: No `src/components/`, no `frontend/`, only Express/NestJS/Fastify deps, Dockerfile without frontend build
- Applicable phases: 1, 2.5, 3, 4, 5, 6 (no 2, 2.25)
- Agents: api-engineer, qa-engineer
- Notes: Skip Phase 2 and 2.25 entirely; Phase 2.5 (API contract) is the primary design artifact

**mobile**
- Indicators: `ios/`, `android/`, `react-native` in deps, `flutter`, SwiftUI files, Jetpack Compose files
- Applicable phases: 1, 2, 2.25, 2.5, 3, 4, 5, 6
- Agents: ui-engineer, api-engineer, qa-engineer, ux-designer

### Impact on Workflow

The detected `project_type` controls:
- Which phases are applicable (skip N/A phases)
- Which agents are available (no ui-engineer for backend-only)
- Which audit checks run (don't flag missing design artifacts for backend-only)
- Roadmap structure (backend features = endpoints/services, frontend = pages/components)

---

## Audit Checklist

Each check targets a specific phase artifact. Checks are filtered by `project_type`.

### Phase 1 Artifacts (Strategy)

**project_context** (weight: core)
- Scan for: `project-context.md`, `README.md`, `docs/PRD.md`, `docs/requirements.md`
- Applicable to: all project types
- If found: mark Phase 1 as partial or complete
- If missing: flag for backfill in Step 4

**roadmap** (weight: core)
- Scan for: `roadmap.yaml`, `roadmap.md`, `docs/roadmap.*`
- Applicable to: all project types
- If found: mark Phase 1 as complete
- If missing: flag for backfill in Step 4

### Phase 2 Artifacts (Design)

**design_system** (weight: nice-to-have)
- Scan for: `design-artifacts/theme.yaml`, `design-artifacts/styled-dsl.yaml`, `tailwind.config.*`
- Applicable to: fullstack, frontend_only, mobile
- Skip for: backend_only

### Phase 2.5 Artifacts (API Architecture)

**api_contract** (weight: core)
- Scan for: `docs/api-contract.md`, `swagger.json`, `swagger.yaml`, `openapi.json`, `openapi.yaml`, `docs/openapi.*`, `docs/swagger.*`
- Applicable to: fullstack, backend_only, mobile
- **use_existing: true** — if found in any format, USE AS-IS (do not convert)
- Store found path in `current-phase.yaml` as `api_contract_path`

### Phase 3 Indicators (Implementation)

**frontend_code** (weight: indicator)
- Scan for: `src/`, `frontend/`, `app/`, `pages/`, `components/`
- Applicable to: fullstack, frontend_only, mobile

**backend_code** (weight: indicator)
- Scan for: `backend/`, `server/`, `api/`, `src/controllers/`, `src/routes/`
- Applicable to: fullstack, backend_only

**test_coverage** (weight: indicator)
- Scan for: `tests/`, `__tests__/`, `*.test.*`, `*.spec.*`
- Applicable to: all project types

### Phase 5 Indicators (Launch)

**cicd** (weight: indicator)
- Scan for: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Dockerfile`
- Applicable to: all project types

---

## Phase Status Determination

Based on audit results, determine each phase's status:

| Status | Meaning |
|--------|---------|
| DONE | All core artifacts exist |
| PARTIAL | Some artifacts exist |
| MISSING | No artifacts found |
| N/A | Not applicable for this project type |

### Recommended Phase Logic

```
if all phases through 3 are DONE and tests exist:
  → recommend Phase 4 (Quality)
elif Phase 3 indicators exist (code written):
  → recommend Phase 3 (continue implementation)
elif Phase 2.5 is DONE (API contract exists):
  → recommend Phase 3 (start implementation)
elif Phase 2 is DONE:
  → recommend Phase 2.5 (API architecture)
elif Phase 1 is DONE:
  → recommend Phase 2 (Design) — or 2.5 for backend_only
else:
  → recommend Phase 1 (but backfill what we can)
```

---

## Context Import: Link-Based Fetching

When importing from external tools (Jira, Linear, Notion, etc.), use **link-based fetching** — NOT bulk data import.

### Flow

1. Ask user to paste links to specific epics/stories they want to import
2. For each link:
   - Use the tool's MCP to fetch the item + its children/sub-tasks
   - Extract: title, description, acceptance criteria, status, priority
   - Map to `roadmap.yaml` feature/story format
3. Present extracted data to user for confirmation/editing
4. Generate `project-context.md` and `roadmap.yaml` from confirmed data

### Why Link-Based

- Avoids fetching entire Jira/Linear projects (massive data, slow, noisy)
- User controls exactly what gets imported
- Works consistently across all PM tools (every tool has linkable items)
- Handles the common case: user knows which epics matter

---

## Gap Report Format

Present the audit results in this format:

```
+--------------------------------------------------+
|           PROJECT ONBOARDING AUDIT               |
+--------------------------------------------------+
|                                                  |
|  Project Type: [type] ([tech details])           |
|  Files: [N] source files, [M] test files         |
|                                                  |
|  Phase 1 (Strategy):     [status]                |
|    [checkmark/x] [artifact] [found/missing]      |
|                                                  |
|  Phase 2 (Design):       [status or N/A]         |
|    [checkmark/x] [artifact] [found/missing]      |
|                                                  |
|  Phase 2.5 (API):        [status]                |
|    [checkmark/x] [artifact] [found/missing]      |
|                                                  |
|  Phase 3 (Implementation): [status]              |
|    [checkmark/x] [indicator details]             |
|                                                  |
|  Recommended starting phase: Phase [N]           |
+--------------------------------------------------+
```

N/A phases for the project type should show as: `Phase 2 (Design): N/A (backend only)`

---

## Artifact Backfill Rules

### Core Artifacts (must address)

For each missing core artifact, offer these options:
1. **Import from tool** — link-based fetch via MCP (see Context Import above)
2. **Local file** — user points to existing docs to translate
3. **Describe it** — structured conversational questions
4. **Skip** — record as a gap in `current-phase.yaml`

### Nice-to-Have Artifacts

Brief mention only, no pressure:
> "Optional: [artifact description]? [Yes / Skip]"

Only shown for applicable project types.

### API Contract Special Handling

- If swagger/openapi file found: use as-is, store path in `api_contract_path`
- If NOT found and project type needs one: offer to generate from existing routes
- If user has their own spec: let them point to it

---

## Roadmap Structure by Project Type

### Fullstack
```yaml
features:
  - id: "F-001"
    name: "Feature Name"
    scope: both  # frontend | backend | both
    frontend_tasks: [...]
    backend_tasks: [...]
```

### Backend Only
```yaml
features:
  - id: "F-001"
    name: "Feature Name"
    tasks:
      - "Endpoint/service description"
```

### Frontend Only
```yaml
features:
  - id: "F-001"
    name: "Feature Name"
    tasks:
      - "Page/component description"
```

---

## Wizard Progress Persistence

If the onboarding wizard is interrupted (e.g., MCP restart needed), save state to `.onboard-progress.yaml`:

```yaml
wizard_step: 2
completed_steps: [1]
detected_tech:
  language: "TypeScript"
  frontend: "React"
  backend: "NestJS"
project_type: "fullstack"
mcps_added: ["jira"]
```

On re-run of `/onboard`, detect this file and resume from the saved step.

---

**This file is loaded by the `/onboard` skill. It provides the rules and logic; the skill provides the interactive wizard flow.**
