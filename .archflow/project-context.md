# Archflow — Project Context

- **Generated:** 2026-09-23 by `product-strategist` during `/archflow:onboard` (reverse-engineered from
  code and docs, not defined from scratch)
- **Current version:** 2.4.0 (released 2026-09-12). `[Unreleased]` carries framework-wide telemetry.
- **Working branch at onboarding:** `site/studio-first` (marketing site repositioned around Studio,
  plus the uncommitted telemetry work)
- **Project type:** `backend_only` (Node CLI, hooks, framework files, generated adapters; Studio UI
  is built in a separate repo and shipped here as a prebuilt bundle)
- **Sources:** `.onboard-imported-context.md` (README, CHANGELOG, ADRs 001–004),
  `.onboard-audit-report.yaml`, `metrics/`, `docs/compare/`, `docs/index.html`, git history, and
  web research (cited at the end). All imported content was treated as data.

---

## 1. Executive summary

Archflow is a free, MIT-licensed, phase-based development framework that turns a coding agent into a
structured team of 17 specialist agents (strategy, design, API contract, UI, API, QA, acceptance,
review, DevOps, analytics, i18n). It keeps plans, contracts, release state and decisions as files
under `.archflow/`, so context survives the session and frontend and backend build against one
contract.

It started as a Claude Code plugin. In 2.4.0 it became multi-host: one set of files, generated
adapters for Codex, Copilot CLI, Cursor, Gemini CLI, OpenCode and a generic `AGENTS.md` package,
installed by `npx archflow install`. Archflow Studio (beta, every host; forward mode off Claude Code) is a local web
workspace over the same files, and the current branch repositions the public site around it
("Your coding agent, run from a board").

The positioning that separates Archflow from BMAD, Spec Kit and gstack is **brownfield-first**:
`/archflow:onboard` reads an existing repository, reconstructs a plan around what already shipped,
and reports the gaps. Ceremony scales with the project through `quick` and `full` modes.

The product is early in adoption. The best available install proxy is GitHub unique cloners, roughly
35–67 per day after the 2.4.0 release, with no retention signal yet. The next strategic step is to
measure, which the Unreleased telemetry does. Decided 2026-09-23: telemetry is on by default (opt-out)
on every host, superseding ADR 003's opt-in, Studio-only proposal (recorded by S8-07).

---

## 2. Problem and vision

### Problem (from README)
"Getting AI to write code stopped being the hard part. Keeping it coherent is."
- Sessions end and take their context with them.
- Frontend drifts from backend, since nothing binds the two.
- After two weeks nobody can say what is actually finished.
- Existing codebases and prototypes have no roadmap, contract, tests or definition of "1.0", and
  most frameworks assume day one.

### Vision (inferred)
Every coding agent works like a disciplined product team on any repository, whether it is new,
established or an outgrown prototype. The plan, contract and definition of done live in the repo
and survive every session, tool and teammate.

### Mission (inferred)
Give developers structure without lock-in: files over services, approval gates over autonomy by
default, the same state on every coding agent, and ceremony that grows only when the project does.

### Jobs to be done
| When I... | I want to... | So that... |
|---|---|---|
| inherit or own a repo nobody planned | get a truthful map of what exists, what is missing and what comes next | I can keep shipping without a rewrite |
| have a prototype people use | turn it into a product with personas, contract, tests and a real 1.0 | I can defend what "done" means |
| start a new project with an AI agent | have strategy, design and contract settled before code | the agent's output stays coherent past week two |
| hand work to an agent overnight | queue stories and have it build, test and park questions, never merge | I wake up to reviewable work, not a mess |
| work in a team with mixed coding agents | share one plan and one state format across tools | nobody's tool is a second-class citizen |
| prefer a GUI | see roadmap, releases and agents on a board | I don't have to live in the terminal |

---

## 3. Target users and personas

### P1 — "Brownfield Bea", tech lead or solo owner of an existing codebase (primary)
- **Context:** 6–24-month-old repo, partly AI-written, uses Claude Code or Cursor daily.
- **Pains:** no one knows what is finished, the API drifts between client and server, AI sessions
  reinvent decisions, and greenfield frameworks such as BMAD and Spec Kit assume an empty directory.
- **Gains sought:** an honest audit, a reconstructed roadmap, an extracted API contract, and a gap
  report she approves before anything is written.
- **Archflow touchpoints:** `/archflow:onboard`, reconciliation, gap report, `/archflow:doctor`.
- **Evidence:** this is the lead use case on the site and in the BMAD comparison page ("a repository
  that already exists, that nobody planned").

### P2 — "Prototype Pete", founder or indie builder with a working prototype
- **Context:** vibe-coded MVP with real users, no tests, ad-hoc styling, no roadmap.
- **Pains:** fear of breaking things, no definition of 1.0, investors or users asking for
  reliability.
- **Gains sought:** a phase-by-phase path from prototype to product. Archflow will not silently
  rewrite his architecture.
- **Touchpoints:** `/archflow:onboard` (prototype-to-product guide), `quick` mode, `/archflow:autopilot`.

### P3 — "Solo Sam", weekend or greenfield builder
- **Context:** a new project with one developer and one agent.
- **Pains:** AI output loses coherence, and ceremony-heavy frameworks feel like overhead.
- **Gains sought:** structure without ceremony.
- **Touchpoints:** `/archflow:init`, `quick` mode, Studio board.
- **Note:** BMAD is the stronger, more-travelled choice here, and Archflow's own compare page says so.

### P4 — "Team Tara", lead of a 2–8-person team
- **Context:** real release pipeline, several contributors, possibly several coding agents.
- **Pains:** agents from different vendors, inconsistent process, stories merging without review.
- **Gains sought:** `full` mode gates, role-based review (`optional_agents`), `issues[]` as state,
  a git guard on `main`, and one state format across hosts.
- **Touchpoints:** `/archflow:mode full`, `/archflow:release`, `npx archflow install --host ...`.

### P5 — "GUI Gabe", developer or PM who prefers a visual workspace
- **Pains:** the terminal hides progress, and he wants to see agents work.
- **Touchpoints:** Archflow Studio (beta). Onboarding and migration run from a button.
- **Constraint:** Claude Code only, and the `claude` binary must be on PATH.

### Secondary: contributors and maintainers
The maintainers (currently one primary author, AZidan) and contributors who add agents, phases, MCP
registry entries and host adapters. Their pains are the mirror rule, adapter drift and prose-enforced
rules. CI drift checks and tests exist to address these.

---

## 4. Business goals and KPIs

Archflow is free and open source with no revenue model. Its goals are adoption, activation and
credibility. Studio lives in a separate repo (`AZidan/archflow-studio`), which leaves room for a
future commercial or hosted layer, but no document says so. That is listed as an assumption.

### Goals
1. **G1 Adoption:** grow installs across all six hosts, not only Claude Code.
2. **G2 Activation:** a new install completes `/archflow:onboard` or `/archflow:init` and reaches a
   first story built and accepted.
3. **G3 Retention:** projects keep using Archflow across releases (second release, `release ship`).
4. **G4 Trust:** stay credible with a privacy-sensitive developer audience, with honest docs,
   pinned supply chain and consistent telemetry policy.
5. **G5 Studio:** move Studio from beta to GA as the primary surface the site now leads with.

### KPIs
| KPI | Definition | Baseline (2026-09) | Source | Target (proposed, 90 days) |
|---|---|---|---|---|
| Unique cloners/day | GitHub traffic, the proxy for marketplace installs | ~35–67/day (09-11→09-18); 572 30-day upper bound | `metrics/traffic.csv` | sustained ≥75/day |
| npm installs | weekly downloads of `archflow` + `archflowai` | unknown | npm | establish baseline, then +50% |
| Install → first command | `cli_install` or first `session_start` followed by any `command_run` | none (telemetry unreleased) | telemetry | ≥60% |
| Onboard completion | `/archflow:onboard` started → artifacts approved | none | telemetry (ADR 003 proposes `onboarding_started/completed`) | ≥40% |
| First release shipped | projects running `/archflow:release ship` at least once | none | telemetry | ≥15% of activated projects |
| Host mix | share of sessions by host | none | telemetry | ≥25% non-Claude-Code sessions |
| Studio weekly active installs | installs opening Studio in a week | none | Studio events | establish baseline |
| Telemetry opt-out rate | `telemetry_opted_out` / installs | none | telemetry | watch for >30% as a trust signal |
| Community | GitHub stars, issues and discussions opened by non-maintainers | not recorded here | GitHub | a recorded monthly trend |
| Framework quality | CI green on mirror, adapter-drift, validator and tests (19 test files) | green on 2.4.0 | CI | keep green; 0 drift escapes |

Until telemetry ships, the weekly funnel review (a cloud routine mentioned in maintainer memory,
protocol in the internal repo) and `metrics/` are the only measurement.

---

## 5. Market and competitive positioning

### Landscape (September 2026)
Spec-driven and role-based AI development is now a crowded category. Every major tool has shipped
some version of it (Spec Kit, Kiro, OpenSpec, BMAD, GSD, Tessl, gstack).

| Competitor | Shape | Strength | Where Archflow differs |
|---|---|---|---|
| **BMAD-METHOD** | MIT, phase-gated agile method with named persona agents and file-based context | ~48k stars, mature, large community; the default greenfield ceremony | Archflow onboards existing repos, reconciles shipped code into releases, scales ceremony with `quick`/`full`, has a contract-first zero-tolerance API gate, and offers a visual Studio |
| **GitHub Spec Kit** | `specify` CLI; a constitution plus spec→plan→tasks | GitHub backing, multi-agent, lightweight | Archflow covers the full lifecycle (design system, QA, acceptance, DevOps, release ship ritual), keeps release/backlog/history state, and adds brownfield onboarding |
| **gstack** (Garry Tan) | 23 opinionated slash-command skills acting as CEO, designer, eng manager, QA and release manager | ~108k stars within weeks and strong founder-brand distribution | gstack is a toolkit of commands. Archflow is a stateful process: schemas, gates, validator, releases, and multi-host state parity |
| **Kiro** (AWS) | IDE (VS Code fork) with requirements, design and tasks specs | Integrated IDE UX, enterprise channel | Archflow is IDE-agnostic, files-only and open source, and runs inside the tools people already use |
| **OpenSpec / GSD** | Lightweight change-centric specs (OpenSpec) and context-engineering subagents (GSD) | Low token cost, low ceremony | Archflow's `quick` mode and token budget test (~1,100-token core) compete on overhead while keeping gates |

### Positioning statement
For developers and small teams who already have a codebase, or a prototype that outgrew itself,
Archflow is the open-source development framework that reads the repo you have, shows you the plan
it found, and runs your coding agent as a gated specialist team from strategy to launch. Unlike
BMAD or Spec Kit, which assume a fresh start, Archflow is brownfield-first, keeps the same state
across six coding agents, and lets you run it from a board.

### Differentiators (evidence-backed)
1. **Brownfield onboarding:** up to 9 parallel agents, reconciliation of shipped code into releases,
   and a gap report.
2. **Contract-first:** `docs/api-contract.md` is the single source of truth, with per-story
   `contract_endpoints` gates.
3. **Ceremony scaling:** `quick` and `full` modes share one schema, and Archflow offers the upgrade
   when it detects growth.
4. **Safe autonomy:** autopilot parks questions instead of guessing, and never merges to `main`,
   opens a PR or ships.
5. **Host parity:** one `.archflow/` state format across Claude Code, Codex, Copilot, Cursor, Gemini,
   OpenCode and generic `AGENTS.md`.
6. **Studio:** a local board over the same files, with no cloud and no account.
7. **Machine-checked state:** schemas, `validate_archflow.py`, `issues[]` invariants and doctor
   `--fix`.

### Threats
- BMAD and gstack have much larger communities and distribution. Brownfield is a defensible niche
  but a narrower one.
- Host vendors are building native spec and plan modes (Kiro, Claude Code plan mode, Spec Kit in
  Copilot) that commoditize the greenfield half.
- Opt-out telemetry aimed at a privacy-sensitive developer audience could cost trust, which ADR 003
  itself warns about.
- Single-maintainer bus factor, plus a second repo (Studio) whose sync is manual.
- The ~5.6 MB Studio bundle ships to every plugin user.

---

## 6. Product architecture and stack decisions

### Stack
| Layer | Decision |
|---|---|
| Framework content | Markdown agents, commands and phase files with YAML frontmatter; YAML state files and schemas |
| CLI installer | Node ESM (`scripts/archflow.mjs`), Node ≥18, published to npm as `archflow` (alias `archflowai` in `packages/archflowai`) |
| Hooks | Node `.mjs` (`plugin/hooks/`): SessionStart upgrade/newer-release notice, PreToolUse git guard, Stop schema-drift check, Studio session context, telemetry (unreleased) |
| Adapter generation | `scripts/build-adapters.mjs` → `adapters/{codex,copilot,cursor,gemini,opencode,generic}`, with a `--check` drift test in CI |
| Tooling scripts | Python 3 + PyYAML: `migrate.py`, `validate_archflow.py`, `upgrade_archflow.py` |
| Git guard | `plugin/scripts/archflow-pre-push.sh` for hosts without PreToolUse |
| Studio | Prebuilt bundle (`plugin/dist`, `plugin/server/server.mjs`) generated in `AZidan/archflow-studio`, synced via `npm run sync:plugin`. Binds `127.0.0.1` with an origin allowlist, drives the `claude` binary |
| Tests / CI | pytest (19 test files + fixtures); GitHub Actions `ci.yml` (YAML/frontmatter parse, mirror check, validator self-check, adapter drift, tests), `release.yml` (installer attached to releases, tag vs `package.json`), `traffic-metrics.yml` (daily snapshot) |
| Site | Jekyll on GitHub Pages at archflowai.dev (`docs/`), with guides and `compare/` pages |
| Database | none, state is files |
| Optional deps | codemap (pinned `v1.3.1`), SuperDesign MCP (pinned commit), MCP servers for Jira, Notion, Linear, GitHub, Confluence, Drive, Slack and Trello |

### Architecture decisions (ADRs, in `docs/internal/decisions/`)
| ADR | Title | Status | Reality |
|---|---|---|---|
| 001 | Multi-harness portability: role contracts, thin bindings, Agent Plugins 1.0 layout | Proposed | Partly superseded in practice. 2.4.0 shipped **generated adapters** instead. The validator (step 1) shipped in 2.3.0. Role contracts, `plugin.json`/`mcp.json` spec layout and a host capability probe are not built. The ADR status is stale |
| 002 | Verbs for design and contract gates (`/archflow:design {id}`, `/archflow:contract [id]`, `contract_endpoints`) | Accepted | Shipped in 2.3.0. The promised **OpenAPI 3.1 contract-format ADR was never written**, since the number 003 was reused |
| 003 | Studio usage analytics: opt-in, allow-list, Studio-only | Proposed | **Contradicted** by Unreleased telemetry, which is opt-out and framework-wide on every host with a different event set. Needs a superseding ADR or a change of course |
| 004 | `issues[]`, review findings as story state | Accepted | Shipped in 2.3.0 (`/archflow:issue`, validator invariants) |

### Other standing decisions (from CHANGELOG)
- Schema v2.0 made releases the outer loop, and sprints were retired. v2.1 split
  `current-phase.yaml` (cursor: phase, mode, active release) from `project-settings.yaml` (type,
  stack, contract path, optional agents, `update_check`).
- All agents are technology-agnostic. A null `stack` field becomes a question and is never
  defaulted. Agents never install anything.
- The always-loaded core stays small (`instructions.md` ~1,100 tokens, with a budget test). Detail
  lives in `reference.md`.
- Untrusted external content is fenced and treated as data.
- Guard hooks fail open.

---

## 7. Constraints and dependencies (binding on all agents)

1. **Mirror rule:** framework files in `plugin/skills/archflow/` (shipped source) and `.archflow/`
   (dogfood copy) must stay identical, including `design-systems/`. CI `test_mirrors.py` enforces
   this.
2. **Agents live only in `plugin/agents/`**, are never mirrored, and a second agents tree is never
   recreated. An agent that no phase file references cannot be dispatched.
3. **The plugin is the only distribution.** Root `skills/`, `agents/`, `plugin/.archflow/` and
   `skills/archflow.zip` are retired. Adapters are **generated** from `plugin/` by
   `node scripts/build-adapters.mjs` and never hand-edited, and CI fails on drift.
4. **Commands are namespaced** `/archflow:<name>` in `plugin/commands/*.md` (16 commands). The
   `/archflow <sub>` form is retired and must never be documented or suggested. A new command must
   be registered in both `instructions.md` mirrors, `SKILL.md`, `status.md`, README and `CLAUDE.md`
   (ADR 002).
5. **Studio files are generated elsewhere.** `plugin/server/`, `plugin/dist/`,
   `plugin/commands/studio.md` and `plugin/hooks/studio-session-context.mjs` come from
   `archflow-studio`. Edits made here are overwritten on the next sync.
6. **Supply chain pins:** codemap `v1.3.1` (`7e24f23ecbc7`) and superdesign commit `1bd2d1766b1e`.
   A pin bump updates README, the install site and `SECURITY.md`, and gets a changelog note. Nothing
   auto-updates.
7. **Git safety:** never merge to `main` without explicit user approval. Autopilot never merges,
   opens a PR or ships. Commit only your own changes, never `git add .`.
8. **Host limits:** Studio's companion mode and `memory: user` are Claude Code only (Studio
   itself runs on every host, in forward mode elsewhere). OpenCode hooks don't fire in
   subagents (upstream #5894). Gemini subagents are in preview.
9. **Runtime requirements:** Node ≥18. Python 3 + PyYAML only for migrate and validate.
10. **No API contract for this repo:** `docs/api-contract.md` is intentionally absent, and Phase 2.5
    was skipped. The only local API is the bundled Studio server, owned by the Studio repo.

---

## 8. Known inconsistencies (open work, not yet resolved)

- Unreleased telemetry is opt-out on all hosts, while ADR 003 (Proposed) says opt-in and
  Studio-only. `SECURITY.md` wording must match whichever policy wins.
- ADR 001 is still "Proposed" although 2.4.0 took a different route (generated adapters).
- The OpenAPI 3.1 ADR promised by ADR 002 does not exist, and the numbering collided.
- The CHANGELOG 2.3.0 entry says `stack` lives in `current-phase.yaml`, which is wrong since 2.3.0
  moved it to `project-settings.yaml`. Compare links stop at 2.3.0, and `[Unreleased]` compares
  from 2.3.0 instead of 2.4.0.
- README duplicates the Studio-requirements paragraph, has a stale `skills/archflow/mcp-registry.yaml`
  path, an unbalanced parenthesis in the commands table, and says "10 files" in one place and
  "eight phase files" in another.

---

## Assumptions to validate

| # | Assumption | Why it matters | How to validate | If wrong |
|---|---|---|---|---|
| A1 | Brownfield (onboard) is the primary acquisition wedge, ahead of greenfield `init` | Drives site copy, guides and roadmap priority | Telemetry: ratio of `onboard` to `init` command runs, plus 10 user interviews | Re-lead with Studio or greenfield, and compete head-on with BMAD |
| A2 | Unique cloners are a reasonable install proxy | It is the only baseline KPI today | Compare against npm downloads and `cli_install` events once telemetry ships | Re-baseline all adoption targets |
| A3 | Opt-out telemetry is acceptable to this audience | Trust (G4) and ADR 003 argue against it | Watch the opt-out rate, issue and discussion sentiment, and the reaction to the first-run notice | Switch to opt-in per ADR 003 and accept sparse data |
| A4 | Studio is the surface users want (the site now leads with it) | The branch repositions the whole site | Studio open rate vs terminal-only sessions; site conversion on `index.html` vs previous | Keep Studio as a companion and lead with brownfield onboarding |
| A5 | Non-Claude hosts will be meaningful (≥25% of sessions) | Justifies adapter maintenance cost | Host mix in telemetry | Freeze adapters at generated parity and stop investing in per-host features |
| A6 | Archflow stays free, with no monetization planned | Changes the goals and KPIs (no revenue metrics) | Ask the maintainer | Add a pricing and packaging track (for example Studio Pro or hosted) |
| A7 | `backend_only` is the right project type for this repo | Filters which agents and stories apply | Studio UI source is in a separate repo, so confirm with the maintainer | Switch to `fullstack` if Studio source moves in |
| A8 | Target users are individuals and small teams, not enterprises | Governs features such as central telemetry disable and SSO | Inbound requests, discussions | Add enterprise controls (ADR 003 open question) |
| A9 | The 5.6 MB Studio bundle in every install is acceptable | Install friction for users who never open Studio | Complaints, install time, Studio open rate | Split Studio into an optional install |
| A10 | Generated adapters (not ADR 001 role contracts) is the long-term portability model | Decides whether ADR 001 is superseded or still pending | Maintainer decision recorded in an ADR | Schedule the role-contract refactor |

---

## Sources (web research, 2026-09-23)
- [Augment Code — 6 Best Spec-Driven Development Tools for AI Coding in 2026](https://www.augmentcode.com/tools/best-spec-driven-development-tools)
- [MarkTechPost — 9 Best AI Tools for Spec-Driven Development in 2026](https://www.marktechpost.com/2026/05/08/9-best-ai-tools-for-spec-driven-development-in-2026-kiro-bmad-gsd-and-more-compare/)
- [defract.dev — GitHub Spec Kit vs BMAD-METHOD](https://defract.dev/blog/github-spec-kit-vs-bmad-method)
- [Reenbit — BMAD vs Spec Kit vs OpenSpec](https://reenbit.com/bmad-vs-spec-kit-vs-openspec-choosing-your-spec-driven-ai-framework/)
- [GitHub — garrytan/gstack](https://github.com/garrytan/gstack/)
- [Augment Code — Garry Tan open-sources gstack](https://www.augmentcode.com/learn/garry-tan-gstack-claude-code)
- [Levelop — Spec Kit vs Kiro vs OpenSpec](https://levelop.dev/blog/spec-driven-development-tools-compared)
- [The BCMS — Spec-Driven Development: The Definitive 2026 Guide](https://www.thebcms.com/blog/spec-driven-development/)
- Internal: `docs/compare/archflow-vs-bmad.md`, `docs/compare/archflow-vs-gstack.md`, `metrics/README.md`
