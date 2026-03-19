# Archflow Framework Gap Report v2

**Date**: 2026-03-16
**Context**: Follow-up to v1 gap report (which has been fixed and deployed). This report covers schema enforcement and acceptance criteria tracking gaps discovered during archflow-studio Drop 1 development.
**Archflow Version**: 1.0.0 (installed at `~/.claude/plugins/cache/archflow/archflow/1.0.0/`)

---

## Executive Summary

The Archflow framework lacks a **canonical roadmap.yaml schema definition** and has **no mechanism for tracking acceptance criteria status**. Acceptance criteria are stored as plain strings with no `met` field, making it impossible to track which criteria pass and which fail. Additionally, the roadmap.yaml format varies between projects because there's no enforced schema — field names, structure, and nesting can deviate freely.

---

## Gap 9: Acceptance Criteria Have No Status Tracking

### Severity: CRITICAL

### What happened
All 7 done stories in archflow-studio had acceptance criteria as plain strings:
```yaml
acceptance_criteria:
  - "Running npx archflow-studio starts a Fastify server"
  - "CLI accepts --project and --port flags"
```

There is no way to record which criteria were met and which failed. The pm-maestro-reviewer writes a separate markdown report, but that data is disconnected from the roadmap — the roadmap itself doesn't know if criteria passed.

### Where the rule exists
- **`pm-maestro-reviewer` agent spec**: Validates acceptance criteria from roadmap.yaml, produces pass/fail verdicts
- **`phase-3-implementation.md`**: "VERDICT REQUIRED: Feature is not complete until pm-maestro-reviewer returns ACCEPTED verdict"
- **`CLAUDE.md`**: "ACCEPTANCE GATE: After qa-engineer completes, launch pm-maestro-reviewer to validate acceptance criteria"

### Why it failed
1. Acceptance criteria schema is **never formally defined** anywhere in the framework
2. Criteria are plain strings — no `met`, `tested`, `verified_by`, or `verified_at` fields
3. pm-maestro-reviewer writes results to a separate markdown file but **never updates roadmap.yaml**
4. There's no feedback loop from acceptance testing back to the roadmap
5. The Kanban board and Roadmap table have no data to show which criteria pass/fail

### What needs to be fixed

#### 1. Define the acceptance criteria schema

Add to the roadmap.yaml schema documentation (wherever the roadmap format is defined — see Gap 10 below):

```yaml
# OLD format (plain strings — DEPRECATED):
acceptance_criteria:
  - "criterion text"

# NEW format (objects with tracking — REQUIRED):
acceptance_criteria:
  - text: "Running npx archflow-studio starts a Fastify server"
    met: false            # true when criterion is verified
    verified_by: null     # "pm-maestro-reviewer" | "qa-engineer" | "manual"
    verified_at: null     # ISO 8601 timestamp when verified
```

**Minimum required fields**: `text` (string) and `met` (boolean)
**Optional fields**: `verified_by` (string), `verified_at` (string)

#### 2. Update pm-maestro-reviewer agent spec

Add to the agent's output responsibilities:

```markdown
## Acceptance Criteria Update Protocol

After running acceptance tests for a story:

1. For each criterion in the story's `acceptance_criteria` array:
   - If criterion PASSES: set `met: true`, `verified_by: "pm-maestro-reviewer"`, `verified_at: "<ISO timestamp>"`
   - If criterion FAILS: set `met: false` (leave verified_by/verified_at as null)

2. Update `.archflow/roadmap.yaml` with the results:
   ```yaml
   acceptance_criteria:
     - text: "Server starts on localhost:3456"
       met: true
       verified_by: pm-maestro-reviewer
       verified_at: "2026-03-16T14:22:00Z"
     - text: "WebSocket reconnects within 5 seconds"
       met: false
       verified_by: null
       verified_at: null
   ```

3. Write the detailed report to `docs/acceptance-reports/{story-id}-review.md`

4. The VERDICT is determined by criteria status:
   - ALL criteria `met: true` → ACCEPTED
   - ANY criteria `met: false` → REJECTED (list failing criteria)

5. Commit the roadmap update:
   ```bash
   git add .archflow/roadmap.yaml
   git commit -m "test({story-id}): acceptance criteria - {X}/{Y} met"
   ```
```

#### 3. Update `/archflow feature` command (feature.md)

When creating new stories (Option A: "Describe it"), generate criteria in the new format:

```yaml
# In Step 2: Update roadmap.yaml
# When adding acceptance criteria from user input:
acceptance_criteria:
  - text: "{criterion_1}"
    met: false
  - text: "{criterion_2}"
    met: false
```

#### 4. Update workflow.md

Add a section documenting acceptance criteria lifecycle:

```markdown
## Acceptance Criteria Lifecycle

1. **Created**: When story is added to roadmap (via `/archflow feature` or manually)
   - `met: false`, `verified_by: null`, `verified_at: null`

2. **Tested**: When pm-maestro-reviewer runs acceptance tests
   - `met: true/false`, `verified_by: "pm-maestro-reviewer"`, `verified_at: "<timestamp>"`

3. **Reset**: If story is re-opened after being done (e.g., bug found)
   - All criteria reset to `met: false`

Criteria are NEVER manually toggled by developers. Only pm-maestro-reviewer
(or qa-engineer for automated test-mapped criteria) sets `met: true`.
```

#### 5. Define display rules for Studio UI (informational — not a framework fix)

These rules should be documented in the framework so any visualization tool knows how to render criteria:

```markdown
## Acceptance Criteria Display Rules

- **Roadmap View** (Strategy/Planning phase):
  Show criteria with checkmarks based on `met` field.
  Done stories show all criteria as checked.
  Read-only — users cannot toggle criteria here.

- **Kanban Board** (Implementation phase):
  Show criteria as a list with check/uncheck indicators based on `met` field.
  Read-only — criteria are set by pm-maestro-reviewer, not manually.
  Before acceptance testing: all show as unchecked.
  After acceptance testing: reflects actual test results.

- **Acceptance Report** (docs/acceptance-reports/):
  Detailed markdown report with pass/fail per criterion + evidence.
  This is the human-readable version; roadmap.yaml is the machine-readable version.
```

---

## Gap 10: No Canonical Roadmap.yaml Schema

### Severity: HIGH

### What happened
The roadmap.yaml format is implicitly defined through examples scattered across multiple files, but there is no single canonical schema definition. This means:
- Different projects could use different field names (e.g., `acceptance_criteria` vs `criteria` vs `acceptanceCriteria`)
- Nesting structure could vary (flat stories vs sprint-grouped stories)
- Required vs optional fields are undefined
- Data types are unspecified (is priority a string? an enum? a number?)

### Where the format is referenced
- **`feature.md` lines 122-173**: Shows 3 different format templates (fullstack, backend_only, frontend_only) — but these define FEATURE format, not STORY format
- **`phase-3-implementation.md`**: References roadmap.yaml but doesn't define its schema
- **`workflow.md`**: References "story" fields but doesn't define the full structure
- **`CLAUDE.md`**: References roadmap.yaml but only as a file path
- **`api-contract.md`** (project-level): Defines TypeScript interfaces for the API — but this is project-specific, not framework-level

### Why this is a problem
1. The `feature.md` templates define a FEATURE schema (with `frontend_tasks` / `backend_tasks` / `tasks`) that is DIFFERENT from the story schema used in the actual roadmap
2. No validation can be performed on roadmap.yaml because there's no schema to validate against
3. Agents (ui-engineer, api-engineer) read roadmap.yaml but might encounter unexpected field names
4. Tools like yamlParser.ts must handle format variations defensively
5. pm-maestro-reviewer needs to know exact field names to update acceptance criteria

### What needs to be fixed

#### 1. Create a canonical schema file

Create a new file in the Archflow framework:

**File**: `~/.claude/plugins/cache/archflow/archflow/1.0.0/.archflow/schemas/roadmap-schema.yaml`

```yaml
# =============================================================================
# Archflow Roadmap Schema Definition
# =============================================================================
# This is the CANONICAL schema for .archflow/roadmap.yaml.
# All Archflow tools, agents, and skills MUST produce and consume this format.
# =============================================================================

schema_version: "1.0"

# -----------------------------------------------------------------------------
# Top-level structure
# -----------------------------------------------------------------------------
roadmap:
  type: object
  required: [project, project_type, sprints]
  properties:
    project:
      type: string
      description: "Project name (directory name)"
      example: "my-app"

    project_type:
      type: string
      enum: [fullstack, frontend_only, backend_only, mobile]
      description: "Project type determines which agents and phases apply"

    sprints:
      type: array
      description: "Ordered list of sprints/drops"
      items:
        $ref: "#/sprint"

# -----------------------------------------------------------------------------
# Sprint
# -----------------------------------------------------------------------------
sprint:
  type: object
  required: [id, name, stories]
  properties:
    id:
      type: string
      pattern: "^[a-z0-9-]+$"
      description: "Kebab-case sprint identifier"
      example: "drop-1"

    name:
      type: string
      description: "Human-readable sprint name"
      example: "Drop 1: The Viewer"

    stories:
      type: array
      items:
        $ref: "#/story"

# -----------------------------------------------------------------------------
# Story
# -----------------------------------------------------------------------------
story:
  type: object
  required: [id, title, priority, status, assigned]
  properties:
    id:
      type: string
      pattern: "^[A-Z][0-9]+-[0-9]+$"
      description: "Story ID: sprint prefix + sequence number"
      example: "D1-01"

    title:
      type: string
      description: "Short story title"
      example: "App Shell & Server"

    priority:
      type: string
      enum: [Critical, High, Medium, Low]
      description: "Story priority level"

    status:
      type: string
      enum: [backlog, in_progress, review, done]
      description: "Current story status (maps to Kanban columns)"

    assigned:
      type: string
      description: "Agent responsible for implementation"
      enum: [ui-engineer, api-engineer, qa-engineer, pm-maestro-reviewer,
             ux-designer, dsl-generator, product-strategist, feature-planner,
             devops-engineer, performance-optimizer, code-reviewer,
             post-launch-analyst, i18n-engineer, a11y-expert, doc-writer]

    description:
      type: string
      description: "Detailed story description (multi-line YAML block scalar)"
      required: false

    acceptance_criteria:
      type: array
      description: "Testable criteria that define when the story is done"
      items:
        $ref: "#/acceptance_criterion"

    subtasks:
      type: array
      description: "Granular implementation tasks within the story"
      items:
        $ref: "#/subtask"

    # Optional tracking fields (set by workflow automation)
    approved:
      type: boolean
      required: false
      default: false
      description: "Whether the user explicitly approved this story"

    approved_at:
      type: string
      format: iso8601
      required: false
      description: "Timestamp of user approval"

# -----------------------------------------------------------------------------
# Acceptance Criterion
# -----------------------------------------------------------------------------
acceptance_criterion:
  type: object
  required: [text, met]
  properties:
    text:
      type: string
      description: "Testable criterion statement"
      example: "Server starts on localhost:3456 within 2 seconds"

    met:
      type: boolean
      default: false
      description: "Whether this criterion has been verified as passing"

    verified_by:
      type: string
      required: false
      enum: [pm-maestro-reviewer, qa-engineer, manual]
      description: "Who/what verified this criterion"

    verified_at:
      type: string
      format: iso8601
      required: false
      description: "When this criterion was verified"

# -----------------------------------------------------------------------------
# Subtask
# -----------------------------------------------------------------------------
subtask:
  type: object
  required: [text, completed]
  properties:
    text:
      type: string
      description: "Subtask description"
      example: "Scaffold monorepo structure"

    completed:
      type: boolean
      default: false
      description: "Whether this subtask has been implemented"
```

#### 2. Add schema reference to CLAUDE.md

In the "Universal Context Files" section:

```markdown
## Universal Context Files (Always Required)
- `.archflow/project-context.md` - Business goals, tech stack, architecture decisions
- `.archflow/roadmap.yaml` - Feature roadmap and sprint planning
  **Schema**: Must follow `.archflow/schemas/roadmap-schema.yaml`
  **Key rules**:
  - `acceptance_criteria` items MUST be objects with `text` and `met` fields (not plain strings)
  - `subtasks` items MUST be objects with `text` and `completed` fields
  - `status` MUST be one of: backlog, in_progress, review, done
  - `priority` MUST be one of: Critical, High, Medium, Low
- `.archflow/current-feature.yaml` - Active development scope and requirements
- `.archflow/current-phase.yaml` - Phase state tracker
```

#### 3. Add schema validation to `/archflow init` and `/archflow onboard`

When creating or importing a roadmap.yaml:

```markdown
## Roadmap Validation

After creating or modifying `.archflow/roadmap.yaml`, validate against the schema:

1. Every story MUST have: id, title, priority, status, assigned
2. Every acceptance_criteria item MUST be an object with at minimum: { text, met }
   - If importing criteria as plain strings, convert to: { text: "<string>", met: false }
3. Every subtask MUST be an object with: { text, completed }
4. priority MUST be one of: Critical, High, Medium, Low
5. status MUST be one of: backlog, in_progress, review, done

If validation fails, fix the format before proceeding.
```

#### 4. Add schema enforcement to feature.md

Update ALL three format templates (fullstack, backend_only, frontend_only) to use the canonical format:

```yaml
# CORRECT format for ALL project types:
- id: "{sprint_prefix}-{next_number}"
  title: "{feature_name}"
  priority: "{Critical|High|Medium|Low}"
  status: backlog
  assigned: "{agent_name}"
  description: >
    {description}
  acceptance_criteria:
    - text: "{criterion_1}"
      met: false
    - text: "{criterion_2}"
      met: false
  subtasks:
    - text: "{subtask_1}"
      completed: false
    - text: "{subtask_2}"
      completed: false
```

**REMOVE** the separate `frontend_tasks` / `backend_tasks` / `tasks` fields from feature templates. These should be `subtasks` with a consistent schema. If scope differentiation is needed, add a `type` field to each subtask:

```yaml
subtasks:
  - text: "Build login form UI"
    completed: false
    type: frontend       # Optional: frontend | backend | both
  - text: "Create auth API endpoints"
    completed: false
    type: backend
```

#### 5. Add migration note for existing projects

When `/archflow onboard` encounters a roadmap with old-format criteria (plain strings):

```markdown
## Schema Migration

If roadmap.yaml contains plain-string acceptance criteria:
```yaml
# OLD format detected:
acceptance_criteria:
  - "Some criterion"
```

Automatically convert to new format:
```yaml
# Converted to:
acceptance_criteria:
  - text: "Some criterion"
    met: false
```

Log: "Migrated {N} acceptance criteria to object format in roadmap.yaml"
Commit: "chore: migrate acceptance criteria to {text, met} format"
```

#### 6. Update agent specs that read/write roadmap.yaml

**product-strategist** and **feature-planner** (Phase 1 agents):
When generating roadmap.yaml, MUST use the canonical schema:
```markdown
## Roadmap Output Format

When writing to .archflow/roadmap.yaml, follow the canonical schema:
- acceptance_criteria: array of { text: string, met: false }
- subtasks: array of { text: string, completed: false }
- Do NOT use plain strings for criteria or tasks
```

**pm-maestro-reviewer**:
When updating criteria after testing:
```markdown
## Criteria Update Format

After testing, update each criterion:
- text: "<unchanged>"
  met: true/false
  verified_by: "pm-maestro-reviewer"
  verified_at: "<ISO timestamp>"
```

---

## Gap 11: Feature Template Schema Inconsistency

### Severity: MEDIUM

### What happened
The `feature.md` command defines THREE different story formats depending on project type:
- **fullstack**: Has `frontend_tasks` + `backend_tasks` arrays
- **backend_only**: Has `tasks` array + `scope: backend`
- **frontend_only**: Has `tasks` array + `scope: frontend`

But the actual roadmap.yaml used in projects has:
- `subtasks` array (not `tasks`, `frontend_tasks`, or `backend_tasks`)
- `assigned` field (not `scope`)

This means the feature command generates stories in a format that doesn't match the roadmap schema.

### Where the inconsistency exists
- **`feature.md` lines 122-173**: Three different templates with `tasks`, `frontend_tasks`, `backend_tasks`
- **Actual roadmap.yaml**: Uses `subtasks` with `{ text, completed }` objects

### What needs to be fixed

#### Unify to a single story format

Replace all three templates in `feature.md` with ONE canonical format:

```yaml
# UNIFIED story format (works for ALL project types):
- id: "{sprint_prefix}-{next_number}"
  title: "{feature_name}"
  priority: "{priority}"
  status: backlog
  assigned: "{primary_agent}"
  description: >
    {description}
  acceptance_criteria:
    - text: "{criterion_1}"
      met: false
    - text: "{criterion_2}"
      met: false
  subtasks:
    - text: "{subtask_1}"
      completed: false
    - text: "{subtask_2}"
      completed: false
  source: "{tool:ID or manual}"
```

**Remove**: `scope`, `frontend_tasks`, `backend_tasks`, `tasks` fields.

**Rationale**:
- The `assigned` field already indicates who does the work (ui-engineer vs api-engineer)
- If a story needs both frontend and backend work, create TWO stories (one per agent) or use subtask `type` field
- Having one format prevents schema drift between project types

---

## Gap 12: No Roadmap Schema Validation on Write

### Severity: MEDIUM

### What happened
Multiple agents and commands write to roadmap.yaml throughout the workflow:
- `product-strategist` creates the initial roadmap
- `feature-planner` adds features
- `/archflow feature` adds stories
- UI-based editing (Kanban drag, Story modal) modifies story status/fields
- `pm-maestro-reviewer` updates acceptance criteria
- Subtask completion updates

None of these validate the output against a schema. Any agent could produce malformed YAML that breaks downstream tools.

### What needs to be fixed

#### 1. Add validation to all roadmap write paths

In `workflow.md`, add a validation step after ANY roadmap modification:

```markdown
## Roadmap Write Validation

After ANY modification to `.archflow/roadmap.yaml`:

1. Parse the YAML (catch syntax errors)
2. Validate required fields exist for every story:
   - id (string, matches pattern)
   - title (string)
   - priority (enum: Critical, High, Medium, Low)
   - status (enum: backlog, in_progress, review, done)
   - assigned (string)
3. Validate acceptance_criteria format:
   - Each item MUST be an object with at least `text` (string) and `met` (boolean)
   - If any item is a plain string, MIGRATE it: { text: "<string>", met: false }
4. Validate subtasks format:
   - Each item MUST be an object with `text` (string) and `completed` (boolean)

If validation fails:
- Log the specific validation error
- Attempt auto-fix for known issues (e.g., string → object migration)
- If auto-fix succeeds, log: "Auto-fixed roadmap format: [what was fixed]"
- If auto-fix fails, HALT: "Roadmap validation failed: [error details]"
```

#### 2. Add validation to the Studio's yamlParser.ts (informational)

The Studio app should validate on both read and write:

```typescript
// On read: normalize old format to new
function normalizeAcceptanceCriteria(criteria: any[]): AcceptanceCriterion[] {
  return criteria.map(c => {
    if (typeof c === 'string') {
      return { text: c, met: false };  // Migrate plain string
    }
    return {
      text: c.text || String(c),
      met: c.met ?? false,
      verified_by: c.verified_by ?? null,
      verified_at: c.verified_at ?? null,
    };
  });
}

// On write: ensure format is canonical
function validateRoadmap(roadmap: Roadmap): ValidationResult {
  const errors: string[] = [];
  for (const sprint of roadmap.sprints) {
    for (const story of sprint.stories) {
      if (!['Critical', 'High', 'Medium', 'Low'].includes(story.priority)) {
        errors.push(`${story.id}: invalid priority "${story.priority}"`);
      }
      if (!['backlog', 'in_progress', 'review', 'done'].includes(story.status)) {
        errors.push(`${story.id}: invalid status "${story.status}"`);
      }
      for (const ac of story.acceptanceCriteria) {
        if (typeof ac === 'string') {
          errors.push(`${story.id}: acceptance criterion is plain string, should be {text, met}`);
        }
      }
    }
  }
  return { valid: errors.length === 0, errors };
}
```

---

## Summary: Files That Need Changes

### Framework Level (Plugin Files)

```
~/.claude/plugins/cache/archflow/archflow/1.0.0/
├── .archflow/
│   ├── schemas/
│   │   └── roadmap-schema.yaml          ← NEW: canonical schema definition (Gap 10)
│   ├── workflow.md                      ← Gap 9 (criteria lifecycle), Gap 12 (write validation)
│   └── phases/
│       └── phase-3-implementation.md    ← Gap 9 (criteria update in acceptance step)
├── skills/archflow/
│   ├── commands/
│   │   ├── feature.md                   ← Gap 10 (unified format), Gap 11 (remove triple template)
│   │   ├── init.md                      ← Gap 10 (schema validation on create)
│   │   └── onboard.md                   ← Gap 10 (schema migration on import)
│   └── SKILL.md                         ← No changes
├── agents/
│   ├── pm-maestro-reviewer.md           ← Gap 9 (update criteria met field after testing)
│   ├── product-strategist.md            ← Gap 10 (use canonical schema for roadmap output)
│   └── feature-planner.md              ← Gap 10 (use canonical schema for roadmap output)
└── [other files — no changes]
```

### Global Instructions
```
~/.claude/CLAUDE.md                      ← Gap 10 (schema reference in Universal Context Files)
```

---

## Fix Priority

| Priority | Gap | Description | Effort |
|----------|-----|-------------|--------|
| **P0** | Gap 9 | Acceptance criteria {text, met} schema | Medium |
| **P0** | Gap 10 | Canonical roadmap-schema.yaml | Large |
| **P1** | Gap 11 | Unify feature templates to one format | Small |
| **P1** | Gap 12 | Write validation on all roadmap modifications | Medium |

---

## Validation Scenario

After implementing these fixes:

1. Run `/archflow init` on a new project
2. Complete Phase 1 → roadmap.yaml should have criteria as `{ text, met: false }` objects
3. Add a feature via `/archflow feature` → new story uses canonical format
4. Run pm-maestro-reviewer → criteria should update to `{ text, met: true/false, verified_by, verified_at }`
5. Check roadmap.yaml → all criteria are objects, never plain strings
6. Import an old-format roadmap via `/archflow onboard` → plain string criteria auto-migrated
7. Drag a story in Kanban → roadmap write validates format before saving
