---
description: Run queued release stories unattended on one branch, after a blocker interview
argument-hint: "[story-id ...] | --plan | resume | report | abort"
---

# /archflow:autopilot — Unattended story runs on a pre-authorized envelope

Argument (`$ARGUMENTS`): optional. A list of story ids to run, or one of the subcommands below.
Empty → every eligible story in the active release.

Autopilot is the framework's **unattended lane**. You interview the user once, get every decision you
cannot make alone answered up front, then build story after story on a single branch without talking
— and report once at the end. It exists because the user is asleep, in another session, or otherwise
not watching, and a stalled run costs a whole night.

Autopilot does NOT relax review. It relaxes *synchronous* review: work accumulates on one branch that
the user reviews and merges themselves.

## Usage
```
/archflow:autopilot                    → interview, then run every eligible story in the active release
/archflow:autopilot S3-04 S3-05        → interview, then run just these stories, in this order
/archflow:autopilot --plan             → interview + print the queue, write the ledger, then STOP
/archflow:autopilot resume             → continue the newest unfinished run from its ledger
/archflow:autopilot report             → reprint the last run's summary
/archflow:autopilot abort              → mark the current run aborted and report what was done
```

## Prerequisites
- `.archflow/current-phase.yaml` and `.archflow/roadmap.yaml` exist.
- A release is `in_progress` (`active_release`), unless explicit story ids were given.
- Git repo, working tree **clean**. A dirty tree → HALT, do not stash: uncommitted work belongs to
  the user and autopilot must never bury it.
- `phase` is 3 or later. Autopilot builds; it does not do strategy, design, or contract work.

---

## Step 1 — Preconditions and queue

1. Read `.archflow/current-phase.yaml` (`project_type`, `mode`, `active_release`, `phase`),
   `.archflow/roadmap.yaml`, and `.archflow/releases/{active_release}.yaml`.
2. Verify the prerequisites above. Any failure → HALT with the single blocking reason. Never
   "work around" a failed precondition — an unattended run that starts from a wrong state is worse
   than one that never starts.
3. Build the **queue**:
   - Explicit ids given → exactly those, in the given order. An id not in the active release → HALT
     (autopilot never promotes from the backlog; that is a decision, and decisions happen awake).
   - No ids → every story in the active release whose `status` is `spec_ready`, `design_ready`,
     `contract_ready`, `ready`, or `in_progress`. Exclude `done`, `review`, and `parked`.
   - Order: dependency first (a story whose subtasks reference another story's output runs after it),
     then `priority` (Critical → Low), then id. State the ordering you chose in the plan.
4. If the queue is empty → report that and stop. Nothing to interview about.

---

## Step 2 — The interview (interactive, the user is present)

This is the step that makes the run safe. Everything the user would otherwise be woken up for gets
asked HERE, in a batch, and the answers are written to the ledger before a single line of code moves.

**Use `AskUserQuestion` for every question in this phase when the tool is available** — it gives the
user tappable options instead of a wall of prose, and it batches. Fall back to numbered prose
questions only if the tool is not available in the session.

Rules for the interview:
- **Batch, never drip.** Up to 4 questions per `AskUserQuestion` call; issue several calls if needed.
  Never ask one question, act, then ask another — the user is here now and may not be in five minutes.
- **Every question carries 2–4 concrete, mutually exclusive options you are willing to implement.**
  "How should errors be handled?" is a bad autopilot question. "Retry policy for the sync job?" with
  options `3 retries, exponential backoff` / `fail fast, surface the error` / `queue for manual retry`
  is a good one. ("Other" is offered automatically — do not add it yourself.)
- **Do not ask what you can read.** Check `docs/api-contract.md`, `design-artifacts/`,
  `.archflow/project-context.md`, and the codebase FIRST. A question answerable from an artifact is a
  question you should have looked up.
- **Ask only what is genuinely the user's call**: product behaviour, data-shape trade-offs, naming
  users will see, third-party choices, anything that costs money, anything irreversible.
- Use `multiSelect: true` where answers are not exclusive (e.g. which stories may skip a gate).

### 2a. Run-policy questions (asked every run)

1. **Stop condition** — `Run the whole queue` / `Cap at N stories` / `Stop at a deadline (e.g. 07:00)`.
2. **Parked stories** — `Block the release until resolved (default)` / `Non-blocking — flag as open
   questions`. This writes `parked_policy` in the ledger and drives the Phase 5 ship check.
3. **Run branch** — propose `{base-branch}-autopilot`, offer `{base-branch}-overnight`, or a custom
   name. `{base-branch}` is the current feature branch if one is active, else the release slug.
4. **Ungated stories** (only if any queued story has an unsatisfied `needs_design` /
   `needs_contract`) — `Skip the gate and build (records started_ungated)` / `Park these stories` /
   `Drop them from the queue`. Ask per gate, `multiSelect` over the affected stories.

### 2b. Story blocker questions

Read every queued story — description, acceptance criteria, subtasks — plus the artifacts it depends
on. For each, list what you cannot decide alone. Then ask those, batched, in `AskUserQuestion` calls.

If a story is too vague to run unattended even after the interview (no verifiable acceptance
criteria, scope you cannot bound), do not guess: offer `Groom it now` (run
`${CLAUDE_PLUGIN_ROOT}/commands/groom.md` inline — the user is still here) / `Drop it from this run`.

### 2c. Write the ledger, then confirm

Create `.archflow/autopilot/{run-id}.yaml` per `autopilot-schema.yaml`
(`run-id` = `{YYYY-MM-DD}-{n}`, from `date -u +%Y-%m-%d` and the next free sequence for that day).
Record: `base_branch`, `run_branch`, `release`, `mode_at_start`, `envelope`, `stop_conditions`,
`parked_policy`, every interview answer in `decisions[]`, and the ordered `queue[]` as `pending`.

Print the queue, the branch, the stop conditions, and the count of recorded decisions — then start.
On `--plan`, leave `status: preflight` and stop here; `/archflow:autopilot resume` starts it later.

**The ledger is not optional bookkeeping.** A multi-hour run will compact its context, possibly
several times. After compaction the ledger is the only thing that still knows what the user answered,
what shipped, and what was parked. Re-read it at the top of every story.

---

## Step 3 — The run (unattended, no user present)

Create the run branch once, from the base branch:
```bash
git checkout {base-branch} && git pull origin {base-branch} 2>/dev/null || true
git checkout -b {run-branch}
git push -u origin {run-branch} 2>/dev/null || true
```

Then, for each `pending` story in queue order:

1. **Re-read the ledger** (`decisions[]` especially) — treat it, not your context, as the truth.
2. Task branch per `.archflow/workflow.md`: `{feature}/{task-name}` off the run branch.
3. Implement with the agents allowed by `project_type` (`backend_only` → `api-engineer`,
   `frontend_only` → `ui-engineer`, `fullstack` → both, scoped per subtask). Every applicable
   universal rule still holds — the API contract is still sacred, agents still hand off via files.
4. `qa-engineer`, then `pm-maestro-reviewer` against the story's acceptance criteria.
5. On ACCEPTED: merge the task branch into the run branch, mark the story `done` in
   `.archflow/releases/{active_release}.yaml` (ACs `met`, subtasks `completed`), append the story
   result to the ledger, delete the task branch.
6. On REJECTED: fix and re-run `pm-maestro-reviewer`, up to `max_qa_retries` (default 2). Still
   rejected → **fail** the story (below).
7. Commit the ledger and the release file with the story's work. Move to the next story.

### Parking — the mid-run blocker rule

**Never guess a decision the user did not answer. Never stall the run waiting for one.** When a story
hits a decision that is genuinely the user's, or an external dependency you cannot satisfy
(credentials, a third-party account, a paid service, production data), or an acceptance criterion you
cannot verify:

1. Commit the work-in-progress on the story's task branch with `wip:` and push it. Never discard it,
   never leave it uncommitted.
2. Do **not** merge it into the run branch.
3. Set the story's `status: parked` in the release file with a `parked` block: the precise question,
   the context needed to answer it, and 2–4 candidate answers so the morning decision is one tap.
4. Record it in the ledger and move to the next story.

Fail (as opposed to park) is for work that is *broken*, not *undecided*: repeated QA rejection, a
build that will not go green, a test suite that regresses. Same handling — wip-commit, leave
unmerged, record `failure`, continue.

### Stop conditions

Stop the run and go to Step 4 when any of these hit:
- The queue is exhausted, or the story cap / deadline from the interview is reached.
- `max_consecutive_parks` (default 2) is hit — repeated parking means the interview missed something
  structural, and burning hours on the rest of the queue will not fix it.
- A merge into the run branch conflicts in a way you cannot resolve without a product decision.
- The working tree contains changes you did not make (someone else is working in the repo).
- Any write to `.archflow/` state fails, or the release file no longer parses.

### Silence policy

No progress narration, no "starting story 3 of 7", no intermediate summaries. The user is not
watching, and chat output is lost anyway if the session compacts. The ledger is the progress channel.
Emit exactly one message: the Step 4 report.

---

## Step 4 — The report (one message)

```
Autopilot run {run-id} — {n} done, {n} parked, {n} failed  ({duration})
Branch: {run-branch}  ({n} commits, not merged to main)

DONE
  [S3-04] Saved payment methods        — 6 commits, QA pass, accepted
  [S3-05] Card deletion                — 3 commits, QA pass, accepted

PARKED (blocking the release)
  [S3-07] Refund flow
    Q: Do partial refunds go back to the original card, or to store credit?
       a) original card   b) store credit   c) user chooses at refund time
    WIP on branch: refund-flow/partial-refunds

FAILED
  [S3-09] Webhook retries — QA rejected 3×: signature check fails on replayed events.
    WIP on branch: webhooks/retry-signature

REVIEW FIRST: [S3-04] (touches payment auth)
Ledger: .archflow/autopilot/{run-id}.yaml
Next: answer the parked questions, then /archflow:autopilot resume
```

Order DONE by review risk, riskiest first — this is the only ordering signal the user gets before
reading a night's worth of diff. Set `status: finished`, `finished_at`, and stop.

---

## Hard constraints — the authority envelope

Autopilot is the ONLY place in Archflow where per-phase approval gates are pre-authorized, so what it
may and may not do is fixed here and is not negotiable at runtime.

**MAY, without asking:**
- Create subtask / task branches; commit; push.
- Merge subtask → task → **the run branch**.
- Run `qa-engineer` and `pm-maestro-reviewer`, and fix its own failures.
- Update `.archflow/releases/{active_release}.yaml` — **only for stories in its queue**.
- Update `.archflow/current-feature.yaml`, `.archflow/current-phase.yaml → current_feature`, and its
  own ledger.

**MUST NOT, ever, in any mode:**
- Merge to `main`, push to `main`, or open a pull request.
- Force-push, rebase a shared branch, delete a branch it did not create, or `git stash` the user's work.
- Touch any story outside its queue, any other release file, or `backlog.yaml`.
- Promote a backlog stub, cut or ship a release, or change `mode`.
- Resolve a product decision the user did not answer in the interview → **park**.
- Spend money, provision infrastructure, deploy, or run a destructive/irreversible operation
  (production migrations, data deletion, sending real messages to real users) → **park**.
- Narrate progress. One report, at the end.

---

## Subcommands

**`resume`** — read the newest ledger whose `status` is `preflight` or `running`. Verify the run
branch still exists and its HEAD matches the ledger; if it diverged, report and stop rather than
building on an unknown base. Re-ask (via `AskUserQuestion`) only questions for stories that were
parked on an unanswered decision, then continue the queue. Do not re-run the whole interview.

**`report`** — reprint Step 4 from the newest ledger. Read-only.

**`abort`** — set `status: aborted`, `finished_at`, then print Step 4. Leaves every branch and
commit intact; aborting is bookkeeping, never cleanup.

---

## Parked stories and shipping

A `parked` story blocks its release by default: the Phase 5 ship ritual's "verify releasable" check
HALTs on any story with `status: parked` and `parked.blocks_release: true`. That default is set by the
interview's parked-stories question and can be waived per story by the user when they answer the
parked question — never by autopilot, and never silently at ship time.

`/archflow:release` status prints parked stories with their open questions, so a release that is
quietly stuck on a decision is visible without opening the ledger.

---

## Quick / full mode

Autopilot runs identically in both modes; `mode` changes only what gets recorded.

- `quick` — gates are auto-satisfied, so step 2a's ungated-stories question is usually skipped entirely.
- `full` — per-phase approval gates are structurally incompatible with an unattended run. Autopilot
  runs under quick-mode gate semantics for the duration and records `mode_at_start: full` in the
  ledger, so the morning report and the release file both show what ran ungated. Every gate skipped
  this way still writes `started_ungated` on the story, exactly as a manual override would.

Autopilot never switches `mode`. It borrows the semantics for one run and says so.

## Notes
- Schemas: `autopilot-schema.yaml` (the ledger), `release-schema.yaml` (`parked` status + block).
- `.archflow/autopilot/` is committed, not ignored — the ledger is the audit trail of what an
  unattended agent decided and why, and it is worth keeping in history.
- Autopilot is a build-lane command. It deliberately cannot groom, plan, promote, or ship: every one
  of those is a decision, and decisions happen while the user is awake.
