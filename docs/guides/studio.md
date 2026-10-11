---
layout: guide
title: "Using Archflow Studio"
description: "Run the whole Archflow workflow in a browser: onboard a project, groom a backlog, cut a release, and watch the agents work, without living in the terminal."
permalink: /guides/studio/
---

Studio is a local workspace over the same `.archflow/` files the CLI uses. The roadmap becomes a
board, the release becomes a pipeline, and the agents work in front of you instead of behind a
scroll of text.

It is the terminal-free path. After Archflow is installed, one command opens it and everything
else, including onboarding an existing codebase, happens in the browser.

**Beta.** Features are still landing. It is already what ships Studio itself, so it is not fragile,
but it is not finished either. [Tell us what's missing](https://github.com/AZidan/archflow/issues).

---

## Start it

```bash
cd your-project
claude
```

```
/archflow:studio
```

That prints a URL, `http://localhost:3456` by default, and offers to open it. On another coding
agent, open it in the project and use that host's spelling of the command; see [Hosts](#hosts).

The server is **detached on purpose**: it outlives the session that started it, so you can close
the terminal and leave Studio open beside your work. That also means it keeps running until you
stop it.

```
/archflow:studio status     # is it running, and for which project?
/archflow:studio stop       # shut it down
/archflow:studio port 3457  # use a different port
```

All three are safe to run twice. Running `stop` on something already stopped is a no-op, not an
error.

---

## The first run

Studio reads the folder you started it in. What it shows depends on what it finds.

**A project with no `.archflow/`.** Studio offers to onboard it. One button runs
`/archflow:onboard` for you: up to nine agents audit the code, import context from Jira, Notion,
Linear, GitHub or Slack if you have those connected, reverse-engineer your design system and API
contracts, and put you in the right phase. You approve the artifacts; nothing is written until you
do.

**A project from Archflow v1.0.** Studio detects the old sprint schema and offers a one-button
migration to v2.0. It backs up `.archflow/` to `.archflow/backup-v1/` first, splits sprints into
releases, moves unstarted stories to the backlog, archives completed sprints into `history.yaml`,
and demotes epics to labels. The run happens in the chat panel; Studio confirms success by
re-reading the project rather than by parsing the output.

**A blank directory.** Ask the assistant for `/archflow:init` to start at Phase 1.

<figure>
  <video controls playsinline preload="none"
         poster="{{ site.baseurl }}/assets/video/studio-onboard-poster.jpg"
         aria-label="Onboarding an existing codebase from Archflow Studio, start to finish.">
    <source src="{{ site.baseurl }}/assets/video/studio-onboard.mp4" type="video/mp4">
    Your browser can't play this clip.
    <a href="{{ site.baseurl }}/assets/video/studio-onboard.mp4">Download it instead</a>.
  </video>
  <figcaption>Onboarding an existing codebase, start to finish. Recorded from the app, 3m20s: Phase B genuinely takes that long.</figcaption>
</figure>

---

## What's in the window

A rail on the left, a work area in the middle, a chat panel on the right.

<figure>
  <video controls playsinline preload="none"
         poster="{{ site.baseurl }}/assets/video/studio-release-poster.jpg"
         aria-label="Cutting a release in Archflow Studio and starting it, recorded from the app.">
    <source src="{{ site.baseurl }}/assets/video/studio-release.mp4" type="video/mp4">
    Your browser can't play this clip.
    <a href="{{ site.baseurl }}/assets/video/studio-release.mp4">Download it instead</a>.
  </video>
  <figcaption>Cutting a release from groomed stories, then starting it. Recorded from the app, 1m24s.</figcaption>
</figure>

| Rail | What it holds |
|------|---------------|
| **Strategy** | `project-context.md`: goals, tech stack, architecture decisions |
| **Backlog** | Unscheduled scope: stubs and groomed `ready` stories |
| **Releases** | The pipeline, plus shipped releases on a timeline |
| **Design** | Wireframes and hi-fi screens from `design-artifacts/` |
| **Contract** | `docs/api-contract.md`, the single source of truth for both sides |
| **History** | What shipped, when, and what it touched (appears after your first ship) |

Destinations appear as the project earns them. History shows up only once something has shipped.
In `quick` mode the rail collapses, because most of it has nothing to hold yet.

The **release workspace** has two views. **Board** is a kanban of the active release: stories move
through Ready, In progress, Review and Done, and each card opens to its acceptance criteria and
subtasks. **Release** is the same release as a document, with its gates and its ship ritual.

---

## The chat panel

This is where the agents run. It streams the same work the CLI would do, with tool calls, sub-agent
activity, and todo lists rendered as cards rather than as text.

<figure>
  <video controls playsinline preload="none"
         poster="{{ site.baseurl }}/assets/video/studio-idea-poster.jpg"
         aria-label="An idea becoming a groomed story with acceptance criteria, in the Archflow Studio chat panel.">
    <source src="{{ site.baseurl }}/assets/video/studio-idea.mp4" type="video/mp4">
    Your browser can't play this clip.
    <a href="{{ site.baseurl }}/assets/video/studio-idea.mp4">Download it instead</a>.
  </video>
  <figcaption>An idea becoming a groomed story with acceptance criteria. Recorded from the app, 1m30s.</figcaption>
</figure>

When an agent needs a decision, it asks in the panel and you answer inline: the question renders as
a card with real options, not as a wall of prose you have to reply to in sentences.

**Full mode is the default.** On Claude Code, Studio's chat runs its own `claude` process,
unrelated to the terminal session you started it from. `/archflow:studio status` reports the mode.

**Companion mode is opt-in.** Set `STUDIO_MODE=companion` in your Claude Code session *before*
running `/archflow:studio`, and Studio's chat starts with *that conversation's history*, on a branch
(`claude --resume <id> --fork-session`). You don't re-explain the project to a second assistant.
Nothing you type in Studio lands back in your terminal, and Studio says so itself.

```bash
export STUDIO_MODE=companion
```

If you opted in but the session context is missing, malformed or more than 12 hours old, Studio
falls back to full mode. That is a stated degrade, not a failure, and the `[mode]` line in the
startup log says which mode it picked and why.

Two sessions that each want their own Studio need `STUDIO_SESSION_CONTEXT` set to a different path
each, since the handoff file is one per machine and the most recently started session owns it.

---

## Hosts

Studio runs on every supported coding agent: Claude Code, OpenAI Codex, GitHub Copilot CLI, Cursor,
Gemini CLI, OpenCode, and any agent that reads `AGENTS.md` and Agent Skills (the generic package).
`npx archflow@latest install` sets it up with the rest of Archflow for each host.
Start it with that host's spelling of the command:

| Host | Command |
|---|---|
| Claude Code, Gemini CLI | `/archflow:studio` |
| OpenAI Codex, generic `AGENTS.md` + Agent Skills | `$archflow-studio` |
| GitHub Copilot CLI, Cursor, OpenCode | `/archflow-studio` |

The board, releases, stories and files work the same everywhere. The chat panel differs:

- **Claude Code:** the agent runs in Studio's own chat panel (full mode, or companion if you opt in).
- **Every other host: forward mode.** Studio runs no agent. You compose in the panel, Studio spells
  the command the way that host expects, and Send copies it for you to paste into the terminal
  session you already have open, so you see every prompt before it goes.

`/archflow:studio status` reports which host Studio resolved and what its chat does, for example
`host codex, chat forward`. Studio picks the host from the Archflow installs it finds in the
project; you can switch it from inside Studio, and the choice is saved per project.

---

## Privacy

Studio binds to `127.0.0.1` and enforces an origin allowlist that covers the WebSocket upgrade, so
a hostile page in another tab cannot reach it. There is no hosted service and no account, and
exposing it beyond loopback is not supported. Your code and your credentials never leave the
machine. The only thing that does is the anonymous usage telemetry below, and you can turn it off.

The coding-agent sessions Studio drives — Claude Code or any other supported host — send Archflow's
anonymous usage telemetry like any other session: which `/archflow:*` commands run, the host,
version, phase and mode. Never project names, paths, file contents or command arguments.
`/archflow:telemetry off`, `npx archflow telemetry off` or `DO_NOT_TRACK=1` turns it off everywhere.
On a host with no native chat channel, a command you copy from Studio and paste into that host's own
session is reported by that host, not by Studio — Studio never sends the copied text itself, only
that a copy happened and which command it was.

Studio also sends its own anonymous events, through the same machine-wide setting: when it starts
and opens a project, when a view is opened (as its route template only — never a project path,
story id, or release name), when you run an onboard, migrate or cut-a-release action from its UI or
copy a command to paste elsewhere, and when you change which host it drives. Nothing rendered on
screen is ever captured. [`SECURITY.md`](https://github.com/AZidan/archflow/blob/main/SECURITY.md#telemetry)
lists every event and field.

---

## When something is wrong

A detached server has nowhere to print, so its output goes to a log:

```bash
cat ~/.archflow/studio/logs/studio-3456.log
```

The `[mode]` line near the top says which chat mode it resolved and, if it degraded, why.

**Port already in use.** Studio never kills a process it does not recognise. If something else owns
the port it tells you what, and suggests `/archflow:studio port 3457`.

**A Studio from an earlier session.** It gets adopted rather than replaced, which is the idempotent
case working. In full mode its chat is its own `claude`. If that earlier session had opted into
companion mode, its chat is still wired to whichever session owned the context file when it
started; `/api/chat/session` says which.

**The board is read-only.** The project is still on the v1.0 schema. Take the migration the banner
offers.

---

## Related

- [Onboarding an existing codebase](https://archflowai.dev/guides/existing-codebase/): what
  `/archflow:onboard` does to your repo
- [Starting a new project](https://archflowai.dev/guides/new-project/): the phases in order
- [Taking a prototype to production](https://archflowai.dev/guides/prototype-to-product/)
