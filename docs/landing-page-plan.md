# Archflow Landing Page Plan

Single-page GitHub Pages site. Clean/modern style.
Primary action: Install the plugin (two terminal commands).
Secondary action: Star on GitHub.
Voice: Technical, confident, direct. Developer-to-developer. No fluff.

## Meta

- **Page title:** Archflow - Turn Claude Code into a structured development team
- **Meta description:** Phase-based AI development framework for Claude Code. 16+ specialized agents, file-based handoffs, and structured phases from strategy to deployment. Works on new and existing projects.
- **Repo:** https://github.com/AZidan/archflow
- **Host:** GitHub Pages

---

## Section 1: Hero (Above the fold)

**Headline:** Turn Claude Code into a structured development team

**Subheadline:** 16+ specialized agents. 6 phases from strategy to deployment. File-based handoffs that keep context intact. For new projects and existing codebases.

**Primary CTA button:** "Install in 2 Commands" (scrolls to install section)
**Secondary CTA button:** "View on GitHub" (links to repo)

**Visual:** Simplified light-theme flow diagram showing agents passing artifacts through phases. Not the existing dark SVG.

---

## Section 2: Proof Bar

Single horizontal bar with key stats:

- 10+ projects
- 16+ agents
- 6 phases
- MIT licensed

No explanation needed. Just the numbers. Quiet confidence strip, not a loud banner.

---

## Section 3: Problem

**Header:** Context gets lost. Quality varies. The same mistakes repeat.

**Body:**
A backend agent makes design decisions it shouldn't. Context disappears between conversations. There's no repeatable process.

You can build faster with AI. But only if the AI knows what it's working on, what it shouldn't touch, and where the last agent left off.

**Origin line:** *Built and refined across 10+ real projects. Every pain point became a fix.*

---

## Section 4: How It Works (3 cards/columns)

**Header:** One agent per job. Files as handoffs. Phases as guardrails.

### Card 1: Specialized Agents
**Icon:** Grid/nodes icon (multiple dots in formation)

16+ agents, each scoped to one domain. A UX designer doesn't write backend code. An API engineer doesn't make design decisions. Deep expertise, not broad awareness.

### Card 2: File-Based Handoffs
**Icon:** Document/arrow icon (file with transfer arrow)

Agents communicate through artifacts, not chat. The API contract becomes the single source of truth. Frontend and backend build against the same spec. Nothing gets lost between conversations.

### Card 3: Phase Gates
**Icon:** Shield/checkpoint icon (gate with checkmark)

6 phases from strategy to deployment. Nothing moves forward without your approval. No skipped steps. No autonomous decisions on what ships.

---

## Section 5: The Phases (Visual/diagram)

**Header:** From idea to production in 6 phases

**Visual:** New light-themed timeline diagram. Horizontal or vertical. Each phase shows name and agent names.

```
Phase 1    Strategy & Planning         product-strategist, feature-planner
Phase 2    Design                      ux-designer, dsl-generator
Phase 2.5  API Architecture            api-contract-architect
Phase 3    Implementation (Parallel)   ui-engineer + api-engineer, qa-engineer
Phase 4    Quality & Optimization      code-reviewer, performance-optimizer
Phase 5    Launch & Operations         devops-engineer, post-launch-analyst
```

**Note below diagram:** Each phase loads only what the active agents need. Less noise. More focused results.

Do NOT include Phase 2.25 (SuperDesign) here. Keep it simple for the landing page.

---

## Section 6: Works on Existing Projects

**Header:** Already have a codebase? Start there.

**Body:** Most AI workflows assume you're starting from scratch. Archflow meets you where you are.

Run `/archflow onboard` and it dispatches up to 9 agents in parallel. They audit your code, import docs from Jira, Notion, Linear, GitHub, and Slack, reverse-engineer your design system and API contracts, and drop you into the right phase.

**3-step visual:**
1. Answer 5 questions about your stack and context sources
2. Up to 9 agents analyze your codebase in parallel
3. Artifacts generated and presented for your approval

**Callout:** New project? `/archflow init` starts you at Phase 1.

---

## Section 7: Commands Reference

**Header:** Four commands. Full workflow.

| Command | What it does |
|---------|-------------|
| `/archflow init` | Initialize a new project at Phase 1 |
| `/archflow onboard` | Analyze an existing codebase and generate all artifacts |
| `/archflow feature` | Add a feature, create branches, assign agents |
| `/archflow setup-mcp` | Connect external tools (Jira, Notion, Linear, GitHub) |

---

## Section 8: Project Types

**Header:** Adapts to what you're building

Four items in a row with icons:
- Fullstack (stack/layers icon)
- Frontend-only (monitor icon)
- Backend-only (server icon)
- Mobile (phone icon)

**Note:** Phases, agents, and roadmap structure adjust based on project type. Set automatically during onboarding.

---

## Section 9: Install CTA (Final section)

**Header:** Two commands to install

```
claude plugin marketplace add archflow https://github.com/AZidan/archflow
claude plugin install archflow --scope project
```

**Trust signals:** Free and open source. No lock-in. Uninstall anytime.

**Primary CTA button:** "View on GitHub"
**Secondary CTA button:** "Star on GitHub"

**Footer:** MIT Licensed. Built by Abdallah Zidan.

---

## Design Notes

- Style: Clean/modern. Light background, sharp typography, generous whitespace
- No dark terminal aesthetic. This is a product page, not a docs site
- Do NOT use the existing `docs/archflow-overview.svg` (dark theme, includes Phase 2.25)
- Create new light-themed visuals: phases diagram, card icons, project type icons
- Code blocks should be styled but not overpowering
- Mobile responsive
- Minimal color palette. One accent color for CTAs
- Cards for the "How It Works" section with subtle borders or shadows
- The proof bar should feel like a quiet confidence strip, not a loud banner

## Visuals To Create

1. **Phases timeline diagram** — Light theme, 6 phases (no 2.25), shows phase name + agents. Horizontal or vertical timeline with connecting lines. Clean, minimal.
2. **How It Works card icons** — 3 inline SVG icons: agents (grid/nodes), handoffs (document/arrow), gates (shield/check). Simple line style, one accent color.
3. **Project type icons** — 4 inline SVG icons: fullstack (layers), frontend (monitor), backend (server), mobile (phone). Same line style as card icons.
4. **Logo** (optional) — Simple wordmark or mark for the hero section. Consider using svg-logo-designer skill.

## Copy Edits Applied (from Seven Sweeps)

- **Sweep 1 (Clarity):** Removed "phase...phases" redundancy from subheadline. Dropped "Building with AI assistants today means" preamble from problem section.
- **Sweep 3 (So What):** Changed "Tokens aren't wasted" to "Less noise. More focused results." (benefit the developer feels, not internal concern). Simplified Card 2 (cut specific filenames, too granular for landing page).
- **Sweep 5 (Specificity):** Removed "3 dependency layers" (internal jargon). Kept all real numbers (16+, 6, 9, 5, 10+).
- **Sweep 7 (Zero Risk):** Added trust signals near install CTA: "Free and open source. No lock-in. Uninstall anytime."
