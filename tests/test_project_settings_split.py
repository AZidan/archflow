"""Guards on the v2.1 split of current-phase.yaml.

current-phase.yaml had accreted into two things: a CURSOR rewritten at every
phase transition, and SETTINGS that change almost never. Mixing them meant every
phase transition dirtied the file holding the project's stack config, so a real
settings change was buried in phase churn — and the filename described eight of
seventeen fields.

v2.1 moves project_type, api_contract_path, stack and optional_agents into
project-settings.yaml. `mode` deliberately stays: it is read on nearly every
operation and is already mirrored in roadmap.yaml.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SCHEMAS = REPO / ".archflow" / "schemas"
CURSOR = SCHEMAS / "current-phase-schema.yaml"
SETTINGS = SCHEMAS / "project-settings-schema.yaml"
UPGRADE = REPO / "plugin" / "scripts" / "upgrade_archflow.py"
VALIDATOR = REPO / "plugin" / "scripts" / "validate_archflow.py"

MOVED = {"project_type", "api_contract_path", "stack", "optional_agents"}


def props(path):
    return set(yaml.safe_load(path.read_text())["properties"])


# --------------------------------------------------------------------------
# The split itself
# --------------------------------------------------------------------------

def test_settings_schema_exists_in_both_mirrors():
    assert SETTINGS.exists()
    assert (REPO / "plugin" / "skills" / "archflow" / "schemas" / SETTINGS.name).exists()


def test_moved_fields_left_the_cursor():
    leftover = MOVED & props(CURSOR)
    assert not leftover, f"still in current-phase-schema: {sorted(leftover)}"


def test_moved_fields_arrived_in_settings():
    missing = MOVED - props(SETTINGS)
    assert not missing, f"missing from project-settings-schema: {sorted(missing)}"


def test_mode_stayed_in_the_cursor():
    """Read on nearly every operation, and already mirrored in roadmap.yaml."""
    assert "mode" in props(CURSOR)
    assert "mode" not in props(SETTINGS)


def test_the_cursor_no_longer_requires_project_type():
    required = yaml.safe_load(CURSOR.read_text())["required"]
    assert "project_type" not in required
    assert "phase" in required and "mode" in required


def test_settings_declares_the_schema_version():
    s = yaml.safe_load(SETTINGS.read_text())
    assert "schema_version" in s["required"]
    rule = s["properties"]["schema_version"]
    assert rule.get("const") == "2.1" or rule.get("enum") == ["2.1"], \
        f"schema_version rule is {rule}, expected 2.1"


def test_both_schema_version_rules_use_the_same_keyword():
    """One rule, two spellings, is how one of them ends up unenforced."""
    a = yaml.safe_load(SETTINGS.read_text())["properties"]["schema_version"]
    b = yaml.safe_load((SCHEMAS / "roadmap-schema.yaml").read_text())
    b = b["roadmap"]["properties"]["schema_version"]
    assert set(a) & {"const", "enum"} == set(b) & {"const", "enum"}, \
        f"schema_version expressed as {set(a) & {'const','enum'}} vs {set(b) & {'const','enum'}}"


def test_roadmap_schema_version_bumped():
    """Assert the CONSTRAINT, not that the string appears somewhere in the file.

    The previous version of this test checked that "2.1" occurred anywhere and that
    no `schema_version: "2.0"` line existed. Both were true while the real rule,
    `const: "2.0"`, sat untouched — so the test written to catch this bug passed
    while the bug was live.
    """
    doc = yaml.safe_load((SCHEMAS / "roadmap-schema.yaml").read_text())
    rule = doc["roadmap"]["properties"]["schema_version"]
    assert rule.get("const") == "2.1" or rule.get("enum") == ["2.1"], \
        f"roadmap schema_version constraint is {rule}, expected 2.1"


def test_every_writer_writes_the_current_schema_version():
    """A writer disagreeing with the constraint produces files that fail validation."""
    offenders = []
    # Scripts write these files too. Globbing only *.md is why plugin/scripts/migrate.py
    # kept writing 2.0 after the bump, and why the Studio bundle was never noticed.
    candidates = (list(REPO.glob("plugin/**/*.md")) + list(REPO.glob(".archflow/**/*.md"))
                  + list(REPO.glob("plugin/scripts/*.py")))
    for path in candidates:
        if "/schemas/" in str(path):
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            # A line offering BOTH versions is detection, not a write.
            if line.count("2.0") and line.count("2.1"):
                continue
            m = re.search(r'schema_version:\s*["\']?([0-9]+\.[0-9]+)', line)
            if m and m.group(1) != "2.1" and "1.0" not in line and "v1" not in line:
                offenders.append(f"{path.relative_to(REPO)}:{i}: writes {m.group(1)}")
    assert not offenders, "writers disagree with the schema:\n" + "\n".join(offenders)


def test_the_validator_enforces_const():
    """Run it. The bump is decoration if the dialect ignores the keyword it uses.

    An earlier version of this asserted that the string "const" appeared in the
    validator's source, which stayed true when the check itself was disabled.
    """
    import json
    import shutil
    import subprocess
    import sys
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        af = Path(tmp) / ".archflow"
        (af / "schemas").mkdir(parents=True)
        for sc in SCHEMAS.glob("*.yaml"):
            shutil.copy(sc, af / "schemas" / sc.name)
        (af / "roadmap.yaml").write_text(
            'schema_version: "2.0"\nproject: t\nproject_type: fullstack\nmode: quick\n'
            "epics: []\nreleases: []\nshipped: []\n"
        )
        proc = subprocess.run([sys.executable, str(VALIDATOR), tmp, "--json"],
                              capture_output=True, text=True)
        data = json.loads(proc.stdout)
        assert any(v["field"] == "schema_version" for v in data["violations"]), \
            "a schema_version violating the const was accepted; const is not enforced"


def test_validator_checks_the_new_file():
    """Assert it is an actual target, not that the string appears in a comment."""
    import subprocess, sys, tempfile, shutil, json
    with tempfile.TemporaryDirectory() as tmp:
        af = Path(tmp) / ".archflow"
        (af / "schemas").mkdir(parents=True)
        for sc in SCHEMAS.glob("*.yaml"):
            shutil.copy(sc, af / "schemas" / sc.name)
        (af / "project-settings.yaml").write_text('schema_version: "9.9"\nproject_type: fullstack\n')
        proc = subprocess.run([sys.executable, str(VALIDATOR), tmp, "--json"],
                              capture_output=True, text=True)
        data = json.loads(proc.stdout)
        assert any("project-settings.yaml" in v["file"] for v in data["violations"]), \
            "the validator does not actually validate project-settings.yaml"


def _docs():
    """Every prose file a reader might follow, including the repo root.

    The previous version globbed only plugin/** and .archflow/**, so README.md and
    CONTRIBUTING.md were never scanned and kept stale instructions.
    """
    seen = {}
    # Files a reader FOLLOWS. CHANGELOG is history and legitimately names the old
    # shape; tests describe what moved and would flag themselves.
    skip = {"CHANGELOG.md"}
    for pattern in ("plugin/**/*.md", ".archflow/**/*.md", "*.md"):
        for path in REPO.glob(pattern):
            if "/schemas/" in str(path) or "/dist/" in str(path) or path.name in skip:
                continue
            seen[path] = path.read_text()
    return seen


def test_no_doc_still_reads_a_moved_field_from_the_cursor():
    """The migration is worthless if the prose still points at the old file.

    Windowed, not line-based: a reference wrapped across two lines was invisible to
    the previous version, which is how two stale passages in reference.md survived.
    Checks all four moved fields — `stack` was missing from the earlier list.
    """
    offenders = []
    for path, body in _docs().items():
        # Paragraphs, not a fixed line window. A reference wrapped across lines was
        # invisible to a line-based check, and a fixed window cuts sentences in half
        # — it flagged the migration instructions in doctor.md, which name the old
        # file and the new one four lines apart.
        # Split keeping exact positions: "A\n\n\nB" must not report B one line early.
        cursor = 0
        for para in re.split(r"\n\s*\n", body):
            idx = body.find(para, cursor)
            if idx < 0:
                idx = cursor
            offset = body[:idx].count("\n") + 1
            cursor = idx + len(para)
            if "current-phase.yaml" in para and "project-settings.yaml" not in para:
                for field in MOVED:
                    if re.search(rf"\b{re.escape(field)}\b", para):
                        offenders.append(f"{path.relative_to(REPO)}:{offset}: {field}")
                        break
    assert not offenders, "still read a moved field from the cursor:\n" + "\n".join(sorted(set(offenders)))


# --------------------------------------------------------------------------
# The migration
# --------------------------------------------------------------------------

@pytest.fixture
def v20(tmp_path):
    af = tmp_path / ".archflow"
    (af / "schemas").mkdir(parents=True)
    for s in SCHEMAS.glob("*.yaml"):
        shutil.copy(s, af / "schemas" / s.name)
    (af / "current-phase.yaml").write_text(
        "phase: 3\nphase_name: Implementation\nphase_file: phases/phase-3-implementation.md\n"
        "project_type: fullstack\nmode: quick\nactive_release: checkout\nonboarded: true\n"
        "api_contract_path: docs/api-contract.md\n"
        "stack:\n  language: typescript\n  backend: {framework: fastapi, database: postgresql}\n"
        "optional_agents:\n  code-reviewer: [story_review]\n"
        "phases_completed: [1, 2]\n"
    )
    return tmp_path


def run_upgrade(project, *flags):
    return subprocess.run(
        [sys.executable, str(UPGRADE), str(project), "--plugin-root", str(REPO / "plugin"),
         "--version", "9.9.9", *flags],
        capture_output=True, text=True,
    )


def test_the_script_detects_the_split_but_does_not_perform_it(v20):
    """The split is done by the agent following doctor.md, not by this script.

    current-phase.yaml is hand-editable and its shape varies per project. A script
    either round-trips the YAML and destroys every comment, or pattern-matches and
    eventually gets a nesting wrong. Detection is deterministic and worth scripting;
    the edit is not.
    """
    import json
    proc = run_upgrade(v20, "--json")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    finding = next(f for f in data["findings"] if f["key"] == "split-project-settings")
    assert finding["fixable"] is False, "the script must not claim it can do this"
    assert finding["fix_by"] == "agent", \
        "the split is repaired by doctor --fix (the agent), not left to the user"
    assert "doctor --fix" in finding["detail"]


def test_the_script_leaves_the_cursor_untouched(v20):
    """Including any comments in it — the reason this is not scripted."""
    (v20 / ".archflow" / "current-phase.yaml").write_text(
        (v20 / ".archflow" / "current-phase.yaml").read_text() + "# a hand-written note\n"
    )
    before = (v20 / ".archflow" / "current-phase.yaml").read_text()
    run_upgrade(v20, "--apply")
    after = (v20 / ".archflow" / "current-phase.yaml").read_text()
    assert "project_type" in after, "the script must not move settings"
    assert "# a hand-written note" in after, "comments must survive"
    for key in MOVED:
        if key in before:
            assert key in after, f"the script removed {key} from the cursor"
    assert not (v20 / ".archflow" / "project-settings.yaml").exists(), \
        "the script must not create the settings file"


def test_apply_reports_the_split_as_still_to_do(v20):
    """It is not 'needs a decision' — doctor --fix does it, just not the script."""
    proc = run_upgrade(v20, "--apply")
    assert proc.returncode == 0
    assert "Still to do, following /archflow:doctor --fix" in proc.stdout
    assert "Needs a decision only you can make" not in proc.stdout


def test_doctor_owns_the_split_procedure():
    """If the script does not do it, the command file must say how."""
    doctor = (REPO / "plugin" / "commands" / "doctor.md").read_text()
    assert "splitting settings out of the cursor" in doctor.lower()
    for required in ("backup-upgrade", "project-settings.yaml", "get approval", "DIFFERENT values"):
        assert required in doctor, f"doctor.md's split procedure never mentions {required!r}"


def test_roadmap_bump_waits_for_the_split(v20):
    """Claiming 2.1 while the file is still v2.0-shaped would be a lie."""
    (v20 / ".archflow" / "roadmap.yaml").write_text(
        'schema_version: "2.0"\nproject: t\nproject_type: fullstack\nmode: quick\n'
        "epics: []\nreleases: []\nshipped: []\n"
    )
    run_upgrade(v20, "--apply")
    assert 'schema_version: "2.0"' in (v20 / ".archflow" / "roadmap.yaml").read_text(), \
        "the roadmap must not be bumped while settings are still stranded in the cursor"


def test_scripted_repairs_still_back_up_what_they_touch(v20):
    (v20 / ".archflow" / "roadmap.yaml").write_text('schema_version: "2.0"\nproject: t\n')
    # remove the settings so the roadmap bump is allowed to fire
    cp = v20 / ".archflow" / "current-phase.yaml"
    doc = yaml.safe_load(cp.read_text())
    for k in MOVED:
        doc.pop(k, None)
    cp.write_text(yaml.safe_dump(doc))
    run_upgrade(v20, "--apply")
    backups = list((v20 / ".archflow").glob("backup-upgrade-*"))
    assert backups, "no backup was written"
    assert (backups[0] / "roadmap.yaml").exists()
