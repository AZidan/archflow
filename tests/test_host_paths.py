"""Host path resolution on Gemini CLI and Cursor (S7-05).

Two hosts, two ways the plugin could fail to find itself or the project:

- Gemini CLI substitutes ``${extensionPath}`` only in the manifest and hooks, never in a command
  prompt, so prompts name the extension by its install path. The prompts quote that path, and a
  shell does not expand ``~`` inside quotes, so ``"~/.gemini/..."`` pointed at a directory literally
  named ``~``. The build now writes ``$HOME``. These tests check every generated command for the
  quoted-tilde form, then lay the extension out under a throwaway HOME and run the doctor's shell
  lines in a real bash, the way the agent would.

- Cursor sends hooks no ``cwd``, only ``workspace_roots``. The bridge has to find the project from
  those. These tests replay Cursor-shaped payloads through the generated ``cursor-bridge.mjs`` with
  the process cwd set somewhere unrelated, so the payload is the only way to find the project.

Nothing here touches the real HOME, ~/.gemini or ~/.archflow, and nothing reaches the network:
HOME, ARCHFLOW_CONFIG_DIR and ARCHFLOW_CACHE_DIR point at temp dirs, ARCHFLOW_TELEMETRY_SINK writes
telemetry to a local file, and ARCHFLOW_NO_UPDATE_CHECK stops the release check. The gemini binary
is never run. The live on-host check is the user's.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ADAPTERS = REPO / "adapters"
GEMINI = ADAPTERS / "gemini"
GEMINI_COMMANDS = sorted((GEMINI / "commands" / "archflow").glob("*.toml"))
CURSOR_DOT = ADAPTERS / "cursor" / ".cursor"
VALID_PROJECT = REPO / "tests" / "fixtures" / "valid-project"

EXT_PREFIX = "$HOME/.gemini/extensions/archflow"


def clean_env(home, **extra):
    """An env that cannot reach the user's real config, the network or a real host."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CLAUDE", "STUDIO_", "ARCHFLOW_", "CURSOR_", "GEMINI_"))
        and k not in ("CI", "DO_NOT_TRACK")
    }
    env.update(
        HOME=str(home),
        ARCHFLOW_CONFIG_DIR=str(home / ".archflow"),
        ARCHFLOW_CACHE_DIR=str(home / ".cache" / "archflow"),
        ARCHFLOW_TELEMETRY_SINK=str(home / "sink.jsonl"),
        ARCHFLOW_NO_UPDATE_CHECK="1",
        # `python3` in a command must be the interpreter running the tests (it has PyYAML).
        PATH=f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}",
    )
    env.update({k: str(v) for k, v in extra.items()})
    return env


def sent(home):
    sink = home / "sink.jsonl"
    if not sink.exists():
        return []
    return [json.loads(line) for line in sink.read_text().splitlines() if line.strip()]


# ==========================================================================
# Gemini CLI: command prompts name the extension by a path the shell expands
# ==========================================================================

def prompt_of(toml_path):
    """The `prompt` string of a Gemini command (a TOML literal multi-line string)."""
    text = toml_path.read_text()
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            tomllib = None
    if tomllib is not None:
        return tomllib.loads(text)["prompt"]
    m = re.search(r"^prompt = '''\n?(.*?)'''", text, re.S | re.M)
    assert m, f"{toml_path.name}: no prompt = '''...''' block"
    return m.group(1)


def shell_blocks(prompt):
    """Fenced bash/sh blocks, with backslash continuations joined into one line each."""
    blocks = re.findall(r"^```(?:bash|sh|shell)\n(.*?)^```", prompt, re.S | re.M)
    return [b.replace("\\\n", " ") for b in blocks]


def extension_paths(prompt):
    """Every `$HOME/.gemini/extensions/archflow/...` path the prompt names, as written."""
    found = re.findall(r"\$HOME/\.gemini/extensions/archflow(?:/[A-Za-z0-9_.\-/]*)?", prompt)
    return {p.rstrip(".") for p in found}


def test_every_gemini_command_was_found():
    assert len(GEMINI_COMMANDS) >= 10, "adapters/gemini/commands/archflow/ is missing; run the build"
    assert any(p.name == "doctor.toml" for p in GEMINI_COMMANDS)


@pytest.mark.parametrize("toml_path", GEMINI_COMMANDS, ids=lambda p: p.stem)
def test_no_gemini_command_names_the_extension_by_tilde(toml_path):
    prompt = prompt_of(toml_path)
    assert "~/.gemini" not in prompt, (
        f"{toml_path.name} names the extension as ~/.gemini; a quoted ~ is not expanded by the "
        "shell. scripts/build-adapters.mjs should write $HOME"
    )
    for block in shell_blocks(prompt):
        for quote in ('"~/', "'~/"):
            assert quote not in block, f"{toml_path.name}: quoted tilde path in a shell block:\n{block}"


@pytest.mark.parametrize("toml_path", GEMINI_COMMANDS, ids=lambda p: p.stem)
def test_gemini_commands_do_not_rely_on_unsubstituted_placeholders(toml_path):
    # Gemini substitutes ${extensionPath} in gemini-extension.json and hooks, not in prompts, and
    # the Claude-only ${CLAUDE_PLUGIN_ROOT} is never set there. Either one left in a prompt is a
    # path that resolves to nothing.
    prompt = prompt_of(toml_path)
    assert "${CLAUDE_PLUGIN_ROOT}" not in prompt
    assert "${extensionPath}" not in prompt


GEMINI_TEXT = sorted(p for p in GEMINI.rglob("*") if p.suffix in (".md", ".toml") and p.is_file())


@pytest.mark.parametrize("path", GEMINI_TEXT, ids=lambda p: str(p.relative_to(GEMINI)))
def test_every_extension_path_in_the_package_exists(path):
    # Commands, agents and skills all point the model at files by this path. Command bodies ship
    # as commands/archflow/<n>.toml here, so a plugin-style commands/<n>.md reference is a dead end.
    for ref in extension_paths(path.read_text()):
        rel = ref[len(EXT_PREFIX):].lstrip("/")
        assert (GEMINI / rel).exists(), f"{path.relative_to(GEMINI)} names {ref}, which the package does not ship"


@pytest.fixture
def gemini_home(tmp_path):
    """A throwaway HOME with the extension installed where `gemini extensions install` puts it."""
    home = tmp_path / "home"
    shutil.copytree(GEMINI, home / ".gemini" / "extensions" / "archflow",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return home


def bash(script, home, cwd):
    return subprocess.run(
        ["bash", "-c", script], cwd=str(cwd), env=clean_env(home),
        capture_output=True, text=True, timeout=60,
    )


def test_every_extension_path_expands_under_a_real_shell(gemini_home, tmp_path):
    """Each path, written exactly as the prompt writes it, inside double quotes, resolves in bash."""
    paths = set()
    for toml_path in GEMINI_COMMANDS:
        paths |= extension_paths(prompt_of(toml_path))
    assert paths, "no command names the extension path at all"
    script = "\n".join(f'test -e "{p}" || echo "MISSING {p}"' for p in sorted(paths))
    proc = bash(script, gemini_home, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "", f"paths that did not resolve under HOME={gemini_home}:\n{proc.stdout}"


@pytest.fixture
def doctor_project(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(VALID_PROJECT, project)
    subprocess.run(["git", "init", "-q", str(project)], check=True, capture_output=True)
    return project


def doctor_blocks():
    blocks = [b for b in shell_blocks(prompt_of(GEMINI / "commands" / "archflow" / "doctor.toml"))
              if EXT_PREFIX in b]
    return {name: next((b for b in blocks if name in b), None)
            for name in ("validate_archflow.py", "upgrade_archflow.py", "archflow-install-git-guard.sh")}


def test_doctor_names_the_plugin_scripts_through_home():
    for name, block in doctor_blocks().items():
        assert block is not None, f"doctor.toml no longer runs {name} through {EXT_PREFIX}"


def test_doctor_validate_runs_against_the_installed_extension(gemini_home, doctor_project):
    proc = bash(doctor_blocks()["validate_archflow.py"], gemini_home, doctor_project)
    assert "No such file" not in proc.stderr, proc.stderr
    # 0 clean, 1 violations, 2 could not run. The fixture is clean, so 0.
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


def test_doctor_upgrade_check_runs_against_the_installed_extension(gemini_home, doctor_project):
    block = next(b for b in shell_blocks(prompt_of(GEMINI / "commands" / "archflow" / "doctor.toml"))
                 if "upgrade_archflow.py" in b and "--apply" not in b)
    proc = bash(block, gemini_home, doctor_project)
    assert "No such file" not in proc.stderr, proc.stderr
    # Documented: it reports and changes nothing; exit 1 means drift found (a WARN), 0 none.
    assert proc.returncode in (0, 1), f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert proc.stdout.strip(), "the drift report printed nothing"


def test_doctor_git_guard_install_runs_against_the_installed_extension(gemini_home, doctor_project):
    proc = bash(doctor_blocks()["archflow-install-git-guard.sh"], gemini_home, doctor_project)
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    hook = doctor_project / ".git" / "hooks" / "pre-push"
    assert hook.exists() and "archflow-pre-push" in hook.read_text()


def test_the_tilde_form_really_would_have_failed(gemini_home, tmp_path):
    """The regression the fix addresses: a quoted ~ is a literal directory name to the shell."""
    proc = bash('test -e "~/.gemini/extensions/archflow/scripts/validate_archflow.py"', gemini_home, tmp_path)
    assert proc.returncode != 0
    proc = bash(f'test -e "{EXT_PREFIX}/scripts/validate_archflow.py"', gemini_home, tmp_path)
    assert proc.returncode == 0


# ==========================================================================
# Cursor: the hook bridge finds the project from workspace_roots, not cwd
#
# Root choice, as the bridge implements it:
#   1. payload `cwd`, when a host sends one;
#   2. else the first workspace root that contains .archflow/;
#   3. else workspace_roots[0];
#   4. else the process cwd.
# So a multi-root workspace with the Archflow project listed second still gets its hooks, and a
# workspace with no Archflow root behaves as a plain workspace (telemetry only, every gate open).
# ==========================================================================

@pytest.fixture
def cursor_env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    elsewhere = tmp_path / "elsewhere"  # the bridge's process cwd: never an Archflow project
    elsewhere.mkdir()
    return home, elsewhere


def make_project(path, project_type="backend_only", branch="main"):
    (path / ".git").mkdir(parents=True)
    (path / ".git" / "HEAD").write_text(f"ref: refs/heads/{branch}\n")
    af = path / ".archflow"
    af.mkdir()
    (af / "current-phase.yaml").write_text("phase: 3\nphase_file: phases/phase-3.md\nmode: quick\n")
    (af / "project-settings.yaml").write_text(f"project_type: {project_type}\n")
    (af / "instructions.md").write_text(f"ARCHFLOW-INSTRUCTIONS-FOR-{path.name}\n")
    shutil.copytree(CURSOR_DOT, path / ".cursor", ignore=shutil.ignore_patterns("__pycache__"))
    return path


def plain_folder(path):
    path.mkdir(parents=True)
    return path


def cursor_payload(event, roots, **fields):
    """A Cursor hook payload as Cursor sends it: common fields, workspace_roots, no cwd."""
    payload = {
        "conversation_id": "c0ffee00-0000-4000-8000-000000000001",
        "generation_id": "c0ffee00-0000-4000-8000-000000000002",
        "hook_event_name": event,
        "cursor_version": "1.7.0",
        "workspace_roots": [str(r) for r in roots],
    }
    payload.update(fields)
    return payload


EVENT_FIELDS = {
    "sessionStart": {"session_id": "s-1", "is_background_agent": False, "composer_mode": "agent"},
    "beforeSubmitPrompt": {"prompt": "/archflow:status", "attachments": []},
    "beforeShellExecution": {"command": "git push --force origin main"},
    "stop": {"status": "completed", "loop_count": 0},
}


def bridge(event, payload, home, cwd, bridge_dir=CURSOR_DOT):
    script = bridge_dir / "archflow" / "hooks" / "cursor-bridge.mjs"
    proc = subprocess.run(
        ["node", str(script), event],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        cwd=str(cwd), env=clean_env(home), capture_output=True, text=True, timeout=20,
    )
    assert proc.returncode == 0, f"bridge exited {proc.returncode}: {proc.stderr}"
    return proc, (json.loads(proc.stdout) if proc.stdout.strip() else None)


def run_all_events(roots, home, cwd, bridge_dir):
    return {e: bridge(e, cursor_payload(e, roots, **EVENT_FIELDS[e]), home, cwd, bridge_dir)
            for e in EVENT_FIELDS}


def test_cursor_payloads_carry_no_cwd():
    for event, fields in EVENT_FIELDS.items():
        assert "cwd" not in cursor_payload(event, ["/x"], **fields)


def assert_acted_on(project, results, home):
    """Each event reached the hook scripts with `project` as the project directory."""
    _, start = results["sessionStart"]
    assert f"ARCHFLOW-INSTRUCTIONS-FOR-{project.name}" in start["additional_context"], \
        "sessionStart did not load the project's .archflow/instructions.md"

    _, prompt = results["beforeSubmitPrompt"]
    assert prompt == {"continue": True}

    _, shell = results["beforeShellExecution"]
    assert shell["permission"] == "deny", "the git guard did not see the project (on main, force push)"
    assert project.name in shell["agent_message"], "the guard's block must name the resolved project"

    _, stop = results["stop"]
    assert stop == {}

    events = {e["event"]: e for e in sent(home)}
    assert set(events) >= {"session_start", "command_run"}, f"telemetry sent: {list(events)}"
    for name in ("session_start", "command_run"):
        props = events[name]["properties"]
        assert props["has_project"] is True, f"{name} did not see the project"
        assert props["project_type"] == "backend_only"
        assert props["host"] == "cursor"
    assert events["command_run"]["properties"]["command"] == "archflow:status"


def test_single_root_without_cwd_resolves_the_project(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    results = run_all_events([project], home, elsewhere, project / ".cursor")
    assert_acted_on(project, results, home)


def test_multi_root_with_the_archflow_project_first(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    other = plain_folder(tmp_path / "shared-docs")
    results = run_all_events([project, other], home, elsewhere, project / ".cursor")
    assert_acted_on(project, results, home)


def test_multi_root_with_the_archflow_project_not_first(cursor_env, tmp_path):
    # Previously the bridge took workspace_roots[0] blindly, so here every Archflow hook went
    # silent. It now prefers the first root that is an Archflow project.
    home, elsewhere = cursor_env
    other = plain_folder(tmp_path / "shared-docs")
    project = make_project(tmp_path / "shop-api")
    results = run_all_events([other, project], home, elsewhere, project / ".cursor")
    assert_acted_on(project, results, home)


def test_two_archflow_roots_use_the_first(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    first = make_project(tmp_path / "first-api")
    second = make_project(tmp_path / "second-api")
    _, start = bridge("sessionStart", cursor_payload("sessionStart", [first, second], **EVENT_FIELDS["sessionStart"]),
                      home, elsewhere, first / ".cursor")
    assert "ARCHFLOW-INSTRUCTIONS-FOR-first-api" in start["additional_context"]
    assert "second-api" not in start["additional_context"]


def test_no_archflow_root_falls_back_to_the_first_root_as_a_plain_workspace(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    a = plain_folder(tmp_path / "a")
    b = plain_folder(tmp_path / "b")
    results = run_all_events([a, b], home, elsewhere, CURSOR_DOT)
    assert results["beforeSubmitPrompt"][1] == {"continue": True}
    # No project: every gate is open and nothing is denied.
    assert results["beforeShellExecution"][1] == {}
    assert results["stop"][1] == {}
    start = results["sessionStart"][1]
    assert "ARCHFLOW-INSTRUCTIONS" not in json.dumps(start)
    # Telemetry still runs in every workspace, and reports no project.
    for e in sent(home):
        assert e["properties"]["has_project"] is False


def test_an_explicit_cwd_still_wins(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    other = make_project(tmp_path / "other-api")
    payload = cursor_payload("sessionStart", [other], **EVENT_FIELDS["sessionStart"])
    payload["cwd"] = str(project)
    _, start = bridge("sessionStart", payload, home, elsewhere, project / ".cursor")
    assert "ARCHFLOW-INSTRUCTIONS-FOR-shop-api" in start["additional_context"]


@pytest.mark.parametrize("event", list(EVENT_FIELDS))
@pytest.mark.parametrize("payload", [
    {"conversation_id": "c", "generation_id": "g", "hook_event_name": "x"},  # neither cwd nor roots
    {"workspace_roots": []},
    {"workspace_roots": None},
    {"workspace_roots": [None, 3]},
    "",          # empty stdin
    "not json",  # garbage stdin
], ids=["no-roots", "empty-roots", "null-roots", "junk-roots", "empty-stdin", "garbage"])
def test_no_workspace_is_a_graceful_no_op(cursor_env, event, payload):
    home, elsewhere = cursor_env
    proc, out = bridge(event, payload, home, elsewhere)
    expected = {
        "beforeSubmitPrompt": {"continue": True},
        "beforeShellExecution": {},
        "stop": {},
    }
    if event in expected:
        assert out == expected[event]
    else:
        # sessionStart: at most the one-time telemetry notice, never project instructions.
        assert out == {} or set(out) == {"additional_context"}
        assert "ARCHFLOW-INSTRUCTIONS" not in json.dumps(out)


def test_stop_surfaces_state_drift_for_the_resolved_project(cursor_env, tmp_path):
    """check-state runs on the project found from workspace_roots and its advisory reaches stderr."""
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    shutil.copytree(REPO / "tests" / "fixtures" / "invalid-project" / ".archflow", project / ".archflow",
                    dirs_exist_ok=True)
    proc, out = bridge("stop", cursor_payload("stop", [plain_folder(tmp_path / "docs"), project],
                                              **EVENT_FIELDS["stop"]), home, elsewhere, project / ".cursor")
    assert out == {}
    assert "drifted from their schemas" in proc.stderr, proc.stderr
