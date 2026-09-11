# Stack detection

**The single definition of how Archflow reads a project's stack out of the repo.** Read by
`/archflow-onboard` (Step A1, on a project being set up) and `/archflow-doctor --fix` (Step 5c, on a
project whose `stack:` is incomplete). Neither restates it — two copies of a procedure become two
different procedures, and this one decides what every agent believes about the project.

The output is the `stack:` block in `.archflow/project-settings.yaml`, whose shape is defined by
`project-settings-schema.yaml`. Detection fills that block; it does not invent fields.

## Why this exists

Agents carry no technology. They read `stack:` and work in whatever it names, and **a null field is
a question they ask, never a default they assume.** That makes detection worth doing well and worth
doing honestly: a null costs one question, and a wrong value costs a feature built on the wrong
framework before anyone notices.

## Step 1 — Read the evidence

Manifests first. They are declarative and a machine wrote them, so they lie less than layout does.

| Source | Read for |
|---|---|
| **Manifests** — `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle`, `Cargo.toml`, `composer.json`, `Podfile`, `*.csproj` | language, frameworks, every dependency |
| **Lockfiles** — `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `uv.lock`, `poetry.lock`, `Gemfile.lock` | package manager, and the versions actually installed |
| **Layout** — `src/`, `backend/`, `frontend/`, `ios/`, `android/`, `e2e/`, `tests/` | project type, and which lanes exist |
| **Config** — any framework's own config file, `Dockerfile`, `.github/workflows/`, `.gitlab-ci.yml`, deploy config | CI, hosting, styling, test runners |

## Step 2 — Map evidence to fields

Fill only what the evidence supports:

- `language`, `package_manager` — from the manifest and lockfile
- `backend.framework` / `backend.database` / `backend.orm` / `backend.auth` — from dependencies and
  data-layer files
- `web.framework` / `web.language` / `web.styling` / `web.state` — from dependencies and config
- `mobile.framework` / `mobile.ios` / `mobile.android` — from `Podfile`, `build.gradle`, or a
  cross-platform framework in the manifest
- `test.unit` / `test.integration` / `test.e2e` — from dev dependencies, test scripts, and the test
  directories that actually exist
- `ci`, `hosting` — from CI config and deploy config

`.archflow/stacks/*.yaml` holds worked profiles for common combinations. Use one to recognise a
shape, never to fill in fields the repo does not actually have.

## Step 3 — The null rule

**Write `null` for anything the evidence does not support.**

Do not infer a database from an ORM. Do not infer an e2e runner from the presence of a `tests/`
folder. Do not infer `hosting` from a Dockerfile. A null makes the agent ask with the repo in front
of it; a wrong value makes it silently build the wrong thing, and nothing surfaces that until a
story is already built.

Detection confidence is not a reason to guess — it is exactly what the confirmation step is for.

## Step 4 — Confirm before writing

Detection proposes. The user disposes. Present what was found and what it came from, so a wrong read
is visible without opening the repo:

```
Detected stack
  language          typescript        package.json
  package_manager   pnpm              pnpm-lock.yaml
  backend           nestjs            @nestjs/core
    database        postgresql        docker-compose.yml + pg driver
    orm             prisma            prisma/schema.prisma
  web               react             react + react-dom
    styling         tailwind          tailwind.config.ts
  test.unit         jest              jest.config.ts
  test.e2e          null              no runner found — agents will ask
```

Name the evidence for every non-null field. "react" is a claim; "react — react + react-dom in
package.json" is a claim someone can check.

## The conflict rule

A field that is already set and disagrees with the evidence is **a decision, not a merge.** Show
both values, say where each came from, and ask which is correct. Never overwrite silently and never
pick one on the user's behalf.

A stack field can be deliberately set against what the manifests suggest — a project mid-migration
with both frameworks installed, a monorepo whose root manifest is not the app, a runner that is
installed but not the one acceptance uses. Detection cannot see intent, and the value it would
overwrite is the only place that intent is written down.
