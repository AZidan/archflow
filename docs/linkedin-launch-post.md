Over the past few months, I've used Claude Code to build 10+ projects. Not experiments. Real apps, real backends, real deployments.

Every one of them was built with the same framework. One I kept refining with each project. Pain points became fixes. Context losses became guardrails. Quality gaps became phase gates.

Today I'm open-sourcing it.

Archflow turns Claude Code into a structured development team:

- 16+ specialized agents, each scoped to one domain (a UX designer doesn't write backend code; an API engineer doesn't make design decisions)
- 6 phases from strategy to deployment. Nothing ships without you approving each gate
- File-based handoffs. Agents communicate through artifacts, not messages. The API contract becomes the single source of truth that both frontend and backend build against
- Dynamic phase loading. Each agent only gets the context it needs for its current phase. No bloated context windows, no wasted tokens

The biggest bottleneck across those 10+ projects was never intelligence. It was context management. Archflow gives each agent the right information at the right time and nothing else.

It works on existing codebases too. Run `/archflow onboard` and it dispatches up to 9 agents in parallel. They audit your code, import docs from Jira/Notion/Linear/GitHub/Slack, reverse-engineer your design system and API contracts, and drop you into the right phase.

Starting fresh? `/archflow init`.
Adding a feature? `/archflow feature` handles branches, tasks, and agent assignment.

Fullstack, frontend-only, backend-only, mobile. It adapts.

MIT licensed. Two commands to install:

`claude plugin marketplace add archflow https://github.com/AZidan/archflow`
`claude plugin install archflow --scope project`

Repo link in comments.
