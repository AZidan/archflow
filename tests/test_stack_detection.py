"""Guards on stack detection — the shared procedure, and /archflow:doctor --fix Step 5c.

Detection decides what every agent believes about the project, so the rules that
matter here are the ones about restraint: write null rather than infer, and never
overwrite a value a human set. Most of these assert a refusal.

The procedure is defined once and read by two commands. That is the same rule the
Phase 3 dispatch payload follows, for the same reason: two copies of a procedure
become two different answers about the same repo.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHARED = REPO / "plugin" / "skills" / "archflow" / "stack-detection.md"
MIRROR = REPO / ".archflow" / "stack-detection.md"
DOCTOR = REPO / "plugin" / "commands" / "doctor.md"
ONBOARD = REPO / "plugin" / "commands" / "onboard.md"
UPGRADE = REPO / "plugin" / "scripts" / "upgrade_archflow.py"


def flat(path):
    """Whitespace-collapsed, so prose assertions survive rewrapping."""
    return re.sub(r"\s+", " ", path.read_text())


# --------------------------------------------------------------------------
# Defined once
# --------------------------------------------------------------------------

def test_the_shared_procedure_exists_in_both_mirrors():
    assert SHARED.exists() and MIRROR.exists()
    assert SHARED.read_text() == MIRROR.read_text()


def test_both_commands_point_at_it():
    for cmd in (DOCTOR, ONBOARD):
        assert "skills/archflow/stack-detection.md" in cmd.read_text(), \
            f"{cmd.name} does not read the shared detection procedure"


def test_neither_command_restates_the_evidence_list():
    """The manifests and lockfiles live in one place. Two lists drift."""
    for cmd in (DOCTOR, ONBOARD):
        body = cmd.read_text()
        # Probes must be unique to the evidence list. `build.gradle` is not: doctor
        # Step 2 reads it for the e2e runner, and onboard reads it to detect a design
        # system. Both are different questions asked of the same file.
        for probe in ("Gemfile", "pnpm-lock.yaml", "pyproject.toml", "Cargo.toml"):
            assert probe not in body, (
                f"{cmd.name} restates the evidence list ({probe}). "
                "It belongs in stack-detection.md only."
            )


def test_the_shared_procedure_actually_carries_the_evidence_list():
    """Guards against the previous test passing because nobody documents it."""
    body = SHARED.read_text()
    for probe in ("package.json", "pnpm-lock.yaml", "go.mod", "Podfile", "build.gradle"):
        assert probe in body


# --------------------------------------------------------------------------
# The null rule — the difference between detection and guessing
# --------------------------------------------------------------------------

def test_null_is_the_answer_when_evidence_is_absent():
    body = flat(SHARED)
    assert "Write `null` for anything the evidence does not support." in body


def test_the_specific_inferences_that_are_banned_are_named():
    """A rule with examples survives contact with a plausible-looking repo."""
    body = flat(SHARED)
    assert "Do not infer a database from an ORM" in body
    assert "Do not infer an e2e runner from the presence of a `tests/` folder" in body


def test_confidence_is_not_a_licence_to_guess():
    assert "Detection confidence is not a reason to guess" in flat(SHARED)


def test_detection_must_name_its_evidence():
    body = flat(SHARED)
    assert "Name the evidence for every non-null field" in body


# --------------------------------------------------------------------------
# The conflict rule — never overwrite a human
# --------------------------------------------------------------------------

def test_a_disagreement_is_a_question_not_a_merge():
    body = flat(SHARED)
    assert "a decision, not a merge" in body
    assert "Never overwrite silently and never pick one on the user's behalf" in body


def test_the_reasons_a_human_value_may_beat_the_manifests_are_stated():
    """Without these, "the repo says otherwise" reads as sufficient grounds to rewrite."""
    for body in (flat(SHARED), flat(DOCTOR)):
        assert "mid-migration" in body
        assert "monorepo" in body


def test_doctor_asks_one_field_at_a_time():
    body = flat(DOCTOR)
    assert "one field at a time" in body
    assert "never batch them into a single" in body


# --------------------------------------------------------------------------
# Step 5c
# --------------------------------------------------------------------------

def test_step_5c_exists_and_is_last():
    body = DOCTOR.read_text()
    assert "## Step 5c — Stack detection" in body
    assert body.index("## Step 5c") > body.index("## Step 5b"), "5c must run after 5b"
    assert body.index("## Step 5c") < body.index("## Step 6"), "5c is a fix step, not a report step"


def test_step_5c_is_fix_only():
    body = flat(DOCTOR)
    start = body.index("## Step 5c")
    section = body[start:body.index("## Step 6", start)]
    assert "only** with `--fix`" in section or "only with `--fix`" in section
    assert "No `--fix`." in section, "the skip conditions must name the no-fix case"


def test_step_5c_skips_when_there_is_nowhere_to_write():
    section = flat(DOCTOR)
    assert "No `.archflow/project-settings.yaml`" in section


def test_step_5c_sorts_every_field_into_a_bucket():
    """The three-bucket table IS the step; without it this is 'update the stack'."""
    body = flat(DOCTOR)
    start = body.index("## Step 5c")
    section = body[start:body.index("## Step 6", start)]
    for bucket in ("Propose to fill", "Nothing. Do not rewrite a file to change nothing", "**Ask.**"):
        assert bucket in section, f"the bucket table is missing: {bucket}"


def test_step_5c_backs_up_and_validates_like_every_other_repair():
    body = flat(DOCTOR)
    start = body.index("## Step 5c")
    section = body[start:body.index("## Step 6", start)]
    assert "backup-upgrade-" in section
    assert "run the validator" in section
    assert "Show the diff and get approval" in section


def test_an_absent_lane_is_not_a_gap():
    """A backend_only project has no web.* to fill, and must not be nagged about it."""
    assert "absent lanes are not gaps" in flat(DOCTOR)


# --------------------------------------------------------------------------
# The rule this replaced
# --------------------------------------------------------------------------

def test_doctor_no_longer_claims_a_missing_stack_is_unfixable():
    assert "**Not auto-fixable**" not in DOCTOR.read_text()


def test_doctor_still_refuses_to_invent_a_value():
    """The narrow rule stayed; only the line about 'picks a stack' moved."""
    body = flat(DOCTOR)
    assert "invents a value the repo does not evidence" in body
    assert "never installs anything" in body


# --------------------------------------------------------------------------
# Shipped files reach existing projects
#
# A file added to the skill but not to FRAMEWORK_DIRS/FRAMEWORK_FILES is shipped
# to new projects and never copied into old ones. stack-detection.md was exactly
# that until this test was written.
# --------------------------------------------------------------------------

# Not project copies: the plugin's own manifest, and the two files the session
# hook reads from the plugin rather than from .archflow/.
NOT_COPIED = {"SKILL.md", "mcp-registry.yaml", "instructions.md", "reference.md"}


def test_every_shipped_framework_file_is_copied_into_projects():
    src = UPGRADE.read_text()
    dirs = re.search(r"FRAMEWORK_DIRS = \[(.*?)\]", src, re.S).group(1)
    files = re.search(r"FRAMEWORK_FILES = \[(.*?)\]", src, re.S).group(1)
    covered = set(re.findall(r'"([^"]+)"', dirs)) | set(re.findall(r'"([^"]+)"', files))

    skill = REPO / "plugin" / "skills" / "archflow"
    shipped = {p.name for p in skill.iterdir() if p.name != ".DS_Store"}
    uncovered = sorted(shipped - covered - NOT_COPIED)
    assert not uncovered, (
        f"shipped in the skill but never copied into an existing project: {uncovered}. "
        "Add each to FRAMEWORK_FILES (a file) or FRAMEWORK_DIRS (a directory) in "
        "upgrade_archflow.py, or to NOT_COPIED here if that is deliberate."
    )


def test_stack_detection_is_in_the_copy_list():
    assert '"stack-detection.md"' in UPGRADE.read_text()
