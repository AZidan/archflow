# Acceptance Review Report
## Release: v2-5-0 | Story: S9-04 | Date: 2026-10-04

### Verdict
**ACCEPTED**

AC3 is accepted on the user's decision (D5, D11), not on what the repo currently ships. The
CHANGELOG and Studio build sync is still outstanding (see Recommendation).

### How this was tested
- **Tooling**: chrome-devtools MCP (Chromium) driving the live page, plus the project's own pytest
  suite. Both were already available. Nothing was installed.
- **Commands**: `python3 -m pytest -q tests/test_site_publishing.py` gave `11 passed in 0.21s`.
  Browser checks were DOM reads and clicks run with `evaluate_script`.
- **Environment**: `docs/` served by the orchestrator at `http://127.0.0.1:8765/index.html`, branch
  `site/studio-first-homepage` at `eb79222`. Desktop at 1440x900. Mobile emulated at 390x844 (DPR 3,
  touch). Isolated browser context.
- **Design system**: `.archflow/design-systems/{design_system}.md` does not exist in this repo.
  The story only changes copy on the existing visual system, so this is not a defect.

### Summary
- **Total acceptance criteria**: 4
- **Passed**: 4 · **Failed**: 0 · **Blocked**: 0

### Criterion results
- **AC 1**: Homepage hero leads with Studio
  - **Result**: PASS
  - **Evidence**: `<title>` reads "Archflow Studio: your coding agent, run from a board". The first
    content section is the hero, with the badge "ARCHFLOW STUDIO · BETA", the H1 "Your coding
    agent, run from a board." and a lede that opens "Archflow Studio turns a repo into…". The
    install block reads `$ npx archflow install`, then "Then /archflow:studio in your project". The
    banner reads "Archflow Studio now runs on every supported coding agent →" and links to `#studio`.
    The first nav item is "Studio". The hero renders correctly at 390px: no horizontal overflow
    (scrollWidth 390), and the badge, H1 and install block are all in the first viewport.
- **AC 2**: Studio guide matches current Studio behavior
  - **Result**: PASS
  - **Evidence**: `docs/guides/studio.md` agrees with `plugin/commands/studio.md` on every point
    below.
    - Default port 3456.
    - The `status`, `stop` and `port <n>` verbs, all idempotent. `stop` on a stopped server is a
      no-op.
    - The server runs detached and outlives the session.
    - Log path `~/.archflow/studio/logs/studio-<port>.log` and its `[mode]` line.
    - Full mode is the default. Companion mode is opt-in through `STUDIO_MODE=companion`, using
      `--resume <id> --fork-session`, and nothing typed in Studio lands back in the terminal.
    - A session context older than 12 hours degrades to full mode.
    - `STUDIO_SESSION_CONTEXT` is per session.
    - A foreign process on the port is never killed, and `port 3457` is suggested.
    - A Studio left from an earlier session is adopted.

    The homepage Studio section matches too ("if you opt in it can start from your running
    session's history, forked"). The one difference is the host behaviour on non-Claude hosts,
    covered under AC3.
- **AC 3**: Page states which hosts Studio supports, consistent with the CHANGELOG
  - **Result**: PASS (met by decision D5/D11)
  - **Evidence**: The banner, hero, Studio section and the guide's "Hosts" section all say Studio
    runs on every supported host: in-panel on Claude Code, and through the user's own terminal
    session on OpenAI Codex, GitHub Copilot CLI, Cursor, Gemini CLI and OpenCode. The old
    contradicting line ("Codex is next, then OpenCode, then the rest") is gone (D5, D7), and no
    text reads "Claude Code only" or "Claude Code today". The page is internally consistent.
  - **Pending, not a rejection**: `CHANGELOG.md` 2.4.0 still says "`/archflow:studio` stays Claude
    Code only". `plugin/commands/studio.md` also still says chat forwarding to the terminal "is not
    built yet". Under D11 the user keeps the every-host claim and will sync the Studio build and the
    CHANGELOG before shipping. Until that sync lands, the shipped page claims more than this repo's
    Studio does.
- **AC 4**: Page passes the archflow-marketing guardrails (no pricing hints, no total command count,
  one-argument marketplace command, install command present)
  - **Result**: PASS
  - **Evidence**: All checks were run against the rendered page text:
    - **Pricing**: no match for pric, paid, $N, "per month" or trial. "Free" appears once: "The
      Archflow framework is free and MIT licensed, and open source." It is attached to the
      framework, not to Studio (D12). The Studio badges say "BETA" only, in both the hero and the
      `#studio` section. The meta description says "The Archflow framework is free and MIT."
    - **Command count**: no total command count. The command list is enumerated ("init, onboard,
      design, …").
    - **Marketplace command**: the only marketplace command is `claude plugin marketplace add
      AZidan/archflow`, the one-argument form.
    - **Install command**: `npx archflow install` appears in the hero, the `#install` block and the
      copy-button payload (`copyInstallCommands` writes `npx archflow install`).
    - **Stale command**: `npx archflow studio` appears nowhere in the served HTML, and a grep of
      `docs/` and `README.md` (excluding reports) found no match.
    - **Guardrail 7** ("Studio stays Claude Code only") is overridden by D5.
    - "17 specialized agents" is guardrail 6. It is already open as I-2, the user's call, and was
      not re-filed.

### Prior issues re-checked
- **I-1**: Fixed. All 8 subtasks read `completed: true`.
- **I-3**: Fixed. JSON-LD `softwareVersion` is 2.4.0, the same as `plugin/.claude-plugin/plugin.json`.
  All three FAQ questions are on the page. Every answer sentence is on the page, except the
  `quick`/`full` cards and the two compare links, which the JSON-LD flattens to prose with the same
  content.
- **I-4**: Fixed. The logo's `href="#"` no longer throws. Clicking it from scrollY 3000 returns to
  0. Every in-page link points to an existing target (10/10). All six nav links scroll their
  section to about 121px from the top, which is just below the fixed nav.
- **I-5**: Fixed. At 390px the dismiss button spans x 350–382 and the banner text ends at x 334.7.
  No text rect intersects the button.
- **I-6**: Fixed. The proof bar reads "This repo runs on it too." and links to the repo's
  `.archflow/`.
- **I-7**: Fixed. `tests/test_site_publishing.py:168-177` asserts that the homepage
  `softwareVersion` equals `plugin.json` (part of the 11 passing tests).

### Blocking defects (must fix)
None.

### Non-blocking observations
1. **CHANGELOG and Studio build sync (D11).** Before v2.5.0 ships, `CHANGELOG.md` (2.4.0, "stays
   Claude Code only") and `plugin/commands/studio.md` ("forwarding to your terminal is not built
   yet") must be brought in line with the every-host claim on the page and in the guide. Otherwise
   the published site contradicts the shipped plugin. This is a pre-ship task the user owns, not a
   defect in this story.
2. **Proof figure (D8).** "1,100+ projects" is the sum of daily unique cloners. Repeat cloners are
   counted more than once, so the figure is an upper bound.
3. **"Start it" in the guide is Claude-only.** It shows `claude` then `/archflow:studio`. Starting
   Studio from another host is not shown. This follows from the same D11 sync.
4. **Console (pre-existing, not introduced by this story).** The console shows a Tailwind CDN
   production warning and three DevTools issues: a CSP-blocked resource, Quirks Mode in a subframe
   (the document itself has `<!DOCTYPE html>`), and one unlabeled form field. There are no
   JavaScript errors.

### Recommendation
Proceed: S9-04 can be marked done. Before v2.5.0 ships, the user must still sync the Studio build,
the CHANGELOG and `plugin/commands/studio.md` with the every-host claim, per D11.
