"""Guards on the optional-agents setting.

Four agents are useful but not on the critical path. They used to be unreachable:
present in the plugin, referenced by no phase, so nothing could ever dispatch
them automatically and nothing told a user they existed. code-reviewer had the
inverse problem — it ran only as a Phase 4 whole-codebase pass, so a story could
be built, tested, accepted and merged with no code review at all.

`optional_agents` in current-phase.yaml fixes both by letting a project say which
of them join, and where. These tests assert the wiring is complete, because a
hook point that exists in the schema but in no phase file is worse than none.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCHEMA = REPO / ".archflow" / "schemas" / "current-phase-schema.yaml"
PHASES = REPO / ".archflow" / "phases"
COMMANDS = REPO / "plugin" / "commands"

OPTIONAL = {"a11y-expert", "code-reviewer", "doc-writer", "ui-animation-designer"}
HOOKS = {"design", "story_review", "release_quality", "pre_ship"}

HOOK_FILES = {
    "design": PHASES / "phase-2-design.md",
    "story_review": PHASES / "phase-3-implementation.md",
    "release_quality": PHASES / "phase-4-quality.md",
    "pre_ship": PHASES / "phase-5-launch.md",
}


def schema():
    return yaml.safe_load(SCHEMA.read_text())["properties"]["optional_agents"]


def test_schema_defines_the_setting():
    s = schema()
    assert set(s["propertyNames"]["enum"]) == OPTIONAL
    assert set(s["additionalProperties"]["items"]["enum"]) == HOOKS


def test_every_hook_point_is_implemented_by_a_phase():
    """A hook in the schema that no phase reads is a promise nothing keeps."""
    for hook, path in HOOK_FILES.items():
        body = path.read_text()
        assert "optional_agents" in body, f"{path.name} never reads optional_agents"
        assert hook in body, f"{path.name} does not name the {hook} hook"


def test_every_optional_agent_still_exists():
    for agent in OPTIONAL:
        assert (REPO / "plugin" / "agents" / f"{agent}.md").exists()


def test_the_three_formerly_unreachable_agents_are_now_reachable():
    """They were in the plugin and in no phase file. That is the bug this closes."""
    reference = (REPO / ".archflow" / "reference.md").read_text()
    for agent in ("a11y-expert", "doc-writer", "ui-animation-designer"):
        assert agent in reference, f"{agent} is undocumented"
        assert any(agent in p.read_text() for p in [SCHEMA]), f"{agent} is not a valid key"


def test_empty_list_means_available_but_not_automatic():
    """The whole point: discoverable without being mandatory."""
    body = SCHEMA.read_text()
    assert re.search(r"EMPTY list means available but never automatic", body, re.I)
    for path in HOOK_FILES.values():
        assert "empty list is NOT dispatched here" in path.read_text(), \
            f"{path.name} must say an empty list does not run"


def test_a_direct_request_always_wins():
    """Not automatic must never mean not allowed."""
    core = (REPO / ".archflow" / "instructions.md").read_text()
    assert "available on request" in core
    for path in HOOK_FILES.values():
        assert "available on request" in path.read_text()


def test_autopilot_runs_the_story_review_hook():
    """An unattended run that skips the project's own review is not its process."""
    body = (COMMANDS / "autopilot.md").read_text()
    assert "story_review" in body
    assert "optional_agents" in body


def test_story_review_runs_between_qa_and_acceptance():
    body = HOOK_FILES["story_review"].read_text()
    assert re.search(r"AFTER `qa-engineer`.*BEFORE `pm-reviewer`", body, re.S)


def test_init_and_onboard_ask_rather_than_assume():
    init = (COMMANDS / "init.md").read_text()
    onboard = (COMMANDS / "onboard.md").read_text()
    assert "optional_agents" in init and "optional_agents" in onboard
    assert "Ask once" in init
    # onboard defers to init rather than restating the options
    assert "Step 4a2" in onboard


def test_mode_switch_does_not_silently_rewrite_the_setting():
    body = (COMMANDS / "mode.md").read_text()
    assert "optional_agents" in body
    assert re.search(r"does NOT rewrite that block silently", body)


def test_doctor_reports_the_setting():
    assert "optional_agents" in (COMMANDS / "doctor.md").read_text()


def test_mirrors_carry_the_hook_points():
    for path in HOOK_FILES.values():
        mirror = REPO / "plugin" / "skills" / "archflow" / "phases" / path.name
        assert mirror.read_text() == path.read_text()
