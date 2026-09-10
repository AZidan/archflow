"""Guards on keeping a project's framework files in step with the plugin.

A project's .archflow/ is a COPY made at setup. The only reconciliation that ever
existed copied files that were ABSENT — which almost never happens, since every
project gets the full set. The real drift is staleness: the plugin moves on and the
project keeps its copy forever, so it validates against last quarter's schemas and
injects last quarter's instructions into every session.

The hard part is not copying. It is not copying over someone's edit. These tests
are mostly about that.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "plugin" / "scripts" / "upgrade_archflow.py"
SKILL = REPO / "plugin" / "skills" / "archflow"

SHIPPED_ROOT_FILES = ["workflow.md", "base-dsl-structure.yaml", "test-accounts.example.yaml",
                      "stack-detection.md", "instructions.md", "reference.md"]
SHIPPED_DIRS = ["phases", "schemas", "design-systems", "stacks"]


def project(tmp_path, stamp="2.2.0"):
    """A project carrying the full shipped set, stamped at `stamp`."""
    root = tmp_path / "p"
    af = root / ".archflow"
    af.mkdir(parents=True)
    for d in SHIPPED_DIRS:
        (af / d).mkdir()
        for f in (SKILL / d).glob("*"):
            if f.is_file():
                (af / d / f.name).write_bytes(f.read_bytes())
    for name in SHIPPED_ROOT_FILES:
        (af / name).write_bytes((SKILL / name).read_bytes())
    (af / "current-phase.yaml").write_text(
        'phase: 3\nphase_file: "phase-3-implementation.md"\nmode: quick\n'
        + (f'plugin_version: "{stamp}"\n' if stamp else ""))
    return root


def run(root, *extra, version="2.3.1"):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--plugin-root", str(REPO / "plugin"),
         "--version", version, "--json", *extra],
        capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def keys(data):
    return {f["key"] for f in data.get("findings", [])}


def finding(data, key):
    return next(f for f in data["findings"] if f["key"] == key)


# --------------------------------------------------------------------------
# A project in step is quiet
# --------------------------------------------------------------------------

def test_an_up_to_date_project_reports_no_file_drift(tmp_path):
    _, data = run(project(tmp_path, stamp="2.3.1"))
    assert "stale-framework-files" not in keys(data)
    assert "edited-framework-files" not in keys(data)


def test_identical_files_are_never_reported_merely_for_being_old(tmp_path):
    """Staleness is a content difference, not an old version stamp."""
    _, data = run(project(tmp_path, stamp="2.0.0"))
    assert "stale-framework-files" not in keys(data), \
        "a behind-stamp project whose files match the plugin has no file drift"


# --------------------------------------------------------------------------
# Stale files are found and refreshed
# --------------------------------------------------------------------------

def test_a_stale_schema_is_detected(tmp_path):
    """The case that matters most: a stale schema validates the wrong shape."""
    root = project(tmp_path)
    (root / ".archflow" / "schemas" / "release-schema.yaml").write_text("stale: true\n")
    code, data = run(root)
    assert code == 1
    assert "schemas/release-schema.yaml" in finding(data, "stale-framework-files")["files"]


def test_stale_files_are_found_across_every_shipped_location(tmp_path):
    root = project(tmp_path)
    for rel in ("instructions.md", "reference.md", "workflow.md", "stack-detection.md",
                "phases/phase-3-implementation.md", "schemas/roadmap-schema.yaml",
                "design-systems/shadcn.md", "stacks/native-mobile.yaml"):
        (root / ".archflow" / rel).write_text("stale\n")
    _, data = run(root)
    found = set(finding(data, "stale-framework-files")["files"])
    for rel in ("instructions.md", "reference.md", "workflow.md", "stack-detection.md",
                "phases/phase-3-implementation.md", "schemas/roadmap-schema.yaml",
                "design-systems/shadcn.md", "stacks/native-mobile.yaml"):
        assert rel in found, f"{rel} is shipped but its staleness is invisible"


def test_apply_refreshes_them_to_match_the_plugin(tmp_path):
    root = project(tmp_path)
    for rel in ("instructions.md", "schemas/release-schema.yaml"):
        (root / ".archflow" / rel).write_text("stale\n")
    code, _ = run(root, "--apply")
    assert code == 0
    for rel in ("instructions.md", "schemas/release-schema.yaml"):
        assert (root / ".archflow" / rel).read_bytes() == (SKILL / rel).read_bytes()


def test_the_original_is_backed_up_before_being_overwritten(tmp_path):
    root = project(tmp_path)
    (root / ".archflow" / "instructions.md").write_text("MY OLD COPY\n")
    run(root, "--apply")
    backups = list((root / ".archflow").glob("backup-upgrade-*/instructions.md"))
    assert backups, "a refresh with no backup is unrecoverable"
    assert backups[0].read_text() == "MY OLD COPY\n"


# --------------------------------------------------------------------------
# What must never be touched
# --------------------------------------------------------------------------

def test_a_file_the_plugin_does_not_ship_is_left_alone(tmp_path):
    """A design system or stack profile the user wrote is not the plugin's business."""
    root = project(tmp_path)
    mine = root / ".archflow" / "design-systems" / "acme-inhouse.md"
    mine.write_text("our tokens\n")
    (root / ".archflow" / "instructions.md").write_text("stale\n")
    _, data = run(root)
    assert "design-systems/acme-inhouse.md" not in finding(data, "stale-framework-files")["files"]
    run(root, "--apply")
    assert mine.read_text() == "our tokens\n", "the user's own file was modified"
    assert mine.exists()


def test_an_edit_on_an_up_to_date_project_is_reported_not_overwritten(tmp_path):
    """The outcome worse than staleness: silently discarding a deliberate edit."""
    root = project(tmp_path, stamp="2.3.1")
    edited = root / ".archflow" / "instructions.md"
    edited.write_text("our team's extra rule\n")
    code, data = run(root)
    assert code == 1
    assert "edited-framework-files" in keys(data)
    assert "stale-framework-files" not in keys(data)
    f = finding(data, "edited-framework-files")
    assert f["fixable"] is False and f["fix_by"] == "user"

    run(root, "--apply")
    assert edited.read_text() == "our team's extra rule\n", "a local edit was overwritten"


def test_an_unstamped_project_is_treated_as_behind(tmp_path):
    """No stamp means it has never been reconciled, so a difference is staleness."""
    root = project(tmp_path, stamp=None)
    (root / ".archflow" / "instructions.md").write_text("stale\n")
    _, data = run(root)
    assert "stale-framework-files" in keys(data)


# --------------------------------------------------------------------------
# Ordering
# --------------------------------------------------------------------------

def test_the_stamp_is_written_after_the_refresh_it_describes(tmp_path):
    """The stamp is the signal the next run reads to tell stale from edited.

    Stamping before refreshing would make the next run classify anything still
    stale as a deliberate edit, and it would never be repaired.
    """
    root = project(tmp_path)
    (root / ".archflow" / "instructions.md").write_text("stale\n")
    _, data = run(root, "--apply")
    applied = " | ".join(data["applied"])
    assert "refreshed" in applied and "stamped" in applied
    assert applied.index("refreshed") < applied.index("stamped")
    # And the next run is clean, which is the property that ordering buys.
    code, data2 = run(root)
    assert "stale-framework-files" not in keys(data2)
    assert "edited-framework-files" not in keys(data2)


# --------------------------------------------------------------------------
# Absence is still the other detector's job
# --------------------------------------------------------------------------

def test_a_missing_file_is_reported_as_missing_not_stale(tmp_path):
    root = project(tmp_path)
    (root / ".archflow" / "workflow.md").unlink()
    _, data = run(root)
    assert "missing-framework-files" in keys(data)
    assert "workflow.md" in finding(data, "missing-framework-files")["files"]
    stale = finding(data, "stale-framework-files")["files"] if "stale-framework-files" in keys(data) else []
    assert "workflow.md" not in stale


def test_deleting_a_file_is_how_a_user_restores_it(tmp_path):
    """The escape hatch the edited-files finding tells the user about."""
    root = project(tmp_path, stamp="2.3.1")
    (root / ".archflow" / "instructions.md").unlink()
    run(root, "--apply")
    assert (root / ".archflow" / "instructions.md").read_bytes() == (SKILL / "instructions.md").read_bytes()
