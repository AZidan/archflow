"""Tests for the safety-envelope hooks.

The guard's value is entirely in what it blocks, so most of these assert a
block. The rest assert what it must NOT block: a guard that fights ordinary work
gets switched off, and then it protects nothing.
"""

import json
import subprocess
import sys
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


# --------------------------------------------------------------------------
# The upgrade notice (SessionStart)
#
# A project's .archflow/ is a copy that goes stale when the plugin updates. This
# is the only thing that tells the user before their first command rather than
# midway through a story.
# --------------------------------------------------------------------------

import json as _json
import os as _os

CHECK_UPGRADE = REPO / "plugin" / "hooks" / "check-upgrade.mjs"


def run_check_upgrade(cwd):
    return subprocess.run(
        ["node", str(CHECK_UPGRADE)],
        capture_output=True, text=True, timeout=15,
        env={"PATH": _os.environ["PATH"],
             "CLAUDE_PROJECT_DIR": str(cwd),
             "CLAUDE_PLUGIN_ROOT": str(REPO / "plugin"),
             # these tests are about drift, not releases; keep them off the network and the real cache
             "ARCHFLOW_NO_UPDATE_CHECK": "1"},
    )


@pytest.fixture
def stale_project(tmp_path):
    af = tmp_path / ".archflow"
    (af / "schemas").mkdir(parents=True)
    (af / "schemas" / "release-schema.yaml").write_text(
        (REPO / ".archflow" / "schemas" / "release-schema.yaml").read_text()
    )
    (af / "current-phase.yaml").write_text(
        "phase: 3\nphase_file: x\nproject_type: fullstack\nmode: quick\n"
        "tech_stack:\n  language: typescript\n  backend: nestjs\n"
    )
    return tmp_path


def _installed_version():
    return _json.loads(
        (REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text()
    )["version"]


def test_notice_fires_on_a_stale_project(stale_project):
    proc = run_check_upgrade(stale_project)
    assert proc.returncode == 0
    assert "behind the installed Archflow plugin" in proc.stdout
    assert "/archflow:doctor --fix" in proc.stdout


def test_notice_names_what_is_wrong(stale_project):
    out = run_check_upgrade(stale_project).stdout
    assert "tech_stack" in out
    assert "framework file" in out


def test_notice_is_silent_once_the_stamp_matches(stale_project):
    """--fix stamps plugin_version, and the same field silences the notice."""
    subprocess.run(
        [sys.executable, str(REPO / "plugin" / "scripts" / "upgrade_archflow.py"),
         str(stale_project), "--plugin-root", str(REPO / "plugin"),
         "--version", _installed_version(), "--apply"],
        capture_output=True, check=True,
    )
    proc = run_check_upgrade(stale_project)
    assert proc.stdout.strip() == "", "the notice should stop once the project is repaired"


def test_notice_is_silent_outside_an_archflow_project(tmp_path):
    proc = run_check_upgrade(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_notice_fast_path_is_cheap(tmp_path):
    """Runs on every session start. An up-to-date project must cost almost nothing."""
    import time
    af = tmp_path / ".archflow"
    af.mkdir()
    (af / "current-phase.yaml").write_text(
        f'phase: 1\nphase_file: x\nproject_type: fullstack\nmode: quick\n'
        f'plugin_version: "{_installed_version()}"\n'
    )
    start = time.monotonic()
    proc = run_check_upgrade(tmp_path)
    elapsed = time.monotonic() - start
    assert proc.stdout.strip() == ""
    assert elapsed < 1.5, f"fast path took {elapsed:.2f}s; it must not run the detector"


def test_upgrade_hook_registered_on_session_start():
    hooks = _json.loads((REPO / "plugin" / "hooks" / "hooks.json").read_text())["hooks"]
    assert "check-upgrade.mjs" in _json.dumps(hooks["SessionStart"])


# --------------------------------------------------------------------------
# Newer-release notice (hosts other than Claude Code)
#
# The adapters are copied files that nothing refreshes. The hook reads a cache
# and, when it is stale, refreshes it in a detached child. The hook itself must
# never wait on the network.
# --------------------------------------------------------------------------

import http.server as _http
import threading as _threading
import time as _time


def run_check_upgrade_as(cwd, host, cache_dir, extra=None):
    env = {"PATH": _os.environ["PATH"],
           "CLAUDE_PROJECT_DIR": str(cwd),
           "CLAUDE_PLUGIN_ROOT": str(REPO / "plugin"),
           "ARCHFLOW_CACHE_DIR": str(cache_dir),
           # never reach GitHub from a test; a refresh would fail fast and write nothing
           "ARCHFLOW_RELEASES_URL": "http://127.0.0.1:9/releases/latest"}
    if host:
        env["ARCHFLOW_HOST"] = host
    env.update(extra or {})
    return subprocess.run(["node", str(CHECK_UPGRADE)], capture_output=True, text=True, timeout=15, env=env)


@pytest.fixture
def current_project(tmp_path):
    """A project that is up to date with the installed plugin: the fast path."""
    af = tmp_path / ".archflow"
    af.mkdir()
    (af / "current-phase.yaml").write_text(
        f'phase: 1\nphase_file: x\nproject_type: fullstack\nmode: quick\n'
        f'plugin_version: "{_installed_version()}"\n'
    )
    return tmp_path


def _cache(tmp_path, tag, age_seconds=0):
    d = tmp_path / "cache"
    d.mkdir(exist_ok=True)
    (d / "latest.json").write_text(_json.dumps({"tag": tag, "checkedAt": int((_time.time() - age_seconds) * 1000)}))
    return d


def test_release_notice_names_the_newer_release_and_the_host(current_project, tmp_path):
    out = run_check_upgrade_as(current_project, "codex", _cache(tmp_path, "99.0.0")).stdout
    assert "Archflow 99.0.0 is available" in out
    assert "npx archflow-install --host codex" in out
    assert "doctor" in out


def test_release_notice_also_prints_alongside_the_drift_notice(stale_project, tmp_path):
    out = run_check_upgrade_as(stale_project, "cursor", _cache(tmp_path, "99.0.0")).stdout
    assert "Archflow 99.0.0 is available" in out
    assert "behind the installed Archflow plugin" in out


def test_release_notice_on_claude_code_names_the_plugin_update(current_project, tmp_path):
    """No ARCHFLOW_HOST means Claude Code: the fix is the plugin update, not the installer."""
    cache = _cache(tmp_path, "99.0.0")
    for host in (None, "claude"):
        out = run_check_upgrade_as(current_project, host, cache).stdout
        assert "Archflow 99.0.0 is available" in out
        assert "claude plugin update archflow@archflow" in out
        assert "archflow-install" not in out


def test_release_notice_is_silent_when_installed_is_current_or_newer(current_project, tmp_path):
    assert run_check_upgrade_as(current_project, "codex", _cache(tmp_path, _installed_version())).stdout.strip() == ""
    assert run_check_upgrade_as(current_project, "codex", _cache(tmp_path, "0.0.1")).stdout.strip() == ""


def test_release_notice_respects_update_check_false(current_project, tmp_path):
    (current_project / ".archflow" / "project-settings.yaml").write_text("project_type: fullstack\nupdate_check: false\n")
    assert run_check_upgrade_as(current_project, "codex", _cache(tmp_path, "99.0.0")).stdout.strip() == ""


def test_release_notice_respects_the_env_opt_out(current_project, tmp_path):
    out = run_check_upgrade_as(current_project, "codex", _cache(tmp_path, "99.0.0"), {"ARCHFLOW_NO_UPDATE_CHECK": "1"}).stdout
    assert out.strip() == ""


def test_release_notice_ignores_a_garbled_cache(current_project, tmp_path):
    d = tmp_path / "cache"
    d.mkdir()
    (d / "latest.json").write_text("{ not json")
    proc = run_check_upgrade_as(current_project, "codex", d)
    assert proc.returncode == 0 and proc.stdout.strip() == ""


class _Redirect(_http.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "/releases/tag/9.9.9")
        self.end_headers()

    def log_message(self, *_):
        pass


class _Tag(_http.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_):
        pass


def test_stale_cache_is_refreshed_in_the_background_without_blocking(current_project, tmp_path):
    """The hook returns at once; a detached child resolves the tag through the redirect."""
    class Handler(_http.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.endswith("/releases/latest"):
                self.send_response(302); self.send_header("Location", "/releases/tag/9.9.9"); self.end_headers()
            else:
                self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        def log_message(self, *_):
            pass
    server = _http.HTTPServer(("127.0.0.1", 0), Handler)
    _threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        cache = _cache(tmp_path, "0.0.1", age_seconds=2 * 24 * 3600)  # two days old
        url = f"http://127.0.0.1:{server.server_port}/releases/latest"
        start = _time.monotonic()
        proc = run_check_upgrade_as(current_project, "opencode", cache, {"ARCHFLOW_RELEASES_URL": url})
        assert _time.monotonic() - start < 3, "the hook must not wait for the refresh"
        assert proc.stdout.strip() == "", "a stale cache with an old tag says nothing this session"
        deadline = _time.monotonic() + 8
        while _time.monotonic() < deadline:
            data = _json.loads((cache / "latest.json").read_text())
            if data["tag"] == "9.9.9":
                break
            _time.sleep(0.2)
        assert data["tag"] == "9.9.9", "the detached refresh should have rewritten the cache"
        # Next session sees it.
        assert "Archflow 9.9.9 is available" in run_check_upgrade_as(current_project, "opencode", cache).stdout
    finally:
        server.shutdown()


def test_every_adapter_names_its_host_to_the_hook():
    """Without ARCHFLOW_HOST the hook assumes Claude Code and points at the plugin update."""
    wiring = {
        "codex": REPO / "adapters" / "codex" / ".codex" / "hooks.json",
        "copilot": REPO / "adapters" / "copilot" / ".github" / "hooks" / "archflow.json",
        "cursor": REPO / "adapters" / "cursor" / ".cursor" / "archflow" / "hooks" / "cursor-bridge.mjs",
        "gemini": REPO / "adapters" / "gemini" / "hooks" / "hooks.json",
        "opencode": REPO / "adapters" / "opencode" / ".opencode" / "plugins" / "archflow.ts",
        "generic": REPO / "adapters" / "generic" / "AGENTS.archflow.md",
    }
    for host, path in wiring.items():
        text = path.read_text()
        forms = (f"ARCHFLOW_HOST={host}", f'ARCHFLOW_HOST: "{host}"', f'"ARCHFLOW_HOST": "{host}"')
        assert any(f in text for f in forms), f"{path} does not set ARCHFLOW_HOST={host}"
