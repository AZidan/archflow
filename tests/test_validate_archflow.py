"""Tests for the .archflow/ state-file validator.

The point of these is not that the validator runs, but that it FAILS on drift.
A validator that only ever passes is worse than none, because it buys confidence
it has not earned.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "plugin" / "scripts" / "validate_archflow.py"
VALID = REPO / "tests" / "fixtures" / "valid-project"
INVALID = REPO / "tests" / "fixtures" / "invalid-project"


def run(project, *extra):
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(project), *extra],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def report(project):
    code, out, _ = run(project, "--json")
    return code, json.loads(out)


# --------------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------------

def test_valid_project_passes():
    code, data = report(VALID)
    assert code == 0
    assert data["ok"] is True
    assert data["violations"] == []


def test_valid_project_actually_checked_something():
    """Guards against a validator that passes by finding nothing to do."""
    _, data = report(VALID)
    assert ".archflow/current-phase.yaml" in data["checked"]
    assert any("releases/" in f for f in data["checked"])


def test_absent_optional_files_are_skipped_not_failed():
    _, data = report(VALID)
    skipped = {s["file"] for s in data["skipped"]}
    assert any("roadmap.yaml" in f for f in skipped)
    assert data["ok"] is True


# --------------------------------------------------------------------------
# The point: it must fail on drift
# --------------------------------------------------------------------------

def test_invalid_project_fails():
    code, data = report(INVALID)
    assert code == 1
    assert data["ok"] is False


def _fields(data):
    return {v["field"] for v in data["violations"]}


def test_catches_enum_violation():
    _, data = report(INVALID)
    assert "mode" in _fields(data)
    assert any("turbo" in v["message"] for v in data["violations"])


def test_catches_pattern_violation():
    _, data = report(INVALID)
    assert "stories[0].id" in _fields(data)


def test_catches_missing_required_field():
    _, data = report(INVALID)
    assert "stories[0].gates.needs_contract" in _fields(data)


def test_catches_wrong_type():
    _, data = report(INVALID)
    msgs = [v["message"] for v in data["violations"] if v["field"] == "stories[0].acceptance_criteria[0].met"]
    assert msgs and "expected boolean" in msgs[0]


def test_reports_nested_paths_not_just_the_file():
    """A violation the reader cannot locate is barely a violation."""
    _, data = report(INVALID)
    assert any("." in v["field"] or "[" in v["field"] for v in data["violations"])


# --------------------------------------------------------------------------
# Operational behaviour
# --------------------------------------------------------------------------

def test_missing_project_exits_2_not_1(tmp_path):
    code, _, err = run(tmp_path)
    assert code == 2
    assert "no .archflow" in err


def test_unparseable_yaml_is_a_violation_not_a_crash(tmp_path):
    proj = tmp_path / "p"
    (proj / ".archflow").mkdir(parents=True)
    (proj / ".archflow" / "schemas").mkdir()
    for s in (REPO / ".archflow" / "schemas").glob("*.yaml"):
        (proj / ".archflow" / "schemas" / s.name).write_text(s.read_text())
    (proj / ".archflow" / "current-phase.yaml").write_text("phase: [unclosed\n")
    code, data = report(proj)
    assert code == 1
    assert any("will not parse" in v["message"] for v in data["violations"])


def test_every_shipped_schema_declares_a_root():
    """A schema with no $root cannot validate anything, silently."""
    import yaml
    for path in sorted((REPO / ".archflow" / "schemas").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        assert "$root" in doc, f"{path.name} has no $root declaration"
        root = doc["$root"]
        if root is not None:
            assert root in doc, f"{path.name} declares $root: {root} which does not exist"


# --------------------------------------------------------------------------
# Historical autopilot runs
#
# Found by running the validator against a real project for the first time: four
# real ledgers produced 72 violations because the autopilot schema had never been
# checked against reality. Three of the four used different envelope shapes,
# because they were written by whatever version was current at the time.
#
# A finished run is a RECORD of what happened, like history.yaml. An active run is
# state the framework is still acting on.
# --------------------------------------------------------------------------

import yaml as _yaml


def _project_with_run(tmp_path, status, **overrides):
    af = tmp_path / ".archflow"
    (af / "autopilot").mkdir(parents=True)
    (af / "schemas").mkdir()
    for s in (REPO / ".archflow" / "schemas").glob("*.yaml"):
        (af / "schemas" / s.name).write_text(s.read_text())
    run = {
        "run_id": "2026-01-01-1", "status": status,
        "started_at": "2026-01-01T00:00:00Z",
        "base_branch": "main", "run_branch": "auto", "release": "r1",
        "envelope": {"merge_to_run_branch": True, "merge_to_main": False,
                     "open_pr": False, "run_qa": True, "run_acceptance": True},
        "queue": [{"story_id": "S1-01", "title": "t", "order": 1, "state": "done"}],
    }
    run.update(overrides)
    (af / "autopilot" / "r.yaml").write_text(_yaml.safe_dump(run, sort_keys=False))
    return tmp_path


def test_a_finished_run_is_not_validated(tmp_path):
    """It cannot be made to conform; the past was written by an older framework."""
    proj = _project_with_run(tmp_path, "finished", envelope={"nonsense": True})
    code, data = report(proj)
    assert code == 0, data
    assert any("historical record" in s["reason"] for s in data["skipped"])


def test_an_aborted_run_is_not_validated(tmp_path):
    proj = _project_with_run(tmp_path, "aborted", envelope={"nonsense": True})
    assert report(proj)[0] == 0


def test_an_active_run_IS_validated(tmp_path):
    """Live state must conform. This is the whole point of the distinction."""
    proj = _project_with_run(tmp_path, "running", envelope={"nonsense": True})
    code, data = report(proj)
    assert code == 1
    assert any("envelope" in v["field"] for v in data["violations"])


def test_commits_is_a_count_not_a_list_of_shas(tmp_path):
    """The schema asked for short SHAs for months while every real run wrote a number."""
    proj = _project_with_run(
        tmp_path, "running",
        queue=[{"story_id": "S1-01", "title": "t", "order": 1, "state": "done", "commits": 2}],
    )
    assert report(proj)[0] == 0, "a commit COUNT must be accepted"


def test_a_queue_item_may_be_non_story_work(tmp_path):
    """A real run queued PRE-EXISTING-FAILURE for a broken test it inherited."""
    proj = _project_with_run(
        tmp_path, "running",
        queue=[{"story_id": "PRE-EXISTING-FAILURE", "title": "t", "order": 1, "state": "done"}],
    )
    assert report(proj)[0] == 0


def test_lowercase_junk_is_still_rejected(tmp_path):
    proj = _project_with_run(
        tmp_path, "running",
        queue=[{"story_id": "not-a-real-id", "title": "t", "order": 1, "state": "done"}],
    )
    assert report(proj)[0] == 1


# --------------------------------------------------------------------------
# Lessons from running against two real projects
# --------------------------------------------------------------------------

def _proj(tmp_path, **files):
    af = tmp_path / ".archflow"
    (af / "schemas").mkdir(parents=True)
    for s in (REPO / ".archflow" / "schemas").glob("*.yaml"):
        (af / "schemas" / s.name).write_text(s.read_text())
    for name, body in files.items():
        p = af / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return tmp_path


def test_explicit_null_on_an_optional_field_is_accepted(tmp_path):
    """`key: null` is normal YAML and means the same as omitting the key.

    Real backlogs write `target: null` and real release files write
    `pulled_from: null`. Rejecting that made the validator fight a convention it
    does not own.
    """
    proj = _proj(tmp_path, **{"backlog.yaml":
        "epics:\n  - id: E1\n    stories:\n"
        "      - id: S1-01\n        title: t\n        priority: High\n"
        "        status: backlog\n        description: d\n        target: null\n"})
    assert report(proj)[0] == 0


def test_history_entries_need_only_their_identity(tmp_path):
    """History is a RECORD. You cannot add acceptance criteria to a story that
    shipped in March, so requiring them is a rule the past cannot satisfy."""
    proj = _proj(tmp_path, **{"history.yaml":
        "- story: S1-01\n  release: r1\n  summary: shipped\n"})
    assert report(proj)[0] == 0


def test_a_backlog_story_may_not_be_done(tmp_path):
    """This one stays strict: a story lives in ONE place and moves, never copies.

    Two real stories were found marked done while existing only in the backlog,
    in no release file. That is inconsistent state and the validator should keep
    saying so rather than being relaxed to accommodate it.
    """
    proj = _proj(tmp_path, **{"backlog.yaml":
        "epics:\n  - id: E1\n    stories:\n"
        "      - id: S1-01\n        title: t\n        priority: High\n"
        "        status: done\n        description: d\n"})
    code, data = report(proj)
    assert code == 1
    assert any("'done' is not one of" in v["message"] for v in data["violations"])
