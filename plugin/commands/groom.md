---
description: Turn a backlog stub into a ready story: acceptance criteria, subtasks, gates
argument-hint: "[story-id]"
---

# /archflow:groom — Detail a backlog stub into a `ready` story

Argument (`$ARGUMENTS`): optional story id (e.g. `S2-11`). Empty → list stubs and ask which to groom.

Grooming turns a bare stub (title + one line) into a `ready` story with acceptance criteria,
subtasks, and gates. It is the canonical description of *how a story gets detailed* — `release.md`
(feature-planner Mode B) and the phase-3 pull-forward both defer here rather than restating it.

Grooming refines scope. It does NOT commit the story to a release or start a build — those stay
separate on purpose, so a story can be made ready without anyone deciding when to ship it.

## Usage
```
/archflow:groom              → list stubs in backlog.yaml, ask which to groom
/archflow:groom S2-11        → groom that story
```

## Flow
1. Read `.archflow/current-phase.yaml` (for `project_type`, `mode`) and `.archflow/backlog.yaml`.
   Resolve the id. With no argument, list stubs grouped by epic and ask which one.
2. **The story must be in `backlog.yaml`.**
   - If the id lives in a release file → HALT: "[{id}] is already committed to release {slug}.
     Grooming only edits the backlog — refine it directly in `.archflow/releases/{slug}.yaml`."
     There is deliberately no release-story edit path here; see Notes.
   - If the id is unknown → HALT. Never create the story — capture is `/archflow:feature`.
3. If the story is already `ready`, say so: you are REFINING existing detail, not starting fresh.
   Show the current ACs/subtasks and amend them — never blind-append duplicates.
4. **Elicit the detail — do not invent it.** Ask what's in scope and what "done" looks like; propose
   ACs and subtasks; let the user correct them before writing.
   - Derive `gates` from the work's TRUE scope, not from the repo's `project_type`: user-visible
     surface → `needs_design: true`; new or changed endpoints → `needs_contract: true`.
   - Suggest `assigned` from the scope. Leave `target` alone unless the user changes it.
5. Write the story **in place** in `backlog.yaml`: add `gates`, `assigned`, `acceptance_criteria`
   (`{text, met: false}`), `subtasks` (`{text, completed: false}`), and set `status: ready`.
6. Confirm, and name the next step without taking it:
   > "Groomed [{id}] {title} — N acceptance criteria, M subtasks, gates: design/contract.
   > Still in the backlog."
   - `full` mode → next: `/archflow:feature {id}` (pull into the active release) or
     `/archflow:release new` (carve a release around it).
   - `quick` mode → next: `/archflow:feature {id}` ONLY. Do not mention `/archflow:release new`;
     quick has no create/ship ceremony until asked, and graduating to `full` is offered, never forced.

## Hard constraints
- **`status` may only be `backlog` or `ready`** — `backlog-schema.yaml` allows nothing else.
  `spec_ready` is a RELEASE-file status: it is what promotion into a release sets, not what grooming
  sets. Writing `spec_ready` into `backlog.yaml` violates the schema. Note that `feature.md` and
  `phase-3-implementation.md` both write `spec_ready` in their promotion paths — copying that here
  is the single most likely way to get this wrong.
- **Never move the story.** Grooming ends in `backlog.yaml`. Do not touch `roadmap.yaml`, write
  `current-feature.yaml`, or create a branch.
- **Preserve unmodelled keys.** Hand-written `note:` / `scope_note:` annotations on the story must
  survive the rewrite.
- `acceptance_criteria` items MUST be `{text, met}` objects; `subtasks` MUST be `{text, completed}`.

## Quick mode
Ceremony mode is a density switch, not a schema fork — `quick` writes the same shape, just with a
shorter conversation (fewer ACs, skip the `assigned` question — it's optional in the schema).

Grooming matters MORE in quick mode than it looks: `/archflow:init` seeds `backlog.yaml` with the
full scope as stubs, so a quick project has a large groomable backlog from day one, and grooming a
stub just before building it is the normal path. Gates are still derived and written — `quick` makes
them auto-satisfied (non-blocking), not absent.

New scope added later via `/archflow:feature` defaults straight into the implicit release with ACs
written inline. That is correct and is NOT rerouted through grooming: `groom` serves the seeded
backlog, `feature` serves new scope.

## Notes
- Schemas: `backlog-schema.yaml` (what grooming writes), `release-schema.yaml` (what promotion later
  writes). Read the backlog schema before writing if unsure of the shape.
- There is currently no command that refines an existing RELEASE story's acceptance criteria —
  `/archflow:feature` on an in-release story goes straight to the git workflow. That gap is
  deliberate for now; if we want it, it's a separate command, not a wider `groom`.
