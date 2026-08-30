---
layout: guide
title: "Taking a Prototype to Production"
description: "Your prototype works and people are using it. Here's how to give it the roadmap, contracts, tests, and launch path it never had."
permalink: /guides/prototype-to-product/
---

You built something fast. It works. People are using it.

What it doesn't have is a roadmap, an API contract, a test plan, or a defensible answer to what
version 1.0 means. That's not a failure: that's what shipping quickly costs, and the tradeoff was
probably correct at the time. The problem is that the tradeoff compounds, and at some point the next
feature starts costing more than the last three combined.

This guide covers turning that into a product you can maintain, hand to someone else, and actually
launch.

---

## Start by finding out where you stand

```bash
cd your-project
claude
```

```
/archflow:onboard
```

Onboarding reads your code and **reconstructs the plan around what you already shipped**. Where it
finds working features with no story behind them, it writes the story and marks it delivered. Your
roadmap opens describing reality, not pretending you're on day one.

Two outputs matter most here:

**The gap report**: a plain list of what's missing. No tests. No API contract. No design system.
Auth handled three different ways. Read this one twice; it usually reorders your priorities.

**The phase assessment**: where you actually are. Most prototypes land in Phase 2 or 2.5: code
exists, but the design system and contract that should have preceded it don't.

Nothing is written without your approval.

---

## Then close the gaps that are costing you

You don't have to do these in order, and you don't have to do all of them. Pick by what hurts.

| Symptom | Fix | Phase |
|---|---|---|
| Can't decide what to build next | Personas, KPIs, prioritized backlog | 1 |
| Every screen looks slightly different | Design tokens and a component system | 2 |
| Frontend and backend disagree about the API | A contract both sides build against | 2.5 |
| Scared to change anything | Test coverage and acceptance criteria | 3 |
| No idea if it's secure or fast enough | Code review, security, performance | 4 |
| No repeatable way to ship | CI/CD, versioning, app store, analytics | 5 |

Phase 2.5 is usually the highest-leverage one. A prototype's API is typically whatever the frontend
needed at the time, and locking a contract stops the two halves from drifting further apart while
you fix everything else.

---

## Be honest about what this does

**It gives you** the plan, the contracts, the gates, and the launch path your prototype never had.
Phase 4 agents will review your code for quality, security, and performance, and tell you what they
find.

**It does not** silently rewrite your architecture. Archflow won't refactor your prototype behind
your back or quietly restructure your data model. It makes sure you *know* what needs attention and
gives you a structured way to work through it, but what gets refactored, and when, stays your call.

If you were hoping to point a tool at a messy codebase and get a clean one back, no framework
honestly offers that. What you can get is knowing exactly what's wrong and having a plan.

---

## Let the ceremony grow with you

Stay in `quick` mode while it's still small. One implicit release, gates that record but don't
block, no ship ritual until you ask for one.

Archflow watches for signs you've outgrown it (a second release, a second contributor, crossing a size threshold) and *offers* the upgrade:

> This project looks like it's outgrowing quick mode (second contributor joined). Switch to full
> mode? It adds explicit releases and role-based design/spec gates.

It never switches on its own, and if you decline it remembers rather than asking every session.

```
/archflow:mode full
```

`full` adds an explicit release pipeline, enforced readiness gates, and role lanes: the structure that matters once more than one person is committing.

---

## Ship a real release

Once the gaps that mattered are closed:

```
/archflow:release new "1.0"     # carve a release from the backlog
/archflow:release start          # the build gate: at most one release in progress
/archflow:release ship           # the Phase 5 ship ritual
```

`ship` verifies the release is actually releasable, tags the version, generates release notes,
archives the release file, and appends to `history.yaml`, which later tells you *"`PaymentForm.tsx`
last shipped for S3-04; its acceptance criterion was X"* before an agent modifies it.

That ledger is the thing prototypes never have and mature products can't work without.

---

## A realistic first week

| Day | Do this |
|---|---|
| 1 | `/archflow:onboard`, read the gap report, don't fix anything yet |
| 2 | Phase 1: decide what this product is actually for |
| 3 | Phase 2.5: lock the API contract |
| 4–5 | Backfill tests on whatever you're most afraid to change |
| Then | `/archflow:release new "1.0"` and work the backlog properly |

---

## Related

- [Onboarding an existing codebase](https://archflowai.dev/guides/existing-codebase/): the mechanics of `/archflow:onboard`
- [Starting a new project](https://archflowai.dev/guides/new-project/): the phases in order, from scratch
