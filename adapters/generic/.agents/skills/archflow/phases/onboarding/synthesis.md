# Onboarding — synthesis and output shapes

Loaded by `phase-onboarding.md` at Phase C, when the audit results are turned into
`.archflow/` state. Not needed during the audit itself.

## Canonical Roadmap Structure (v2.0 — multi-file)

All project types use the SAME structure. Project-type differentiation is handled by the `scope` field
on epics (labels), not by structural differences. **Epics are labels — they do NOT contain stories.**
Stories live in `backlog.yaml` (stubs) or a release file (detailed); a story is in exactly ONE place.

Use the "CANONICAL OUTPUT FORMAT (v2.0 — Mode A)" template earlier in this file as the authoritative
shape, and the split schemas: `roadmap-schema.yaml` (index), `backlog-schema.yaml` (stubs),
`release-schema.yaml` (detailed releases/stories), `history-schema.yaml`.

```yaml
# .archflow/roadmap.yaml — INDEX only (no stories under epics)
schema_version: "2.1"
project: "{name}"
project_type: "{fullstack|frontend_only|backend_only|mobile}"
mode: "{quick|full}"
epics:                                    # LABELS only
  - {id: E1, name: "Epic Name", scope: backend}   # backend|frontend|mobile|both|unknown
active_release: null                      # or the in_progress slug
releases: []                              # planning/ready/in_progress refs
shipped: []                               # ledger of shipped releases

# .archflow/backlog.yaml — stubs (unscheduled scope)
# .archflow/releases/{slug}.yaml — detailed stories (readiness status + gates + ACs + subtasks)
# .archflow/releases/archive/{slug}.yaml — shipped releases
# .archflow/history.yaml — shipped-story intent layer

# There is NO phases:/sprints: block. Instead:
#   - roadmap.yaml holds the index (mode, epic LABELS, releases[] pipeline, shipped[] ledger)
#   - backlog.yaml holds unbuilt scope as stubs
#   - releases/archive/{slug}.yaml holds already-shipped scope (status: released)
# See the "CANONICAL OUTPUT FORMAT (v2.0 — Mode A)" section above for the full shape.
```

**Key rules:**
- **Scope field is required on ALL epics** regardless of project type. It represents the TRUE scope of the work, which may differ from the repo's project_type (e.g., a "mobile app" epic imported into a backend repo should have `scope: mobile`).
- **Stories live in exactly one place** — a backlog stub OR one release file. Epics are labels; they don't contain stories in the index.
- **Every release story has `gates {needs_design, needs_contract}`** derived from scope.
- **acceptance_criteria** MUST be `{text, met}` objects, NEVER plain strings.
- **subtasks** MUST be `{text, completed}` objects.
- **Readiness status** values: `backlog | spec_ready | design_ready | contract_ready | ready | in_progress | review | done`.

---

## Progress File Schema

```yaml
wizard_phase: "B"  # A | B | C
completed_steps: ["A1", "A2", "A3", "A4", "A5"]
user_inputs:
  project_type: "fullstack"
  tech_stack:
    language: "TypeScript"
    frontend: "React"
    backend: "NestJS"
    database: "PostgreSQL"
  import_source: "jira"  # jira | notion | linear | github | google_drive | trello | slack | confluence | local | conversational | skip
  import_links:
    - { url: "https://...", type: "epic" }
  additional_doc_links: ["https://..."]
  extract_design_system: true
  generate_api_contract: true
  existing_api_spec: null
  user_vision_notes: "Planning real-time collaboration in Q3"
  completed_features_override: ["user-auth"]
agent_outputs:
  codebase_audit: { status: "completed", output: ".onboard-audit-report.yaml" }
  doc_deep_dive: { status: "completed", output: ".onboard-imported-context.md" }
  design_extraction: { status: "running", output: null }
  route_extraction: { status: "pending", output: null }
  product_strategist: { status: "pending", output: null }
  ux_designer: { status: "pending", output: null }
  api_contract_architect: { status: "pending", output: null }
  dsl_generator: { status: "pending", output: null }
  feature_planner: { status: "pending", output: null }
```

---

## Phase C: Synthesis Rules

### C1: Roadmap Reconciliation

Read `roadmap.yaml` (index) + `backlog.yaml` + any `releases/*.yaml` + `.onboard-audit-report.yaml` +
user overrides from `.onboard-progress.yaml`:
- If a story is a backlog stub but audit shows the code exists/shipped → move it into a `released`
  release under `releases/archive/` + the `shipped` ledger + add a `history.yaml` entry.
- In-progress code → put those stories in the `in_progress` release (set `active_release`).
- If the user explicitly overrode a status in `completed_features_override` → use the user's status.
- Everything unbuilt stays as backlog stubs. Set `mode` (full for substantial repos, else quick).
- If `format_valid: false` (v2.0 shape): auto-fix before writing:
  - Plain-string `acceptance_criteria` → `{text: "...", met: false}`
  - Plain-string `subtasks` → `{text: "...", completed: false}`
  - Story missing `gates` → derive `{needs_design, needs_contract}` from scope
  - Invalid readiness `status` → map to the nearest pipeline state
  - Missing `scope` on epics → infer or default to `unknown`
  - More than one `in_progress` release → ask which is truly being built; others' stories → backlog

### C2: Phase Determination

Use the Recommended Phase Logic (above) with enriched audit data from `.onboard-audit-report.yaml`.

### C3: Gap Report

Generate gap report based on real agent outputs. Format:

```
+--------------------------------------------------+
|           PROJECT ONBOARDING AUDIT               |
+--------------------------------------------------+
|                                                  |
|  Project Type: [type] ([tech details])           |
|  Files: [N] source files, [M] test files         |
|                                                  |
|  Phase 1 (Strategy):     [status]                |
|    [checkmark/x] [artifact] [found/generated]    |
|    [warning]    roadmap.yaml — [N] format         |
|                 violations (see below)           |
|                                                  |
|  Phase 2 (Design):       [status or N/A]         |
|    [checkmark/x] [artifact] [found/generated]    |
|                                                  |
|  Phase 2.5 (API):        [status]                |
|    [checkmark/x] [artifact] [found/generated]    |
|                                                  |
|  Phase 3 (Implementation): [status]              |
|    [checkmark/x] [indicator details]             |
|                                                  |
|  Recommended starting phase: Phase [N]           |
+--------------------------------------------------+
```

N/A phases for the project type should show as: `Phase 2 (Design): N/A (backend only)`

If `format_valid: false`, append a violations block after the audit box:

```
roadmap format violations ([N] total):
  ⚠ releases/checkout.yaml → stories[2].acceptance_criteria[1]
    rule: acceptance_criteria item must be {text, met} object
    found: plain string: "User can log in"
  ⚠ releases/checkout.yaml → stories[0]
    rule: story must have gates {needs_design, needs_contract}
    found: missing gates
  ⚠ roadmap.yaml → releases
    rule: at most one release may be in_progress
    found: 2 in_progress (checkout, q3-launch)

These violations will be fixed during roadmap reconciliation (Step C1).
(A v1.0 roadmap is not shown here — it is redirected to $archflow-migrate.)
```

### C4: Presentation Format

```
ONBOARDING COMPLETE

Project: [Name] ([Type]: [Tech Stack])
Recommended Phase: [N] ([Phase Name])

Generated Artifacts:
  ✅ project-context.md (by product-strategist — domain research + [source] synthesis)
  ✅ roadmap.yaml ([N] epics, [M] stories: [X] done, [Y] in-progress, [Z] backlog)
  ✅ API contract: {api_contract_path} (reverse-engineered from [N] routes)
  ✅ Design system: design-artifacts/theme.yaml ([N] tokens extracted)
  ✅ Component specs: design-artifacts/styled-dsl.yaml ([N] screens)
  ✅ User flows: design-artifacts/user-flows.md

Review each artifact? [Yes / Trust the agents]
```

If "Yes": present each artifact for approval/editing, one at a time.

### C5: Finalization

1. Create `.archflow/current-phase.yaml` with full schema (see onboard.md)
2. Create or update the project's agent instruction file with the Archflow section (see onboard.md for full template).
   Write `AGENTS.md` (read by every host) and also `CLAUDE.md` (skip: Claude Code only):
   - If the file does NOT exist: create it with project overview, common commands, architecture, and Archflow section — all derived from onboarding analysis
   - If the file ALREADY exists: append the Archflow section to the end (between `<!-- archflow:start -->` / `<!-- archflow:end -->` markers so it can be updated in place later)
   - The Archflow section MUST include: current phase, links to project-context.md, roadmap.yaml, api-contract.md (if generated), and available `$archflow-*` commands
   - Only list artifacts that were actually created
3. Clean up ALL temporary `.onboard-*` files (`rm .onboard-*`). No `.onboard-*` files should remain after finalization
4. Offer to remove onboarding-only MCPs
5. Print summary with next steps (include AGENTS.md — and CLAUDE.md (skip: Claude Code only) — in the created artifacts list)

---
