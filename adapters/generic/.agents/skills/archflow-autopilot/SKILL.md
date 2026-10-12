---
name: archflow-autopilot
description: "Use ONLY when the user asks for $archflow-autopilot or \"archflow autopilot\". Run queued release stories unattended on one branch, after a blocker interview"
---

> Arguments are the text after the skill name.


# $archflow-autopilot — Unattended story runs on a pre-authorized envelope

Argument (`the text the user wrote after the skill name`): optional. A list of story ids to run, or one of the subcommands below.
Empty → every eligible story in the active release.

Autopilot is the framework's **unattended lane**. You interview the user once, get every decision you
cannot make alone answered up front, then build story after story on a single branch without talking
— and report once at the end. It exists because the user is asleep, in another session, or otherwise
not watching, and a stalled run costs a whole night.

Autopilot does NOT relax review. It relaxes *synchronous* review: work accumulates on one branch that
the user reviews and merges themselves.

## Usage
```
$archflow-autopilot                    → interview, then run every eligible story in the active release
$archflow-autopilot S3-04 S3-05        → interview, then run just these stories, in this order
$archflow-autopilot --plan             → interview + print the queue, write the ledger, then STOP
$archflow-autopilot resume             → continue an unfinished run, or ask every parked story's question, even after a run finished or was aborted
$archflow-autopilot report             → reprint the last run's summary
$archflow-autopilot abort              → mark the current run aborted and report what was done
```

## Prerequisites
- `.archflow/current-phase.yaml` and `.archflow/roadmap.yaml` exist.
- A release is `in_progress` (`active_release`), unless explicit story ids were given.
- Git repo, working tree **clean**. A dirty tree → HALT, do not stash: uncommitted work belongs to
  the user and autopilot must never bury it.
- `phase` is 3 or later. Autopilot builds; it does not do strategy, design, or contract work.

---

## Step 1 — Preconditions and queue

1. Read `.archflow/current-phase.yaml` (`mode`, `active_release`, `phase`) and `.archflow/project-settings.yaml` (`project_type`),
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

**Use `a direct question to the user (wait for the reply before continuing)` for every question in this phase when the tool is available** — it gives the
user tappable options instead of a wall of prose, and it batches. Fall back to numbered prose
questions only if the tool is not available in the session.

Rules for the interview:
- **Batch, never drip.** Up to 4 questions per `a direct question to the user (wait for the reply before continuing)` call; issue several calls if needed.
  Never ask one question, act, then ask another — the user is here now and may not be in five minutes.
- **Every question carries 2–4 concrete, mutually exclusive options you are willing to implement.**
  "How should errors be handled?" is a bad autopilot question. "Retry policy for the sync job?" with
  options `3 retries, exponential backoff` / `fail fast, surface the error` / `queue for manual retry`
  is a good one. ("Other" is offered automatically — do not add it yourself.)
- **Do not ask what you can read.** Check the contract at `api_contract_path`, `design-artifacts/`,
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
on. For each, list what you cannot decide alone. Then ask those, batched, in `a direct question to the user (wait for the reply before continuing)` calls.

If a story is too vague to run unattended even after the interview (no verifiable acceptance
criteria, scope you cannot bound), do not guess: offer `Groom it now` (run
`.agents/skills/archflow-groom/SKILL.md` inline — the user is still here) / `Drop it from this run`.

### 2c. Write the ledger, then confirm

Check out `base_branch` (*Where autopilot commits*, below). A run that starts now (no `--plan`)
then cuts its run branch from it with the commands at the top of Step 3, so its ledger is written
straight onto the run branch. Then create `.archflow/autopilot/{run-id}.yaml` per
`autopilot-schema.yaml`
(`run-id` = `{YYYY-MM-DD}-{n}`, from `date -u +%Y-%m-%d` and the next free sequence for that day).
Record: `base_branch`, `run_branch`, `release`, `mode_at_start`, `envelope`, `stop_conditions`,
`parked_policy`, every interview answer in `decisions[]`, the ordered `queue[]` as `pending`, and
`status: preflight`. Commit the ledger alone on the run branch (`chore(autopilot): plan {run-id}`).

Print the queue, the branch, the stop conditions, and the count of recorded decisions — then start
(Step 3).

On `--plan` there is no run branch yet. Commit the ledger alone on `base_branch` instead (same
message), print the same summary, and stop, with the ledger still `preflight` on `base_branch`;
`$archflow-autopilot resume` starts it later (*Where autopilot commits*).

### Where autopilot commits

Every ledger and release-file write is committed as it is made, on one branch, so the state
travels with the run: `resume` needs a clean tree, and its branch scan reads committed state only.

- **The run branch**, once it exists. A write made on a story's task branch (the status walk,
  reviewers' `issues[]`, a `parked` block) is committed there with the work, and reaches the run
  branch when the story leaves that branch: by the merge on ACCEPTED, or, for a parked or failed
  story, by checking out the run branch and committing the task branch's copy of the release file
  (`git checkout {task-branch} -- .archflow/releases/{active_release}.yaml`). Stories run one at a
  time, so that copy differs from the run branch's only in this story. Once the run branch
  exists, the ledger is only ever written there.
- **`base_branch`** for a `--plan` ledger only: it waits there, `preflight`, until `resume` starts
  it. **Starting a planned run:** `resume` sets the ledger `running` and commits it alone on
  `base_branch` (`chore(autopilot): start {run-id}`), and only then does Step 3 cut the run branch
  from `base_branch`, so the ledger goes with it, already `running`, and the copy left behind never
  reads `preflight` for a run that has started. That is the last ledger write on `base_branch`,
  except `abort` on a run whose run branch is gone. A run that starts now has its
  run branch cut in Step 2c before its ledger is written, so no copy of a started run's ledger is
  ever left on `base_branch`. Only Step 2c may create `base_branch`, and only when it
  exists neither as a local branch nor as `origin/{base_branch}` (fetch-free:
  `git show-ref --verify --quiet refs/heads/{base_branch}`, then the same for
  `refs/remotes/origin/{base_branch}`); then it is cut from the current HEAD. If only
  `origin/{base_branch}` exists, create the local branch tracking it
  (`git checkout --track origin/{base_branch}`), never a new one cut from HEAD.
- **Never `main`.** If `base_branch` would be `main`, HALT before writing anything. A command that
  writes to an earlier run's ledger (`resume`'s rule 1, `abort`) checks out that run's
  `run_branch`, else its `base_branch`, before writing; if neither exists, it commits nothing and
  tells the user. `resume`'s rule 2 writes on the current branch or a run branch cut from it, and
  commits nothing on `main`.

**The ledger is not optional bookkeeping.** A multi-hour run will compact its context, possibly
several times. After compaction the ledger is the only thing that still knows what the user answered,
what shipped, and what was parked. Re-read it at the top of every story.

---

## Step 3 — The run (unattended, no user present)

The run branch is cut once, from the base branch: by Step 2c for a run that starts now, or here
for a `--plan` run that `resume` starts (its ledger comes along from `base_branch`). Run these
commands only when the run branch does not exist yet:
```bash
git checkout {base-branch} && git pull origin {base-branch} 2>/dev/null || true
git checkout -b {run-branch}
git push -u origin {run-branch} 2>/dev/null || true
```
Set the ledger `status: running` and commit it on the run branch, unless it already reads
`running`: a planned run is started that way (*Where autopilot commits*), and a follow-on run is
written `running` (rule 2).

Then, for each `pending` story in queue order:

1. **Re-read the ledger** (`decisions[]` especially) — treat it, not your context, as the truth.
2. Task branch per `.archflow/workflow.md`: `{feature}/{task-name}` off the run branch. Set the
   story `status: in_progress` in the release file and commit it **before** any code exists.
3. Implement with the agents allowed by `project_type` (`backend_only` → `api-engineer`,

> **DESIGN SYSTEM IN THE PROMPT, NOT THE CONTEXT.** Every dispatch of a UI agent
> (`ui-engineer`, `ux-designer`, `dsl-generator`, `ui-animation-designer`) must carry this line
> verbatim in its prompt: *Design system: read `.archflow/design-system.yaml`, then read and follow
> `.archflow/design-systems/{design_system}.md` before producing any output.* A subagent does not
> inherit this session's context.

   `frontend_only` → `ui-engineer`, `fullstack` → both, scoped per subtask). Every applicable
   universal rule still holds — the API contract is still sacred, agents still hand off via files.
4. Set the story `status: review`, then run `qa-engineer`, then any agent whose `optional_agents`
   list contains `story_review` — **one at a time**, since they all write to the release file — then
   `pm-reviewer` against the story's acceptance criteria. The optional agents are part of the story
   loop, not an extra the user has to remember — an unattended run that skips the review the project
   asked for is not running the project's process.
5. On ACCEPTED: merge the task branch into the run branch, mark the story `done` in
   `.archflow/releases/{active_release}.yaml` (ACs `met`, subtasks `completed`, every issue `fixed`),
   append the story result to the ledger, delete the task branch.
6. On REJECTED: fix and re-run `pm-reviewer`, up to `max_qa_retries` (default 2). The story stays at
   `review` while it is being fixed — do not flap it back to `in_progress`. Still rejected →
   **fail** the story (below).
7. Commit the ledger on the run branch (*Where autopilot commits*). Move to the next story.

### Walk the status, never jump it

A story's `status` is the only live record of where an unattended run got to. A run that writes
`done` without ever having written `in_progress` and `review` leaves a release file that cannot be
read the morning after, and a run that dies mid-story leaves a story that still looks untouched.

```
ready → in_progress → review → done          (the normal path)
        in_progress → parked                 (an undecided question)
        review      → review → … → failed    (broken; retries exhausted)
```

Every one of those writes is committed as it happens, not batched at the end of the story. This is
the same ladder Phase 3 walks (*Story status transitions*); autopilot does not get a shorter one
because nobody is watching. `done` is the only transition that also requires a merge.

### Issues

`qa-engineer`, the `story_review` agents and `pm-reviewer` write their findings into the story's
`issues[]` (see `release-schema.yaml`). The run does not copy them into the ledger — a story lives in
exactly one place and so do its issues. What the run does with them:

- A story cannot be marked `done` while it holds an open `blocking` issue. `validate_archflow.py`
  fails the release file if one does, which is the check that catches a mis-marked story before the
  morning.
- A **failed** story keeps its open issues exactly as the reviewers wrote them. That is the whole
  reason the morning report can say *what* failed rather than only *that* it failed.
- Autopilot never defers an issue. Deferring a `minor` finding to the backlog is the user's decision
  and belongs to a session where the user is present.

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
   Commit it on the task branch, then carry the release file onto the run branch (*Where
   autopilot commits*), the branch the user merges.
4. Record it in the ledger and move to the next story.

Fail (as opposed to park) is for work that is *broken*, not *undecided*: repeated QA rejection, a
build that will not go green, a test suite that regresses. Same handling — wip-commit, leave
unmerged, carry the release file onto the run branch, record `failure`, continue.

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
    Open issues:
      I-2 blocking  signature check fails on replayed events
                    src/webhooks/verify.ts:88  ·  docs/qa-reports/S3-09-qa.md
      I-3 blocking  retry backoff never caps
                    src/webhooks/retry.ts:31   ·  docs/qa-reports/S3-09-qa.md
    WIP on branch: webhooks/retry-signature

REVIEW FIRST: [S3-04] (touches payment auth)
Ledger: .archflow/autopilot/{run-id}.yaml
Next: $archflow-autopilot resume — asks the parked questions, then builds the stories you answer
```

The `Next:` line must name a command that works on this run after it is `finished`, and after it
is `aborted`, since `abort` prints this same report. Choose it from the run branch's release file
at the end of the run, not from what this run parked: a follow-on that builds only the answered
stories parks nothing new, yet a story left unanswered is still parked there. If any story is still
`status: parked` in `.archflow/releases/{active_release}.yaml` on `{run-branch}` (counted as
`resume` counts *Parked stories*, minus any it says were picked up), it is the line above: `resume`
picks up the still-parked stories of a finished or aborted run (see *Subcommands*).
With nothing parked, write `Next: review {run-branch} and merge it yourself` instead — there is
nothing for `resume` to pick up, and it would say so.

List every open `blocking` issue under each FAILED story, read from the release file — with its
file, line and report path. "QA rejected 3×" is a status; the issue list is something the user can
start from. Read them from `issues[]`, never from what this session remembers.

Order DONE by review risk, riskiest first — this is the only ordering signal the user gets before
reading a night's worth of diff.

Then close the run: set `status: finished` and `finished_at` in the ledger, commit the ledger alone
on the run branch (`chore(autopilot): finish {run-id}`), push it, and stop. Two callers print this
report without closing a run, and both skip that write:
- **`abort`** has already set and committed `status: aborted` and `finished_at`. Leave both as they
  are: the run stays `aborted`, never `finished`.
- **`report`** is read-only. It writes nothing to the ledger or anywhere else.

---

## Hard constraints — the authority envelope

Autopilot is the ONLY place in Archflow where per-phase approval gates are pre-authorized, so what it
may and may not do is fixed here and is not negotiable at runtime.

**MAY, without asking:**
- Create subtask / task branches; commit; push.
- Merge subtask → task → **the run branch**.
- Run `qa-engineer` and `pm-reviewer`, and fix its own failures.
- Update `.archflow/releases/{active_release}.yaml` for stories in its queue, and record on a
  parked story the `blocks_release` waiver the user gives in person when `resume` asks its
  question (rule 2). No other story is ever touched.
- Update `.archflow/current-feature.yaml`, `.archflow/current-phase.yaml → current_feature`, and its
  own ledger.

**MUST NOT, ever, in any mode:**
- Merge to `main`, push to `main`, or open a pull request.
- Force-push, rebase a shared branch, delete a branch it did not create, or `git stash` the user's work.
- Touch any other story (beyond recording that waiver), any other release file, or `backlog.yaml`.
- Promote a backlog stub, cut or ship a release, or change `mode`.
- Resolve a product decision the user did not answer in the interview → **park**.
- Spend money, provision infrastructure, deploy, or run a destructive/irreversible operation
  (production migrations, data deletion, sending real messages to real users) → **park**.
- Narrate progress. One report, at the end.

---

## Subcommands

**`resume`** — the one command that brings parked work back, whether the run that parked it is
still open, has finished, or was aborted. Verify the Prerequisites first (as Step 1.2), and HALT
on any failure before checking out a branch or writing any state.

**Ledgers** (`.archflow/autopilot/`) find a `preflight` or `running` run for rule 1, carry policy
into a follow-on run, and name other run branches; they never select parked stories. They are
read from the current checkout first and then, always, from the committed `.archflow/` of every
local branch, without checking anything out: `git for-each-ref --format='%(refname:short)'
refs/heads`, then `git ls-tree --name-only {branch} {dir}` and `git show {branch}:{path}` (a run's
ledger lives on its run branch, which may be unmerged). Keep one copy per `run_id`: the most
advanced `status` (`preflight` < `running` < `finished` or `aborted`); on a tie, the copy on its
own `run_branch`, else the current checkout's. That is the run's **source branch**; say
`Found {run-id} on {branch}.` when a run chosen came from another branch. *Newest* means by
`run_id` (date, then sequence). A **follow-on** is a kept ledger with `resumes`.

**Parked stories** are the stories still `status: parked` in
`.archflow/releases/{active_release}.yaml` in the current checkout, and nowhere else. `resume`
never reads another branch's copy of that file, and never reads or edits another release file.
Drop any that a **live** follow-on whose `run_branch` is not the current branch has in its
`queue[]`, and say `{story} was picked up by {run-id} on {run_branch}.` A follow-on is live when
its `run_branch` still exists locally (`git show-ref --verify --quiet refs/heads/{run_branch}`)
and its kept ledger is not `aborted`. One whose run branch is gone, or that was aborted, never
delivered the story, so the story is asked as normal.

The **current run** is the newest `running` ledger, else the newest `preflight` one (`abort`
closes the same run); name any other unfinished ledger in one line. Choose by it, so that
`resume` never starts unattended work the user did not pick:

- A `running` ledger → rule 1. If stories are also parked, say so in one line before
  continuing: they wait for the next `resume`.
- A `preflight` ledger and parked stories both → ask which to resume (`a direct question to the user (wait for the reply before continuing)`; numbered
  prose if the tool is not available): `start the planned run {run-id}` or `answer the parked
  questions`. Never default either way. The choice not taken stays as it is.
- Only one of the two → that rule. Neither → rule 3.

1. **Continue an unfinished run.**
   - A **`preflight`** ledger is a planned run (`--plan`) that never started, so it has no run
     branch yet. **Refuse to start it if its `run_branch` already exists**, locally or on `origin`
     (a run cut it, perhaps one that died before Step 3). Check fetch-free,
     `git show-ref --verify --quiet refs/heads/{run_branch}` and
     `git show-ref --verify --quiet refs/remotes/origin/{run_branch}`, then, if an `origin` remote
     is configured, `git ls-remote --exit-code --heads origin {run_branch}` (an unreachable remote
     leaves the two ref checks standing). On any hit, write nothing, say `{run_branch} already
     exists as {ref}, so {run-id} cannot start from its plan. Close that run with
     $archflow-autopilot abort before starting again.`, and stop. Otherwise check out `base_branch`
     first, where Step 2c committed the ledger, start it there (*Starting a planned run*, in
     *Where autopilot commits*), and go to Step 3.
   - A **`running`** ledger: verify the run branch still exists locally and its HEAD matches the
     ledger; if it has diverged, report and stop. If it is not a local branch, write nothing and
     run the `preflight` guard's three checks. On a hit, say `{run_branch} exists as {ref} but not
     locally. Check it out and run $archflow-autopilot resume again.` and stop. With no hit the run
     branch is gone, so never continue or restart the run: say `{run-id}'s run branch {run_branch}
     no longer exists, not continuing it; $archflow-autopilot abort closes it, then run
     $archflow-autopilot resume again.`, write nothing, and **stop**, without choosing another
     ledger or parked story in the same invocation. Otherwise check it out, re-ask (via `a direct question to the user (wait for the reply before continuing)`) only questions for stories
     parked on an unanswered decision, then continue the queue.
   Do not re-run the whole interview in either case.
2. **Pick up the parked stories of a finished or aborted run.** Each ledger is a record: never
   reopen it, never change its `status`, never edit it. An aborted run stays `aborted` and its
   queue is not continued; only its still-parked stories come back.
   - **Not on a WIP branch.** If the current branch is a queue item's `branch` in a kept ledger,
     or a parked story's `parked.branch`, write nothing, say `This is {story}'s WIP branch; check
     out {run_branch} and run $archflow-autopilot resume there.` (the newest kept ledger that
     queued that story names `{run_branch}`), and stop.
   - **Ask** every parked story's `parked.question` and `parked.options`, batched in
     `a direct question to the user (wait for the reply before continuing)`, offering for each one left unanswered to waive `parked.blocks_release` so
     the release can ship without it. A story the user leaves unanswered stays `parked`.
   - **Nothing answered and nothing waived** → stop: check out nothing, write no ledger, change
     nothing.
   - **Nothing answered, some waived** → write no ledger. On the current branch, set each waived
     story's `parked.blocks_release: false` (the story stays `parked`) and commit only the release
     file. Never `main`: on `main`, commit nothing and tell the user to check out a non-`main`
     branch that holds the park and run `resume` again. Then stop.
   - **Some answered** → one **follow-on run** over all of them. Its **source run** is the newest
     kept ledger whose `run_branch` is the current branch, else the newest kept `finished` or
     `aborted` ledger whose `release` is the `active_release` and whose `queue[]` parked any
     answered story, else none. Do not re-run the interview: the envelope, stop conditions,
     `parked_policy`, `base_branch` and `decisions[]` carry over from the source run's ledger,
     plus one decision per new answer. With no source run, ask Step 2a's questions except the run
     branch one, and `base_branch` is Step 2a's `{base-branch}`. The run branch is the current
     branch if it is the `run_branch` of a kept ledger, else a new `{base_branch}-autopilot-{run-id}`
     (the follow-on's own `run-id`) cut from the current branch, which holds the parked state just
     read (cutting from `main` is fine; committing on it never is). Choose it before writing
     anything, then check out the run branch (cut it now if new), and on it, in one commit before
     any story work:
     - Write a new ledger per Step 2c, but `status: running` from the start, with `resumes:
       {source run-id}` (omitted without a source run) and a queue of the answered stories in
       release-file order, each `pending` with its WIP `branch`.
     - In `.archflow/releases/{active_release}.yaml`, clear each answered story's `parked` block
       and set it back to `in_progress` (that is how a story leaves `parked`), and set
       `parked.blocks_release: false` on each waived one.
     An interrupted follow-on is then a `running` run for rule 1. Each story continues on its WIP
     task branch (its `queue[].branch` in a kept ledger that parked it, else `parked.branch`) if
     that exists locally, after merging the run branch into it (taking the run branch's release
     file on a conflict there, and its copy of any ledger); else on a new one per Step 3. Then
     Step 3 from its story loop, and Step 4.
3. **Nothing to resume** — no unfinished run and no parked story in the current checkout: print
   `Nothing to resume.` with the reason and stop, writing nothing. A run with no parked stories is
   over and is not restarted, and an aborted run's queue is never continued; a new run is
   `$archflow-autopilot`.

**Other run branches.** Rules 2 and 3 end by naming the branches that may hold parked work this
checkout does not show. Take each kept `finished` or `aborted` ledger whose `release` is the
`active_release` and whose `queue[]` has a `parked` item that no newer live follow-on (as for
*Parked stories*) has in its `queue[]`. If its `run_branch` exists locally and is not the current branch, print one line per
branch, naming the newest such run on it: `Parked work from {run-id} may be on {run_branch}: check
it out and run $archflow-autopilot resume there.` This is information only: nothing is read from
those branches' release files or decided from them. With no parked story here and at least one
such line, end with those lines instead of `Nothing to resume.`

**`report`** — reprint Step 4 from the newest ledger. Read-only: skip Step 4's closing status
write.

**`abort`** — closes the current run, as `resume` picks it after its branch scan and
one-copy-per-run choice (none → `Nothing to abort.`, and stop). A dirty tree → HALT, as for
`resume`. Check out the branch that ledger lives on: its `run_branch` if that exists locally, else
its `base_branch` (a `--plan` run that never started, or a started run whose run branch is gone),
never `main`; if neither exists, commit nothing and tell the user. Set `status: aborted` and
`finished_at`, and commit the ledger alone on the branch it lives on:
`chore(autopilot): abort {run-id}`. Then print Step 4, skipping its closing status write so the
ledger stays `aborted`. Leaves every branch and commit intact; aborting is bookkeeping, never
cleanup. The aborted run's queue is never continued, but its parked stories stay parked, and
`resume` picks them up in a follow-on run (rule 2), so the report's `Next:` line is the same as for
a finished run.

---

## Parked stories and shipping

A `parked` story blocks its release by default: the Phase 5 ship ritual's "verify releasable" check
HALTs on any story with `status: parked` and `parked.blocks_release: true`. That default is set by the
interview's parked-stories question and can be waived per story by the user when `resume` asks the
parked question, whether or not they answer it (rule 2) — never by autopilot, and never silently at
ship time.

`$archflow-release` status prints parked stories with their open questions, so a release that is
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
- Schemas: `autopilot-schema.yaml` (the ledger), `release-schema.yaml` (story `status` ladder,
  `parked` block, `issues[]`).
- `.archflow/autopilot/` is committed, not ignored — the ledger is the audit trail of what an
  unattended agent decided and why, and it is worth keeping in history.
- Autopilot is a build-lane command. It deliberately cannot groom, plan, promote, or ship: every one
  of those is a decision, and decisions happen while the user is awake.
