PASS

# S9-04 Studio-first site repositioning: code review

- Story: S9-04 (release v2-5-0), branch `site/studio-first-homepage`
- Scope: `git diff v2.5.0-autopilot..HEAD -- docs/` (docs/index.html, which replaces the former
  index-next.html, plus docs/guides/studio.md). The QA report in the diff was not reviewed.
- Reviewer: code-reviewer, story_review pass during an unattended autopilot run
- Tests: `python3 -m pytest -q tests/test_site_publishing.py` gave 10 passed

## Design System Compliance

Not applicable. The project is `backend_only` and has no `.archflow/design-system.yaml`. `docs/` is
the Jekyll marketing site, and this story changes only content on the existing visual system. As
instructed, the missing design system is not filed.

## Summary

The change is copy plus one small JS fix, and it holds together. I found no blocking defects and two
minor ones (I-6, I-7).

## What was checked

| Area | Result |
|------|--------|
| Smooth-scroll handler (`docs/index.html` ~L1430-1446) | Correct. A bare `#` now scrolls to the top, and `querySelector` is wrapped in try/catch. Checked in the browser at http://127.0.0.1:8765: the logo click went from scrollY 3000 to 0, `#autopilot` scrolled to its section, and no page errors were logged. Every `href="#x"` on the page resolves to an existing id. There are no duplicate ids (the `id="phases"` match inside an HTML comment is not an element). |
| PostHog / analytics | The ANALYTICS block through `</body>` is byte-identical to both the previous `index.html` and the former `index-next.html`. The DNT early return, the `posthog.init` options and all 7 capture hooks are unchanged. Every element id or selector the hooks depend on (`studio`, `start`, `studio-video`, `onboard-demo`, `install`, `[data-tabs="start"]`, `details.faq`, `[data-ph]`, `copyInstallCommands`) is still present. `window.posthog` loads, and the only console warning is the existing Tailwind CDN notice. |
| Security | The only external script is `cdn.tailwindcss.com` and the only iframe is joinbox, both already there before this change. Every `target="_blank"` link has `rel="noopener"`, including the new SECURITY.md link. The `phc_` value is PostHog's public project key, which is meant to sit in client-side code. It is not a secret. |
| JSON-LD | Both blocks parse (SoftwareApplication and FAQPage). The FAQ answers match the visible copy. The version value has a forward-drift risk (I-7). |
| Accessibility | The heading order is h1, then h2, then h3, with no skipped levels. The banner close button keeps `aria-label="Dismiss announcement"` and its SVG is `aria-hidden`. The new link text "What is sent" makes sense next to the telemetry sentence around it. |
| Claims vs repo | Telemetry copy ("code, prompts, paths or project names"; `/archflow:telemetry off`, `npx archflow telemetry off`, `DO_NOT_TRACK=1`) matches SECURITY.md#Telemetry. The Studio event list in the guide (opens a project, route template, onboard/migrate/cut-a-release/copy, host change) matches SECURITY.md. The guide's companion-mode description (opt-in through `STUDIO_MODE=companion`, full mode by default, degrade after 12 hours, `status` reporting the mode) matches `plugin/commands/studio.md` and `resolveMode` in `plugin/server/server.mjs`. |
| Decisions | D5: the "Codex is next" line is gone and the page claims Studio runs on every host. D7: no ordering is given. D8: one figure, "1,100+", with the source and upper-bound caveat recorded in an HTML comment. D10: the hero says `npx archflow install`, then `/archflow:studio`, and `npx archflow studio` is gone. D11: the CHANGELOG is untouched and not filed here. D12: the Studio badge says "Beta" only, and "free and MIT" is said of the framework. "17 agents" is not re-filed because it is already open as I-2. |

## Findings

### I-6 (minor): "This repo is one of them." has an unclear referent
`docs/index.html:480`. The link used to read "One of the five is this repo.", pointing back to the
"5 production codebases" figure. Two plural nouns now sit closer to the link than "1,100+ projects":
the stack list ("NestJS, Next.js, ...") and "6 coding agents". Read in order, the sentence suggests
this repo is a stack or a coding agent.
Expected: the link names its own antecedent, for example "This repo is one of those projects." or
"One of them is this repo's own `.archflow/`."

### I-7 (minor): JSON-LD `softwareVersion` is a hand-kept literal that will be wrong once this release ships
`docs/index.html:99`. `"softwareVersion": "2.4.0"` matches `plugin/.claude-plugin/plugin.json`
today. This story belongs to release v2-5-0, though, and the ship ritual bumps the plugin to 2.5.0
without touching the homepage. The same drift happened once before (it was 2.3.0, QA I-3), and
nothing in `tests/test_site_publishing.py` catches it.
Expected: bump the value as part of the v2.5.0 ship, or add a test that compares it with
`plugin.json` / `package.json`.

## Positive observations
- The scroll fix is narrow and handles the bad-selector case.
- The "runs on your machine" card now says what leaves the machine and links to the full list.
  That removes the earlier contradiction between telemetry being on by default and the "only local"
  heading.
- The source comments next to the proof figure and the host-parity copy name the decision behind
  each one and what to do before changing them.

## Recommendations
1. Reword the link text at L480 (I-6).
2. Tie the JSON-LD version to the release bump (I-7).
