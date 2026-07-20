# /archflow release — Inspect and manage releases

The release is the v2.0 outer-loop unit. This command surfaces the pipeline and drives the
release-level lifecycle actions. It reads the index (`roadmap.yaml`), the active release file, and the
shipped ledger; it does not itself write application code.

## Usage
```
/archflow release                 → status: pipeline + active release progress + shipped ledger
/archflow release new [name]      → create a release from the backlog (feature-planner Mode B)
/archflow release start [slug]    → transition a ready release to in_progress (the build gate)
/archflow release ship            → run the Phase 5 ship ritual for the active release
```

## `release` (no argument) — status
Read `.archflow/roadmap.yaml`. Print:
- **Active release** (`active_release`): its goal, and story progress from
  `.archflow/releases/{active_release}.yaml` — count by readiness status
  (spec_ready / design_ready / contract_ready / ready / in_progress / review / done), release_criteria
  met/total, and any stories carrying `started_ungated`.
- **Pipeline** (`releases[]`): each planning/ready/in_progress release with its status.
- **Shipped** (`shipped[]`): the ledger (id, version, released_at).
- **Backlog**: count of stubs in `backlog.yaml` (grep, don't load fully).
In `quick` mode, collapse to just the single implicit release's progress.

## `release new [name]` — create
1. Derive a slug from `[name]` (lowercase, kebab, filesystem-safe, unique).
2. Set/suggest the goal: if `[name]` is vague, suggest 2–3 candidate goals from high-priority backlog
   stubs, their `target` clusters, what just shipped (`history.yaml`), and project KPIs.
3. Invoke **feature-planner (Mode B)**: select stubs from `backlog.yaml`, MOVE them into
   `.archflow/releases/{slug}.yaml`, detail ACs + subtasks, derive `gates`. Status starts `planning`.
4. Register the release in `roadmap.yaml → releases` with `status: planning`.
Creating a release is unconstrained — many may be in `planning`/`ready` at once (a PM preparing ahead
while an engineer builds the active one).

## `release start [slug]` — build gate
1. Confirm `[slug]` (or the sole `ready` release) exists and is `ready`.
2. **Gate: at most one `in_progress`.** If another release is already `in_progress`, HALT — finish or
   park it first.
3. Optional re-validation: reconcile against what has shipped since it was drafted (`history.yaml`).
4. Set `status: in_progress` in the release file and `roadmap.yaml → releases`; set `active_release`
   in `roadmap.yaml` and `current-phase.yaml`; set `current-phase.yaml → phase` to 2 (or 3 if design +
   contract are unchanged from a prior release). Re-enter the inner loop.

## `release ship` — finalize
Run the **Phase 5 ship ritual** (`.archflow/phases/phase-5-launch.md`, Step 5C) for the active
release: verify releasable → mark released + version + tag → generate `docs/releases/{slug}.md` →
archive the release file → append `history.yaml` (with `touched` from the tag-to-tag diff) → roll off
the index into `shipped` → clear `active_release` → commit. Then offer the next release (Step 5D).

## Notes
- Source of truth for status is `roadmap.yaml` + the release files; `current-phase.yaml → active_release`
  is a validated cache.
- Schemas: `roadmap-schema.yaml` (index), `release-schema.yaml` (release files).
