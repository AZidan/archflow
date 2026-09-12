# Contributing to Archflow

Archflow is a set of instructions that drive a coding agent. Almost everything here is markdown and
YAML, so the usual advice about tests and types does not apply in the usual way. What follows is
what actually keeps it working.

## Setup

```bash
git clone https://github.com/AZidan/archflow
cd archflow
python -m pip install pyyaml pytest
python -m pytest tests/ -q
```

Node 18+ is needed for the hooks and Studio. `/archflow:doctor` in any project lists what is missing.

## The three rules that matter most

### 1. The mirrored trees must stay byte-identical

`plugin/skills/archflow/` is what ships. `.archflow/` is this repo's own dogfood copy. Edit a
framework file and you edit it in both, including `design-systems/`, `schemas/`, `stacks/` and
`phases/`.

```bash
diff -r -x SKILL.md -x mcp-registry.yaml .archflow plugin/skills/archflow
```

CI enforces this, and `tests/test_mirrors.py` covers it. It matters because a divergence is invisible
until an agent reads the stale copy and does something inexplicable.

### 2. Agents live in `plugin/agents/` only

They are **not** mirrored. The marketplace ships `./plugin`, so that is the one copy that reaches
users, and Claude Code loads project agents from `.claude/agents/`, which this repo does not use.

A root `agents/` tree existed for months, was never packaged, and silently drifted. Do not recreate
it. A test asserts it stays gone.

### 3. Behaviour is defined once, in the phase file

Commands are entry points, not second definitions. `/archflow:design {story-id}` resolves the story,
checks the gate, dispatches the agent, and then delegates the transition to `phase-2-design.md`
rather than restating it.

The rule exists because the framework has already been bitten by it: the API contract had no schema
and three projects each invented a different format. Two copies of a rule become two different rules.

## Adding an agent

1. Write `plugin/agents/{name}.md`. The `name` in frontmatter must match the filename.
2. **Wire it into a phase file.** An agent no phase references can never be dispatched. Three shipped
   for months that way.
3. Register it in `.archflow/instructions.md` and its mirror.
4. Update the agent count in `plugin/.claude-plugin/plugin.json`, `marketplace.json` and the README.
   A test checks these agree.

### What an agent must not contain

- **A technology.** Agents read `stack:` from `.archflow/project-settings.yaml` and work in what it
  names. Naming candidates to *detect among* is fine; naming one to impose is not. A test enforces
  the imperative forms.
- **A long description.** It loads into every session. One shape: what it does, when it runs, what it
  produces, what binds it. Under 400 characters, no `<example>` blocks.
- **Generic knowledge.** A capable model already knows how to write a Dockerfile. Keep the rules that
  are specific to this framework and cut the tutorial.
- **An absolute path or a credential.** A test greps for both.

Every agent needs an output contract, a handoff, and a stop condition. An agent that ends by
praising its own thoroughness has no stop condition.

## Adding a command

`plugin/commands/{name}.md`, with `description` and, where it takes arguments, `argument-hint`.

**Quote the description if it contains a colon.** Four shipped commands had frontmatter that would
not parse for exactly this reason. CI checks it now.

Register it in both instruction mirrors, `SKILL.md`, `status.md`, the README and `CLAUDE.md`. A
command that exists but is not listed is a command nobody finds.

## Changing a schema

Schemas live in `.archflow/schemas/` and its mirror, in a small hand-written dialect rather than JSON
Schema: `type`, `required`, `properties`, `enum`, `items`, `pattern`, `$ref`, `format`, and a `$root`
saying which definition validates the document.

The state files split by lifetime: `current-phase.yaml` is a CURSOR rewritten at every phase
transition, `project-settings.yaml` is how the project works and changes almost never. Putting a
setting in the cursor buries it in phase churn. That is what v2.1 fixed.

Adding a required field is breaking for existing projects. Either give it a default, or add a
migration path, and say which in the changelog.

```bash
python3 plugin/scripts/validate_archflow.py tests/fixtures/valid-project
python3 plugin/scripts/validate_archflow.py tests/fixtures/invalid-project   # must fail
```

## Adding a design system

See `.archflow/design-systems/CONTRIBUTING.md`. In short: a component vocabulary table, scales,
rules, and anti-patterns concrete enough that a reviewer can fail a diff against them.

## Tests

Prefer a test that fails on a real defect over one asserting something exists. The suite has caught
two live bugs: four commands with unparseable frontmatter, and the drifted agents tree.

For the validator and the hooks, at least half the tests should assert *failure*. A validator that
only ever passes is worse than none, because it buys confidence it has not earned.

## Commits and releases

Conventional commits: `feat(scope):`, `fix(scope):`, `docs(scope):`, `test(scope):`, `refactor:`,
`chore:`. Explain **why** in the body; the diff already shows what.

Commit only what you changed. Never `git add .` — this repo usually has unrelated work in progress.

To release: update the version in `plugin/.claude-plugin/plugin.json`, `marketplace.json`,
`package.json` and `packages/archflowai/package.json` (the release workflow refuses a tag they
disagree with), move
`[Unreleased]` into a dated section in `CHANGELOG.md`, then tag. The release workflow builds the
GitHub release from the changelog section.

## What is generated, not authored here

`plugin/server/`, `plugin/dist/`, `plugin/commands/studio.md` and
`plugin/hooks/studio-session-context.mjs` come from the
[archflow-studio](https://github.com/AZidan/archflow-studio) repo via its `npm run sync:plugin`.
Edits made here are overwritten on the next sync.

`.gitattributes` marks `plugin/dist/**` and `plugin/server/*.mjs` as
`linguist-generated -diff`, so GitHub keeps them out of the repo's language statistics and collapses
them in pull requests. Without it the repo reads as a JavaScript project — roughly 6 MB of bundled
output against under 1 MB of framework content — and a Studio rebuild buries a real change under
fifty files of hashed churn.

## Reporting a vulnerability

See [SECURITY.md](SECURITY.md). Please do not open a public issue for anything exploitable.
