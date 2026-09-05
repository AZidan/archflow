"""Tests for the v1.0 -> v2.0 migration.

migrate.py rewrites a project's entire planning state. It is the one script in
the repo where a silent mistake destroys user data, so the bar is that its
output validates against the v2.0 schemas rather than merely being produced.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
MIGRATE = REPO / "plugin" / "scripts" / "migrate.py"
VALIDATOR = REPO / "plugin" / "scripts" / "validate_archflow.py"
V1_FIXTURE = REPO / "tests" / "fixtures" / "v1-project"


@pytest.fixture
def v1_project(tmp_path):
    """A throwaway copy of the v1 fixture, with schemas, in a git repo."""
    proj = tmp_path / "proj"
    shutil.copytree(V1_FIXTURE, proj)
    shutil.copytree(REPO / ".archflow" / "schemas", proj / ".archflow" / "schemas")
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1"],
        cwd=proj, check=True,
    )
    return proj


def run_migrate(proj, *flags):
    return subprocess.run(
        [sys.executable, str(MIGRATE), "--path", str(proj), *flags],
        capture_output=True, text=True,
    )


def load(p):
    return yaml.safe_load(Path(p).read_text())


# --------------------------------------------------------------------------

def test_dry_run_changes_nothing(v1_project):
    before = (v1_project / ".archflow" / "roadmap.yaml").read_text()
    proc = run_migrate(v1_project, "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert (v1_project / ".archflow" / "roadmap.yaml").read_text() == before
    assert not (v1_project / ".archflow" / "releases").exists()


def test_apply_produces_the_v2_layout(v1_project):
    proc = run_migrate(v1_project, "--apply")
    assert proc.returncode == 0, proc.stderr
    af = v1_project / ".archflow"
    assert (af / "roadmap.yaml").exists()
    assert (af / "releases").is_dir(), "releases/ was not created"
    assert list((af / "releases").glob("*.yaml")), "no release files were written"


def test_v1_keys_are_gone(v1_project):
    run_migrate(v1_project, "--apply")
    roadmap = load(v1_project / ".archflow" / "roadmap.yaml")
    assert "phases" not in roadmap, "v1.0 phases: survived the migration"
    assert "sprints" not in roadmap, "v1.0 sprints: survived the migration"


def test_roadmap_becomes_an_index(v1_project):
    run_migrate(v1_project, "--apply")
    roadmap = load(v1_project / ".archflow" / "roadmap.yaml")
    assert "releases" in roadmap
    for ref in roadmap.get("releases") or []:
        assert "stories" not in ref, "roadmap.yaml is an index; stories live in the release file"


def test_no_story_is_lost(v1_project):
    """A story that vanishes in migration is silent data loss."""
    src = load(V1_FIXTURE / ".archflow" / "roadmap.yaml")
    expected = {
        s["id"] for epic in src["epics"] for s in epic.get("stories", [])
    }
    run_migrate(v1_project, "--apply")
    found = set()
    releases = v1_project / ".archflow" / "releases"
    for f in list(releases.rglob("*.yaml")):
        doc = load(f) or {}
        for s in doc.get("stories") or []:
            found.add(s["id"])
    backlog = v1_project / ".archflow" / "backlog.yaml"
    if backlog.exists():
        doc = load(backlog) or {}
        for epic in doc.get("epics") or []:
            for s in epic.get("stories") or []:
                found.add(s["id"])
    assert expected <= found, f"stories lost in migration: {sorted(expected - found)}"


def test_migrated_output_validates_against_the_v2_schemas(v1_project):
    """The migration's real contract: what it writes must be loadable by v2.0."""
    run_migrate(v1_project, "--apply")
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(v1_project)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"migrated project fails validation:\n{proc.stdout}\n{proc.stderr}"


def test_migrate_refuses_a_project_with_no_roadmap(tmp_path):
    (tmp_path / ".archflow").mkdir()
    proc = run_migrate(tmp_path, "--apply")
    assert proc.returncode != 0
    assert "roadmap.yaml not found" in (proc.stderr + proc.stdout)


# --------------------------------------------------------------------------
# Variant B: top-level sprints with inline story objects
# --------------------------------------------------------------------------

V1B_FIXTURE = REPO / "tests" / "fixtures" / "v1-project-variant-b"


@pytest.fixture
def v1b_project(tmp_path):
    proj = tmp_path / "projb"
    shutil.copytree(V1B_FIXTURE, proj)
    shutil.copytree(REPO / ".archflow" / "schemas", proj / ".archflow" / "schemas")
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v1b"],
        cwd=proj, check=True,
    )
    return proj


def test_variant_b_migrates_and_validates(v1b_project):
    proc = run_migrate(v1b_project, "--apply")
    assert proc.returncode == 0, proc.stderr
    roadmap = load(v1b_project / ".archflow" / "roadmap.yaml")
    assert "sprints" not in roadmap
    out = subprocess.run(
        [sys.executable, str(VALIDATOR), str(v1b_project)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"


def test_variant_b_keeps_every_story(v1b_project):
    src = load(V1B_FIXTURE / ".archflow" / "roadmap.yaml")
    expected = {s["id"] for sp in src["sprints"] for s in sp.get("stories", [])}
    run_migrate(v1b_project, "--apply")
    found = set()
    for f in (v1b_project / ".archflow").rglob("*.yaml"):
        if "schemas" in f.parts or "backup-v1" in f.parts:
            continue
        doc = load(f) or {}
        if isinstance(doc, dict):
            for s in doc.get("stories") or []:
                found.add(s.get("id"))
            for epic in doc.get("epics") or []:
                for s in epic.get("stories") or []:
                    found.add(s.get("id"))
    assert expected <= found, f"stories lost: {sorted(expected - found)}"
