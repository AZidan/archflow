"""Guards on `issues[]` — review findings as story state (ADR 004).

The reject loop used to hand findings back as prose: qa-engineer said what broke,
the orchestrator paraphrased it into the re-dispatch, and after a compaction
nothing remembered any of it. `issues[]` makes a finding a property of the
repository instead of a fact in someone's context.

Two invariants carry the whole design, and both are semantic — the schema dialect
cannot express either — so they are tested against the validator, not the schema.
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "plugin" / "scripts" / "validate_archflow.py"
SCHEMA = REPO / ".archflow" / "schemas" / "release-schema.yaml"
PHASE3 = REPO / ".archflow" / "phases" / "phase-3-implementation.md"
PHASE4 = REPO / ".archflow" / "phases" / "phase-4-quality.md"
AUTOPILOT = REPO / "plugin" / "commands" / "autopilot.md"

REVIEWERS = ("qa-engineer", "pm-reviewer", "code-reviewer", "a11y-expert")


def schema():
    return yaml.safe_load(SCHEMA.read_text())


# --------------------------------------------------------------------------
# The schema
# --------------------------------------------------------------------------

def test_story_has_an_optional_issues_array():
    story = schema()["story"]["properties"]
    assert "issues" in story
    assert story["issues"]["required"] is False, "existing projects must validate without it"
    assert story["issues"]["items"]["$ref"] == "#/issue"
    assert "issues" not in schema()["story"]["required"]


def test_issue_requires_the_fields_a_re_dispatch_needs():
    issue = schema()["issue"]
    assert set(issue["required"]) == {"id", "summary", "found_by", "severity", "status"}


def test_every_reviewing_agent_can_be_a_finder():
    found_by = schema()["issue"]["properties"]["found_by"]["enum"]
    for agent in REVIEWERS:
        assert agent in found_by, f"{agent} reviews stories but cannot own a finding"
    assert "human" in found_by


def test_severity_and_status_are_closed_sets():
    props = schema()["issue"]["properties"]
    assert props["severity"]["enum"] == ["blocking", "minor"]
    assert props["status"]["enum"] == ["open", "fixed", "deferred"]


def test_report_is_a_pointer_not_a_copy():
    """ADR 002's rule, applied again: state files index artifacts, never duplicate them."""
    desc = schema()["issue"]["properties"]["report"]["description"]
    assert "POINTER" in desc
    assert "never a copy" in desc


def test_issue_ids_are_story_scoped():
    assert schema()["issue"]["properties"]["id"]["pattern"] == "^I-[0-9]+$"


def test_the_schema_mirrors_match():
    other = REPO / "plugin" / "skills" / "archflow" / "schemas" / "release-schema.yaml"
    assert other.read_text() == SCHEMA.read_text()


# --------------------------------------------------------------------------
# The invariants — these must FAIL on drift, which is the point of having them
# --------------------------------------------------------------------------

def project(tmp_path, story_overrides):
    """A minimal valid project whose one story carries `story_overrides`."""
    root = tmp_path / "p"
    (root / ".archflow" / "releases").mkdir(parents=True)
    (root / ".archflow" / "schemas").mkdir()
    for s in (REPO / ".archflow" / "schemas").glob("*.yaml"):
        (root / ".archflow" / "schemas" / s.name).write_text(s.read_text())

    story = {
        "id": "S1-01",
        "title": "A story",
        "priority": "High",
        "status": "review",
        "gates": {"needs_design": False, "needs_contract": False},
        "assigned": "ui-engineer",
        "description": "d",
        "acceptance_criteria": [{"text": "works", "met": False}],
        "subtasks": [{"text": "build it", "completed": False}],
    }
    story.update(story_overrides)
    (root / ".archflow" / "releases" / "r.yaml").write_text(yaml.safe_dump({
        "id": "r", "name": "R", "goal": "g", "status": "in_progress", "stories": [story],
    }))
    return root


def report(root):
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(root), "--json"], capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def issue(**over):
    base = {"id": "I-1", "summary": "broken", "found_by": "qa-engineer",
            "severity": "blocking", "status": "open"}
    base.update(over)
    return base


def test_done_with_an_open_blocking_issue_fails(tmp_path):
    """The invariant the whole change exists for."""
    code, data = report(project(tmp_path, {"status": "done", "issues": [issue()]}))
    assert code == 1
    msgs = [v["message"] for v in data["violations"] if v["field"] == "stories[0].status"]
    assert msgs and "I-1" in msgs[0]


def test_done_with_a_fixed_issue_passes(tmp_path):
    code, _ = report(project(tmp_path, {"status": "done", "issues": [issue(status="fixed")]}))
    assert code == 0


def test_done_with_an_open_minor_issue_passes(tmp_path):
    """Minor findings do not hold a story; only blocking ones do."""
    code, _ = report(project(tmp_path, {"status": "done", "issues": [issue(severity="minor")]}))
    assert code == 0


def test_open_blocking_issue_is_fine_while_the_story_is_still_in_review(tmp_path):
    """A story in review is SUPPOSED to carry open findings. Only `done` is constrained."""
    code, _ = report(project(tmp_path, {"status": "review", "issues": [issue()]}))
    assert code == 0


def test_deferred_without_a_backlog_stub_fails(tmp_path):
    code, data = report(project(tmp_path, {"issues": [issue(status="deferred", severity="minor")]}))
    assert code == 1
    fields = {v["field"] for v in data["violations"]}
    assert "stories[0].issues[0].deferred_to" in fields


def test_deferred_with_a_backlog_stub_passes(tmp_path):
    code, _ = report(project(tmp_path, {
        "issues": [issue(status="deferred", severity="minor", deferred_to="S1-09")]}))
    assert code == 0


def test_a_story_without_issues_still_validates(tmp_path):
    """Every project that predates this change must keep validating untouched."""
    code, _ = report(project(tmp_path, {"status": "done"}))
    assert code == 0


def test_the_invalid_fixture_carries_both_semantic_violations():
    """The shipped fixture must exercise them, or a refactor could drop the rules silently."""
    _, data = report(REPO / "tests" / "fixtures" / "invalid-project")
    fields = {v["field"] for v in data["violations"]}
    assert "stories[1].status" in fields
    assert "stories[1].issues[1].deferred_to" in fields


def test_the_valid_fixture_exercises_the_happy_path():
    release = yaml.safe_load(
        (REPO / "tests" / "fixtures" / "valid-project"
         / ".archflow" / "releases" / "checkout-redesign.yaml").read_text())
    issues = release["stories"][0]["issues"]
    assert {i["status"] for i in issues} == {"open", "deferred"}


# --------------------------------------------------------------------------
# The protocol — a typed field nobody is told to write is a field nobody writes
# --------------------------------------------------------------------------

def test_every_reviewing_agent_is_told_to_write_issues():
    for agent in REVIEWERS:
        body = (REPO / "plugin" / "agents" / f"{agent}.md").read_text()
        assert "issues:" in body, f"{agent} is never told to record findings as issues"
        assert f"found_by: {agent}" in body, f"{agent} does not stamp its own findings"


def test_no_reviewer_may_close_or_defer_its_own_finding():
    """An agent that can clear what it found has stopped being a check."""
    for agent in REVIEWERS:
        body = (REPO / "plugin" / "agents" / f"{agent}.md").read_text()
        assert "You do not close issues, and you do not defer them." in body


def test_phase3_gates_done_on_open_blocking_issues():
    body = PHASE3.read_text()
    assert "issues[]" in body
    assert "status: open" in body and "severity: blocking" in body


def test_phase3_dispatches_story_review_agents_sequentially():
    """They all write the release file; two in parallel lose a finding."""
    body = PHASE3.read_text()
    assert "One at a time." in body


def test_phase3_re_dispatch_carries_the_open_issues():
    body = PHASE3.read_text()
    start = body.index("## 📦 The dispatch payload")
    section = body[start:start + 2600]
    assert "Open issues" in section, "a re-dispatch after review does not carry what review found"


def test_phase4_reuses_phase3s_issue_rules_rather_than_restating_them():
    body = PHASE4.read_text()
    assert "issues[]" in body
    assert "See Phase 3" in body


def test_phase_mirrors_match():
    for name in ("phase-3-implementation.md", "phase-4-quality.md"):
        a = REPO / ".archflow" / "phases" / name
        b = REPO / "plugin" / "skills" / "archflow" / "phases" / name
        assert a.read_text() == b.read_text(), f"{name} mirrors have drifted"


# --------------------------------------------------------------------------
# The status ladder
#
# Autopilot runs were writing `done` onto stories that had never been written
# `in_progress` or `review`. A release file that jumps two states cannot be read
# the morning after, and a run that dies mid-story leaves it looking untouched.
# --------------------------------------------------------------------------

def test_phase3_defines_the_status_transitions_once():
    body = PHASE3.read_text()
    assert "### 📍 Story status transitions" in body
    for transition in ("`ready` → `in_progress`", "`in_progress` → `review`", "`review` → `done`"):
        assert transition in body, f"the ladder does not state {transition}"


def test_phase3_sets_in_progress_before_any_code():
    body = PHASE3.read_text()
    assert "status: in_progress" in body
    assert "before any code exists" in body


def test_phase3_sets_review_before_qa():
    body = PHASE3.read_text()
    start = body.index("### ✅ Step 3C: STORY TESTING")
    assert "status: review" in body[start:start + 400]


def test_autopilot_walks_every_state():
    body = AUTOPILOT.read_text()
    assert "### Walk the status, never jump it" in body
    for state in ("in_progress", "review", "done", "parked"):
        assert state in body


def test_autopilot_sets_in_progress_before_implementing():
    body = AUTOPILOT.read_text()
    start = body.index("## Step 3 — The run")
    step3 = body[start:start + 1800]
    assert "status: in_progress" in step3
    assert step3.index("status: in_progress") < step3.index("Implement with the agents")


def test_autopilot_does_not_flap_the_status_back_on_rejection():
    body = AUTOPILOT.read_text()
    assert "do not flap it back to `in_progress`" in body


def test_autopilot_reports_the_open_issues_of_a_failed_story():
    """"QA rejected 3x" is a status. The issue list is something the user can start from."""
    body = AUTOPILOT.read_text()
    start = body.index("## Step 4 — The report")
    section = body[start:start + 2200]
    assert "Open issues:" in section


def test_autopilot_never_defers_an_issue_on_its_own():
    assert "Autopilot never defers an issue." in AUTOPILOT.read_text()
