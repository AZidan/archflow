<div align="center">

# Archflow

**Turn Claude Code into a structured development team.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Claude Code](https://img.shields.io/badge/Claude%20Code-Framework-blueviolet)](https://docs.anthropic.com/en/docs/claude-code) [![Agents](https://img.shields.io/badge/Agents-16+-blue)](https://github.com/AZidan/archflow) [![Phases](https://img.shields.io/badge/Phases-6-green)](https://github.com/AZidan/archflow)

[Website](https://azidan.github.io/archflow/) · [Quick Start](#quick-start) · [What is Archflow?](#what-is-archflow) · [Phases](#the-phases) · [Agents](#agents) · [Commands](#slash-commands) · [Principles](#core-principles)

<img src="docs/archflow-overview.svg" alt="Archflow Overview" width="700" />

</div>

---

## What is Archflow?

Archflow is a **phase-based AI development framework** for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that orchestrates 16+ specialized agents through a rigorous workflow — from product strategy to production deployment.

Instead of one general-purpose AI doing everything, Archflow assigns each task to a dedicated agent with deep expertise in its domain: a `product-strategist` defines your business goals, a `ux-designer` creates your design system, an `api-contract-architect` locks down your API specs, and `ui-engineer` + `api-engineer` build the frontend and backend in parallel — all coordinated through file-based handoffs and mandatory approval gates.

Archflow works with any project type — fullstack, frontend-only, backend-only, or mobile — and adapts its phases, agents, and artifact structure accordingly.

### Works with new and existing projects

Most AI development workflows assume you're starting from scratch. Archflow works both ways:

- **Greenfield projects** start at Phase 1 — Archflow guides you from business strategy through design, implementation, and deployment, generating every artifact along the way.
- **Existing codebases** start with `/archflow onboard` — a three-phase orchestration that gathers your input, dispatches up to 9 specialized agents in parallel to deeply analyze your codebase, imports context from tools you already use (Jira, Notion, Linear, GitHub, Confluence, Slack), reverse-engineers artifacts (API contracts, design systems, roadmaps), and drops you into the right phase based on what already exists.

This means you can adopt Archflow on a project that's been in development for months — it meets you where you are instead of forcing you to start over.

#### How onboarding works

```
Phase A: Interactive Collection     You answer 5 quick questions (tech stack, context source,
                                    design/API preferences, roadmap vision)

Phase B: Autonomous Agent Dispatch  Up to 9 agents run in parallel across 3 dependency layers:
                                    codebase audit → doc deep-dive → design extraction →
                                    route/API extraction → product-strategist → ux-designer →
                                    api-contract-architect → dsl-generator → feature-planner

Phase C: Synthesis & Presentation   Results are reconciled, a gap report is generated,
                                    and artifacts are presented for your approval
```

The onboarding agents generate production-quality `project-context.md`, `roadmap.yaml`, `api-contract.md`, `theme.yaml`, `styled-dsl.yaml`, and `user-flows.md` — all reverse-engineered from your existing code and imported documentation. It also creates or updates your project's `CLAUDE.md` with architecture context derived from the analysis.

---

## Why Archflow?

Building software with AI assistants often means context gets lost, quality varies, and there's no consistent process. Archflow solves this by:

- **Phase gates with approval checkpoints** — No phase is skipped, no feature ships without verification
- **Specialized agents** — A UX designer doesn't write backend code; an API engineer doesn't make design decisions
- **Contract-first development** — API contracts are defined before implementation, enabling true parallel frontend/backend development
- **Token efficiency** — Dynamic phase loading means only relevant instructions are in context at any time
- **File-based handoffs** — Agents communicate through artifacts, not chat messages, so nothing gets lost
- **Greenfield and brownfield** — Works with new projects from scratch and existing codebases mid-development

---

## The Phases

```
Phase 1    Strategy & Planning         product-strategist, feature-planner
Phase 2    Design                      ux-designer, dsl-generator
Phase 2.25 High-Fidelity Screens       SuperDesign MCP (optional)
Phase 2.5  API Architecture            api-contract-architect
Phase 3    Implementation (Parallel)   ui-engineer + api-engineer, qa-engineer, pm-maestro-reviewer
Phase 4    Quality & Optimization      code-reviewer, performance-optimizer, pm-maestro-reviewer
Phase 5    Launch & Operations         devops-engineer, post-launch-analyst
Phase 6    Enhancement (On-Demand)     i18n-engineer, post-launch-analyst, any agent as needed
```

Each phase has explicit completion criteria, expected output artifacts, and requires user approval before advancing.

---

## Quick Start

### 1. Add the Marketplace (one-time)

Register the Archflow marketplace with Claude Code:

```bash
claude plugin marketplace add azidan/archflow https://github.com/AZidan/archflow
```

### 2. Install the Plugin

```bash
claude plugin install archflow --scope project
```

This saves the plugin reference to `.claude/settings.json` in your repo — any team member who clones gets prompted to install automatically.

### 3. Start Your Project

Open Claude Code in your project directory:

```bash
cd your-project
claude
```

- **New project?** Archflow starts at Phase 1 (Strategy).
- **Existing codebase?** Run `/archflow onboard` — the three-phase orchestration collects your input, dispatches specialized agents to deeply analyze your code, and presents production-quality artifacts for approval.

### 4. Develop Features

Once set up, use `/archflow feature` to add features and start the git workflow:

```
/archflow feature          # Interactive wizard
/archflow feature login    # Quick-add by name
```

Archflow creates the feature branch, breaks it into tasks, and guides implementation through the appropriate agents. Features are filtered by scope — a `backend_only` repo only sees backend-scoped features from the roadmap.

---

## Agents

### Phase 1: Strategy & Planning
| Agent | Role |
|-------|------|
| `product-strategist` | Business strategy, user personas, KPIs, market positioning |
| `feature-planner` | Feature roadmaps, user stories, epic breakdown, sprint planning |

### Phase 2: Design
| Agent | Role |
|-------|------|
| `ux-designer` | User flows, design systems, themes, wireframes |
| `dsl-generator` | Component specifications with styling (styled-dsl.yaml) |

### Phase 2.25: High-Fidelity Design (Optional)
| Tool | Role |
|------|------|
| SuperDesign MCP | Generate polished HTML screens from styled-dsl.yaml for visual approval |

### Phase 2.5: API Architecture
| Agent | Role |
|-------|------|
| `api-contract-architect` | API contracts from wireframes — the single source of truth |

### Phase 3: Implementation
| Agent | Role |
|-------|------|
| `ui-engineer` | All frontend: React, React Native, SwiftUI, Jetpack Compose |
| `api-engineer` | NestJS/PostgreSQL backends, strictly follows API contract |
| `qa-engineer` | Unit, integration, and e2e testing across all platforms |
| `pm-maestro-reviewer` | Acceptance testing via Maestro against roadmap criteria |

### Phase 4: Quality & Optimization
| Agent | Role |
|-------|------|
| `code-reviewer` | Code quality, security, best practices |
| `performance-optimizer` | Performance bottleneck identification and fixes |
| `pm-maestro-reviewer` | Full acceptance regression suite |

### Phase 5: Launch & Operations
| Agent | Role |
|-------|------|
| `devops-engineer` | CI/CD pipelines, deployment, infrastructure, app store prep |
| `post-launch-analyst` | Analytics, user insights, performance monitoring |

### Phase 6: Enhancement
| Agent | Role |
|-------|------|
| `i18n-engineer` | Internationalization for web, iOS, and Android |
| Any agent | Re-enter earlier phases for new features |

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/archflow` | Show available subcommands and current project status |
| `/archflow init` | Initialize Archflow in a new project (creates `.archflow/` state files) |
| `/archflow onboard` | Onboard an existing codebase — 3-phase orchestration: collect input, dispatch agents, synthesize results |
| `/archflow feature` | Add a feature to the roadmap (with scope-based filtering) and start the git workflow |
| `/archflow setup-mcp` | Configure MCP servers for external tools (Jira, Notion, Linear, GitHub, etc.) |

---

## Project Types

Archflow detects and adapts to your project type:

| Type | Frontend Agent | Backend Agent | Notes |
|------|---------------|---------------|-------|
| `fullstack` | Yes | Yes | Parallel frontend/backend development |
| `frontend_only` | Yes | No | Pages, components, flows |
| `backend_only` | No | Yes | Endpoints, services, modules |
| `mobile` | Yes | Yes | React Native, SwiftUI, or Jetpack Compose |

Phase instructions, agent selection, audit checks, and roadmap structure all adapt to the project type.

---

## Git Workflow

Archflow uses a structured branching strategy:

```
main
 └── feature/user-auth              (feature branch)
      ├── user-auth/login-form       (task branch)
      ├── user-auth/auth-api         (task branch)
      └── user-auth/session-mgmt     (task branch)
```

- Feature branches from `main`
- Task branches from the feature branch
- Merges only happen after explicit user approval
- Feature completion triggers cleanup and roadmap updates

---

## Key Artifacts

Archflow manages these files in your project:

| File | Purpose |
|------|---------|
| `.archflow/project-context.md` | Business goals, tech stack, architecture decisions |
| `.archflow/roadmap.yaml` | Feature roadmap and sprint planning |
| `.archflow/current-phase.yaml` | Phase state tracker (auto-created) |
| `.archflow/current-feature.yaml` | Active feature scope and task tracking |
| `docs/api-contract.md` | API specifications (single source of truth) |
| `design-artifacts/styled-dsl.yaml` | Component specifications with styling |
| `design-artifacts/theme.yaml` | Design system tokens |
| `design-artifacts/wireframes/` | Screen layouts |
| `docs/acceptance-reports/` | Maestro acceptance test results |

---

## Core Principles

### API Contract is Sacred
Both `api-engineer` and `ui-engineer` must follow `docs/api-contract.md` exactly. Zero deviations. This eliminates integration issues and enables parallel development.

### Approval Gates Everywhere
Every phase requires explicit user approval before advancing. Working features must be demonstrated. No autonomous phase skipping.

### One Feature at a Time
Phase 3 processes one feature at a time. Agents are scoped to single feature boundaries. This prevents conflicts and keeps context focused.

### Agents Communicate Through Files
No information passes through chat between agents. `api-engineer` produces endpoints; `ui-engineer` consumes the API contract and styled-dsl.yaml. This makes handoffs reliable and auditable.

### Acceptance Testing is Mandatory
After QA, the `pm-maestro-reviewer` validates acceptance criteria from `.archflow/roadmap.yaml`. A feature is not complete until it receives an ACCEPTED verdict.

---

## File Structure

Archflow is distributed as a Claude Code plugin marketplace. The plugin contains all framework code; your project only stores state files.

### Marketplace (this repo)

```
archflow/
├── .claude-plugin/marketplace.json  # Marketplace registry
├── plugin/                          # Installable plugin
│   ├── .claude-plugin/plugin.json   # Plugin manifest
│   ├── hooks/hooks.json             # SessionStart hook (loads instructions after compaction)
│   ├── agents/                      # 17 specialized agent definitions
│   ├── skills/archflow/             # Slash command implementations
│   │   ├── SKILL.md                 # Router (onboard, feature, setup-mcp)
│   │   ├── mcp-registry.yaml        # Curated MCP server registry
│   │   └── commands/
│   │       ├── onboard.md           # /archflow onboard
│   │       ├── feature.md           # /archflow feature
│   │       └── setup-mcp.md         # /archflow setup-mcp
│   └── .archflow/                   # Framework instructions and phase files
│       ├── instructions.md          # Core instructions (reloaded via hook)
│       ├── workflow.md              # Git branching strategy
│       ├── base-dsl-structure.yaml  # DSL template for design artifacts
│       └── phases/                  # Phase-specific instruction files (10 files)
├── README.md
└── LICENSE
```

### Project (created by `/archflow onboard` or Phase 1 setup)

```
your-project/
├── .archflow/                       # Project state (version-controlled)
│   ├── current-phase.yaml           # Phase state tracker
│   ├── project-context.md           # Business goals, tech stack, architecture
│   ├── roadmap.yaml                 # Feature roadmap and sprint planning
│   └── current-feature.yaml         # Active feature scope and tasks
├── .claude/settings.json            # Plugin reference (auto-created on install)
└── CLAUDE.md                        # Updated with Archflow section by onboarding
```

---

## External Tool Integration

The `/archflow setup-mcp` command configures MCP servers to connect with your existing tools:

| Tool | Transport | Purpose |
|------|-----------|---------|
| Jira | HTTP/OAuth | Import epics, stories, sprint data |
| Confluence | HTTP/OAuth | Import documentation |
| Notion | HTTP/OAuth | Import pages and databases |
| Linear | HTTP/OAuth | Import issues, projects, cycles |
| GitHub | HTTP/OAuth | Import issues, PRs, project boards |
| Google Drive | stdio/OAuth | Import Google Docs and Sheets |
| Slack | HTTP/OAuth | Import context from channels/threads |
| Trello | stdio/env | Import boards, lists, cards |

These integrations are primarily used during `/archflow onboard` (Phase A: Context Import) to pull existing project context into Archflow's format.

---

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (latest version)
- Git
- Node.js (for some MCP servers)

---

## Contributing

Contributions are welcome. Areas of interest:

- **New agents** — Add specialized agents in `agents/` following the existing format
- **Phase improvements** — Refine phase instructions in `.archflow/phases/`
- **MCP registry** — Add tool integrations in `skills/archflow/mcp-registry.yaml`
- **Bug fixes** — Open an issue or submit a PR

---

## Community & Support

- **Bug reports:** [GitHub Issues](https://github.com/AZidan/archflow/issues)
- **Feature requests:** [GitHub Issues](https://github.com/AZidan/archflow/issues)
- **Questions:** [GitHub Discussions](https://github.com/AZidan/archflow/discussions)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Archflow: Because building software deserves structure, not chaos.**

[Back to top](#archflow)

</div>
