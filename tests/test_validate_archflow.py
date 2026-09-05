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
