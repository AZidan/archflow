# Issue: Roadmap Format Incompatibility After Onboarding

## Summary

When the `/archflow onboard` command generates `.archflow/roadmap.yaml` for an existing project, it uses an `epics[].features[].stories[]` nested structure with sprint references by feature ID. The Archflow Studio parser expects a flat `sprints[].stories[]` structure with stories inlined directly under each sprint. This causes the Kanban board and Sprint View to load sprint headers but display zero stories.

## Observed Behavior

The onboard agent generated this structure:

```yaml
# What was generated (WRONG for Studio)
epics:
  - id: E1
    name: Admin Authentication
    features:
      - id: F1.1
        name: Admin Login
        stories:
          - id: S1.1.1
            story: >
              As an admin user, I want to log in...
            status: completed
            acceptance_criteria:
              - Login page with email/password form
              - Firebase Auth integration

sprints:
  - id: sprint_1
    name: "Sprint 1: Auth & Shell"
    phase: 1
    status: completed
    features: [F1.1, F1.2, F1.3]   # <-- references, not inline stories
    deliverables:
      - Firebase Auth login page
```

**Result in Studio:** Sprint headers render ("Sprint 1: Auth & Shell"), but 0 stories appear. The Kanban board columns are empty.

## Expected Format

The Studio parser (`server/services/projectLoader.ts:208-249`) reads:

```typescript
data.sprints[].stories[].{id, title, priority, status, assigned, description, acceptance_criteria, subtasks}
```

### Required YAML Structure

```yaml
project: <project-name>
project_type: fullstack  # or frontend_only, backend_only, mobile
sprints:
  - id: sprint-1
    name: "Sprint 1: Auth & Shell"
    stories:
      - id: S1-01
        title: Admin Login                        # required: short title (not a user story)
        priority: Critical                        # required: Critical | High | Medium | Low
        status: done                              # required: backlog | in_progress | review | done
        assigned: ui-engineer                     # required: agent name or role
        description: >                            # required: multi-line description
          Firebase Auth with custom claims for role-based access control.
          Login page, logout, session management.
        acceptance_criteria:                      # required: list of strings OR list of {text, met} objects
          - text: Login page with email/password form
            met: true
          - text: Firebase Auth integration with custom claims
            met: true
        subtasks:                                 # required: list of {text, completed}
          - text: Build login page component
            completed: true
          - text: Wire Firebase Auth SDK
            completed: true
      - id: S1-02
        title: Role-Based Access Control
        priority: High
        status: done
        assigned: api-engineer
        description: >
          Middleware for checking user roles (Super Admin, Support Agent, Analyst).
        acceptance_criteria:
          - text: Role checking middleware
            met: true
        subtasks:
          - text: Implement RBAC middleware
            completed: true

  - id: sprint-2
    name: "Sprint 2: Dashboard Core"
    stories:
      - id: S2-01
        title: Dashboard Metrics Cards
        # ... same structure
```

### Field Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `project` | string | yes | Project name (top-level) |
| `project_type` | enum | yes | `fullstack`, `frontend_only`, `backend_only`, `mobile` |
| `sprints` | array | yes | Top-level sprints array |
| `sprints[].id` | string | yes | Unique sprint ID |
| `sprints[].name` | string | yes | Human-readable sprint name |
| `sprints[].stories` | array | yes | **Stories must be inlined here, not referenced by ID** |
| `stories[].id` | string | yes | Unique story ID (e.g., `S1-01`, `D1-01`) |
| `stories[].title` | string | yes | Short title, NOT a full user story sentence |
| `stories[].priority` | enum | yes | `Critical`, `High`, `Medium`, `Low` |
| `stories[].status` | enum | yes | `backlog`, `in_progress`, `review`, `done` |
| `stories[].assigned` | string | yes | Agent/role name (e.g., `ui-engineer`, `api-engineer`) |
| `stories[].description` | string | yes | Multi-line description of the work |
| `stories[].acceptance_criteria` | array | yes | List of strings or `{text, met}` objects |
| `stories[].subtasks` | array | yes | List of `{text, completed}` objects |

### Key Constraints

1. **No `epics` key.** The Studio parser ignores it entirely.
2. **Stories must be under `sprints[].stories[]`**, not under `epics[].features[].stories[]`.
3. **`title` must be a short name** (e.g., "Admin Login"), not a user story ("As an admin user, I want to..."). The description field holds the detailed explanation.
4. **`acceptance_criteria` supports two formats:**
   - Simple strings: `- "Login page renders correctly"`
   - Objects with met flag: `- { text: "Login page renders correctly", met: true }`
5. **`subtasks` must have `{text, completed}` shape.** Both fields required.
6. **`status` values must be lowercase:** `backlog`, `in_progress`, `review`, `done` (not `completed`, `planned`, etc.)

## Fix Required

The `/archflow onboard` command (in the archflow plugin's `commands/onboard.md`) must be updated to:

1. Generate `sprints[].stories[]` format, NOT `epics[].features[].stories[]`
2. Flatten epics/features into sprint-scoped stories
3. Use `title` (short name) instead of `story` (user story sentence)
4. Map status values: `completed` -> `done`, `planned` -> `backlog`
5. Include `assigned`, `description`, `acceptance_criteria`, and `subtasks` for each story
6. Set `project` and `project_type` at the top level

## Affected Files

- **Parser:** `server/services/projectLoader.ts` — `parseRoadmapData()` (lines 208-249)
- **Types:** `server/types.ts` — `Roadmap`, `Sprint`, `Story`, `Subtask` interfaces
- **Consumers:** Kanban board, Sprint view, Roadmap table, Story modal
