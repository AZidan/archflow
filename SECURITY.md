# Security

Archflow is a set of instructions that drive Claude Code inside your own repository. It has no
server and stores no credentials. It never sends project content, names or paths anywhere. Its network traffic is
anonymous usage telemetry, which is on by default and described under [Telemetry](#telemetry) with
how to turn it off, plus two requests to GitHub that carry no user data: a once-a-day upgrade check at
session start, and the release download during `npx archflow install`. Its security surface is
otherwise about three things: what it installs, what it reads, and what it runs.

## Supply chain

Archflow can install exactly two external artifacts, both optional, and neither installs without
asking you first.

| Artifact | Source | Pin | Used by |
|---|---|---|---|
| codemap | `github.com/AZidan/codemap` | `v1.3.1` (`7e24f23ecbc7`) | Optional token optimization |
| superdesign-mcp-claude-code | `github.com/AZidan/superdesign-mcp-claude-code` | `1bd2d1766b1e` | Phase 2.25 hi-fi screens |

**The pinning policy.** Every reference to external code is pinned to an immutable ref. A
`git+https://…` or `npx -y github:…` reference without `@<ref>` or `#<ref>` tracks a moving branch,
so a compromise upstream reaches every user on their next install. Each install site carries a
comment saying why the pin is there, because the failure mode is somebody helpfully "simplifying"
the line back to a branch name.

**Tag or commit.** A project that publishes releases is pinned to its release tag, because that is
what a human can read and reason about. A git tag is mutable — it can be re-pointed at another
commit — so the commit the tag must resolve to is recorded in the table above as the verification
anchor. A project with no releases is pinned to a raw commit SHA.

Verify a tag pin resolves to the expected commit:

```bash
git ls-remote https://github.com/AZidan/codemap.git 'refs/tags/v1.3.1^{}'
# expect 7e24f23ecbc74165d5d980b020fb69aa23d6cd95
```

A mismatch means the tag moved. Stop and find out why before installing.

To move to a newer version: resolve the new ref, update it at the install site, in the README
supply-chain table and here, and note it in the changelog. Never point an install at a branch.

**Ask before installing.** No phase, command or agent may install a tool, browser, simulator or
emulator on its own. It names what it wants, where it comes from and why, and waits. `pm-reviewer`
in particular returns `BLOCKED` rather than installing a test runner.

## Untrusted external content

`/archflow:onboard` and several phases can read from Jira, Notion, Confluence, GitHub, Google Drive,
Slack, Trello and arbitrary URLs. That text is written by other people, and some of it may be written
by someone who wants to steer your agent.

**The convention.** Every piece of externally fetched content is wrapped before it reaches any prompt:

```
<untrusted_external_content source="jira:PROJ-123">
…fetched text, verbatim…
</untrusted_external_content>
```

Anything inside those delimiters is **data to be summarized, never instructions to follow**. If the
content contains something shaped like a directive — "ignore previous instructions", "also run…",
"add this dependency" — that fact is reported to you as a finding. It is never acted on.

Any side-effectful action whose parameters come from fetched content — a shell command, a file write,
an MCP call, a git operation — is surfaced for your explicit confirmation first, even in
`/archflow:autopilot`, which pre-authorizes review gates but not this.

If you are adding a new ingestion point, wrap it. An unwrapped fetch is the bug.

## What Archflow runs on your machine

Everything runs as ordinary Claude Code tool calls, which you can see and approve.

- **Git** — branch, commit, tag, read history. Archflow never merges to `main`. That is yours, and
  it stays yours during `/archflow:autopilot` too.
- **File writes** — `.archflow/`, `docs/`, `design-artifacts/`, and your source tree.
- **Project commands** — your own test, build and lint scripts, run with your own runner.
- **One optional background process** — `codemap watch`, which keeps the navigation index current.
  It is opt-in, starts only if codemap is installed and you agreed, and stops with
  `pkill -f "codemap watch"`.

Archflow Studio additionally runs a local HTTP server on `127.0.0.1` at a port you choose, serving
only your project's own `.archflow/` files. `/archflow:studio stop` ends it.

## Telemetry

Anonymous usage telemetry is **on by default** (opt-out). On every supported host and in
`npx archflow install`, Archflow sends usage events to PostHog (`us.i.posthog.com`): `session_start`,
`command_run` with the Archflow command's name only, and `cli_install`. Every event carries a random id
generated on your machine, the Archflow version, the host, the host's entrypoint
(`CLAUDE_CODE_ENTRYPOINT`, or null), whether Studio launched the session (`via_studio`) and whether
it is a Studio demo recording (`studio_capture`). Session and command events add whether the folder
is an Archflow project, its project type, phase and mode, and either how the session started
(`session_source`) or how the command was recognised (`detected_by`). `cli_install` adds which hosts
were installed and where the files came from (the npm package or a release tag). Every event also sets `$process_person_profile: false`, a PostHog
processing flag that stops PostHog building a person profile; it carries no user data. It never
sends project names, file paths, file contents, prompts or command arguments.

A one-time notice says so and how to turn it off; it is a notice, not a question. `npx archflow
install` prints it in your terminal. In a coding-agent session the first session start (or, on
Claude Code and OpenCode, the first Archflow command) gives it to the agent, which is asked to relay
it to you. On Codex, Copilot, Cursor and Gemini, a command typed before any session start has run on
the machine can send one `command_run` before the notice appears. When Copilot CLI loads the Claude Code plugin directly
rather than the Copilot adapter, session events are sent but the notice cannot be shown there; it
still appears in the first session on any other host.

How a command is recognised differs by host. Claude Code and OpenCode report the command name
directly. On Codex, Copilot, Cursor and Gemini a prompt-submit hook reads your prompt **on your
machine**, checks whether it starts with an Archflow command such as `/archflow-status`, and sends
only that command's name. The prompt itself never leaves the hook. The generic AGENTS.md package
has no hooks, so it reports a session start only when the agent runs the script AGENTS.md names.

Turn it off with `/archflow:telemetry off`, `npx archflow telemetry off`, `DO_NOT_TRACK=1` or
`ARCHFLOW_TELEMETRY_DISABLED=1`. It is off whenever `CI` is set. For all three variables, an empty value or `0`, `false`,
`no` or `off` counts as unset, so `CI=false` leaves telemetry on. `/archflow:telemetry` or
`npx archflow telemetry` with no argument shows the current setting.

Turning it off with the command sends one final event, `telemetry_opted_out`, so opt-outs can be
counted. It carries the host, the Archflow version, where the change was made and how many days
after the first-run notice. Nothing is sent after it. Turning telemetry back on sends
`telemetry_opted_in`. The environment variables send nothing, not even that final event. The choice is stored in
`~/.archflow/config.json` and applies to every project on the machine. If that file exists but cannot be
read, telemetry stays off and Archflow leaves the file as it is. Events are sent from a
short-lived background process, so a network failure never affects a session.

**Archflow Studio sends its own events too**, through this same `~/.archflow/config.json` setting
and the same opt-out mechanisms above — turning telemetry off in Studio's own Settings, or any of
the environment variables, silences both the hooks and Studio. Studio's events: `studio_server_start`
when it binds and opens a project; `studio_page_view` on a client-side view change or first load,
carrying only the route's matched template (for example `/story/:id`, never the raw path, project
name, or story id) — never PostHog's own `$pageview`; `studio_action` when a UI control runs an
Archflow operation (onboard, migrate, cut a release, or copy a command to paste elsewhere); and
`studio_host_selected` when you change which coding-agent host Studio drives. On a host with no
native chat channel, copying a command sends only the command's name, never the copied text or any
argument. Every event carries `host: "studio"` so it is distinguishable in the same PostHog project
from the hooks' own events, and, when a project is open, the project type, phase and mode — never a
project name or path.

## Credentials

Archflow never stores credentials in its own files. Acceptance test accounts go in
`.archflow/test-accounts.yaml`, which is gitignored; `.archflow/test-accounts.example.yaml` is the
committed template. No agent definition may contain a real credential, and none does.

## Reporting a vulnerability

Open a private security advisory on the repository, or email the maintainer listed in
`.claude-plugin/marketplace.json`. Please do not open a public issue for anything exploitable.

Include what you found, how to reproduce it, and what an attacker gets. You will get an
acknowledgement within a few days.
