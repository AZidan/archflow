# Feature Development Workflow

A generalized workflow for managing feature development with tasks and subtasks.

## Branch Structure

```
[feature-branch] (feature branch)
└── [feature]/[task-name] (task branch)
    ├── [feature]/[task-number]-[subtask-name] (subtask branch)
    ├── [feature]/[task-number]-[subtask-name] (subtask branch)
    └── ...
```

**Example:**
```
user-auth (feature branch)
└── auth/login-flow (task branch)
    ├── auth/1.1-email-validation (subtask branch)
    ├── auth/1.2-password-strength (subtask branch)
    └── auth/1.3-remember-me (subtask branch)
└── auth/registration (task branch)
    └── ...
```

---

## Starting a New Feature

```bash
# 1. Create feature branch from main/develop
git checkout main  # or develop
git pull origin main
git checkout -b [feature-branch]
git push -u origin [feature-branch]
```

---

## Starting a New Task (within a Feature)

```bash
# 1. Create task branch from feature branch
git checkout [feature-branch]
git pull origin [feature-branch]
git checkout -b [feature]/[task-name]
git push -u origin [feature]/[task-name]
```

---

## For Each Subtask

### Step 1: Create subtask branch from task branch
```bash
git checkout [feature]/[task-name]
git pull origin [feature]/[task-name]
git checkout -b [feature]/[task-number]-[subtask-name]
```

### Step 2: Implement changes
- Make code changes as specified in the subtask requirements
- Follow existing code patterns and styling conventions

### Step 3: Build and test locally
```bash
# Run your project's build/test commands
yarn build && yarn start
# or
npm run build && npm run dev
```

- Test the feature to verify requirements
- Check responsiveness if applicable
- Verify dark mode/themes work correctly

### Step 4: Commit and push
```bash
git add .
git commit -m "feat: [description of changes]"
git push -u origin [feature]/[task-number]-[subtask-name]
```

### Step 5: Wait for EXPLICIT user approval
- **CRITICAL**: Do NOT merge until user EXPLICITLY approves
- Push subtask branch and wait for user to test
- User will test the changes
- Address any feedback before proceeding
- **Never auto-merge** - user must confirm the task is done

### Step 6: After EXPLICIT approval, merge subtask to task branch
```bash
git checkout [feature]/[task-name]
git pull origin [feature]/[task-name]
git merge [feature]/[task-number]-[subtask-name]
git push origin [feature]/[task-name]
```

### Step 7: Clean up subtask branch
```bash
git branch -d [feature]/[task-number]-[subtask-name]
git push origin --delete [feature]/[task-number]-[subtask-name]
```

### Step 8: Update tracking documentation
- Mark subtask as "Complete"
- Move to next subtask

---

## Completing a Task

After ALL subtasks in a task are complete and approved:

```bash
# Merge task branch to feature branch
git checkout [feature-branch]
git pull origin [feature-branch]
git merge [feature]/[task-name]
git push origin [feature-branch]

# Clean up task branch
git branch -d [feature]/[task-name]
git push origin --delete [feature]/[task-name]
```

Then:
1. Update tracking docs with next task
2. Update status tracker
3. Start next task if applicable

---

## Completing a Feature

After ALL tasks in a feature are complete and approved:

```bash
# Merge feature branch to main/develop
git checkout main  # or develop
git pull origin main
git merge [feature-branch]
git push origin main

# Clean up feature branch (optional - may keep for reference)
git branch -d [feature-branch]
git push origin --delete [feature-branch]
```

---

## Testing Checklist

Before requesting user review:
- [ ] Build succeeds without errors
- [ ] App runs correctly
- [ ] Feature works as specified in requirements
- [ ] Responsive design verified (if applicable)
- [ ] Dark mode/themes work correctly (if applicable)
- [ ] No console errors
- [ ] Accessibility considerations addressed
- [ ] Unit/integration tests pass (if applicable)

---

## Branch Naming Conventions

| Level | Pattern | Example |
|-------|---------|---------|
| Feature | `[feature-name]` | `user-auth`, `payment-flow` |
| Task | `[feature]/[task-name]` | `auth/login-flow`, `payment/checkout` |
| Subtask | `[feature]/[number]-[name]` | `auth/1.1-validation`, `payment/2.3-stripe` |

---

## Commit Message Conventions

```bash
# Feature commits
feat: add user authentication flow

# Bug fixes
fix: resolve login redirect issue

# Refactoring
refactor: extract validation logic to utils

# Documentation
docs: update API documentation

# Styling
style: improve button hover states

# Tests
test: add unit tests for auth service
```

---

## Quick Reference

### Create Subtask Branch
```bash
git checkout [feature]/[task-name] && \
git pull origin [feature]/[task-name] && \
git checkout -b [feature]/[subtask]
```

### Merge Subtask (after approval)
```bash
git checkout [feature]/[task-name] && \
git merge [feature]/[subtask] && \
git push origin [feature]/[task-name] && \
git branch -d [feature]/[subtask] && \
git push origin --delete [feature]/[subtask]
```

### Merge Task (after all subtasks complete)
```bash
git checkout [feature-branch] && \
git merge [feature]/[task-name] && \
git push origin [feature-branch] && \
git branch -d [feature]/[task-name] && \
git push origin --delete [feature]/[task-name]
```

---

## Template Variables

Replace these placeholders with your actual values:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `[feature-branch]` | Main feature branch name | `user-auth` |
| `[feature]` | Feature prefix for branches | `auth` |
| `[task-name]` | Name of the current task | `login-flow` |
| `[task-number]` | Task number (1, 2, 3...) | `1` |
| `[subtask-name]` | Name of the subtask | `email-validation` |
| `[subtask]` | Full subtask identifier | `1.1-email-validation` |

---

*Reference this file when starting new features, tasks, or subtasks*
