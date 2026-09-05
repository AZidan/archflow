"""Tests for the safety-envelope hooks.

The guard's value is entirely in what it blocks, so most of these assert a
block. The rest assert what it must NOT block: a guard that fights ordinary work
gets switched off, and then it protects nothing.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "plugin" / "hooks" / "guard-git.mjs"
CHECK_STATE = REPO / "plugin" / "hooks" / "check-state.mjs"

ALLOW, BLOCK = 0, 2


def guard(command, cwd, tool="Bash"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}, "cwd": str(cwd)})
    proc = subprocess.run(
        ["node", str(GUARD)], input=payload, capture_output=True, text=True, timeout=10
    )
    return proc.returncode, proc.stderr


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/feature-x\n")
    (tmp_path / ".archflow").mkdir()
    return tmp_path


@pytest.fixture
def autopilot(project):
    d = project / ".archflow" / "autopilot"
    d.mkdir()
    (d / "2026-09-06-1.yaml").write_text(
        "run_id: 2026-09-06-1\nstatus: running\nbase_branch: main\nrun_branch: overnight\n"
    )
    return project


def on_main(project):
    (project / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    return project


# --------------------------------------------------------------------------
# Scope: Archflow projects only
#
# Installing a development framework is not consent to a global git policy. The
# guard ships with the plugin and therefore loads in every session, so it has to
# decline jurisdiction itself.
# --------------------------------------------------------------------------

def test_guard_is_silent_in_a_non_archflow_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    code, err = guard("git push --force origin main", tmp_path)
    assert code == ALLOW, "the guard must not police repos that never opted in"
    assert err.strip() == ""


def test_guard_is_silent_in_a_plain_directory(tmp_path):
    code, _ = guard("git push --force origin main", tmp_path)
    assert code == ALLOW


def test_block_message_names_the_project(project):
    code, err = guard("git push --force origin main", project)
    assert code == BLOCK
    assert project.name in err, "a block must say which project it applies to"


# --------------------------------------------------------------------------
# Blocked in an Archflow project, run or no run
# --------------------------------------------------------------------------

def test_force_push_to_main_is_always_blocked(project):
    code, err = guard("git push --force origin main", project)
    assert code == BLOCK
    assert "force-push" in err


def test_force_with_lease_to_main_is_blocked(project):
    code, _ = guard("git push --force-with-lease origin main", project)
    assert code == BLOCK


def test_force_push_to_a_feature_branch_is_allowed(project):
    """Rewriting your own branch is normal work."""
    code, _ = guard("git push --force origin feature-x", project)
    assert code == ALLOW


# --------------------------------------------------------------------------
# Blocked only during an autopilot run
# --------------------------------------------------------------------------

def test_push_to_main_blocked_during_a_run(autopilot):
    code, err = guard("git push origin main", autopilot)
    assert code == BLOCK
    assert "autopilot" in err
    assert "2026-09-06-1" in err, "the block should name the run so it can be resolved"


def test_push_to_main_allowed_outside_a_run(project):
    code, _ = guard("git push origin main", project)
    assert code == ALLOW, "outside a run the approval gates are the control"


def test_checkout_main_blocked_during_a_run(autopilot):
    code, err = guard("git checkout main", autopilot)
    assert code == BLOCK
    assert "protected branch" in err


def test_switch_main_blocked_during_a_run(autopilot):
    code, _ = guard("git switch main", autopilot)
    assert code == BLOCK


def test_merge_into_main_blocked_during_a_run(autopilot):
    code, err = guard("git merge overnight", on_main(autopilot))
    assert code == BLOCK
    assert "merge_to_main" in err


def test_merge_on_a_feature_branch_allowed_during_a_run(autopilot):
    """Autopilot merges subtask into task into the run branch. That is its job."""
    code, _ = guard("git merge subtask-1", autopilot)
    assert code == ALLOW


def test_compound_command_is_caught(autopilot):
    """The setup move and the merge in one line must not slip through."""
    code, _ = guard("git checkout main && git merge overnight", autopilot)
    assert code == BLOCK


def test_finished_run_does_not_guard(project):
    d = project / ".archflow" / "autopilot"
    d.mkdir()
    (d / "old.yaml").write_text("run_id: old\nstatus: finished\n")
    code, _ = guard("git push origin main", project)
    assert code == ALLOW


def test_aborted_run_does_not_guard(project):
    d = project / ".archflow" / "autopilot"
    d.mkdir()
    (d / "old.yaml").write_text("run_id: old\nstatus: aborted\n")
    code, _ = guard("git push origin main", project)
    assert code == ALLOW


# --------------------------------------------------------------------------
# It must stay out of the way
# --------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "git status",
    "git add -A",
    "git commit -m 'work'",
    "git push origin feature-x",
    "git log --oneline -5",
    "git diff main",                      # reading main is not touching it
    "npm test",
    "echo 'git push origin main'",        # a string, not an invocation
])
def test_ordinary_commands_are_allowed(autopilot, cmd):
    code, _ = guard(cmd, autopilot)
    assert code == ALLOW, f"guard blocked ordinary command: {cmd}"


def test_non_bash_tools_are_ignored(autopilot):
    code, _ = guard("git push origin main", autopilot, tool="Edit")
    assert code == ALLOW


def test_malformed_input_fails_open():
    proc = subprocess.run(["node", str(GUARD)], input="not json", capture_output=True, text=True)
    assert proc.returncode == ALLOW


def test_empty_input_fails_open():
    proc = subprocess.run(["node", str(GUARD)], input="", capture_output=True, text=True)
    assert proc.returncode == ALLOW


def test_guard_is_fast(autopilot):
    import time
    start = time.monotonic()
    guard("git push origin main", autopilot)
    assert time.monotonic() - start < 2.0, "the guard runs on every Bash call; it must stay cheap"


# --------------------------------------------------------------------------
# The Stop hook is advisory
# --------------------------------------------------------------------------

def run_check_state(cwd):
    return subprocess.run(
        ["node", str(CHECK_STATE)],
        capture_output=True, text=True, timeout=10,
        env={"PATH": __import__("os").environ["PATH"],
             "CLAUDE_PROJECT_DIR": str(cwd),
             "CLAUDE_PLUGIN_ROOT": str(REPO / "plugin")},
    )


def test_check_state_is_silent_without_a_project(tmp_path):
    proc = run_check_state(tmp_path)
    assert proc.returncode == 0
    assert proc.stderr.strip() == ""


def test_check_state_warns_but_never_blocks():
    invalid = REPO / "tests" / "fixtures" / "invalid-project"
    proc = run_check_state(invalid)
    assert proc.returncode == 0, "the Stop hook is advisory and must never block"
    assert "drifted" in proc.stderr


def test_check_state_quiet_on_a_valid_project():
    valid = REPO / "tests" / "fixtures" / "valid-project"
    proc = run_check_state(valid)
    assert proc.returncode == 0
    assert proc.stderr.strip() == ""


def test_hooks_json_registers_both_hooks():
    hooks = json.loads((REPO / "plugin" / "hooks" / "hooks.json").read_text())["hooks"]
    assert "PreToolUse" in hooks and "Stop" in hooks
    pre = json.dumps(hooks["PreToolUse"])
    assert "guard-git.mjs" in pre and '"Bash"' in pre
    assert "check-state.mjs" in json.dumps(hooks["Stop"])
