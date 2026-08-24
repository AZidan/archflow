# Phase 5: Ship the Active Release

## 🎯 Phase Objective
Ship the active release: deploy to production with CI/CD + monitoring, then run the **ship ritual**
that finalizes the release record (mark released, tag, archive, append history), and loop back to the
next release. Phase 5 is NOT terminal — it is the bottom of the release loop.

## 📋 Required Agents
- `devops-engineer` - CI/CD, deployment, infrastructure, app store preparation
- `post-launch-analyst` - Analytics setup, user insights, performance monitoring

## 📚 Prerequisites
- Phase 4 quality gates passed for the active release
- All stories in `.archflow/releases/{active_release}.yaml` are `done`
- `release_criteria` (if any) all `met`
- User approval from Phase 4

## 🚀 Execution Steps

### Step 5A: Deployment Infrastructure
```bash
devops-engineer: setup CI/CD + deployment → .github/workflows/ + deployment/
  - CI/CD pipelines, staging + production environments, automated tests in pipeline
  - Deployment automation, backup/recovery, security/access controls
  - App store submissions (if mobile)
```

### Step 5B: Analytics & Monitoring
```bash
post-launch-analyst: setup analytics + monitoring → docs/analytics-setup.md
  - Analytics tracking, performance + error monitoring, dashboards, alerting
```

### Step 5C: 🚢 SHIP RITUAL (Release Finalization — MANDATORY)

Runs once the release is deployed and accepted. This is the archflow bookkeeping that closes a
release and keeps the roadmap bounded. Perform IN ORDER:

1. **Verify releasable**: every story `done`, all ACs `met`, all `release_criteria` `met`, Phase 4
   regression passed. Any gap → HALT.
   - **Parked stories block the ship.** Any story with `status: parked` and
     `parked.blocks_release: true` → HALT and print its `parked.question`: a release does not ship
     with an unanswered product question inside it. Resolving it means the user answers, the story
     is built out and marked `done` — or the user explicitly sets `blocks_release: false` on that
     story. Never clear the flag yourself to get past this check.

2. **Set version + mark released** in `.archflow/releases/{active_release}.yaml`:
   `status: released`, `version: vX.Y.Z`, `released_at: <iso8601>`.

3. **Git tag** the release: `git tag vX.Y.Z && git push origin vX.Y.Z`.

4. **Generate release notes** → `docs/releases/{active_release}.md` from the release's stories
   (titles + ACs) and goal. This is the durable human record.

5. **Archive** the release file: move `.archflow/releases/{active_release}.yaml` →
   `.archflow/releases/archive/{active_release}.yaml`.

6. **Append `history.yaml`** — one entry per shipped story (the intent layer). Capture `touched`
   (files / endpoints / screens) from the git diff of this release (previous tag → this tag), plus
   the story's summary + ACs. Symbol/path anchors only, never line numbers.
   ```bash
   git diff <previous-tag>..vX.Y.Z --name-only   # -> touched.files per story (best-effort per story)
   ```

7. **Roll off the index**: remove the release from `roadmap.yaml → releases`, append it to
   `roadmap.yaml → shipped` (id, name, version, released_at, file → archive path).

8. **Clear the pointer**: remove the `active_release` key from `roadmap.yaml` and `current-phase.yaml`
   (omit it rather than writing `null` — matches how migrate leaves it). (In quick mode with a single
   implicit release, just mark it released.)

9. **Commit** the finalization:
   ```bash
   git add .archflow/ docs/releases/{active_release}.md
   git commit -m "release: ship {active_release} vX.Y.Z"
   ```

### Step 5D: ➡️ Next Release (loop back)

The release loop continues. Offer the next step (never auto-start):
- If a `ready` release exists in `roadmap.yaml → releases` → offer to start it (→ transition it to
  `in_progress`, re-enter the inner loop at Phase 2 or Phase 3 per scope of change).
- If only `planning` drafts exist → offer to finalize one to `ready`.
- If none → suggest 2–3 candidate goals (from remaining high-priority backlog stubs, their `target`
  clusters, what just shipped in `history.yaml`, and project KPIs) and let the user pick, then
  feature-planner (Mode B) creates the release.
- Or → Phase 6 (Enhancement) / stop.

## 📤 Expected Outputs
- `.github/workflows/` + `deployment/` - CI/CD + infrastructure
- `docs/analytics-setup.md` - analytics + monitoring
- `docs/releases/{active_release}.md` - release notes
- Updated `.archflow/roadmap.yaml` (release rolled to `shipped`), archived release file, appended
  `.archflow/history.yaml`, git tag `vX.Y.Z`

## ✅ Completion Criteria
- [ ] CI/CD + production infra deployed and secured; rollback tested
- [ ] Analytics + monitoring operational
- [ ] Release marked `released` + versioned + tagged
- [ ] Release notes generated; history.yaml appended; release archived; index rolled off
- [ ] `active_release` cleared
- [ ] Next-release step offered to the user

## 🚨 Critical Requirements
- **STAGING FIRST**; automated tests pass in CI/CD; **ROLLBACK READY**; monitoring operational.
- **USER APPROVAL MANDATORY** before actual production launch — **NO AUTONOMOUS LAUNCH**.
- **Ship ritual is not optional** — a release is not shipped until it is marked released, tagged,
  archived, and rolled off the index. A half-shipped release left `in_progress` blocks the next one.

## 🚀 Launch Types
Soft launch · Full launch · Staged rollout · Blue-green (zero-downtime). Choose per risk.

## ➡️ Phase Transition (loop, not terminus)
After the ship ritual completes and `active_release` is cleared:
1. If starting the next release → set the new `active_release`, `current-phase.yaml → phase: 2` (or 3
   if no design/contract change), re-enter the inner loop.
2. If pausing → `current-phase.yaml → phase: monitoring`; Phase 6 (`phase-6-enhancement.md`) for
   on-demand enhancements.

---
**Release shipped** 🚀 → **Next release (loop)** or **Monitoring / Enhancement** 📊
