VERDICT: FAIL

# S6-04 code review: Studio on non-Claude hosts (forward mode)

Reviewer: code-reviewer. Scope: `git diff 408b49a..HEAD`, excluding `plugin/dist`, `plugin/server`,
`adapters` and `docs/qa-reports` (one generated adapter file per host spot-checked for the launch
path and host id). Stack: Node ESM (`.mjs`), pytest. No API contract (this story touches no API).

## Design System Compliance

Not applicable. The story changes no UI code (the Studio bundle is prebuilt and out of scope), so
the design-system anti-pattern gate has nothing to run against.

## Code Review Summary

**Overall assessment:** solid, well-tested work. The installer change is small and safe, the
build-adapters change is the minimum needed, and the new tests check real behaviour (they run the
installer into a temp HOME and project, and compare placed bytes with the plugin's). Checked here:
`node scripts/build-adapters.mjs --check` passes, and `tests/test_studio_hosts.py`,
`test_help_command.py`, `test_host_paths.py` and `test_build_adapters.py` pass (316 tests).

One flow fails for a realistic group of users: anyone whose npx cache still holds a pre-2.5.0
installer (I-3). That fails the verdict. The fix is a one-word change in several places.

## Critical Issues

### I-3 (blocking): a cached pre-2.5.0 installer gives Studio's command without its bundle, and the documented fix reruns that same installer

- Location: `plugin/commands/studio.md:124`, with the same advice in `CHANGELOG.md`, `README.md`
  and each adapter README's Studio row (`scripts/build-adapters.mjs` `studioRow()`).
- The README says it directly (line 82): "the adapters come from the latest GitHub release, whatever
  version of the installer npx has cached". A user who last ran `npx archflow install` on 2.4.x
  has a 2.4.x installer in the npx cache. Re-running it downloads the 2.5.0 release adapters, which
  now ship `archflow-studio`. The old installer has no `installStudio()`, though, so it places no
  bundle and does not print the `skip  Archflow Studio bundle` line either.
- The studio command then finds `bundle=missing` and tells the user to run `npx archflow install`.
  That runs the same cached installer, with the same result. The user is stuck in a loop, and
  nothing they are told breaks it.
- Expected: the missing-bundle remedy is one that fetches the current installer. Use
  `npx archflow@latest install` in `studio.md`'s step 2 (and so in every adapter), in `studioRow()`,
  and in the CHANGELOG/README sentences that describe how a teammate gets the bundle.
- Why blocking: it fails the AC "/archflow:studio starts ... on a non-Claude host" for upgrading
  users, the usual 2.5.0 audience, and the fix the doc gives does not work.

## High Priority Issues

None.

## Medium Priority Issues

### I-4 (minor): `--dry-run` reports actions the real run does not take

- `scripts/archflow.mjs:277`: in dry-run the `.gitignore` verb is always `write`, but the real run
  may `merge` or `keep` (see `ensureIgnored`). So a re-run dry-run says it will write a file it
  will leave alone.
- `scripts/archflow.mjs:512` → `:523`: the Gemini dry-run prints
  `run gemini extensions install <package>/adapters/gemini`, but the real run installs from the
  staged copy under `~/.cache/archflow/gemini-extension/<version>/archflow`. That is the directory
  Gemini remembers as the extension's source, and the comment at `:506-509` says that is the point.
- Dry-run purity itself holds: the test checks that nothing is written under the project, `~/.gemini`
  or `~/.cache`, and the code confirms it (`ensureIgnored` and the staging both sit behind `!dry`).
- Suggestion: work out the verb without writing (factor the "what would change" half of
  `ensureIgnored`). For Gemini, print the staged path the real run would use.

### I-5 (minor): studio.md does not cover hosts that sandbox shell commands

- Location: `plugin/commands/studio.md:127-134` (the detached start).
- On Codex, with its default `workspace-write` sandbox, the start step writes outside the
  workspace (`mkdir -p "$HOME/.archflow/studio/logs"` and the log redirect), and the probe and wait
  steps use localhost networking (`curl 127.0.0.1`, and the server's `listen`). Depending on
  configuration, the sandbox blocks some or all of these. A detached child can also be reaped when
  the sandboxed command ends. QA's launch check ran the command's steps by hand in a shell, not
  inside a Codex or Gemini sandboxed session, so this path is unverified.
- Expected: one line in Settings or step 3 saying that on a host that sandboxes shell commands,
  the start (and the probe) must run with that host's approval to leave the sandbox, and that a
  `bundle=ok` but never-answering server on such a host means the sandbox, not Studio.
- Not blocking: Codex's default approval policy asks to re-run a failed command outside the sandbox,
  so the flow usually recovers. It is unverified, though, and the doc says nothing about it.

## Low Priority Issues

These are not recorded as issues, since none needs action to ship.

- `docs/guides/studio.md:172` uses `/archflow:studio status` in the host-neutral paragraph straight
  after the per-host spelling table. A reader on Codex has to translate it. Saying "the studio
  command's `status`" would be host-neutral.
- `studio.md` is now about 260 lines and is loaded on every invocation. The detection-ranking
  paragraph in "Hosts and chat" is reference detail the agent never acts on (Studio does the
  ranking). It could move to `docs/guides/studio.md` with a link.
- `ensureIgnored` matches lines by exact trimmed text, so an existing `server/` or `dist` entry gets
  a near-duplicate `/server/` added next to it. This is harmless, and the merge is idempotent:
  re-runs return `keep`, and the test covers keeping a user's line.
- The `plugin/hooks/hooks.json` diff (from the bundle-sync commit) only reorders two `SessionStart`
  entries. It is functionally neutral, and the Codex hook build still drops Studio's session hook.

## Positive Observations

- **The `dist/` replacement cannot reach outside the intended directory.** `root` is always
  `join(project, host.hookRoot)` with a constant `hookRoot`, or the staged Gemini directory, and
  the removed path is `join(root, "dist")`. Node's `rmSync` unlinks a symlinked `dist` rather than
  following it. `copyInto` skips symlinks inside the source. There is no user-controlled path
  component.
- Replacing `dist/` whole instead of merging it is the right call for content-hashed assets. A test
  (`test_reinstall_replaces_dist_instead_of_piling_up_old_builds`) proves it, and the same test
  covers keeping the `.gitignore` lines a user added.
- A source with no bundle degrades properly: the install succeeds, prints a `skip` line, and the
  command gives a clear missing-bundle message. A test builds a bundle-less package and checks this.
- The npm package holds one copy of the bundle, which adds about 1.67 MB compressed (measured here,
  matching the CHANGELOG). A test asserts there is exactly one `server.mjs` and one `dist/index.html`
  in the pack.
- `build-adapters.mjs` stays minimal: it empties the skip sets, adds a shared `studioRow()`, and has
  one vocab rule for the host id. Each generated command was spot-checked and launches from its own
  root with the right host id (`.codex/archflow`, `.agents/archflow`, `.github/archflow`,
  `.cursor/archflow`, `.opencode/archflow`, `$HOME/.gemini/extensions/archflow`). No
  `${CLAUDE_PLUGIN_ROOT}` remains in any of them.
- The Claude Code path has not regressed. The launch line, `--session-context`, full as the default
  and companion as opt-in are unchanged, and a test pins the launch path and host id.
- In studio.md the probe states, "FOREIGN is never killed", the detached start and stopping by pid
  are all intact and read clearly. The new "chat line" derivation is explicit and is never guessed.
- On the marketing guardrails, the site and README edits add no total command count and no pricing
  hints. Nothing uses the `/archflow <sub>` form. No framework file under `plugin/skills/archflow/`
  changed, so there is no mirror drift to check.

## Recommendations

1. (I-3, blocking) Change the missing-bundle remedy to `npx archflow@latest install` in studio.md,
   `studioRow()`, CHANGELOG and README. Regenerate the adapters, and add a test that pins the
   `@latest` spelling in every host's studio command.
2. (I-4) Make the dry-run output match the real run: the `.gitignore` verb and the Gemini staged
   path.
3. (I-5) Add one line to studio.md about sandboxed hosts, and verify one real Codex-session launch
   before release.
