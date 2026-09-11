---
description: Check the environment and project state — what Archflow needs, what is missing, and how to fix it
argument-hint: "[--validate] [--fix]"
---

# /archflow:doctor — Environment and project health check

Arguments (`$ARGUMENTS`): `--validate` also validates every `.archflow/` state file against its
schema. `--fix` repairs the mechanical drift between this project and the installed plugin, and completes
the project's `stack:` from what the repo declares. Empty → environment and project checks only.

Report only, **except with `--fix`**, which is the one mode that writes. Without it, `doctor` never
installs anything, never edits state, and never changes a phase. It ends with the exact commands the
user can run themselves.

## How to read the results

- **PASS** — present and usable.
- **WARN** — absent or degraded, but Archflow still works. Say what it costs to leave it.
- **FAIL** — Archflow cannot work correctly until it is fixed.

Never upgrade a WARN to a FAIL because it would be nicer to have. codemap missing is a WARN. A v1.0
schema is a FAIL only for the commands that cannot run against it.

## Step 1 — Tooling

Run each check, then report the table. Use `command -v` so a missing tool is a clean negative rather
than an error.

```bash
command -v git       >/dev/null 2>&1 && git --version              || echo "MISSING git"
command -v node      >/dev/null 2>&1 && node --version             || echo "MISSING node"
command -v python3   >/dev/null 2>&1 && python3 --version          || echo "MISSING python3"
command -v python3   >/dev/null 2>&1 && python3 -c "import yaml; print('PyYAML', yaml.__version__)" 2>/dev/null || echo "MISSING PyYAML"
command -v codemap   >/dev/null 2>&1 && codemap --version 2>/dev/null || echo "MISSING codemap"
command -v claude    >/dev/null 2>&1 && echo "claude on PATH"      || echo "MISSING claude"
```

| Check | Severity if missing | Why it matters | Fix |
|---|---|---|---|
| `git` | **FAIL** | Branch-per-story, release tags and the ship ritual all need it | Install git |
| `node` ≥ 18 | **FAIL** | Archflow Studio and the `SessionStart` hook run on it | Install Node 18+ |
| `python3` + PyYAML | **WARN** | Only `/archflow:migrate` needs it. FAIL only if the project is v1.0 | `pip install pyyaml` |
| `codemap` | **WARN** | Token optimization. Agents navigate by structural index instead of reading whole files, roughly 60-80% fewer tokens on navigation. Without it they fall back to Glob/Grep and every story costs more | See below |
| `claude` on PATH | **WARN** | Only `/archflow:studio` needs it | Already present if Claude Code runs |

codemap install, pinned on purpose (see `SECURITY.md`) — offer it, never run it unasked:

```bash
pip install "git+https://github.com/AZidan/codemap.git@v1.3.1"
```

## Step 2 — End-to-end test tooling

Only for `project_type` of `fullstack`, `frontend_only` or `mobile`. Skip entirely for `backend_only`,
where `pm-reviewer` uses the project's own HTTP test stack.

Detect what the project already has rather than prescribing a tool. Check `package.json` scripts and
devDependencies, `Podfile`, `build.gradle`, and the presence of `e2e/`, `tests/e2e/`, `cypress/`,
`playwright/`, `maestro/`, `UITests/` or `androidTest/`.

- Something found → **PASS**, and name it. That is what `pm-reviewer` will use.
- Nothing found → **WARN**: acceptance testing will return `BLOCKED` until a runner exists. List the
  options that fit this project type with their install commands, and say plainly that Archflow will
  not install one for them.

## Step 3 — Project state

```bash
ls .archflow/ 2>/dev/null
```

| Check | Severity | Notes |
|---|---|---|
| `.archflow/` exists | **FAIL** if missing | Not an Archflow project. Suggest `/archflow:init` or `/archflow:onboard` |
| `current-phase.yaml` | **FAIL** if missing | The cursor. Everything reads `phase`, `mode` and `active_release` from it |
| `project-settings.yaml` | **FAIL** if missing on a v2.1 project | How the project works: `project_type`, `stack`, `api_contract_path`, `optional_agents`. A project with settings still inside `current-phase.yaml` is pre-2.1 — `--fix` splits it |
| `schema_version: "2.1"` in `roadmap.yaml` | **FAIL** if v1.0 | A `phases:` or `sprints:` key means v1.0. Suggest `/archflow:migrate` |
| `roadmap.yaml`, `backlog.yaml` | **WARN** if missing | Expected from Phase 1 onward |
| `releases/{active_release}.yaml` | **FAIL** if `active_release` is set but the file is absent | The release index points at nothing |
| `design-system.yaml` | **FAIL** if the project has a UI and it is missing | Every screen becomes an independent guess. Suggest `/archflow:design` |
| `design-systems/{design_system}.md` | **FAIL** if named but absent | The agents are told to read a file that is not there |
| `api_contract_path` in `project-settings.yaml` | **WARN** if unset | Phase 3 reads it. Default is `docs/api-contract.md` |
| `test-accounts.yaml` | **WARN** if absent on a project with a UI | `pm-reviewer` needs credentials. Template is `.archflow/test-accounts.example.yaml` |
| `project_type` disagrees between `project-settings.yaml` and `roadmap.yaml` | **WARN** | `project-settings.yaml` is the owner; `roadmap.yaml` mirrors it for readers that only load the index. Report both values and offer to correct the mirror |
| `stack` in `project-settings.yaml` | **WARN** if absent or empty past Phase 1 | Agents carry no technology of their own. An unset stack means each one stops and asks mid-story. `--fix` detects it from the repo and asks before writing (Step 5c); `/archflow:onboard` does the same on setup |

Also report, without judging them: current phase, mode, active release with stories done over total,
and any story with `status: parked`, since a parked story blocks the ship by default.

**Report the stack as a block**, naming every `null` field rather than hiding it. A null is not a
failure — it is a question an agent will ask later — but the user should see them together now
rather than one at a time mid-story:

```
  Stack
    language          typescript
    backend           nestjs · postgresql · prisma
    web               react · tailwind
    test              jest · — · playwright
    ci                github-actions
    hosting           (not set)
```
Show `(not set)` for null. Omit whole sections that do not apply to the project type.

**Report the optional agents too**, since a project that never answered the question silently runs
without the review steps it might expect:

```
  Optional agents
    code-reviewer         story_review, release_quality
    a11y-expert           not automatic (available on request)
    ui-animation-designer  not automatic
    doc-writer            not automatic
```
If `optional_agents` is absent entirely, say so and note that nothing optional runs automatically —
that is a valid state, and also what a project set up before the setting existed looks like.

## Step 4 — Repo hygiene

- `.archflow/test-accounts.yaml` must be gitignored. If `git check-ignore -q .archflow/test-accounts.yaml`
  fails and the file exists, that is a **FAIL** — credentials are about to be committed.
- Warn on any `.archflow/` file with a merge conflict marker.

## Step 5 — `--validate` (only when asked)

Run the validator that ships with the plugin. Do not re-implement the checks here.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_archflow.py" .
```

It validates every `.archflow/` state file against its schema and exits 0 for clean, 1 for
violations, 2 if it could not run. Add `--json` if you need to reason about the output rather than
show it.

| File | Schema |
|---|---|
| `current-phase.yaml` | `current-phase-schema.yaml` |
| `roadmap.yaml` | `roadmap-schema.yaml` |
| `backlog.yaml` | `backlog-schema.yaml` |
| `releases/*.yaml`, `releases/archive/*.yaml` | `release-schema.yaml` |
| `history.yaml` | `history-schema.yaml` |
| `autopilot/*.yaml` | `autopilot-schema.yaml` |

Report its output as-is: it already names the file, the field path and what it expected. A schema
violation is a **FAIL** — the state files are the contract every agent reads, and a field that has
drifted surfaces later as an agent doing the wrong thing somewhere unrelated.

Exit code 2 means the validator could not run, usually a missing `.archflow/schemas/` directory.
That is a FAIL too, but say which it is: a project with no schemas is not a project with bad data.

If PyYAML is missing the validator says so and exits 2. Report the install command rather than
trying to validate by hand.

## Step 5b — Upgrade drift (always checked, repaired only with `--fix`)

A project's `.archflow/` is a COPY of framework files made when it was set up. The plugin then moves
on and nothing reconciles the two, so a project onboarded months ago runs against files the agents no
longer match. Report this every run; it is the most common cause of "it used to work".

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/upgrade_archflow.py" . \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

It reports and changes nothing. Exit 1 means drift was found, which is a **WARN**, not a FAIL — the
project still works, it is just behind. It detects:

| Drift | Why it matters |
|---|---|
| A retired agent name in release or history files | A story assigned to it dispatches an agent that does not exist, and `verified_by` fails validation |
| `tech_stack:` present, `stack:` absent | Agents read `stack:`. Without it each one stops and asks on its first dispatch |
| No stack at all | Same, but nothing to convert from. `--fix` detects it from the repo's manifests and asks before writing (Step 5c) |
| Framework files the plugin ships that the project lacks | An agent told to read a missing design system stops rather than guessing |
| Framework files whose content is **behind** the plugin | The drift that was invisible until now. A stale schema validates the wrong shape, a stale phase file teaches a retired rule, and a stale `instructions.md` is injected into every session. Refreshed with the originals backed up |
| Framework files that differ on a project already **in step** with the plugin | Someone edited them after the last upgrade. Reported, never refreshed — an edit made on purpose outranks the shipped copy. Deleting the file restores it |
| `plugin_version` behind the installed plugin | The only signal a project has fallen behind |

### The one repair `--fix` does itself: splitting settings out of the cursor

The script deliberately does NOT do this one. `current-phase.yaml` is hand-editable and its shape
varies between projects — extra keys, hand-written comments, a layout someone rearranged. A script
rewriting it either round-trips the YAML and destroys every comment, or pattern-matches and
eventually gets a nesting wrong. You can read the file. Do this by hand.

**Only when the detector reports `split-project-settings`.** Otherwise skip this entirely.

1. **Read `.archflow/current-phase.yaml`.** Identify the keys that belong in
   `.archflow/project-settings.yaml`: `project_type`, `api_contract_path`, `stack`,
   `optional_agents`. Everything else stays where it is.

2. **If `.archflow/project-settings.yaml` already exists**, compare. A key present in both with the
   SAME value is fine — drop it from the cursor. A key present in both with DIFFERENT values is a
   decision, not a merge: show both, say which file each came from, and ask. Never pick one. That
   field gates agent rosters and phase filtering, and guessing silently converts the project.

3. **Copy both files to `.archflow/backup-upgrade-{timestamp}/`** before writing anything.

4. **Move the keys.** Edit both files rather than regenerating them, so comments, ordering and any
   hand-written notes survive. Carry a key's own comments with it. Add
   `schema_version: "2.1"` to the settings file if absent.

5. **Show the diff and get approval** before writing. This is the user's configuration.

6. **Verify**: run the validator on both files, and re-run the detector — it should now report
   nothing for this item.

If anything in the file is unexpected — a key you do not recognise, a shape that does not match the
schema, a merge conflict marker — stop and show it. An odd file is a reason to ask, not to improvise.

### With `--fix`

Show the dry-run plan FIRST and get explicit approval. This writes to the user's project.

```
This will change {n} thing(s) in .archflow/:
  {the plan from the dry run}

Originals are backed up to .archflow/backup-upgrade-{timestamp}/.
Apply? [Apply / Cancel]
```

On approval:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/upgrade_archflow.py" . \
  --plugin-root "${CLAUDE_PLUGIN_ROOT}" --apply
```

Then report what it did, name the backup directory, and repeat anything it flagged as needing a
human. Suggest committing `.archflow/` afterwards so the change is reviewable.

`--fix` is deliberately narrow. The script renames, converts and copies — operations where the
input's shape does not matter. Anything that requires reading and understanding a document, like the
settings split above or the stack detection in 5c, you do yourself, showing a diff first. Neither
ever writes project content, invents a value the repo does not evidence, or resolves a conflict;
those are reported for the user to decide.

## Step 5c — Stack detection (the last thing `--fix` does)

Runs **after** every repair above, and **only** with `--fix`. It goes last on purpose: the settings
split in 5b may be what creates `project-settings.yaml` in the first place, and detection writes into
that file.

**Skip entirely, silently, when any of these hold:**

- No `--fix`. Without it, an incomplete stack is reported in Step 6 and nothing else.
- No `.archflow/project-settings.yaml`. There is nowhere to write, and a project without one is an
  onboarding job — say so and point at `/archflow:onboard`.
- `stack:` is already complete for this `project_type`. Nothing to fill, so nothing to ask about.
  A `backend_only` project needs no `web.*`, and absent lanes are not gaps.

### What it does

1. **Detect**, following `${CLAUDE_PLUGIN_ROOT}/skills/archflow/stack-detection.md`. That file is the
   procedure — the evidence sources, the field mapping, and the rule that anything the evidence does
   not support is written `null`. `/archflow:onboard` runs the same one, which is why neither
   restates it.

2. **Sort every field into exactly one of three buckets.** This is the whole step; the rest is
   reporting.

   | Current value | Evidence | Action |
   |---|---|---|
   | null or missing | found | **Propose to fill.** This is the case worth having |
   | set | agrees | Nothing. Do not rewrite a file to change nothing |
   | set | disagrees | **Ask.** Never overwrite, never pick |
   | null or missing | none found | Leave null, and say so — a null is a working state, not a defect |

3. **On a disagreement, ask — one field at a time.** Show both values and where each came from:

   ```
   test.e2e disagrees with the repo.
     settings say   cypress
     repo suggests  playwright   (@playwright/test in devDependencies; no cypress dependency)

   Which is correct?  [Keep cypress / Use playwright / Neither — I'll edit it myself]
   ```

   A set value can be deliberately against the evidence: a project mid-migration with both
   frameworks installed, a monorepo whose root manifest is not the app, a runner installed but not
   the one acceptance uses. Detection cannot see intent, and the value it would overwrite is the
   only place that intent is written down. **Never resolve one of these on the user's behalf**, and
   never batch them into a single "apply all" — each is a separate decision.

4. **Show the diff and get approval**, then write. Same discipline as every other `--fix` repair:
   back up `project-settings.yaml` to `.archflow/backup-upgrade-{timestamp}/` first, edit the file
   rather than regenerating it so comments and ordering survive, and run the validator afterwards.

5. **Report what changed**, by field, with the evidence for each — not "stack updated".

### Why this is a repair and not a guess

`--fix` does not pick a stack. It reads what the repo already declares in its own manifests and
lockfiles, proposes it, and asks. The alternative is not neutrality: a null `test.e2e` means
`pm-reviewer` returns BLOCKED on every acceptance run and the user answers the same question every
time, while `@playwright/test` sits in `package.json` the whole while.

What stays out of reach is unchanged. `--fix` still never installs anything, never writes a value the
evidence does not support, and never overrules a value a human set.

## Step 5d — Git guard (checked always, installed only with `--fix`)

On Claude Code the plugin's `PreToolUse` hook stops an agent force-pushing to `main` or pushing during
an autopilot run. Other hosts get the same protection from a plain git `pre-push` hook, which also
covers the human's own terminal. Report **WARN** if `.git/hooks/pre-push` does not mention
`archflow-pre-push`; with `--fix`, ask, then run:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/archflow-install-git-guard.sh"
```

It chains any existing `pre-push` hook rather than replacing it. Skip silently when the project is
not a git repository.

## Step 6 — Report

Print the three sections, then a summary line, then only the fixes that apply:

```
Archflow doctor

  Tooling
    PASS  git 2.43.0
    PASS  node v20.11.0
    WARN  codemap — not installed (token optimization; agents will read whole files)

  Project
    PASS  schema v2.0 · phase 3 · mode quick
    PASS  active release: v0.3-onboarding (4/7 stories done)
    FAIL  design-system.yaml missing — this project has a UI

  Acceptance tooling
    PASS  playwright (package.json devDependencies)

  2 to fix, 1 optional

  Fixes
    /archflow:design
      pick a design system before any further UI work

    /archflow:doctor --fix
      3 stack fields are null that the repo answers (test.e2e, backend.orm, package_manager)

    pip install "git+https://github.com/AZidan/codemap.git@v1.3.1"
      optional — cuts navigation tokens by roughly 60-80%
```

If everything passes, say so in one line and stop. Do not pad a clean report.

## Rules

1. **Report only, unless `--fix` was asked for.** Never install. Never edit state without it, and
   even with it, show the plan and get approval before writing.
2. **A missing optional tool is a WARN, never a FAIL.** Archflow works without codemap.
3. **Name the cost, not just the gap.** "codemap missing" is less useful than what it costs.
4. **Never invent a check.** If you cannot determine something, report UNKNOWN and say why.
5. Run `/archflow:doctor` as the first step when a user reports that something "isn't working".
