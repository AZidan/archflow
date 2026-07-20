# Proposal: Release Model + Collaboration Model (schema v2.0)

This proposal has **two pillars** and one cross-cutting knob:

- **Pillar 1 — Release model.** Releases become the first-class outer loop (sprints retired,
  centralized backlog, bounded context, searchable history).
- **Pillar 2 — Collaboration model.** Design/spec work leaves the implementation batch-phase and
  becomes a **per-story readiness pipeline**, so roles (PM → designer → engineer) work in parallel
  lanes instead of waiting on each other.
- **Modes — quick vs full.** Both pillars run over one schema; `mode: quick` dials the ceremony down
  for small/solo projects and graduates to `full` without a rewrite.


## Context

Archflow overloads the word **"phase"** for two orthogonal concepts, and only one of them
actually drives behavior:

1. **Lifecycle phases (1–6)** — the process loop (strategy → design → API → implementation →
   quality → launch). Fully operationalized: `current-phase.yaml`, per-phase instruction files,
   approval gates, agent filtering.
2. **Product phases (MVP / Growth / Scale)** — declared in `roadmap-schema.yaml` and emitted by
   `feature-planner`, but **write-only**. Nothing downstream reads them. Phase 3 selects work via
   sprints, blind to which product phase a sprint belongs to; Phase 5 (Launch) is modeled as a
   single terminal event; nothing detects or celebrates "MVP is done, ship it."

The deeper problem: the lifecycle is modeled as a **line** (1 → 6, done), but real products are a
**loop** — strategy runs once, then per release you cycle design → implement → quality → launch and
come back. In practice a mature project ships tens or hundreds of releases, and today's schema has
no first-class concept for that.

Three secondary problems compound it:

- **`roadmap.yaml` grows without bound** (one real project is 5000+ lines) because all scope, across
  all releases, shipped and unshipped, lives in one file.
- **Shipped work has no institutional memory.** When a new feature touches an area built long ago,
  nothing surfaces what was done there or why, so changes silently break shipped guarantees.
- **Design is trapped inside the implementation batch.** Because per-story design lives in Phase 2
  (all design, *then* all build in Phase 3), a designer and an engineer can never work in parallel —
  every story's design must finish before any story's code begins. That makes a genuinely
  collaborative, multi-role workflow impossible (Pillar 2).

## Goal

Make **releases** the first-class outer loop of the framework, retire sprints, keep working context
bounded no matter how large the project grows, and turn the shipped-work archive into searchable
institutional memory (Pillar 1). Move per-story design/spec out of the implementation batch into a
**readiness pipeline** so roles collaborate in parallel lanes (Pillar 2). Make both scale down to a
frictionless **quick mode** for small/solo projects and up to **full mode** without a rewrite.

This is a **breaking `schema_version: 2.0`** change with a migration path in `/archflow onboard`.

---

## Core model

```
project
└── releases            (outer loop — many may be prepared; at most one built at a time)
    └── stories         (the work unit; sprints retired)
        └── subtasks
```

Two axes tracked in `current-phase.yaml`:

```yaml
phase: 3                       # WHERE in the process loop (inner)
active_release: checkout-redesign   # WHAT we're shipping (outer) — a cached pointer
```

Lifecycle phases 2–5 become an **inner loop scoped to the active release**. Phase 5 completion =
release shipped → mark released, tag, archive, then prompt for the next release. Phase 1 (strategy)
runs once (or rarely).

`active_release` and `phase` track **implementation only** — the one release being built. Releases
in `planning`/`ready` (a PM's forward pipeline) exist out-of-band and do not move these pointers
until they transition to `in_progress`. See **Concurrency**.

### Decisions locked during brainstorm

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Rename `phases:` → `releases:`** in the roadmap. | Kills the naming collision permanently. `milestones` is vaguer; renaming the *lifecycle* phases would break every doc/command/habit. |
| 2 | **Soft release boundary.** | Real life has "ship this early" moments. But "soft" = *ask, record, reconcile* — not "warn and shrug" (see Pull-forward). |
| 3 | **Sprints retired.** | A sprint is a time-boxed container that never terminates in a ship. Archflow is scope-boxed and always ends in a release, so the release already does the sprint's job — with a terminal event. |
| 4 | **Centralized backlog; releases detailed just-in-time.** | Dissolves the count, naming, and staleness problems — you hold a small in-prep pipeline + a backlog, never 100s of forward plans. Note: creation is *not* serialized (see #7 and Concurrency). |
| 5 | **Backlog stories are stubs; release stories are fully detailed.** | Prevents the backlog from becoming the 5000-line monolith again. Detail (ACs, subtasks) is added only when a story is promoted into a release — agile's "definition of ready." |
| 6 | **Arbitrary user naming.** | User provides a display name at creation time; framework derives a filesystem-safe slug. No fixed MVP/Growth/Scale enum. |
| 7 | **At most one release `in_progress` (implementation), gated at `ready → in_progress`.** | Separates *preparation* (a PM detailing future releases — unconstrained, concurrent) from *implementation* (the engineer's single active build). Only building is serialized; preparing is not. See Concurrency. |
| 8 | **Archive shipped releases, keep them searchable.** | Archive doubles as institutional memory — an *intent layer* over codemap (see History Index). |
| 9 | **Per-story readiness pipeline; design leaves the batch phase.** | Lets PM → designer → engineer work parallel lanes. A story is designed just-in-time, one step ahead of its build, not all-design-then-all-build (Pillar 2). |
| 10 | **Split lifecycle phases into release-foundation vs per-story gates.** | Design *system* / contract *architecture* are release-wide (set once); per-*screen* design and per-*endpoint* specs are per-story gates applied just-in-time. Resolves the "phases dissolve" tension. |
| 11 | **`mode: quick \| full` as a profile over one schema, not a fork.** | Quick collapses ceremony (single implicit release, gates auto-satisfied, one lane) for small/solo work and graduates to full by flipping the flag — no re-onboard, no migration cliff. |

---

## File layout

```
.archflow/
├── roadmap.yaml            # index: project meta, epics (labels), releases pipeline, active_release pointer, shipped ledger
├── backlog.yaml            # all unshipped scope as STUBS, grouped by epic, optional target hints
├── history.yaml            # append-only searchable index of shipped stories (intent layer)
└── releases/
    ├── archive/                 # shipped release files (never loaded by the workflow)
    │   └── {slug}.yaml
    ├── checkout-redesign.yaml   # in_progress — the engineer's active build
    ├── q3-launch.yaml           # planning/ready — a PM's forward-pipeline draft
    └── loyalty-program.yaml     # planning — another draft
```

Multiple release files coexist: **at most one `in_progress`**, plus any number in `planning`/`ready`
that a PM is preparing concurrently. A story lives in **exactly one place** at any time:
`backlog.yaml` → a release file → `releases/archive/`. Moving between drafts (before implementation)
is a cheap file move with no ceremony; moving into the `in_progress` release is the pull-forward
protocol. Never duplicating, so there is never a sync question.

### `roadmap.yaml` (index — stays small forever)

```yaml
schema_version: "2.0"
project: my-app
project_type: fullstack

epics:                          # declarations / labels only — no story ownership
  - {id: E1, name: Admin Authentication, scope: backend}
  - {id: E2, name: Checkout,             scope: both}

active_release: checkout-redesign    # cached pointer to the ONE in_progress release

releases:                       # live pipeline — bounded by planning horizon, not project lifetime
  - {id: checkout-redesign, status: in_progress, file: releases/checkout-redesign.yaml}
  - {id: q3-launch,         status: ready,       file: releases/q3-launch.yaml}
  - {id: loyalty-program,   status: planning,    file: releases/loyalty-program.yaml}

shipped:                        # append-only ledger — one line per shipped release (rolls off `releases`)
  - {id: mvp, name: "MVP", version: v1.0.0, released_at: 2026-01-10, file: releases/archive/mvp.yaml}
```

The backlog holds unscheduled scope; the `releases:` pipeline holds what's being built or prepared.
Shipped releases roll off the pipeline into `shipped`, so the live list stays a planning-horizon
handful regardless of how many releases the project ships over its lifetime.

### `backlog.yaml` (stubs)

```yaml
epics:
  - id: E2
    stories:
      - id: S2-07
        title: "Saved payment methods"
        priority: High
        status: backlog          # literally means "in the backlog file"
        target: checkout          # OPTIONAL, non-binding grouping hint
        description: "Let users store and reuse cards."   # one line, no ACs/subtasks yet
```

### `releases/{current}.yaml` (fully detailed)

```yaml
id: checkout-redesign
name: "Checkout Redesign"
goal: "Frictionless checkout with saved cards and one-tap pay"
status: in_progress             # planning | ready | in_progress | released
version: null                   # set at ship
release_criteria:               # optional release-level acceptance
  - {text: "Checkout completion rate ≥ 80% in staging", met: false}
stories:
  - id: S2-07
    title: "Saved payment methods"
    priority: High
    status: design_ready        # readiness pipeline — see Pillar 2
    gates: {needs_design: true, needs_contract: true}   # which upstream gates apply
    assigned: ui-engineer
    design_artifact: design-artifacts/S2-07/            # designer's handoff (present once design_ready)
    description: >
      ...
    acceptance_criteria:        # added on promotion from backlog (PM, at spec_ready)
      - {text: "User can pay with a saved card", met: false}
    subtasks:
      - {text: "Build saved-card selector", completed: false}
```

Story IDs remain **epic-scoped** (`S2-07`), independent of release name — so arbitrary/changing
release names never touch story identity, and pull-forward never renumbers anything. `status` now
tracks the **readiness pipeline** (Pillar 2), not a flat kanban column.

---

## Lifecycle

**Strategy (once):** `product-strategist` + `feature-planner` produce `backlog.yaml` (full scope as
stubs) + optional `target` hints.

**Prepare (anytime, concurrent — the PM track):**

- **Create release** — set/suggest goal (below), select stubs from backlog, **promote** them:
  move into a new `releases/{slug}.yaml` (status `planning`) and flesh out ACs + subtasks. Multiple
  releases can sit in `planning`/`ready` at once. This is unconstrained — it never blocks on, or is
  blocked by, whatever is being implemented.
- **Mark ready** — when a draft is fully detailed and validated, set `ready`. It's now queued to
  build.

**Build (one at a time — the engineer track):**

1. **Start** — transition a `ready` release to `in_progress` (**gate: at most one in_progress**;
   optional re-validation against what's shipped since it was drafted). Set `active_release`.
2. **Inner loop** — scoped to the active release. Now split in two (see Pillar 2):
   - **Release foundation (once, at start):** Phase 2 establishes/confirms the design *system*;
     Phase 2.5 the API contract *architecture*. Light — these inform every story, they don't design
     screens or specify endpoints.
   - **Per-story flow (continuous):** each story runs its **readiness pipeline** — spec (PM) →
     design (designer, if `needs_design`) → contract (architect, if `needs_contract`) → build
     (engineer) → qa. Stories flow through these gates independently and in parallel across roles.
3. **Ship (Phase 5)** — verify release criteria + all stories done + ACs met + regression pass;
   mark `released`; git tag; generate `docs/releases/{slug}.md`; **archive** the yaml to
   `releases/archive/`; roll off the `releases:` pipeline into the `shipped` ledger + append
   `history.yaml`; clear `active_release`.
4. **Next** — if a `ready` release exists, offer to start it; if only `planning` drafts, offer to
   finalize one; if none, suggest 2–3 candidate goals from remaining high-priority stubs, `target`
   clusters, what just shipped, and project KPIs.

### Naming

User gives a display name ("Checkout Redesign", "Q3 2026 Launch", "v2.1"); framework derives a slug
(`checkout-redesign`, `q3-2026-launch`, `v2-1`) that is lowercase, kebab, filesystem-safe, unique
(dedupe with numeric suffix). The user never types the slug.

---

## Concurrency: preparation vs implementation

The framework runs two tracks against the same roadmap without collision:

| | PM / prep track | Engineer / build track |
|---|---|---|
| **Works in** | `backlog.yaml`, `planning`/`ready` release files | the one `in_progress` release file |
| **Count** | many, concurrent | exactly one |
| **Moves `phase` / `active_release`?** | no | yes |
| **Gate** | none — create/detail freely | `ready → in_progress` (at most one in_progress) |

Because it's a file per release, the two tracks never edit the same file — the split done for token
efficiency also buys clean parallelism. The single serialization point is the `ready → in_progress`
transition; everything upstream of it is free. (If a project ever runs parallel engineering
workstreams, the "at most one in_progress" gate is the single knob to relax to N — nothing else in
the model assumes one.)

The `ready → in_progress` transition is also where the optional **re-validation** lives: a draft
prepared weeks ago is reconciled against what has shipped since (via `history.yaml`) before build
starts — preserving the anti-staleness benefit without serializing preparation.

---

## Pull-forward (the "soft" boundary in practice)

Scope changes for the active release come from either the backlog or a PM's draft release:

1. Phase 3 work is scoped to the active release file only. An agent literally cannot see backlog or
   draft-release detail to be tempted by it.
2. Reaching for an outside story stops and asks: "S2-11 is in `q3-launch` (draft), not this release.
   Pull it in?"
3. On approval, the story is **moved** (from backlog: promoted + detailed; from a draft: relocated)
   into the active release, annotated `pulled_from: {backlog | q3-launch}`. Its origin is updated so
   state is true again — a story is never in two releases at once.

Advisory, never a hard block — consistent with the soft-boundary decision.

---

## Pillar 2 — Collaboration: the per-story readiness pipeline

### The problem it solves

Today per-story design lives in the implementation batch: Phase 2 designs **every** story's screens,
then Phase 3 builds them. A designer and an engineer therefore cannot work at the same time — the
engineer waits for all design, the designer has nothing to do once build starts. For a single
orchestrator that's merely inefficient; for a **multi-role, collaborative** tool it's fatal. The fix
is to make design (and its backend twin, contract spec) **per-story upstream work** that flows one
step ahead of the build.

### Readiness state machine (replaces the flat status enum)

```
backlog → spec_ready → design_ready → contract_ready → ready → in_progress → review → done
          (PM)          (Designer)     (Architect)      (all gates met) (Engineer) (QA)
```

- **`backlog`** — a stub (in `backlog.yaml`).
- **`spec_ready`** — PM has finalized scope + ACs; the story is promoted into a release. Locked from
  the product side (this is your "finalized from the product side").
- **`design_ready`** — designer has produced the story's screens; `design_artifact` points at the
  handoff. **Skipped when `needs_design: false`.**
- **`contract_ready`** — architect has specified the story's endpoints against the release contract
  architecture. **Skipped when `needs_contract: false`.**
- **`ready`** — all applicable upstream gates satisfied → buildable.
- **`in_progress → review → done`** — engineer + QA, as today.

### What keeps it lean, not bureaucratic

- **Gates are conditional.** `gates: {needs_design, needs_contract}` is derived from scope (frontend
  → design; new endpoints → contract). A backend-only story goes `backlog → spec_ready →
  contract_ready → ready`, never touching design. A pure-frontend story skips contract. A
  copy-change story skips both.
- **Handoff via files, per story.** ux-designer writes `design-artifacts/{story-id}/`; ui-engineer
  reads it. api-contract-architect writes the story's slice of `docs/api-contract.md`. This is the
  existing "handoff via files" principle, keyed per story instead of per release — no new agents.
- **Foundation vs per-story** (Decision #10). The release-wide design system and contract
  architecture are set once at release start; the per-story gates *apply* that foundation. Stories
  never reinvent the design language — they instantiate it.
- **Degrades to solo.** The states don't require multiple people; a solo dev is all lanes and walks
  their own story stub → spec → design → build. The payoff even at N=1 is the discipline: finalize
  the spec and design *before* coding, which kills the "coded against an unfinished design → rework"
  loop. (In `quick` mode the gates auto-satisfy — see Modes.)

### Orthogonal to the release pipeline

The readiness pipeline runs *within* a release; it's independent of the release-level
`planning/ready/in_progress` states. So a designer can work the design gates on stories of a `ready`
future release while an engineer builds the `in_progress` one — the PM-works-ahead parallelism from
Concurrency, now extended to design.

Enforcement is **advisory-recorded**: an engineer can start a not-yet-`ready` story, but the
framework flags it and stamps the override on the story — `started_ungated: {gate: design, by:
<role>, reason: ..., at: <iso8601>}`. Soft (the human keeps control) but accountable (every skipped
gate leaves a trace review/QA can catch), matching the pull-forward philosophy. In `quick` mode gates
auto-satisfy, so this never fires.

---

## Modes — quick vs full

Both pillars run over **one schema**. A `mode` field in `current-phase.yaml` (`quick | full`, set at
init, changeable anytime) governs how much ceremony is enforced — it is a profile, **not a fork**.

| Concern | `quick` (small / solo) | `full` (team / scale) |
|---|---|---|
| Releases | one implicit release (`current`); no create/ship ceremony until asked | explicit release pipeline, ship ritual, archive |
| Backlog split | optional — stories can live directly in the release | backlog stubs → promote → detailed |
| Readiness gates | **auto-satisfied** (states exist but don't block); design/contract only if user opts in | enforced advisory gates, role lanes |
| Approval gates | proceed unless the user stops you | explicit per-phase approval |
| Roles | one lane (solo) | PM / designer / architect / engineer / QA lanes |
| History / codemap | still captured on demand | fully on |

**Defaults:** `/archflow init` → `quick` (new small project); `/archflow onboard` → `full` when it
detects a substantial codebase or a second contributor, else `quick`.

**Switching mode:** `/archflow mode` (shows current mode) / `/archflow mode full` / `/archflow mode
quick`. Switching `quick → full` migrates in place — materialize the implicit release, split the
backlog, turn gates on. No re-onboard, no data rewrite, because the schema was always the same.
`full → quick` is also legal (collapse to advisory) for a project that over-scoped itself.

> Command is deliberately named `mode`, **not** `upgrade` — "upgrade" reads as a paid/billing action.
> This is a neutral capability toggle.

**Smart graduation prompt (never forced):** the framework watches for growth signals and *offers* to
switch a `quick` project to `full` — it never migrates silently. Triggers:

- the user asks for a **second release** (quick's single implicit release no longer fits),
- a **second contributor** appears (role lanes start to matter),
- the project **crosses a size threshold** (story count / file count / repo age).

On a trigger: "This project looks like it's outgrowing quick mode (<reason>). Switch to full mode?
It adds explicit releases and role-based design/spec gates. `/archflow mode full` — or keep going as
is." The user decides; declining is remembered so it doesn't nag every session.

---

## History Index (institutional memory / intent layer)

On ship, append one entry per story to `history.yaml` — loaded only on lookup, never per-step:

```yaml
- story: S3-04
  release: checkout-redesign
  version: v1.4.0
  shipped_at: 2026-03-14
  summary: "Redesigned checkout payment form with saved cards"
  touched:
    files:     [frontend/checkout/PaymentForm.tsx, backend/orders/orders.controller.ts]
    endpoints: [POST /orders, GET /payment-methods]
    screens:   [checkout]
  acceptance_criteria:
    - "User can pay with a saved card"
    - "Declined payment shows inline error"
  archive: releases/archive/checkout-redesign.yaml
```

`touched` is captured from the git diff at ship (tag-to-tag) — reliable at release granularity,
best-effort at story granularity per branch structure.

**Two query trigger points:**

- **Feature intake / goal-setting** — match a new feature's area/keywords/endpoints against
  `history.yaml`, surface prior art ("this overlaps Checkout Redesign S3-04, which did X"). Fuzzy;
  a helpful heads-up.
- **Pre-modification check (Phase 3)** — before an agent modifies a file, look up its concrete path
  and flag the shipped story + AC that produced it ("`PaymentForm.tsx` last shipped for S3-04 whose
  AC was 'declined payment shows inline error' — confirm your change preserves that"). Exact, because
  the file is known. **This is the primary safety guarantee.**

**Framing:** codemap answers *what/where is this code*; `history.yaml` answers *why does it exist and
what was it supposed to do*. Together an agent goes file → symbols (codemap) → originating story, ACs,
release (history).

Advisory, never a gate. Flat, append-only, grep-friendly; shard by year/epic only if it ever gets
huge.

---

## Change surface (implementation order)

1. `roadmap-schema.yaml` → v2.0 (releases, backlog stubs vs detailed stories, epics demoted to
   labels, sprints removed, release_criteria, history schema, **story readiness states + `gates`
   flags + `design_artifact`**).
2. `current-phase.yaml` template + `phase-setup.md` (add `active_release`; **add `mode`**;
   derive/validate against roadmap).
3. `feature-planner` + `product-strategist` output formats (produce backlog stubs; release-creation
   promotion + goal suggestion; drop MVP/Growth/Scale enum; **set `gates` from scope**).
4. `phase-1-strategy.md` (produce backlog, not release plans).
5. **`phase-2-design.md` + `phase-2.5-api-architecture.md`** (split into release-foundation setup
   vs per-story gates; design system / contract architecture once, per-screen / per-endpoint work
   moves to the readiness pipeline).
6. `phase-3-implementation.md` (release-scoped story selection; **build only `ready` stories, honor
   readiness gates**; pull-forward protocol; pre-modification history check).
7. `phase-4-quality.md` (regression scope = active release).
8. `phase-5-launch.md` (ship ritual: criteria check, mark released, tag, `docs/releases/{slug}.md`,
   archive, append ledger + history, clear pointer, prompt for next).
9. `workflow.md` (step 8 tracking edits target the active release file; capture footprint for history
   on merge; **readiness-gate handoffs**).
10. **Mode enforcement layer** — a shared helper the phase docs consult: `quick` auto-satisfies gates
    and collapses ceremony; `full` enforces. Plus `/archflow mode [quick|full]` (in-place switch) and
    the **smart graduation prompt** (offer full on growth signals; remember a decline).
11. **New `/archflow migrate` command** — standalone v1 → v2 schema transform (below). *Not* folded
    into `onboard`: different input (existing v1 archflow state, not raw code) and different job
    (transform vs audit-and-build). Keeps `onboard` lean and gives future schema bumps a home.
12. `/archflow init` + `/archflow onboard` — set **mode defaults** only (init → `quick`; onboard →
    `full`/`quick` by codebase size + contributors). No migration logic here.
13. `/archflow` status + new `/archflow release` command (surface active release, % done, criteria,
    **per-story readiness lane**); v1-schema **auto-detect prompt** ("run `/archflow migrate`").
14. Mirror all of the above into `plugin/` and `skills/` copies.

## Migration (`/archflow migrate`, v1 → v2)

Standalone command (not part of `onboard`). Runs only on a project already holding v1 archflow
state; **auto-detected** on any session where `roadmap.yaml` has `phases:` or `schema_version` is
absent/`1.0`, which surfaces a prompt to run it (never auto-runs). **Step 0: back up** the entire v1
`.archflow/` to `.archflow/backup-v1/` before transforming, since the transform is destructive
(splits the monolith, moves stories). Then:

1. Rename `phases:` → `releases:`.
2. Infer each release's status from its sprints (all done → `released`; any in_progress →
   `in_progress`; else split into backlog).
3. Flatten sprints away — their stories attach directly to the release.
4. Split: shipped releases → `releases/archive/` + `shipped` ledger + backfill `history.yaml` from
   git (tag-to-tag diffs where tags exist); the one in_progress release → `releases/{slug}.yaml`;
   everything else → `backlog.yaml` as stubs.
5. Orphan stories (referenced by no sprint) → `backlog.yaml`, flagged for the next release-creation
   review.
6. Set `mode`: `full` if the migrated project has multiple releases / real role separation, else
   `quick`. Backfill `gates` on migrated stories from their scope (existing design artifacts →
   `needs_design: true`; endpoints in the contract → `needs_contract: true`).

## Open questions (none blocking)

- Footprint attribution accuracy depends on branch discipline — capture release-level always,
  story-level best-effort, degrade gracefully.
- `history.yaml` growth at very large scale — flat/grep-friendly is fine into the thousands; shard
  later if needed.
- ~~**Graduation trigger**~~ **Resolved:** smart prompt on growth signals (2nd release / 2nd
  contributor / size threshold), never forced; a decline is remembered. Command is `/archflow mode`,
  not `upgrade` (avoids paid-action connotation).
- ~~**Readiness gate strictness in `full`**~~ **Resolved: advisory-recorded.** Building a
  not-`ready` story is warned + overridable, but the override is stamped on the story
  (`started_ungated: {gate, by, reason, at}`) so skipped gates leave a trace review/QA can catch.
  Soft, but accountable — consistent with pull-forward (Decision #2).

## Related proposals (separate, but they compose)

- **`archflow-skill-scaffolding-proposal.md`** — project-scoped skill catalogs. Kept separate (it's a
  knowledge layer, not a schema change), but it consumes v2.0's `history.yaml` + archived releases as
  its incident/knowledge source, and its `/archflow scaffold-skills` follows the same "new capability
  = new command" pattern as `migrate` and `mode`. The `history.yaml` ↔ skills seam: history is the
  append-only machine record; skills are the curated, human-reviewed distillation fed from it.
