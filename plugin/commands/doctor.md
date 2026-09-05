---
description: Check the environment and project state — what Archflow needs, what is missing, and how to fix it
argument-hint: "[--validate]"
---

# /archflow:doctor — Environment and project health check

Argument (`$ARGUMENTS`): optional `--validate` to also validate every `.archflow/` state file against
its schema. Empty → environment and project checks only.

Report only. `doctor` never installs anything, never edits state, and never changes a phase. It ends
with the exact commands the user can run themselves.

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
| `current-phase.yaml` | **FAIL** if missing | Everything reads `phase`, `mode`, `project_type`, `active_release` from it |
| `schema_version: "2.0"` in `roadmap.yaml` | **FAIL** if v1.0 | A `phases:` or `sprints:` key means v1.0. Suggest `/archflow:migrate` |
| `roadmap.yaml`, `backlog.yaml` | **WARN** if missing | Expected from Phase 1 onward |
| `releases/{active_release}.yaml` | **FAIL** if `active_release` is set but the file is absent | The release index points at nothing |
| `design-system.yaml` | **FAIL** if the project has a UI and it is missing | Every screen becomes an independent guess. Suggest `/archflow:design` |
| `design-systems/{design_system}.md` | **FAIL** if named but absent | The agents are told to read a file that is not there |
| `api_contract_path` in `current-phase.yaml` | **WARN** if unset | Phase 3 reads it. Default is `docs/api-contract.md` |
| `test-accounts.yaml` | **WARN** if absent on a project with a UI | `pm-reviewer` needs credentials. Template is `.archflow/test-accounts.example.yaml` |
| `stack` in `current-phase.yaml` | **WARN** if absent or empty past Phase 1 | Agents carry no technology of their own. An unset stack means each one stops and asks mid-story. Fix with `/archflow:onboard` detection, or write it by hand from `.archflow/stacks/*.yaml` |

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

    pip install "git+https://github.com/AZidan/codemap.git@v1.3.1"
      optional — cuts navigation tokens by roughly 60-80%
```

If everything passes, say so in one line and stop. Do not pad a clean report.

## Rules

1. **Report only.** Never install, never fix, never edit state. Print the command and let the user run it.
2. **A missing optional tool is a WARN, never a FAIL.** Archflow works without codemap.
3. **Name the cost, not just the gap.** "codemap missing" is less useful than what it costs.
4. **Never invent a check.** If you cannot determine something, report UNKNOWN and say why.
5. Run `/archflow:doctor` as the first step when a user reports that something "isn't working".
