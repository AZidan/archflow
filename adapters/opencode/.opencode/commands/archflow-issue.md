---
description: "Record a defect against a story in the active release, list what is open, or defer a minor one to the backlog"
---


# /archflow-issue — Review findings a human found

`qa-engineer`, `pm-reviewer` and the `story_review` agents write their findings into a story's
`issues[]` themselves. This command is the human's way into the same array — and the only sanctioned
way to defer one, which no agent may ever do.

## Usage
```
/archflow-issue                              → every open issue in the active release, by story
/archflow-issue S7-20                        → that story's issues, open ones first
/archflow-issue S7-20 "cards render empty on a 204"
                                             → record a defect against that story
/archflow-issue defer S7-20 I-2              → move a minor finding to the backlog and close it
```

## What an issue is, and is not

An issue is **a defect in a story that is currently being built or reviewed.** It is born inside that
story's build loop and dies before the story is `done` — fixed, or deferred into the backlog. It has
no assignee, no comments, no age, and three states.

It is **not** the place for anything else that is wrong with the project. New scope, a bug in shipped
code, a refactor you want, an idea — all of those are `/archflow-feature`, which puts them in the
backlog where they can be prioritized. A release file that accumulates findings stops being readable,
which is the failure mode this command is most likely to cause if it routes carelessly.

**Routing is this command's first job, not an afterthought.** See Step 2.

---

## Step 0 — Which mode

Match `$ARGUMENTS` against the story-id pattern from `release-schema.yaml`:

```
^S[0-9]+-[0-9]+[a-z]?$
```

| Argument | Mode |
|---|---|
| Empty | **List all** — Step 1 |
| A story id alone | **List one story** — Step 1 |
| A story id followed by quoted text | **Add** — Step 2 |
| `defer <story-id> <issue-id>` | **Defer** — Step 3 |
| Anything else | Say the argument is not a story id, show the usage block, and stop. Do not guess |

**State the mode in your first line of output.**

## Step 0b — Load the release

Read `active_release` from `.archflow/current-phase.yaml`, then
`.archflow/releases/{active_release}.yaml`.

- **`active_release` is null** → no release is being built, so no story can be carrying a defect.
  Say so, and point at `/archflow-feature` for the backlog. Stop.
- **The story id is not in the active release** → it is in the backlog or another release, and a
  release-scoped agent cannot see it. Say where it is if you can find it, and stop. Do not pull it
  in; that is `/archflow-feature`'s decision, and it needs the user.

---

## Step 1 — List

Read `issues[]` from every story (or the one named). Order open before fixed before deferred, and
`blocking` before `minor` within each.

```
Issues — {active_release}

S7-20  Saved payment methods                                    (review)
  I-1  open      blocking  cards render empty on a 204
                           frontend/src/checkout/SavedCards.tsx:42
                           found by qa-engineer · docs/qa-reports/S7-20-qa.md
  I-2  deferred  minor     brand icon 1px off baseline  → S7-31

S7-21  Card deletion                                       (in_progress)
  no issues
```

End with the count that decides whether the release can move: `2 open blocking across 1 story`, or
`No open blocking issues.` Say nothing else — this is a status read.

---

## Step 2 — Add

### 2a. Route it first

Before writing anything, establish that this is a defect in a story in the build loop. Read the
story's `status`:

| Story status | What to do |
|---|---|
| `in_progress`, `review`, `parked` | Record the issue. Continue to 2b |
| `ready`, `spec_ready`, `design_ready`, `contract_ready` | The story has not been built yet, so there is nothing to be defective. This is scope: it belongs in the story's `subtasks` or `acceptance_criteria`. Offer `/archflow-groom {story-id}` and stop |
| `done` | **Ask. Never choose silently** — see 2c |

If the user's text describes something that is not a defect in this story at all — a feature, a
refactor, a bug somewhere else in the codebase — say so plainly, and point at `/archflow-feature`.
Getting this wrong in the permissive direction is what turns a release file into a bug tracker.

### 2b. Write it

Append to that story's `issues[]` in the active release file:

```yaml
- id: I-{highest existing + 1}      # story-scoped; never reuse a number
  summary: "{the user's text, as one line}"
  found_by: human
  severity: blocking                # ask if it is not obvious — see below
  location: "{file:line, endpoint or screen}"   # omit if the user does not know
  status: open
  at: "{iso8601}"
```

**Severity is a real question, not a default.** `blocking` stops the story reaching `done`; `minor`
does not. If the user's wording does not settle it, ask — one question, two options:

- **blocking** — the story is not acceptable while this is true
- **minor** — worth recording, but this story can ship with it

Do not write a `report` path. That field points at a reviewing agent's report, and there is no report
behind a human's finding; the summary and location are the whole record.

Confirm in one line: `S7-20 I-3 recorded (blocking). The story cannot be marked done until it is
fixed or deferred.` Then commit the release file alone.

### 2c. When the story is already `done`

A `done` story with a new open blocking issue would fail `validate_archflow.py` the moment it was
written, so this needs a decision the command must not make alone. Ask which of these it is:

- **A regression found before the release ships** → reopen the story: set its `status: review`,
  record the issue, and say plainly that the story left `done` and needs to go back through
  acceptance. Only offer this while the release is still `in_progress`.
- **New scope, or a defect in code that already shipped** → a backlog stub via `/archflow-feature`.
  The story is closed; this is next release's work.

Never silently reopen a story, and never write an issue that leaves the release file invalid.

---

## Step 3 — Defer

Deferring is the one action in the issue lifecycle reserved for a human. An agent that could
downgrade its own finding would have stopped being a check, which is why no agent has this verb.

1. **Refuse on `blocking`.** Say: `I-2 is blocking — it is fixed, or the story does not ship. Change
   its severity first if it was mis-triaged.` Stop. Do not offer to downgrade it in the same breath;
   re-triage is a separate, deliberate decision.
2. **Refuse if it is not `open`.** A `fixed` issue has nothing to defer; a `deferred` one is done.
3. Write the backlog stub FIRST, in `.archflow/backlog.yaml`, per `backlog-schema.yaml` — carrying
   the summary, the location, and which story and release it came from. A stub that does not say
   where a finding came from is a finding nobody can act on.
4. Then set the issue `status: deferred` and `deferred_to: {new stub id}`.

Order matters: the stub before the pointer. If the write fails halfway, an issue still marked `open`
is recoverable, and a `deferred_to` pointing at nothing is not — `validate_archflow.py` fails the
release file for exactly that.

The issue stays in the release file as a tombstone. That is deliberate: it tells the next reader the
finding was seen and dispositioned rather than missed.

Confirm both halves: `S7-20 I-2 deferred → S7-31 in the backlog.`

---

## What this command never does

- **It never marks an issue `fixed`.** That is set by whoever lands the fix, in the same edit as the
  fix. A human who has fixed it themselves commits the fix and the status together.
- **It never marks a story `done`.** That is Phase 3's approval gate, and it needs the user.
- **It never touches a story outside the active release.**
- **It never edits or renumbers an issue someone else wrote.**

## Related

- `.archflow/schemas/release-schema.yaml` — the `issue` definition and both invariants
- `.archflow/phases/phase-3-implementation.md` — *Issues — review findings as state*
- `/archflow-feature` — where everything that is not a story-scoped defect goes
- `/archflow-doctor --validate` — checks that no `done` story carries an open blocking issue
