# /archflow feature — Add or Start a Feature

Add a new feature to the roadmap from a description or external tool link. Optionally starts the git workflow for development.

## Usage
```
/archflow feature              → Interactive feature wizard
/archflow feature [name]       → Quick-add a feature by name
```

## Prerequisites
- `.archflow/current-phase.yaml` must exist (run `/archflow onboard` first for existing projects, or complete Phase 1 for new ones)
- `.archflow/roadmap.yaml` must exist
- For link-based import: relevant MCP must be configured (will prompt `/archflow setup-mcp` if not)

---

## Flow

### Step 1: Feature Input

Ask the user:
```
How would you like to add this feature?
```

Options:
- **Describe it** — Provide feature details manually
- **Paste a link** — Import from Jira/Linear/Notion/GitHub
- **From roadmap** — Pick an existing planned feature to start working on

---

#### Option A: "Describe it"

Ask these questions (one at a time):

1. **"Feature name?"**
2. **"Description (what does it do, why)?"**
3. **"Acceptance criteria (what defines done)?"** — Ask for a list
4. **"Priority?"** — High / Medium / Low
5. **"Which part of the codebase?"** — Frontend / Backend / Both
   - Only ask this if `project_type` is `fullstack` (read from `.archflow/current-phase.yaml`)
   - For `backend_only`: assume Backend
   - For `frontend_only`: assume Frontend

---

#### Option B: "Paste a link"

```
Paste the epic/story link:
```

1. Detect which tool the link belongs to (Jira, Linear, Notion, GitHub, etc.)
2. Check if the tool's MCP is configured:
   ```bash
   claude mcp list
   ```
3. If NOT configured: run `/archflow setup-mcp [tool]` inline
4. Fetch the item via MCP:
   - Get the item + its children/sub-tasks
   - Extract: title, description, acceptance criteria, status, priority, sub-tasks
5. Present extracted data:
   ```
   Here's what I found:

   Feature: [title]
   Description: [description]
   Acceptance Criteria:
     - [criterion 1]
     - [criterion 2]
   Sub-tasks:
     - [task 1]
     - [task 2]
   Priority: [priority]
   Source: [tool:ID]

   Add to roadmap? [Yes / Edit first]
   ```
6. If "Edit first": let user modify before proceeding

---

#### Option C: "From roadmap"

1. Read `.archflow/roadmap.yaml` and `.archflow/current-phase.yaml` (for `project_type`)
2. **Filter stories by project_type compatibility** (using the parent epic's `scope`):
   - Determine which scopes match this repo's project_type:
     - `backend_only` → show epics with scope: `backend`, `both`
     - `frontend_only` → show epics with scope: `frontend`, `both`
     - `mobile` → show epics with scope: `mobile`, `both`
     - `fullstack` → show all scopes
   - Epics with `scope: unknown` are always shown (may need investigation)
3. List matching stories with status `backlog` or `in_progress`, grouped by epic:
   ```
   Stories relevant to this [project_type] repo:

   Epic: E1 - Admin Authentication (scope: backend)
     1. [S1-01] Admin Login (backlog, Critical, assigned: ui-engineer)
     2. [S1-02] Role-Based Access (backlog, High, assigned: api-engineer)

   Epic: E2 - Dashboard (scope: both)
     3. [S2-01] Dashboard Metrics Cards (backlog, Medium, assigned: ui-engineer)

   [N] stories hidden (epic scope: frontend/mobile — not applicable to this repo)

   Which story to start? [number / "show all"]
   ```
4. If user types "show all": display the hidden stories too, each with a warning:
   ```
   Epic: E5 - Mobile App (scope: mobile)
     ⚠️ [S5-01] Push Notifications (backlog, scope: mobile)
         Warning: This epic's scope (mobile) doesn't match this repo (backend_only).
         It may have no implementable work here. Continue anyway? [Yes / Pick another]
   ```
5. User picks one → skip to Step 3 (git workflow)

---

### Step 2: Update roadmap.yaml

Read `.archflow/current-phase.yaml` to get `project_type`. Read `.archflow/roadmap.yaml` to find existing epics and stories.

The roadmap follows the canonical schema at `.archflow/schemas/roadmap-schema.yaml`. Stories are defined under epics and referenced by sprints.

#### 2a. Epic Selection

Ask the user which epic this story belongs to:
```
Which epic does this belong to?

Existing epics:
  1. [E1] Admin Authentication (scope: backend)
  2. [E2] Dashboard (scope: both)

  [N] Create new epic
```

If "Create new epic":
- Generate next `E{N}` ID (increment from highest existing)
- Ask for epic name and scope (`backend | frontend | mobile | both`)

#### 2b. Story Creation

Generate the next story ID under the chosen epic: `S{epic}-{seq}` (e.g., if epic is E2 and it has stories S2-01, S2-02, the next is S2-03).

Add the story under the epic's `stories` array using the canonical format:
```yaml
- id: "S{epic}-{seq}"
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

#### 2c. Sprint Assignment

Ask which sprint to assign the story to:
```
Assign to a sprint?

  1. [sprint-1] Sprint 1: Auth & Shell (mvp, done)
  2. [sprint-2] Sprint 2: Dashboard (mvp, in_progress)

  [N] Create new sprint
  [S] Skip — leave unassigned for now
```

If "Create new sprint": ask for sprint name, goal, and which phase it belongs to (list existing phases or create new).

Add the story ID to the sprint's `stories` reference list.

Write the updated `.archflow/roadmap.yaml`. Confirm to user:
> "Added [{title}] as [{story_id}] under epic [{epic_id}] {epic_name}."

---

### Step 3: Git Workflow Setup

Ask:
```
Ready to start development? [Yes / Not yet, just add to roadmap]
```

#### If "Not yet"
> "Feature added to roadmap. Run `/archflow feature` again when ready to start."
Done.

#### If "Yes"

**Pre-check: Verify git is available**
```bash
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  HALT: "Git not initialized. Run 'git init' first."
fi
git checkout main
git pull origin main 2>/dev/null || true
```

Follow the branching strategy from `.archflow/workflow.md`:

1. **Create feature branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b {feature-branch-name}
   git push -u origin {feature-branch-name}
   ```
   - Branch name: kebab-case of feature name (e.g., `user-notifications`)

2. **Update `.archflow/current-phase.yaml`:**
   ```yaml
   current_feature: "{story_id}"    # e.g., S1-01
   feature_status: "in_progress"
   ```

3. **Create/update `.archflow/current-feature.yaml`:**
   ```yaml
   story_id: "{story_id}"          # e.g., S1-01
   story_title: "{title}"
   epic_id: "{epic_id}"            # e.g., E1
   branch: "{feature-branch-name}"
   status: in_progress
   subtasks:                        # Populated from roadmap.yaml story subtasks
     - text: "{subtask_1}"
       completed: false
       branch: null
       started_at: null
       completed_at: null
     - text: "{subtask_2}"
       completed: false
       branch: null
       started_at: null
       completed_at: null
   ```

4. **Update `.archflow/roadmap.yaml`:** Set the story's status to `in_progress`.

5. **Present next steps:**
   ```
   Feature branch created: {feature-branch-name}
   Story: [{story_id}] {title} (epic: {epic_id})

   Subtasks from roadmap:
     1. {subtask_1} (pending)
     2. {subtask_2} (pending)

   Start Phase 3 implementation when ready.
   Branch workflow (.archflow/workflow.md):
     - Task branches: {feature}/{subtask-name}
     - Merge only after explicit user approval
   ```

---

### Step 4: Task-Level Git Workflow (During Development)

This step runs during Phase 3 implementation, not during `/archflow feature` itself. It documents how tasks are executed using `workflow.md`.

For each task in `.archflow/current-feature.yaml`:

1. **Create task branch:**
   ```bash
   git checkout {feature-branch}
   git pull origin {feature-branch}
   git checkout -b {feature}/{task-name}
   git push -u origin {feature}/{task-name}
   ```

2. **Update `.archflow/current-feature.yaml`:** Set task status to `in_progress`, record branch name.

3. **Implement** using appropriate agents:
   - Check `project_type` from `.archflow/current-phase.yaml`
   - `backend_only`: only use `api-engineer`
   - `frontend_only`: only use `ui-engineer`
   - `fullstack`: use both based on task `type` field

4. **Build and test locally** (per workflow.md testing checklist)

5. **Commit and push:**
   ```bash
   git add {specific files}
   git commit -m "feat: {description}"
   git push -u origin {feature}/{task-name}
   ```

6. **Wait for explicit user approval** — NEVER auto-merge

7. **After approval, merge task to feature branch:**
   ```bash
   git checkout {feature-branch}
   git pull origin {feature-branch}
   git merge {feature}/{task-name}
   git push origin {feature-branch}
   git branch -d {feature}/{task-name}
   git push origin --delete {feature}/{task-name}
   ```

8. **Update tracking files:**
   - `.archflow/current-feature.yaml`: Mark task as `complete`, record `completed_at`
   - `.archflow/roadmap.yaml`: Mark the corresponding `subtasks[]` entry as `completed: true` for the subtask that maps to this task

### Feature Completion

After ALL tasks are complete and approved:

1. **Merge feature to main** (with user approval):
   ```bash
   git checkout main
   git pull origin main
   git merge {feature-branch}
   git push origin main
   ```

2. **Cleanup:**
   ```bash
   git branch -d {feature-branch}
   git push origin --delete {feature-branch}
   ```

3. **Update files:**
   - `.archflow/roadmap.yaml`:
     - Story `status` → `done`
     - ALL `subtasks[].completed` → `true`
     - ALL `acceptance_criteria[].met` → `true`
   - `.archflow/current-phase.yaml`: `current_feature` → `null`, `feature_status` → `ready`
   - `.archflow/current-feature.yaml`: clear or remove

---

## Notes
- Story IDs follow the pattern `S{epic}-{seq}` (e.g., S1-01, S2-03) and are auto-incremented under their epic
- Epic IDs follow the pattern `E{N}` (e.g., E1, E2) and are auto-incremented
- The `/archflow feature` command can be run at any time, not just during Phase 3
- Git operations always require explicit user approval before merging
- The roadmap follows the canonical schema at `.archflow/schemas/roadmap-schema.yaml`
- The task-level git workflow (Step 4) is executed during Phase 3, referenced here for completeness
