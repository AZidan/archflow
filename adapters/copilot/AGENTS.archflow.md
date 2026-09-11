<!-- archflow:start (managed by Archflow 2.3.2; merge into AGENTS.md) -->
# Archflow

This project is managed by Archflow, a phase-based development workflow. State lives in `.archflow/`.

**At the start of every session, read `.archflow/instructions.md` before doing anything else.** The SessionStart hook injects it; this line is the fallback.

Archflow actions are skills. Run one when the user asks for it by name:

- `/archflow-autopilot` — Run queued release stories unattended on one branch, after a blocker interview
- `/archflow-contract` — The release's API contract architecture, and per-story endpoint specs that clear a story's contract gate
- `/archflow-design` — The project's design system, and per-story screen design that clears a story's design gate
- `/archflow-doctor` — Check the environment and project state — what Archflow needs, what is missing, and how to fix it
- `/archflow-feature` — Add a story (name or description), or pull a backlog story into the active release
- `/archflow-groom` — Detail or refine a story: acceptance criteria, subtasks, gates. Works on a backlog stub or a story already in a release
- `/archflow-init` — Set up Archflow in a NEW, empty project — creates .archflow/ and starts at Phase 1
- `/archflow-issue` — Record a defect against a story in the active release, list what is open, or defer a minor one to the backlog
- `/archflow-migrate` — Upgrade a v1.0 archflow-onboarded project (sprints) to schema v2.0 (releases) — dry-run first, then apply
- `/archflow-mode` — Show or switch ceremony mode: quick (solo, light gates) or full (team, strict gates)
- `/archflow-onboard` — Set up Archflow in an EXISTING codebase — audit code, import context, pick the phase
- `/archflow-release` — Release pipeline: see status, cut a new release, start building it, or ship it
- `/archflow-setup-mcp` — Connect an external tool via MCP (Jira, Notion, Linear, GitHub, SuperDesign, ...)
- `/archflow-status` — Where the project stands: phase, mode, active release, and what to run next

Specialised custom agents live in `.github/agents/` and are dispatched as subagents. Phase 3 runs `ui-engineer` and `api-engineer` in parallel against the same API contract.

Nothing advances a phase or merges to `main` without explicit user approval.
<!-- archflow:end -->
