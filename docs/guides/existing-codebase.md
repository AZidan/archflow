---
layout: guide
title: "Onboarding an Existing Codebase"
description: "How /archflow:onboard reads your code, imports context from your tools, and reconstructs the artifacts you never wrote down."
permalink: /guides/existing-codebase/
---

For a project that already has code — whether it's a mature product with docs and tickets, or
something you inherited and barely understand yet.

If your code works but was never really *planned*, read
[Taking a prototype to production](https://azidan.github.io/archflow/guides/prototype-to-product/) instead. Same command, different
emphasis.

---

## Run it

```bash
cd your-project
claude
```

```
/archflow:onboard
```

Nothing is written until you approve it. Onboarding reads, analyzes, proposes — then waits.

---

## The three phases

### Phase A — Interactive collection *(you're present, ~5 questions)*

Archflow detects your stack and project type (`fullstack`, `frontend_only`, `backend_only`,
`mobile`), then asks where your existing context lives — Jira, Notion, Linear, GitHub, Confluence,
Slack, Google Drive, or nothing at all.

If a tool isn't connected yet, it runs `/archflow:setup-mcp` inline rather than making you stop and
come back.

### Phase B — Autonomous analysis *(you can walk away)*

Up to nine agents run, layered by dependency:

```
Layer 1   codebase audit · doc deep-dive · design extraction · route/API extraction
Layer 2   product-strategist · ux-designer            (need Layer 1 output)
Layer 3   api-contract-architect · dsl-generator · feature-planner
```

The audit walks a checklist filtered by your project type, recording what exists and what doesn't.
The extraction agents reverse-engineer your design tokens, component patterns, and endpoints from
the code as it actually is — not as documentation claims it is.

Progress is saved to `.onboard-progress.yaml`, so an interrupted run resumes instead of restarting.

### Phase C — Synthesis *(you're back)*

**Roadmap reconciliation.** Stories whose code the audit found already shipped are moved into a
completed release. Work in progress lands in the active release. Your roadmap opens describing
reality.

**Phase determination.** Archflow works out which phase you're genuinely in, so you don't redo
finished work.

**Gap report.** A plain list of what's missing — no API contract, no test coverage, no design
system. This is the most useful artifact onboarding produces, and the one worth reading twice.

---

## What you end up with

| File | Reverse-engineered from |
|---|---|
| `.archflow/project-context.md` | Code, README, imported docs |
| `.archflow/roadmap.yaml` | Epic labels + release pipeline |
| `.archflow/backlog.yaml` | Remaining scope, as stubs |
| `docs/api-contract.md` | Actual routes and handlers |
| `design-artifacts/theme.yaml` | Colors, spacing, typography in your code |
| `design-artifacts/styled-dsl.yaml` | Component patterns |
| `design-artifacts/user-flows.md` | Navigation and routing |

Your `CLAUDE.md` also gains an architecture section derived from the analysis.

---

## Already onboarded?

Running `/archflow:onboard` again is safe. It detects existing state and shows a status summary
instead of redoing the work — plus it validates your `roadmap.yaml` against the current schema,
backfills any missing template files, and offers to auto-fix format violations.

On a v1.0 project it will point you at `/archflow:migrate` rather than half-upgrading you.

---

## After onboarding

```
/archflow:status           # confirm the phase it picked
/archflow:feature          # add work
/archflow:groom S2-11      # detail a stub before building it
```

Read the gap report first, though. It usually reorders your priorities.

---

## Related

- [Starting a new project](https://azidan.github.io/archflow/guides/new-project/)
- [Taking a prototype to production](https://azidan.github.io/archflow/guides/prototype-to-product/)
