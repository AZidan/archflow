# /archflow feature — Add or Start a Feature

Add a new feature to the roadmap from a description or external tool link. Optionally starts the git workflow for development.

## Usage
```
/archflow feature              → Interactive feature wizard
/archflow feature [name]       → Quick-add a feature by name
```

## Prerequisites
- `current-phase.yaml` must exist (run `/archflow onboard` first for existing projects, or complete Phase 1 for new ones)
- `roadmap.yaml` must exist
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
   - Only ask this if `project_type` is `fullstack` (read from `current-phase.yaml`)
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

1. Read `roadmap.yaml`
2. List features with status `planned` or `in_progress`:
   ```
   Planned features in roadmap:

   1. [F-001] User Authentication (planned, high priority)
   2. [F-002] Dashboard Analytics (planned, medium priority)
   3. [F-003] Export Reports (planned, low priority)

   Which feature to start? [number]
   ```
3. User picks one → skip to Step 3 (git workflow)

---

### Step 2: Update roadmap.yaml

Read `current-phase.yaml` to get `project_type`. Add the feature in the appropriate format.

**Generate a feature ID**: Find the highest existing `F-NNN` ID in `roadmap.yaml` and increment.

#### Fullstack format
```yaml
- id: "F-{next_id}"
  name: "{feature_name}"
  description: "{description}"
  priority: {priority}
  status: planned
  scope: {frontend|backend|both}
  acceptance_criteria:
    - "{criterion_1}"
    - "{criterion_2}"
  frontend_tasks:
    - "{task_1}"
    - "{task_2}"
  backend_tasks:
    - "{task_1}"
    - "{task_2}"
  source: "{tool:ID or manual}"
```

#### Backend-only format
```yaml
- id: "F-{next_id}"
  name: "{feature_name}"
  description: "{description}"
  priority: {priority}
  status: planned
  acceptance_criteria:
    - "{criterion_1}"
  tasks:
    - "{task_1}"
    - "{task_2}"
  source: "{tool:ID or manual}"
```

#### Frontend-only format
```yaml
- id: "F-{next_id}"
  name: "{feature_name}"
  description: "{description}"
  priority: {priority}
  status: planned
  acceptance_criteria:
    - "{criterion_1}"
  tasks:
    - "{task_1}"
    - "{task_2}"
  source: "{tool:ID or manual}"
```

Write the updated `roadmap.yaml`. Confirm to user:
> "Added [Feature Name] as [F-NNN] to roadmap.yaml."

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

Follow the branching strategy from `ref:workflow.md`:

1. **Create feature branch from main:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b {feature-branch-name}
   git push -u origin {feature-branch-name}
   ```
   - Branch name: kebab-case of feature name (e.g., `user-notifications`)

2. **Update `current-phase.yaml`:**
   ```yaml
   current_feature: "F-{id}"
   feature_status: "in_progress"
   ```

3. **Create/update `current-feature.yaml`:**
   ```yaml
   feature_id: "F-{id}"
   feature_name: "{name}"
   scope: {scope}
   branch: "{feature-branch-name}"
   status: in_progress
   tasks:
     - id: "1"
       name: "{task_1}"
       type: {frontend|backend}
       status: pending
       branch: null
     - id: "2"
       name: "{task_2}"
       type: {frontend|backend}
       status: pending
       branch: null
   ```

4. **Update `roadmap.yaml`:** Set the feature's status to `in_progress`.

5. **Present next steps:**
   ```
   Feature branch created: {feature-branch-name}

   Tasks ready in current-feature.yaml:
     1. [{type}] {task_1} (pending)
     2. [{type}] {task_2} (pending)

   Start Phase 3 implementation when ready.
   Branch workflow (ref: workflow.md):
     - Task branches: {feature}/{task-name}
     - Subtask branches: {feature}/{task-number}-{subtask-name}
     - Merge only after explicit user approval
   ```

---

### Step 4: Task-Level Git Workflow (During Development)

This step runs during Phase 3 implementation, not during `/archflow feature` itself. It documents how tasks are executed using `workflow.md`.

For each task in `current-feature.yaml`:

1. **Create task branch:**
   ```bash
   git checkout {feature-branch}
   git pull origin {feature-branch}
   git checkout -b {feature}/{task-name}
   git push -u origin {feature}/{task-name}
   ```

2. **Update `current-feature.yaml`:** Set task status to `in_progress`, record branch name.

3. **Implement** using appropriate agents:
   - Check `project_type` from `current-phase.yaml`
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

8. **Update `current-feature.yaml`:** Mark task as `complete`.

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
   - `roadmap.yaml`: feature status → `complete`
   - `current-phase.yaml`: `current_feature` → `null`, `feature_status` → `ready`
   - `current-feature.yaml`: clear or remove

---

## Notes
- Feature IDs are auto-incremented from the highest existing ID in `roadmap.yaml`
- The `/archflow feature` command can be run at any time, not just during Phase 3
- Git operations always require explicit user approval before merging
- The task-level git workflow (Step 4) is executed during Phase 3, referenced here for completeness
