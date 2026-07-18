# Proposal: Add project-skill scaffolding to `/archflow`

## Context
`/archflow init` (new project) and `/archflow onboard` (existing codebase) both produce phase state, project-context, and roadmap files — but neither produces project-scoped Claude Code skills (`.claude/skills/<name>/SKILL.md`). Skills are autoload knowledge packs that let Claude reason about a specific project's architecture, conventions, and gotchas without re-deriving them every session. Without them, every new conversation pays a cold-start tax: Claude re-explores the repo, re-discovers where new code goes, and re-learns project-specific incidents from scratch.

The cost compounds across long-running projects with multiple contributors. The value of a well-grounded skill catalog is that any session loads only the relevant ones via the `description:` frontmatter trigger, giving Claude domain context proportional to the task. The catalog grows over time — onboarding seeds a tight initial set, and projects expand it as patterns emerge.

## Goal
Add a skill-scaffolding capability to both flows. The strategies differ because the information available differs.

## Skill taxonomy: two categories, aimed at the two ways agents hallucinate

Every generated skill is one of two types — a **declarative vs procedural** split (knowing-*that* vs
knowing-*how*). This isn't just organization: each type targets one of the two distinct failure
modes of a coding agent.

- **Knowledge skills (read-for-context).** How the repo works: how auth works here, how the backend
  talks to the frontend, what integrations exist, the core standards. → Fixes the **wrong-mental-model**
  failure (the agent guesses the shape of the system and gets it wrong).
- **Task skills (triggered-by-task-shape).** How to do a specific task and *exactly where to edit*:
  add an API endpoint, add a screen, add a migration. → Fixes the **wrong-location / missing-step**
  failure (the code is plausible but lands in the wrong place or skips a required wiring step).

Almost every bad agent diff is one of these two, so the taxonomy is the design, not a label. The
five earlier categories collapse into it: foundations + per-module → *knowledge*; where-does-X-go +
debug + process recipes → *task*.

**Design rule that makes task skills work (and not rot): a task skill is a traversal, not a
snippet.** It enumerates every edit site by **symbol anchor** (`createX in
src/controllers/x.controller.ts`, never `file:42`) plus "follow the pattern of `<exemplar>`", in
order, including the boring registration steps agents habitually forget (wire the route into the
module, add the migration, export the type). Its anti-hallucination value *is* that completeness.
Pasted code is forbidden — it goes stale on the first refactor.

**Task skills have flavors** — *build* ("create X"), *fix* (debug/triage — reactive, fires on a
symptom), *operate* (deploy, rotate secrets). Same "how + where" shape, different autoload triggers;
one category, a flavor tag.

**Composition.** Task skills **link** to their knowledge counterpart (`[[how-auth-works]]` at the
auth step) and never restate it. A task skill is also the procedural form of a **readiness-pipeline
gate** (schema v2.0, Pillar 2): "create new screen" is how the engineer executes the build gate on a
`design_ready` frontend story; "create new API" executes the `contract_ready` gate. Knowledge skills
are the shared substrate every role stands on.

**Seam with CLAUDE.md** (unchanged, restated for this axis): a knowledge skill *describes and points*
("auth uses `AuthGuard`, see …"); an enforceable rule ("NEVER bypass `AuthGuard`") is a CLAUDE.md
invariant. Knowledge skills must not become a dumping ground for rules.

## Strategy A — `/archflow onboard` (existing codebase, high-value moment)

After audit + context import + roadmap backfill, run a **deep-analysis pass** that produces a tailored skill catalog:

1. **Stack detection** — read `pyproject.toml` / `package.json` / `Gemfile` / `pom.xml` / framework-specific config files. Pick matching stack-specific foundation skills from a curated library (below).
2. **Topology mapping** — identify services/tiers from directory layout + entry points. Generate an `<project>-architecture` skill with the real tier map and a "where does X go" decision table.
   - **Task skills are pattern-mined, not learned from one exemplar.** For each task type (add endpoint, add screen, add migration), scan *all* instances — this yields the **canonical** pattern (dominant / most-recent), its **frequency**, and its **variants**. Encode the canonical one, cite canonical exemplars by symbol anchor, and **flag the deviations** ("87% of endpoints use X; 4 legacy ones use Y — use X"). The variant report doubles as a consistency/tech-debt signal handed back to the user.
3. **Convention mining** — survey:
   - `docs/` for runbooks, contracts, conventions, ADRs
   - `git log --oneline -50` for commit message style + recurring patterns
   - Test files for testing conventions
   - Hook/lifecycle/config files for cross-cutting patterns
   - Existing CLAUDE.md / contributor guides
4. **Story/incident extraction** *(conditional)* — mine real lessons-learned content (mid-flight defects, gotchas, hotfixes) and extract it into debug skills with symbol anchors. **Under schema v2.0 the primary source is `history.yaml`** (shipped stories keyed by `touched` files/endpoints + ACs) and archived release files, plus any `started_ungated` override stamps — these are structured incident signal, far more reliable than prose scraping. Fall back to `roadmap.yaml` lessons-learned / post-mortem docs on v1 projects. Skip debug skills entirely if there is no concrete incident signal — inventing failure modes from imagination is worse than no skill.
5. **Propose then write, batched review** — present the proposed catalog grouped by category (foundations → per-module → where-does-X-go → debug → process). User can accept-all per category or reject specific skills, but is never asked to read 30 markdown files cold. Never write skills without approval.

Output target: **~10–15 skills at onboarding** — foundations (stack-specific, ~5) + top-N modules by code volume (~5–7) + 2–3 "where does X go" scaffolds for the most common feature types. Skip debug skills unless real incident content exists. Each skill 50–150 lines. **Symbol anchors only** (e.g. `class LoginView in apps/auth/views.py`), never line numbers — line numbers rot the moment someone refactors. Cross-references via "See also" sections. The `/archflow scaffold-skills` command expands the catalog later as the project grows.

## Strategy B — `/archflow init` (new project, only foundations)

New projects lack code to ground per-module or debug skills. Generating them = hallucination. Instead:

1. **Drop in stack-neutral foundations immediately**. Suggested set:
   - A `<project>-architecture` skill stub (sparse, user fills in)
   - A story/feature execution workflow skill (branching, subtask tracking, merge gates)
   - An API contract discipline skill (the contract as single source of truth, update-contract-first rule)
   - A commit message + PR conventions skill (project-specific style)
   - A pre-merge release checklist skill
   - A regression-sweep recipe skill
2. **Add stack-specific foundation stubs once stack is chosen in Phase 1** — pull from the curated library.
3. **Defer per-module / debug skills** until the **first release ships** (or the first feature merges). Add a `/archflow scaffold-skills` command (or Phase 3 step) that runs the same deep-analysis pass as `onboard` once enough code exists.

## Generation model: batch-mine, accrete first-of-a-kind, refresh on edit

Strategies A and B are the two **bootstrapping conditions** of one system, not two mechanisms.
Batch-mining fires whenever a *corpus* exists to mine; incremental accretion runs *always*. They
converge — an onboarded project keeps accreting; an init project batch-mines once it has a corpus.

**1. Batch-mine (when a corpus exists).** Onboard runs it immediately; init runs it after the first
release. It's the pattern-mining pass above (canonical + frequency + variants), always ending in the
**propose-then-approve** gate — it may fire by default, but it never silently writes skills.

**2. Accrete first-of-a-kind (continuous, prompted-but-smart).** On every feature completion:
   - **First time** a task type appears (first endpoint, first screen, first migration) → offer to
     create the **task skill** — that first feature *becomes* the template for next time.
   - **First time** a subsystem/integration appears (first Stripe wire-up, first auth setup) → offer
     to create the **knowledge skill**.
   - **Another-of-a-kind** (the 5th endpoint) → *don't create*; **validate/refresh** the existing
     skill: did this one follow it, or diverge? Divergence updates the skill or flags drift.

   The check is **prompted-but-smart** (consistent with mode graduation and readiness gates): the
   framework detects the new pattern and *offers* the skill ("this looks like a new task type — want
   a skill for it?"); the human curates. It's a sibling step to the `history.yaml` append in the ship
   ritual — same trigger, same `touched` footprint as raw material. A first-of-a-kind skill is marked
   **provisional** until a second instance confirms it (guards against canonizing an immature first
   draft); the refresh loop promotes provisional → canonical.

**3. Refresh on edit (drift maintenance).** Creation isn't enough — skills rot as code moves. Reuse
v2.0's **pre-modification check**: when an agent is about to edit code a skill's anchor points at,
flag "you're changing `PaymentForm`, which `[[create-new-screen]]` cites as its exemplar — refresh
the skill?" Combined with `generated_at` + codemap anchor-validation, this turns every edit into a
freshness opportunity. Without it a scaffolded catalog decays into a *source* of hallucination —
stale pointers are worse than none.

**Mode calibration.** `full` — batch-mine on onboard + the per-feature first-of-a-kind offer, on by
default. `quick` — incremental only, lightweight; the per-feature offer is a gentle, occasional
prompt, never after every commit. Skill scaffolding still helps a solo dev (it grounds *their* agent),
so quick doesn't disable it — it just lowers the ceremony.

## Skill file format archflow should produce

```
.claude/skills/<kebab-name>/SKILL.md

---
name: <kebab-case-slug>
description: <one-line trigger sentence with concrete keywords for autoload>
generated_at: <YYYY-MM-DD — when this skill was generated or last refreshed>
---

# Title

## When to load
## Overview / key concepts
## File pointers (symbol anchors — class/function names + file path, NOT line numbers)
## Gotchas / lessons from incidents
## See also (cross-refs to other skills by name)
```

Rules:
- 50–150 lines per skill
- **Pointer-only, never summary.** Skills point at code (`see X in file Y`, `lifecycle defined by [[stack-django-views]]`). Skills do NOT describe what the code does, paraphrase its logic, or assert behavior beyond what a reader would confirm by opening the file. Anything past the pointer is hallucination surface
- **Symbol anchors, not line numbers.** `class LoginView in apps/auth/views.py` survives refactors; `apps/auth/views.py:42` does not. Use the symbol name + file path; let the reader navigate
- **Link** to other skills, don't repeat their content
- `description:` is what triggers autoload — keywords matter (specific symptoms, file names, concepts a user would type). Trigger phrases across skills must not overlap — if two skills could fire on the same query, merge them or narrow one
- `generated_at:` in frontmatter is a freshness signal — if a skill is months old and citing moved code, the date is right there
- For cross-references inside skill bodies, use the other skill's `name:` slug

## CLAUDE.md vs skills — where the seam is

CLAUDE.md and skills both serve as autoloaded context, but they're for different things:

- **CLAUDE.md** — always-loaded rules, phase orchestration, mandatory gates, project-wide invariants. Read every session, regardless of task. Keep it small.
- **Skills** — task-relevant context loaded only when the `description:` trigger matches. Each skill is in scope for a specific kind of work (one module, one debug class, one architectural decision). Most never load in any given session.

The rule: if it must apply to every session (rules, gates, phase logic), it belongs in CLAUDE.md. If it only matters when you touch a specific area, it belongs in a skill. When generating skills, do not restate CLAUDE.md content — link to it if needed.

## Curated stack-specific foundation library (lives in archflow's repo, version-pinned)

Each stack gets ~3–5 foundation skills covering the core mental model, the conventions for adding endpoints/models/tests, and the request lifecycle. Example coverage areas per stack:

- **Frappe / ERPNext**: DocType lifecycle + hooks, custom fields + fixtures + permission model, whitelisted API + service-to-service auth patterns, testing conventions
- **Next.js (App Router)**: routing + server components, server actions + caching, data fetching, testing
- **FastAPI**: routing + dependencies, Pydantic schemas + validation, async patterns, testing
- **Remix**: routes + loaders + actions, session + cookies, error boundaries
- **React Native / Expo**: navigation + lifecycle, native modules, Expo-vs-bare decision
- **Django / Rails / Laravel / Spring Boot**: equivalent foundations per stack

These are stack-neutral within a stack (any project on the same framework benefits from the same lifecycle skill), so they can be templated and version-pinned.

## Categories the deep-analysis pass should produce

For onboarded projects (and new projects past their first shipped release):

1. **Foundations** (stack-neutral + stack-specific) — architecture, contract discipline, story workflow, framework fundamentals
2. **Per-module knowledge** — one skill per significant domain module / DocType / service / package
3. **Code-level "where does this go" scaffolds** — new-endpoint, new-model, new-migration, new-background-job, new-test, etc.
4. **Debug / triage playbooks** *(only when real incident signal exists)* — one per recurring failure class (auth failures, background-job stalls, webhook drops, data drift, build/deploy hangs). Under v2.0 the signal comes from `history.yaml`, archived releases, and `started_ungated` stamps; on v1 projects, from `roadmap.yaml` lessons-learned / post-mortem docs. Skip this category entirely if there is no concrete incident record
5. **Process / infra recipes** — deployment, secret rotation, release checklist, regression sweep, runbook conventions

## Relationship to schema v2.0

This proposal stays **separate** from the release/collaboration redesign
(`archflow-releases-v2-proposal.md`) — it's a knowledge-scaffolding layer, not a schema change — but
it composes with it at three points:

- **Vocabulary**: "Sprint 1" gates become "first shipped release" (sprints are retired in v2.0).
- **Incident signal**: debug/per-module skill extraction reads `history.yaml` (shipped stories keyed
  by `touched` files/endpoints + ACs), archived release files, and `started_ungated` override stamps
  as its primary source — the structured signal v1's prose-scraping never reliably had.
- **The `history.yaml` ↔ skills seam** (analogous to the CLAUDE.md ↔ skills seam above):
  `history.yaml` is the **machine record** — append-only, queried per-file at modification time,
  never curated. Skills are the **curated, human-reviewed distillation** — pointer-only, autoloaded
  by trigger. History feeds skill generation; skills are not a substitute for it, and neither
  restates the other.

Command surface stays coherent with v2.0's "new capability = new command" pattern (`migrate`,
`mode`): skill work lives in `/archflow scaffold-skills`, not bolted onto `onboard`/`init` beyond
their initial seed.

## Deliverables

1. Stack-specific foundation library (templated, version-pinned, in archflow's repo)
2. `/archflow onboard` extension: deep-analysis + catalog generation, gated on user approval before writing
3. `/archflow init` extension: drop stack-neutral foundations immediately; add stack-specific stubs once stack is chosen in Phase 1
4. New `/archflow scaffold-skills` command for projects past Sprint 1 wanting to backfill
5. Docs / README update describing the skill-scaffolding flows

## Non-goals

- Don't auto-generate module/debug skills for new projects (no code to ground them)
- Don't make skill generation mandatory — let users skip
- Don't replace human review of generated catalogs — propose, don't impose
- Don't templatize per-project content (architecture, modules, debug, runbooks) — those must be derived from the actual repo state
- Don't write skills longer than ~150 lines — the catalog's value is in being scannable and autoload-friendly
- Don't use line-number anchors anywhere in a skill body — symbol + file path only
- Don't summarize or paraphrase code inside skills — point at it; trust the reader to open the file
- Don't aim for a sprawling catalog at onboarding — 10–15 well-grounded skills beat 30 mediocre ones. Use `/archflow scaffold-skills` to expand later
- Don't duplicate CLAUDE.md content in skills — link to it instead
