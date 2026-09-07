# Framework tests

These test the framework itself, not a project built with it. They exist because Archflow's
correctness lives in files that nothing used to check: agent frontmatter, two mirrored trees, and
six schemas that no code read.

```bash
python3 -m pytest tests/ -q
```

Requires `pyyaml` and `pytest`. CI runs the same suite plus a mirror diff and a validator self-check.

## What each file guards

| File | Guards |
|---|---|
| `test_validate_archflow.py` | The state-file validator. Half these tests assert it **fails** on drift, because a validator that only ever passes buys confidence it has not earned |
| `test_migrate.py` | The v1.0 to v2.0 migration, both roadmap variants. Its real contract is that its output validates against the v2.0 schemas, not merely that it produced something |
| `test_mirrors.py` | `.archflow/` and `plugin/skills/archflow/` stay byte-identical, and no second agents tree reappears |
| `test_story_issues.py` | `issues[]` (ADR 004): the schema shape, the two semantic invariants — a `done` story with an open blocking issue, a `deferred` issue naming no backlog stub — and the story status ladder autopilot used to jump |
| `test_shared_agent_blocks.py` | Blocks duplicated across agent files on purpose — the design-system review gate and the issues protocol — stay byte-identical. Agent files are prompts, so rules are inlined rather than referenced; these tests are what that choice costs |
| `test_plugin_manifest.py` | Frontmatter parses, descriptions stay short, no agent prescribes a technology (AF-32), no author paths or credentials ship, external installs stay pinned |

## Fixtures

| Fixture | Purpose |
|---|---|
| `valid-project/` | A well-formed v2.0 project. Must validate clean |
| `invalid-project/` | One deliberate violation of each kind: enum, id pattern, missing required field, wrong type. Must fail, and the tests assert on the specific fields |
| `v1-project/` | v1.0 roadmap, variant A: stories under `epics:`, sprints reference them by id |
| `v1-project-variant-b/` | v1.0 roadmap, variant B: top-level `sprints:` with inline stories |

Each fixture carries its own copy of `schemas/`, so a test never depends on the repo's own state.

## Adding a check

Prefer a test that fails on a real defect over one that asserts something is present. Three of these
caught live bugs when first written: four shipped commands had frontmatter that would not parse
because of an unquoted colon, and the root `agents/` tree had silently drifted from `plugin/agents/`.
