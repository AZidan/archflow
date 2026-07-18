# /archflow migrate — Migrate a project from schema v1.0 to v2.0

Transforms an existing Archflow project's roadmap from the v1.0 format (`phases:` + `sprints:`, one
monolithic `roadmap.yaml`) into the v2.0 multi-file release model. This is a **standalone command** —
it is NOT part of `onboard` (different input: existing v1 archflow state, not raw code; different job:
transform, not audit-and-build).

## When it runs

- **Manually:** the user runs `/archflow migrate`.
- **Auto-detected (prompt only, never auto-run):** on any session where `.archflow/roadmap.yaml` has a
  `phases:` key OR `schema_version` is absent or `"1.0"`, surface:
  > "This project uses roadmap schema v1.0. Run `/archflow migrate` to upgrade to v2.0 (releases
  > replace phases, sprints retired, multi-file split)."

If `.archflow/roadmap.yaml` already has `schema_version: "2.0"`, tell the user it's already migrated
and stop.

## Canonical schemas

The output MUST conform to the v2.0 schemas in `.archflow/schemas/`: `roadmap-schema.yaml` (index),
`backlog-schema.yaml` (stubs), `release-schema.yaml` (detailed releases), `history-schema.yaml`.

## Procedure

### Step 0 — Back up (MANDATORY, before any change)
The transform is destructive (splits the monolith, moves stories). Snapshot first:
```bash
mkdir -p .archflow/backup-v1
cp -R .archflow/roadmap.yaml .archflow/current-phase.yaml .archflow/current-feature.yaml .archflow/backup-v1/ 2>/dev/null
```
Tell the user where the backup is, so migration is reversible.

### Step 1 — Read the v1 roadmap
Parse `.archflow/roadmap.yaml`: `project`, `project_type`, `epics[]` (with inline `stories[]`), and
`phases[]` (each with `sprints[]`, each sprint referencing story IDs).

### Step 2 — Classify each v1 "phase" (product milestone) into a release status
For each v1 `phase` (e.g. `mvp`, `growth`):
- **All its sprints `done`** → the release is `released` (shipped).
- **Any sprint `in_progress`** → the release is `in_progress` (at most ONE such — see Step 6).
- **Otherwise (all backlog / empty)** → its stories are NOT yet scheduled → they become backlog stubs
  (do not create a release file for an all-empty milestone).

### Step 3 — Flatten sprints away
Sprints are retired. A sprint's referenced stories attach DIRECTLY to their release. The story detail
comes from the epic's inline story definition (v1 stories live under epics). Preserve each story's
`id`, `title`, `priority`, `status`, `assigned`, `description`, `acceptance_criteria`, `subtasks`.

### Step 4 — Derive per-story `gates` (v2.0)
For each story that lands in a release file, add `gates: {needs_design, needs_contract}`:
- `needs_design: true` if the story is frontend/mobile/UI scope (has design artifacts, screens, or
  `assigned: ui-engineer`).
- `needs_contract: true` if the story creates/changes API endpoints (`assigned: api-engineer`, or the
  description mentions endpoints/API).
Map the v1 flat `status` (backlog|in_progress|review|done) onto the readiness pipeline: `done`→`done`,
`review`→`review`, `in_progress`→`in_progress`, `backlog`→`ready` (already scheduled into a release)
unless a gate is clearly unmet.

### Step 5 — Write the v2.0 file layout
- **`.archflow/releases/archive/{slug}.yaml`** — one per `released` milestone (per `release-schema.yaml`),
  with `status: released`. If a git tag exists for it, set `version`/`released_at`.
- **`.archflow/releases/{slug}.yaml`** — the single `in_progress` milestone (if any).
- **`.archflow/backlog.yaml`** — every story from unscheduled milestones + orphan stories (Step 5b),
  as STUBS (`status: backlog`, drop ACs/subtasks — keep title/priority/one-line description, add
  optional `target` = old milestone id as a hint).
- **`.archflow/history.yaml`** — one entry per story in archived (released) releases. Backfill
  `touched` from git where tags exist (`git diff <prev-tag>..<tag> --name-only`); if no tags, leave
  `touched` best-effort/empty and note it. Include summary + AC text.
- **`.archflow/roadmap.yaml`** — rewrite as the v2.0 INDEX: `schema_version: "2.0"`, `project`,
  `project_type`, `mode` (Step 6), `epics` as LABELS (id/name/scope only, drop inline stories),
  `active_release` (the in_progress slug or null), `releases[]` (in_progress + any planning/ready),
  `shipped[]` (ledger of archived releases).

#### Step 5b — Orphan stories
Stories referenced by no sprint → `backlog.yaml` as stubs, flagged in your summary for the user to
sort into a release later (a good first job for the next release-creation review).

### Step 6 — Set `mode` and update current-phase.yaml
- `mode: full` if the project has multiple releases (milestones) or clear role separation; else
  `mode: quick`.
- Update `.archflow/current-phase.yaml`: add `mode` and `active_release` (the in_progress slug or null).
- **Invariant check:** at most ONE release may be `in_progress`. If v1 had two milestones each with an
  in_progress sprint, STOP and ask the user which one is actually being built; the other's unshipped
  stories go to backlog.

### Step 7 — Report + commit
Summarize: releases archived, active release (if any), stubs moved to backlog, orphans flagged, mode
chosen, whether history `touched` was backfilled from tags. Then:
```bash
git add .archflow/
git commit -m "chore: migrate roadmap to schema v2.0 (releases, multi-file split)"
```
Point the user at `.archflow/backup-v1/` for rollback, and note they can now use `/archflow release`
and `/archflow mode`.

## Guarantees
- **Non-destructive to source code** — only `.archflow/` is transformed.
- **Reversible** — the v1 files are preserved under `.archflow/backup-v1/`.
- **A story lands in exactly one place** — a release file OR backlog, never both.
