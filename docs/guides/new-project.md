---
layout: guide
title: "Starting a New Project"
description: "Run /archflow:init on an empty repo and move from strategy through design, API contract, and implementation."
permalink: /guides/new-project/
---

For a blank directory, or a repo with nothing in it yet. If you already have code, use
[onboarding](https://azidan.github.io/archflow/guides/existing-codebase/) instead — it won't make you throw anything away.

---

## Run it

```bash
cd your-project
claude
```

```
/archflow:init
```

`init` is deliberately small. It:

- initializes git if you haven't (it asks first)
- creates `.archflow/` with `current-phase.yaml` at Phase 1
- copies in the phase instructions, schemas, and the branching strategy
- adds an Archflow section to your `CLAUDE.md`
- makes the initial commit

You start in **`quick` mode** — one implicit release, no ceremony. You can grow into `full` later
without migrating anything.

---

## What happens next

Archflow moves through phases. Each one produces artifacts the next one reads, and none of them
advance without you approving what came out.

### Phase 1 — Strategy

`product-strategist` works out who this is for, what problem it solves, and what success looks like
→ `.archflow/project-context.md`

`feature-planner` turns that into epic labels and a backlog of story stubs
→ `.archflow/roadmap.yaml` + `.archflow/backlog.yaml`

Stubs are intentionally thin at this stage — a title and one line. Detail comes later, when a story
is actually next up. Planning everything in full detail on day one is how roadmaps rot.

### Phase 2 — Design

`ux-designer` produces user flows, a theme, and wireframes. `dsl-generator` turns those into
component specs → `design-artifacts/styled-dsl.yaml`

Optional Phase 2.25 generates hi-fi screens if you have the SuperDesign MCP configured. Skip it
freely — Phase 2 → 2.5 is a supported path.

### Phase 2.5 — API Contract

`api-contract-architect` writes `docs/api-contract.md` from the wireframes. This becomes the single
source of truth: frontend and backend both build against it, and neither is permitted to deviate.

This is the phase people are most tempted to skip. Don't. It's the one that stops the frontend and
backend from quietly disagreeing for two weeks.

### Phase 3 — Implementation

`ui-engineer` and `api-engineer` run in parallel against the contract. Then `qa-engineer`, then
`pm-maestro-reviewer` checks the work against the story's acceptance criteria and returns a verdict.
A story isn't done until that verdict is ACCEPTED.

### Phases 4–6 — Quality, Launch, Enhancement

Code review, performance, security. Then CI/CD, versioning, app store prep, analytics. Then
on-demand work like internationalization.

---

## Day-to-day loop

```
/archflow:status           # where am I, what's next
/archflow:feature          # add a story
/archflow:groom S2-11      # detail a stub when it's next up
/archflow:feature S2-11    # pull it into the release, branch, build
```

When adding a story you choose where it goes: **backlog** (capture it, decide later) or **active
release** (build it now). In `quick` mode the release is the default, since there's only one.

---

## When to graduate to `full` mode

Stay in `quick` while it's just you and one line of work. Archflow will *offer* `full` when it
notices growth — a second release, a second contributor, or the project crossing a size threshold.
It never switches on its own, and declining is remembered so it doesn't nag.

`full` adds an explicit release pipeline (`planning → ready → in_progress → released`), enforced
readiness gates, and role lanes. Same schema, so switching is instant and nothing is rewritten.

```
/archflow:mode full
```

---

## Related

- [Onboarding an existing codebase](https://azidan.github.io/archflow/guides/existing-codebase/)
- [Taking a prototype to production](https://azidan.github.io/archflow/guides/prototype-to-product/)
