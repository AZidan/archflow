"""Tests for upgrade drift detection and repair.

A project's .archflow/ is a copy of framework files made at setup. The plugin
moves on; nothing reconciled the two until now. These tests build a realistic
pre-upgrade project and assert both halves: that the drift is found, and that
repairing it produces a project the validator accepts.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
UPGRADE = REPO / "plugin" / "scripts" / "upgrade_archflow.py"
VALIDATOR = REPO / "plugin" / "scripts" / "validate_archflow.py"
PLUGIN = REPO / "plugin"


def run(project, *flags):
    proc = subprocess.run(
        [sys.executable, str(UPGRADE), str(project),
         "--plugin-root", str(PLUGIN), "--version", "9.9.9", *flags],
        capture_output=True, text=True,
    )
    return proc


def report(project, *flags):
    proc = run(project, "--json", *flags)
    return proc.returncode, json.loads(proc.stdout)


@pytest.fixture
def stale(tmp_path):
    """A project as it would look after being set up on an older plugin."""
    af = tmp_path / ".archflow"
    (af / "releases").mkdir(parents=True)
    (af / "schemas").mkdir()
    # only the schemas that existed before this release
    for name in ("release-schema.yaml", "roadmap-schema.yaml", "backlog-schema.yaml",
                 "history-schema.yaml", "autopilot-schema.yaml"):
        shutil.copy(REPO / ".archflow" / "schemas" / name, af / "schemas" / name)
    (af / "current-phase.yaml").write_text(
        "phase: 3\n"
        'phase_name: "Implementation"\n'
        'phase_file: "phases/phase-3-implementation.md"\n'
        "project_type: fullstack\n"
        "onboarded: true\n"
        "tech_stack:\n"
        '  language: "typescript"\n'
        '  frontend: "react"\n'
        '  backend: "nestjs"\n'
        '  database: "postgresql"\n'
        "mode: quick\n"
        "active_release: checkout\n"
    )
    (af / "releases" / "checkout.yaml").write_text(
        "id: checkout\nname: Checkout\ngoal: Ship it\nstatus: in_progress\nstories:\n"
        "  - id: S2-07\n    title: Saved cards\n    priority: High\n    status: review\n"
        "    gates: {needs_design: true, needs_contract: false}\n"
        "    assigned: pm-maestro-reviewer\n    description: Reuse saved cards.\n"
        "    acceptance_criteria:\n"
        "      - {text: Pay with a saved card, met: true, verified_by: pm-maestro-reviewer}\n"
        "    subtasks:\n      - {text: Card selector, completed: true}\n"
    )
    return tmp_path


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def test_dry_run_reports_drift_and_changes_nothing(stale):
    before = (stale / ".archflow" / "current-phase.yaml").read_text()
    code, data = report(stale)
    assert code == 1, "drift should signal with exit 1"
    assert data["drift"] is True
    assert (stale / ".archflow" / "current-phase.yaml").read_text() == before


def _keys(data):
    return {f["key"].split(":")[0] for f in data["findings"]}


def test_detects_the_retired_agent_name(stale):
    _, data = report(stale)
    assert "renamed-agent" in _keys(data)


def test_detects_tech_stack_needing_conversion(stale):
    _, data = report(stale)
    assert "tech-stack-convert" in _keys(data)


def test_detects_missing_framework_files(stale):
    _, data = report(stale)
    f = next(f for f in data["findings"] if f["key"] == "missing-framework-files")
    assert any("design-systems/" in n for n in f["files"])
    assert any("stacks/" in n for n in f["files"])


def test_detects_a_missing_version_stamp(stale):
    _, data = report(stale)
    assert "version-stamp" in _keys(data)


def test_a_project_with_no_stack_at_all_is_not_auto_fixable(tmp_path):
    """Choosing a stack is a judgement. The tool must refuse to guess."""
    af = tmp_path / ".archflow"
    af.mkdir()
    (af / "current-phase.yaml").write_text(
        "phase: 1\nphase_file: x\nproject_type: fullstack\nmode: quick\n"
    )
    _, data = report(tmp_path)
    finding = next(f for f in data["findings"] if f["key"] == "stack-absent")
    assert finding["fixable"] is False


# --------------------------------------------------------------------------
# Repair
# --------------------------------------------------------------------------

def test_apply_renames_the_retired_agent(stale):
    run(stale, "--apply")
    text = (stale / ".archflow" / "releases" / "checkout.yaml").read_text()
    assert "pm-maestro-reviewer" not in text
    assert text.count("pm-reviewer") == 2, "both assigned and verified_by should be renamed"


def test_apply_converts_tech_stack_preserving_the_values(stale):
    """tech_stack -> stack is a shape-independent rewrite, so it stays scripted."""
    run(stale, "--apply")
    doc = yaml.safe_load((stale / ".archflow" / "current-phase.yaml").read_text())
    assert "tech_stack" not in doc
    assert doc["stack"]["language"] == "typescript"
    assert doc["stack"]["backend"]["framework"] == "nestjs"
    assert doc["stack"]["backend"]["database"] == "postgresql"
    assert doc["stack"]["web"]["framework"] == "react"
    # what the old block could not express stays null, so an agent asks
    assert doc["stack"]["backend"]["orm"] is None
    assert doc["stack"]["test"]["e2e"] is None


def test_apply_keeps_the_rest_of_current_phase_intact(stale):
    """Scripted repairs touch only what they claim to. The split is not one of them."""
    before = yaml.safe_load((stale / ".archflow" / "current-phase.yaml").read_text())
    run(stale, "--apply")
    after = yaml.safe_load((stale / ".archflow" / "current-phase.yaml").read_text())
    for key in ("phase", "phase_file", "project_type", "mode", "active_release", "onboarded"):
        assert after[key] == before[key], f"{key} changed during the upgrade"


def test_apply_copies_the_missing_framework_files(stale):
    run(stale, "--apply")
    af = stale / ".archflow"
    assert (af / "design-systems" / "shadcn.md").exists()
    assert (af / "stacks" / "nestjs-postgres-react.yaml").exists()
    assert (af / "schemas" / "current-phase-schema.yaml").exists()


def test_apply_stamps_the_version(stale):
    run(stale, "--apply")
    doc = yaml.safe_load((stale / ".archflow" / "current-phase.yaml").read_text())
    assert doc["plugin_version"] == "9.9.9"


def test_apply_backs_up_everything_it_changed(stale):
    run(stale, "--apply")
    backups = list((stale / ".archflow").glob("backup-upgrade-*"))
    assert backups, "no backup directory was written"
    assert (backups[0] / "current-phase.yaml").exists()
    original = yaml.safe_load((backups[0] / "current-phase.yaml").read_text())
    assert "tech_stack" in original, "the backup should hold the pre-upgrade content"


def test_repaired_project_validates(stale):
    """The whole point: after repair, the project is loadable by the new schemas."""
    run(stale, "--apply")
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(stale)], capture_output=True, text=True
    )
    assert proc.returncode == 0, f"repaired project still fails validation:\n{proc.stdout}"


def test_upgrade_is_idempotent_for_what_it_repairs(stale):
    """Only the manual split should remain outstanding after --apply."""
    run(stale, "--apply")
    code, data = report(stale)
    remaining = {f["key"] for f in data["findings"]}
    assert remaining <= {"split-project-settings"}, f"scripted repairs are not idempotent: {remaining}"
    second = run(stale, "--apply")
    assert second.returncode == 0


def test_a_current_project_reports_no_drift(tmp_path):
    af = tmp_path / ".archflow"
    shutil.copytree(REPO / ".archflow", af, ignore=shutil.ignore_patterns("*.md.bak"))
    (af / "current-phase.yaml").write_text(
        "phase: 1\nphase_file: x\nmode: quick\n"
        'plugin_version: "9.9.9"\n'
    )
    (af / "project-settings.yaml").write_text(
        'schema_version: "2.1"\nproject_type: fullstack\nstack: {language: typescript}\n'
    )
    code, data = report(tmp_path)
    assert code == 0, f"a current project reported drift: {data}"


def test_missing_project_exits_2(tmp_path):
    proc = run(tmp_path / "nope")
    assert proc.returncode == 2
