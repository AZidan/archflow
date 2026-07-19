# /archflow migrate — Migrate a project from schema v1.0 to v2.0

Transforms an existing Archflow project's v1.0 roadmap into the v2.0 multi-file **release** model,
using a deterministic engine (`scripts/migrate.py`) — reconstructing real releases from git shipping
evidence, not from sprints. Standalone command (NOT part of `onboard`).

**Load-bearing idea: a sprint is NOT a release.** v1 sprints were agile time-boxes; many shipped
nothing. The engine reconstructs releases from **git evidence** (deploy-pipeline landing, prod-branch
merges, tags) and routes everything else to the backlog. Validated against real 3.4k–5.8k-line roadmaps.

## When it runs
- **Manually:** the user runs `/archflow migrate`.
- **Auto-detected (prompt only, never auto-run):** any session where `.archflow/roadmap.yaml` has a
  `phases:` OR `sprints:` key, OR `schema_version` is absent/`"1.0"`:
  > "This project uses roadmap schema v1.0. Run `/archflow migrate` to upgrade to v2.0."

If `roadmap.yaml` already has `schema_version: "2.0"`, say it's already migrated and stop.

## How to run it (the deterministic engine)

The migration is performed by **`scripts/migrate.py`**, which ships alongside this command in the
archflow skill (sibling of `commands/`). It requires `python3` + `pyyaml`. Run it from the archflow
skill directory against the target project root.

**1. DRY RUN first (writes nothing) — reconstruct + show the plan:**
```bash
python3 <archflow-skill>/scripts/migrate.py --path <project-root> --dry-run
```
It prints: detected v1 variant, git deploy boundary, prod branch/release events, the reconstructed
release timeline (baseline + discrete/rolling releases with story counts), the proposed active
release, backlog size, and warnings (e.g. multiple `in_progress` sprints, git-dating coverage).

**2. PRESENT the plan to the user; get confirmation / adjustments (MANDATORY).**
- If it warns of **multiple `in_progress` sprints**, ask which one is truly being built and pass it as
  `--active <sprint-id>`.
- The user can also plan to merge/rename reconstructed releases *after* migration via `/archflow release`.
- Do not proceed to apply until the user confirms.

**3. APPLY — back up and write the v2.0 layout:**
```bash
python3 <archflow-skill>/scripts/migrate.py --path <project-root> --apply --active <sprint-id>
```
It backs up v1 to `.archflow/backup-v1/`, then writes `roadmap.yaml` (index), `backlog.yaml`,
`releases/{active}.yaml`, `releases/archive/{slug}.yaml` per reconstructed release, and `history.yaml`.

**4. Review the written files, then commit** (the engine does NOT commit):
```bash
git add .archflow/ && git commit -m "chore: migrate roadmap to schema v2.0 (releases reconstructed from git)"
```
Point the user at `.archflow/backup-v1/` for rollback; note `/archflow release` and `/archflow mode`.

## What the engine does (reference)

- **Variant handling:** canonical (epics/phases → sprints) AND top-level `sprints:` with inline
  stories, no epics/phases (the common real-world shape). Does not assume `^sprint-[0-9]+$` IDs.
- **Status normalization:** maps `done/completed→done`, `in_progress/partial-done→in_progress`,
  `review→review`, `backlog/planned/deferred→ready`; infers a sprint's status from its stories when
  missing; warns on unknown values.
- **Release reconstruction (from git):**
  - *Deploy boundary* = first-commit date of strong CD infra (`buildspec`, `cloudbuild`,
    `kubernetes/**/deployment`, `helm`, `/eks`, `infra/**prod**`, `docker-compose.prod`, `kustomize`) —
    NOT test CI. Work before it → a `baseline` release.
  - *Release events* = prod-branch merges (`from */staging`, `staging into prod`) / release tags,
    coalesced within ~5 days. None → continuous deploy: `baseline` + one rolling release.
  - *Story dating* from `S{n}-{m}` commit subjects; undated done work → `baseline`.
- **Routing:** `done` → reconstructed `releases/archive/` + `shipped` ledger + `history.yaml`; the ONE
  current `in_progress` sprint → the active `in_progress` release; everything else → `backlog.yaml` as
  **`ready` DETAILED stories** (ACs/subtasks kept, not stripped), with `target` = source sprint theme.
- **Fill-ins:** epic labels synthesized from `S{n}-` prefixes; per-story `gates` from `assigned`;
  archived-release `version` = tag or `v0-{slug}` (never null); `mode: full`; `active_release` set in
  `roadmap.yaml` + `current-phase.yaml`.
- **Invariant:** at most one `in_progress` release — refuses to guess when >1 in_progress sprint exists
  (requires `--active`).

## Guarantees
- **Non-destructive to source code** — only `.archflow/` changes.
- **Reversible** — v1 preserved under `.archflow/backup-v1/`.
- **Dry-run by default** — nothing is written without `--apply`, and only after human confirmation.
- **A story lands in exactly one place** — a release file OR backlog, never both.
- **Sprints are not releases** — releases come from shipping evidence; unshipped work → backlog.
