---
name: archflow-groom
description: "Detail or refine a story: acceptance criteria, subtasks, gates. Works on a backlog stub or a story already in a release"
---

> Invoke with `$archflow-groom`. Arguments are the text after the mention.

Arguments: `[story-id]`


# $archflow-groom — Detail or refine a story

Argument (`the text the user wrote after the skill mention`): optional story id (e.g. `S2-11`). Empty → list stubs and ask which to groom.

Grooming turns a bare stub (title + one line) into a `ready` story with acceptance criteria,
subtasks, and gates, and **refines a story that is already in a release** when its scope turns out
to be wrong. It is the canonical description of *how a story gets detailed* — `release.md`
(feature-planner Mode B) and the phase-3 pull-forward both defer here rather than restating it.

Grooming refines scope. It does NOT commit the story to a release or start a build — those stay
separate on purpose, so a story can be made ready without anyone deciding when to ship it.

## Usage
```
$archflow-groom              → list stubs in backlog.yaml, ask which to groom
$archflow-groom S2-11        → groom that story, wherever it lives
```

**Two modes, chosen by where the story is, not by an argument.** A backlog story is groomed into
`ready` (**backlog mode**). A story already in a release is refined in place with its gates
re-derived (**release mode**). The user's question is "refine this story"; which file it happens to sit in is an
implementation detail they should not have to know.

## Flow
1. Read `.archflow/current-phase.yaml` (for `mode`), `.archflow/project-settings.yaml` (for `project_type`) and `.archflow/backlog.yaml`.
   Resolve the id. With no argument, list stubs grouped by epic and ask which one.
2. **Find the story, and pick the mode from where it lives.**
   - In `.archflow/backlog.yaml` → **backlog mode**, the flow below. This is the common case.
   - In `.archflow/releases/{slug}.yaml` → **release mode** (see its own section). Say which
     release it is in
     before making any change, so the user knows the scope of what they are editing.
   - In neither → HALT. Never create the story; capture is `$archflow-feature`.
   - In a file under `releases/archive/` → HALT. That release has shipped. Its stories are history
     and are not edited; capture the new work as a new story.
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
   - `full` mode → next: `$archflow-feature {id}` (pull into the active release) or
     `$archflow-release new` (carve a release around it).
   - `quick` mode → next: `$archflow-feature {id}` ONLY. Do not mention `$archflow-release new`;
     quick has no create/ship ceremony until asked, and graduating to `full` is offered, never forced.

## Release mode — refining a story already in a release

Acceptance criteria change during a release. Design surfaces a case nobody considered; the contract
shows an AC was wrong.

Eliciting the detail works exactly as in backlog mode. What differs is where it is written, that
gates and status re-derive from the new scope, and how carefully you have to tread — this story may
already be built.

### 1. Check the story's status first — this decides how safe the edit is

| Status | What to do |
|---|---|
| `spec_ready`, `design_ready`, `contract_ready`, `ready` | Refine freely. Nothing has been built against these criteria yet. |
| `in_progress` | **STOP and ask.** An engineer is building against the current criteria right now. Show what would change and let the user decide whether to interrupt. If they proceed, say the story's branch may already contain work the new criteria invalidate. |
| `review` | **STOP and ask.** The work is built and being verified. Changing the criteria now moves the goalposts under `qa-engineer` or `pm-reviewer`. Usually the right answer is a follow-up story, so offer that first. |
| `done` | HALT. Refine nothing. The story shipped against its criteria and that record is what `history.yaml` reports. Capture the change as a new story. |
| `parked` | Show the parked question first. Often the refinement IS the answer, and resolving it un-parks the story. |

### 2. Amend, never replace

Show the current acceptance criteria and subtasks and edit them with the user. Preserve every
`met: true` and `completed: true` flag on items that survive — those are evidence that something was
verified, and silently resetting them destroys the acceptance record.

If an AC that was already `met: true` is being changed, say so explicitly. Its verification no longer
applies, so it becomes `met: false` and loses its `verified_by` and `verified_at`.

### 3. Re-derive the gates, and regress the status if they reopened

Derive `gates` from the story's NEW true scope, exactly as backlog mode does. Then compare:

- **A gate went `false` → `true`** — that step has not happened for this story. Regress `status` to
  `spec_ready` so the readiness pipeline runs the new gate. Say plainly what this means: the story
  needs `$archflow-design {id}` or `$archflow-contract {id}` again before it can be built.
- **A gate went `true` → `false`** — leave the status alone. Work already done is not invalidated by
  needing less, and regressing would discard a real artifact.
- **No gate changed** — leave the status alone.

Never regress past `spec_ready`, and never regress a `done` story.

Clear `design_artifact` or `contract_endpoints` only when the corresponding gate reopened AND the
user confirms the old artifact no longer applies. A stale pointer is easier to spot than a lost one.

### 4. Write and report

Write in place in `.archflow/releases/{slug}.yaml`. Do not move the story, do not touch
`roadmap.yaml`, do not create a branch.

```
Refined {id} {title} in release {slug}.
  Acceptance criteria: {n} ({added} added, {changed} changed, {removed} removed)
  Gates: needs_design {before} → {after} · needs_contract {before} → {after}
  Status: {before} → {after}

{when a gate reopened:}
  {id} needs $archflow-{design|contract} {id} again before it can be built.
```

## Hard constraints
- **In backlog mode, `status` may only be `backlog` or `ready`** — `backlog-schema.yaml` allows nothing else.
  `spec_ready` is a RELEASE-file status: it is what promotion into a release sets, not what grooming
  sets. Writing `spec_ready` into `backlog.yaml` violates the schema. Note that `feature.md` and
  `phase-3-implementation.md` both write `spec_ready` in their promotion paths — copying that here
  is the single most likely way to get this wrong.
- **Never move the story.** Grooming ends where the story already was — `backlog.yaml` in backlog
  mode, the release file in release mode. Never touch `roadmap.yaml`, write `current-feature.yaml`,
  or create a branch.
- **`status` in a RELEASE file follows the readiness ladder**, not the backlog's two values. Release
  mode may only ever set `spec_ready`, and only when a gate reopened.
- **Preserve unmodelled keys.** Hand-written `note:` / `scope_note:` annotations on the story must
  survive the rewrite.
- `acceptance_criteria` items MUST be `{text, met}` objects; `subtasks` MUST be `{text, completed}`.

## Quick mode
Ceremony mode is a density switch, not a schema fork — `quick` writes the same shape, just with a
shorter conversation (fewer ACs, skip the `assigned` question — it's optional in the schema).

Grooming matters MORE in quick mode than it looks: `$archflow-init` seeds `backlog.yaml` with the
full scope as stubs, so a quick project has a large groomable backlog from day one, and grooming a
stub just before building it is the normal path. Gates are still derived and written — `quick` makes
them auto-satisfied (non-blocking), not absent.

New scope added later via `$archflow-feature` defaults straight into the implicit release with ACs
written inline. That is correct and is NOT rerouted through grooming: `groom` serves the seeded
backlog, `feature` serves new scope.

## Notes
- Schemas: `backlog-schema.yaml` (what grooming writes), `release-schema.yaml` (what promotion later
  writes). Read the backlog schema before writing if unsure of the shape.
- `groom` refines scope; `$archflow-feature` on an in-release story starts work. If the user wants
  to change what a story means, this is the command. If they want to build it, that one is.
