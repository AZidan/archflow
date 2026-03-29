<div align="center">

# Archflow

**Turn Claude Code & Cursor into a structured development team.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Claude Code](https://img.shields.io/badge/Claude%20Code-Framework-blueviolet)](https://docs.anthropic.com/en/docs/claude-code) [![Cursor](https://img.shields.io/badge/Cursor-Plugin-blue)](https://www.cursor.com/) [![Agents](https://img.shields.io/badge/Agents-16+-blue)](https://github.com/AZidan/archflow) [![Phases](https://img.shields.io/badge/Phases-6-green)](https://github.com/AZidan/archflow)

[Website](https://azidan.github.io/archflow/) · [Quick Start](#quick-start) · [How It Works](#how-it-works) · [Phases](#the-phases) · [Agents](#agents) · [Commands](#commands)

<img src="docs/archflow-overview.svg" alt="Archflow Overview" width="700" />

</div>

---

## What is Archflow?

Archflow is a **phase-based AI development framework** for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [Cursor](https://www.cursor.com/). It orchestrates 16+ specialized agents through a structured workflow — from product strategy to production deployment.

Instead of one AI doing everything, each task goes to an agent with deep expertise in its domain. A `product-strategist` defines business goals. A `ux-designer` creates the design system. An `api-contract-architect` locks down API specs. Then `ui-engineer` and `api-engineer` build frontend and backend in parallel — coordinated through file-based handoffs and mandatory approval gates.

Archflow works with any project type — fullstack, frontend-only, backend-only, or mobile — and adapts its phases, agents, and artifact structure accordingly.

---

## Quick Start

### Claude Code

#### 1. Add the Marketplace (one-time)

```bash
claude plugin marketplace add azidan/archflow https://github.com/AZidan/archflow
```

#### 2. Install the Plugin

```bash
claude plugin install archflow --scope project
```

This saves the plugin reference to `.claude/settings.json` in your repo — any team member who clones gets prompted to install automatically.

Free and open source. No lock-in. Uninstall anytime with `claude plugin uninstall archflow`.

#### 3. Start Your Project

Open Claude Code in your project directory:

```bash
cd your-project
claude
```

- **New project?** Archflow starts at Phase 1 (Strategy).
- **Existing codebase?** Run `/archflow onboard` — agents analyze your code, import context from your tools, and generate all artifacts for approval.

#### 4. Develop Features

```
/archflow feature          # Interactive wizard
/archflow feature login    # Quick-add by name
```

Archflow creates the feature branch, breaks it into tasks, and guides implementation through the appropriate agents. Features are filtered by scope — a `backend_only` repo only sees backend-scoped features from the roadmap.

### Cursor IDE

#### 1. Install the Plugin

Copy the `cursor-plugin/` directory from this repo into your Cursor local plugins folder:

```bash
cp -R cursor-plugin ~/.cursor/plugins/local/archflow
```

This installs Archflow as a local Cursor plugin. The plugin includes:

- **Rules** (`rules/archflow-instructions.mdc`) — Always-applied workspace rules that load Archflow's phase-based instructions automatically.
- **Agents** — All 16+ specialized agents available as Cursor sub-agents.
- **Skills** — The `/archflow` slash command and all subcommands.

#### 2. Open Your Project in Cursor

```bash
cd your-project
cursor .
```

Archflow activates automatically via the `rules/archflow-instructions.mdc` file, which is loaded as an always-applied rule in Cursor.

- **New project?** Tell the agent to run `/archflow init` — it starts at Phase 1 (Strategy).
- **Existing codebase?** Tell the agent to run `/archflow onboard` — agents analyze your code and generate all artifacts.

#### 3. Develop Features

Use the same commands as Claude Code — they work identically in Cursor:

```
/archflow feature          # Interactive wizard
/archflow feature login    # Quick-add by name
```

> **Note:** The Cursor plugin uses `.cursor-plugin/plugin.json` instead of `.claude-plugin/plugin.json`, and adds a `rules/` directory with `.mdc` rule files — Cursor's native format for always-applied workspace rules.

---

## How It Works

Building software with AI means context gets lost, quality varies, and the same mistakes repeat. Archflow fixes this with three ideas:

- **Specialized agents** — A UX designer doesn't write backend code. An API engineer doesn't make design decisions. 16+ agents, each scoped to one domain.
- **File-based handoffs** — Context survives between conversations. Agents communicate through artifacts, not chat — so nothing gets lost when a session ends.
- **Phase gates** — 6 phases from strategy to deployment. Nothing moves forward without your approval. No skipped steps. No autonomous decisions on what ships.
- **Contract-first development** — API contracts are defined before implementation. Frontend and backend build against the same spec, so they never disagree.
- **Focused context** — Each phase loads only what the active agents need. Less noise, better results.
- **Acceptance testing** — Features aren't done until they pass acceptance testing against your roadmap criteria.

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

## Works with Existing Projects

Most AI workflows assume you're starting from scratch. Archflow meets you where you are.

Run `/archflow onboard` and it dispatches up to 9 agents in parallel to deeply analyze your codebase. They import context from tools you already use (Jira, Notion, Linear, GitHub, Confluence, Slack), reverse-engineer your design system and API contracts, and drop you into the right phase based on what already exists.

```
Phase A: Interactive Collection     Answer 5 questions about your stack and context sources

Phase B: Autonomous Agent Dispatch  Up to 9 agents analyze your codebase in parallel:
                                    codebase audit → doc deep-dive → design extraction →
                                    route/API extraction → product-strategist → ux-designer →
                                    api-contract-architect → dsl-generator → feature-planner

Phase C: Synthesis & Presentation   Artifacts generated and presented for your approval
```

The onboarding agents generate ready-to-use `project-context.md`, `roadmap.yaml`, `api-contract.md`, `theme.yaml`, `styled-dsl.yaml`, and `user-flows.md` — all reverse-engineered from your existing code and imported documentation. It also creates or updates your project's `CLAUDE.md` with architecture context derived from the analysis.

**New project?** `/archflow init` starts you at Phase 1 with a clean slate.

---

## Agents

| Phase | Agents |
|-------|--------|
| 1. Strategy & Planning | `product-strategist`, `feature-planner` |
| 2. Design | `ux-designer`, `dsl-generator` |
| 2.25 High-Fidelity (optional) | SuperDesign MCP |
| 2.5 API Architecture | `api-contract-architect` |
| 3. Implementation | `ui-engineer`, `api-engineer`, `qa-engineer`, `pm-maestro-reviewer` |
| 4. Quality & Optimization | `code-reviewer`, `performance-optimizer`, `pm-maestro-reviewer` |
| 5. Launch & Operations | `devops-engineer`, `post-launch-analyst` |
| 6. Enhancement | `i18n-engineer`, any agent as needed |

---

## Commands

| Command | What it does |
|---------|-------------|
| `/archflow` | Show available subcommands and current project status |
| `/archflow init` | Initialize a new project at Phase 1 |
| `/archflow onboard` | Analyze an existing codebase and generate all artifacts |
| `/archflow feature` | Add a feature, create branches, assign agents |
| `/archflow setup-mcp` | Connect external tools (Jira, Notion, Linear, GitHub, etc.) |

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

<details>
<summary><strong>File Structure</strong></summary>

Archflow is distributed as a Claude Code plugin marketplace and a Cursor local plugin. The plugin contains all framework code; your project only stores state files.

### Marketplace (this repo)

```
archflow/
├── .claude-plugin/marketplace.json  # Marketplace registry
├── plugin/                          # Claude Code plugin
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
├── cursor-plugin/                   # Cursor IDE plugin
│   ├── .cursor-plugin/plugin.json   # Cursor plugin manifest
│   ├── rules/                       # Cursor-specific rules
│   │   └── archflow-instructions.mdc  # Always-applied workspace rules
│   ├── hooks/hooks.json             # SessionStart hook
│   ├── agents/                      # 17 specialized agent definitions (shared)
│   ├── skills/archflow/             # Slash command implementations (shared)
│   └── .archflow/                   # Framework instructions and phase files (shared)
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

</details>

<details>
<summary><strong>External Tool Integration</strong></summary>

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

These integrations are primarily used during `/archflow onboard` to pull existing project context into Archflow's format.

</details>

---

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (latest version) **or** [Cursor IDE](https://www.cursor.com/) (latest version)
- Git
- Node.js (for some MCP servers)

---

## Contributing

Contributions are welcome. Areas of interest:

- **New agents** — Add specialized agents in `agents/` following the existing format
- **Phase improvements** — Refine phase instructions in `.archflow/phases/`
- **MCP registry** — Add tool integrations in `skills/archflow/mcp-registry.yaml`
- **Cursor plugin** — Improve the Cursor integration in `cursor-plugin/`
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
