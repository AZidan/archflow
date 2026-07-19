# /archflow migrate — Migrate a project from schema v1.0 to v2.0

Transforms an existing Archflow project's v1.0 roadmap into the v2.0 multi-file **release** model.
Standalone command — NOT part of `onboard` (different input: existing v1 archflow state, not raw code;
different job: transform, not audit-and-build).

**The load-bearing idea: a sprint is NOT a release.** v1 sprints were agile time-boxes; many (e.g.
foundation/infra sprints) shipped nothing. So migration does NOT map sprint→release. It reconstructs
**real releases from shipping evidence in git/CI** (deploy pipeline landing, prod-branch merges, tags),
and routes everything else to the backlog. Verified against real 3.4k–5.8k-line roadmaps.

## When it runs
- **Manually:** the user runs `/archflow migrate`.
- **Auto-detected (prompt only, never auto-run):** any session where `.archflow/roadmap.yaml` has a
  `phases:` OR `sprints:` key, OR `schema_version` is absent/`"1.0"`:
  > "This project uses roadmap schema v1.0. Run `/archflow migrate` to upgrade to v2.0."

If `roadmap.yaml` already has `schema_version: "2.0"`, say it's already migrated and stop.

## Canonical schemas
Output MUST conform to `.archflow/schemas/`: `roadmap-schema.yaml` (index), `backlog-schema.yaml`
(stories at mixed readiness), `release-schema.yaml` (detailed releases), `history-schema.yaml`.

---

## Step 0 — Back up (MANDATORY, before any change)
The transform is destructive. Snapshot first, and tell the user where the backup is (reversible):
```bash
mkdir -p .archflow/backup-v1
cp -R .archflow/roadmap.yaml .archflow/current-phase.yaml .archflow/current-feature.yaml .archflow/backup-v1/ 2>/dev/null
```

## Step 1 — Read + detect the v1 variant
Parse `roadmap.yaml`. Real projects use one of these shapes — handle all:
- **Variant A (canonical):** `epics[] → stories[]` (definitions) + `phases[] → sprints[] → story-ID refs`.
- **Variant B (most common in practice):** top-level `sprints[]` with **inline stories**, NO
  `epics:`/`phases:`. Story IDs are `S{n}-{seq}` where `n` is a loose grouping, not necessarily the sprint number.
- **Unknown:** if neither, collect all `stories[]` you can find and treat them as a flat list; warn.

Normalize to a **flat list of stories** (each with id, title, priority, status, assigned, description,
acceptance_criteria, subtasks) regardless of variant. Do NOT assume sprint IDs match `^sprint-[0-9]+$`
(real data has `sprint-3_5`, `post-mvp-backlog`).

## Step 2 — Normalize statuses (real data is dirty)
Map every story `status` onto the readiness pipeline; map every sprint `status` for inference. Unknown
values → warn, don't crash.

| v1 story status | → readiness | | v1 sprint status | → meaning |
|---|---|---|---|---|
| `done`, `completed` | `done` | | `done` | shipped work (→ reconstruct releases) |
| `in_progress` | `in_progress` | | `in_progress` | the active release candidate |
| `partial-done` | `in_progress` | | `backlog`, `planned`, `null`/missing | not shipped |
| `review` | `review` | | | |
| `backlog`, `planned` | `ready` | | | |
| `deferred` | `ready` (flag `target: deferred`) | | | |
| missing/other | `ready` (warn) | | | |

**Missing sprint status** → infer: all stories `done` → `done`; any `in_progress`/`partial-done` →
`in_progress`; else treat as not-shipped.

## Step 3 — Reconstruct releases from shipping evidence (the core algorithm)

### 3a. Deploy boundary (when the project started shipping to environments)
Find the FIRST-commit date of **deployment/CD** infra — NOT test CI:
```bash
git log --diff-filter=A --format='COMMIT|%ad' --date=short --name-only
```
Strong CD markers (use these): `buildspec`, `codebuild`, `cloudbuild`, `kubernetes/**/deployment`,
`/k8s/`, `helm`, `/eks`, `infra/**prod**`, `docker-compose.prod`, `deploy.ya?ml`, `kustomiz*`.
**Exclude** `*test*` workflows (a `.github/workflows/test.yml` is test CI, not a release pipeline).
Fall back to a non-test `.github/workflows/*.yml` only if no strong marker exists.
→ Everything committed **before** this date is **pre-release foundation** → one `baseline` release.

### 3b. Release events (discrete production releases)
- **Prod/release branch** (strongest): find a branch matching `(^|/)prod$` or `release*`. Its
  merges-from-staging / merge-to-prod commits are dated **production releases**:
  ```bash
  git log <prod-branch> --format='%ad|%s' --date=short   # keep 'from */staging', 'staging into prod', 'release'
  ```
- **Git tags** (`v*`) → each tag is a release with its date.
- **Neither → continuous deploy:** no discrete events. Use `baseline` + one rolling
  `continuously-deployed` release for post-boundary done work.
- **Coalesce** events within ~5 days into one release (tight clusters are usually one release, not
  four). Present them for confirmation in Step 6 — never silently split hairs.

### 3c. Date each story from its commits
Story IDs appear in commit subjects (`feat(S6-14): …`). Map `story_id → last commit date` across all
branches:
```bash
git log --all --format='%ad|%s' --date=short   # regex S\d+-\d+ in %s
```
Expect **partial coverage** (~40–50% in practice) — early/bulk work often isn't tagged. Undated `done`
stories fall to `baseline` (honest: they predate release tracking).

### 3d. Bucket done stories into release windows
Windows = `baseline` (≤ boundary) → one per (coalesced) release event → `active/rolling`. Assign each
`done` story to the window containing its landing date; undated → `baseline`.

## Step 4 — Route every story
- **`done`** → its reconstructed release (`releases/archive/{slug}.yaml`, `status: released`) +
  `roadmap.yaml → shipped` ledger + one `history.yaml` entry each (capture `touched` from that
  release window's git diff where possible; else leave empty).
- **The ONE current release** (the active `in_progress` sprint's non-done stories, or the story cluster
  actively being built) → `releases/{slug}.yaml`, `status: in_progress`, `active_release` set.
  **Invariant: at most one `in_progress`.** If v1 has multiple in_progress sprints (real data had
  2–3), STOP and ask the user which is truly active; the others' non-done stories → backlog.
- **Everything else** (planned, no-status, `backlog`/`planned`/`deferred` stories, the non-active
  in_progress sprints) → **`backlog.yaml` as `ready` DETAILED stories** — keep their ACs/subtasks
  (do NOT downgrade to bare stubs; real v1 work is already detailed). Add `target:` = the source
  sprint's theme as a grouping hint.

## Step 5 — Epics, gates, version, mode
- **Epic labels:** synthesize from story-ID prefixes (`S{n}-` → `E{n}`); name each from the theme of
  the sprint where that prefix predominates; `scope` inferred from stories' `assigned` (default `both`).
- **Gates** per release story: `needs_design` if `assigned` ~ ui/ux/frontend/mobile; `needs_contract`
  if ~ api/backend/frappe. (Backlog `ready` stories carry gates too.)
- **Version** for archived releases: use the git tag if one maps to the window; else a placeholder
  `v0-{slug}` (NEVER `null` — `shipped_ref` requires `version`). `released_at` = the release event date.
- **Mode:** `full` (a project being migrated is substantial). Write `mode` + `active_release` to
  `roadmap.yaml` and `current-phase.yaml`.

## Step 6 — PRESENT the reconstructed plan, get confirmation (MANDATORY — do not write yet)
Show the user the reconstructed **release timeline** and routing summary, e.g.:
```
Reconstructed from git (deploy boundary 2026-06-16, prod branch found):
  baseline / pre-release        57 done stories
  release @ 2026-06-19          3 done   (S18-02 deploy, S6-12, S1-09)
  release @ 2026-06-22 (+24,25) 2 done   [3 prod events coalesced]
  release @ 2026-07-10          1 done
  active (in_progress)          → sprint-20  (2 stories)
  backlog (ready)               20 stories
Confirm, or adjust: merge/rename releases, reassign stories, pick the active release.
```
Let the user **merge/rename/reassign** and pick the active release. Only proceed on confirmation.

## Step 7 — Write the v2.0 layout
`roadmap.yaml` (index: schema_version 2.0, project, project_type, mode, epic labels, `active_release`,
`releases[]`, `shipped[]`) + `backlog.yaml` (ready detailed stories) + `releases/{active}.yaml` +
`releases/archive/{slug}.yaml` per reconstructed release + `history.yaml`. A story lands in exactly
ONE place.

## Step 8 — Report + commit
Summarize: releases reconstructed (+ how: boundary/prod/tags/continuous), active release, backlog
count, epics synthesized, dating coverage (`X/Y stories datable from git`), any unknown statuses
warned. Then:
```bash
git add .archflow/
git commit -m "chore: migrate roadmap to schema v2.0 (releases reconstructed from git history)"
```
Point the user at `.archflow/backup-v1/` for rollback; note `/archflow release` and `/archflow mode`.

## Guarantees
- **Non-destructive to source code** — only `.archflow/` changes.
- **Reversible** — v1 preserved under `.archflow/backup-v1/`.
- **A story lands in exactly one place** — a release file OR backlog, never both.
- **Sprints are not releases** — releases come from shipping evidence; unshipped work → backlog.
- **Human-confirmed** — the reconstructed timeline is presented and adjustable before anything is written.
