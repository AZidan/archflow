<!-- archflow:start (managed by Archflow 2.4.0; merge into AGENTS.md) -->
# Archflow

This project is managed by Archflow, a phase-based development workflow. State lives in `.archflow/`.

**At the start of every session, read `.archflow/instructions.md` before doing anything else.** Then run `ARCHFLOW_HOST=generic node .agents/archflow/hooks/check-upgrade.mjs` and `ARCHFLOW_HOST=generic node .agents/archflow/hooks/telemetry.mjs </dev/null`, and relay anything either prints: they are the upgrade check and usage telemetry other hosts run automatically at session start.

Archflow actions are skills under `.agents/skills/`. Run one when the user asks for it by name:

- `$archflow-autopilot` — Run queued release stories unattended on one branch, after a blocker interview
- `$archflow-contract` — The release's API contract architecture, and per-story endpoint specs that clear a story's contract gate
- `$archflow-design` — The project's design system, and per-story screen design that clears a story's design gate
- `$archflow-doctor` — Check the environment and project state — what Archflow needs, what is missing, and how to fix it
- `$archflow-feature` — Add a story (name or description), or pull a backlog story into the active release
- `$archflow-groom` — Detail or refine a story: acceptance criteria, subtasks, gates. Works on a backlog stub or a story already in a release
- `$archflow-help` — Every Archflow command with a one-line usage note, and a short primer on how Archflow works
- `$archflow-init` — Set up Archflow in a NEW, empty project — creates .archflow/ and starts at Phase 1
- `$archflow-issue` — Record a defect against a story in the active release, list what is open, or defer a minor one to the backlog
- `$archflow-migrate` — Upgrade a v1.0 archflow-onboarded project (sprints) to schema v2.0 (releases) — dry-run first, then apply
- `$archflow-mode` — Show or switch ceremony mode: quick (solo, light gates) or full (team, strict gates)
- `$archflow-onboard` — Set up Archflow in an EXISTING codebase — audit code, import context, pick the phase
- `$archflow-release` — Release pipeline: see status, cut a new release, start building it, or ship it
- `$archflow-setup-mcp` — Connect an external tool via MCP (Jira, Notion, Linear, GitHub, SuperDesign, ...)
- `$archflow-status` — Where the project stands: phase, mode, active release, and what to run next
- `$archflow-studio` — [Beta] Start (or stop) Archflow Studio for the current project and open it in the browser
- `$archflow-telemetry` — Show or change anonymous usage telemetry (on by default; this is how to opt out)

Specialised roles are skills named `archflow-agent-<role>`. When a phase delegates to a role, load that skill and perform the role yourself, one role at a time. Phase 3 runs `ui-engineer` then `api-engineer` serially against the same API contract.

Never push to or merge into `main` yourself; a git pre-push guard enforces this. Nothing advances a phase without explicit user approval.
<!-- archflow:end -->
