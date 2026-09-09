# Security

Archflow is a set of instructions that drive Claude Code inside your own repository. It has no
server, stores no credentials, and sends nothing anywhere. Its security surface is therefore about
three things: what it installs, what it reads, and what it runs.

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

## Credentials

Archflow never stores credentials in its own files. Acceptance test accounts go in
`.archflow/test-accounts.yaml`, which is gitignored; `.archflow/test-accounts.example.yaml` is the
committed template. No agent definition may contain a real credential, and none does.

## Reporting a vulnerability

Open a private security advisory on the repository, or email the maintainer listed in
`.claude-plugin/marketplace.json`. Please do not open a public issue for anything exploitable.

Include what you found, how to reproduce it, and what an attacker gets. You will get an
acknowledgement within a few days.
