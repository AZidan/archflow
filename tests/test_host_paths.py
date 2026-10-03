"""Host path resolution on Gemini CLI and Cursor (S7-05).

Two hosts, two ways the plugin could fail to find itself or the project:

- Gemini CLI substitutes ``${extensionPath}`` only in the manifest and hooks, never in a command
  prompt, so prompts name the extension by its install path. The prompts quote that path, and a
  shell does not expand ``~`` inside quotes, so ``"~/.gemini/..."`` pointed at a directory literally
  named ``~``. The build now writes ``$HOME``. These tests check every generated command for the
  quoted-tilde form, then lay the extension out under a throwaway HOME and run the doctor's shell
  lines in a real bash, the way the agent would.

- Cursor sends every hook ``workspace_roots`` but sends ``cwd`` only on some events (of the four
  the bridge handles, only ``beforeShellExecution``), and that ``cwd`` is the shell's directory,
  which may be a subdirectory of the project. The bridge has to find the project from those. These
  tests replay payloads shaped per Cursor's hook docs through the generated ``cursor-bridge.mjs``
  with the process cwd set somewhere unrelated, so the payload is the only way to find the project.

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


def plugin_shell_blocks(text):
    """Fenced bash/sh blocks in a plugin markdown file (fences may be indented in lists)."""
    blocks = re.findall(r"^[ \t]*```(?:bash|sh|shell)\n(.*?)^[ \t]*```", text, re.S | re.M)
    return [b.replace("\\\n", " ") for b in blocks]


def unquoted(block, prefix):
    """Lines of a shell block where `prefix` appears outside double quotes."""
    bad = []
    for line in block.splitlines():
        for m in re.finditer(re.escape(prefix), line):
            if line[:m.start()].count('"') % 2 == 0:
                bad.append(line.strip())
    return bad


PLUGIN_MD = sorted((REPO / "plugin").rglob("*.md"))


@pytest.mark.parametrize("path", PLUGIN_MD, ids=lambda p: str(p.relative_to(REPO / "plugin")))
def test_plugin_shell_lines_quote_the_plugin_root(path):
    # Every host's generated copy inherits this. Unquoted, a plugin root with a space in it (a
    # HOME such as "/Users/Jane Doe" on Gemini) splits into two words and the command fails.
    for block in plugin_shell_blocks(path.read_text()):
        bad = unquoted(block, "${CLAUDE_PLUGIN_ROOT}")
        assert not bad, f"{path.name}: unquoted plugin root in a shell line: {bad}"


@pytest.mark.parametrize("toml_path", GEMINI_COMMANDS, ids=lambda p: p.stem)
def test_gemini_shell_lines_quote_the_extension_path(toml_path):
    for block in shell_blocks(prompt_of(toml_path)):
        bad = unquoted(block, EXT_PREFIX)
        assert not bad, f"{toml_path.name}: unquoted extension path in a shell line: {bad}"


@pytest.fixture
def spaced_home(tmp_path):
    """Like gemini_home, but HOME has a space in it, as many real macOS/Windows homes do."""
    home = tmp_path / "Jane Doe"
    shutil.copytree(GEMINI, home / ".gemini" / "extensions" / "archflow",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return home


def test_doctor_lines_survive_a_home_with_a_space(spaced_home, doctor_project):
    blocks = doctor_blocks()
    proc = bash(blocks["validate_archflow.py"], spaced_home, doctor_project)
    assert proc.returncode == 0, f"validate:\n{proc.stdout}\n{proc.stderr}"
    block = next(b for b in shell_blocks(prompt_of(GEMINI / "commands" / "archflow" / "doctor.toml"))
                 if "upgrade_archflow.py" in b and "--apply" not in b)
    proc = bash(block, spaced_home, doctor_project)
    assert proc.returncode in (0, 1) and "No such file" not in proc.stderr, f"upgrade:\n{proc.stderr}"
    proc = bash(blocks["archflow-install-git-guard.sh"], spaced_home, doctor_project)
    assert proc.returncode == 0, f"git guard:\n{proc.stdout}\n{proc.stderr}"
    assert "archflow-pre-push" in (doctor_project / ".git" / "hooks" / "pre-push").read_text()


def test_migrate_dry_run_survives_a_home_with_a_space(spaced_home, tmp_path):
    project = tmp_path / "v1 project"
    shutil.copytree(REPO / "tests" / "fixtures" / "v1-project", project)
    before = sorted(str(p.relative_to(project)) for p in project.rglob("*"))
    blocks = [b for b in shell_blocks(prompt_of(GEMINI / "commands" / "archflow" / "migrate.toml"))
              if "migrate.py" in b and "--dry-run" in b]
    assert blocks, "migrate.toml no longer shows the dry-run line"
    # The agent fills <project-root> in; quote it, as it must for a path with a space.
    script = blocks[0].replace("<project-root>", f'"{project}"')
    proc = bash(script, spaced_home, tmp_path)
    assert "No such file" not in proc.stderr and "can't open file" not in proc.stderr, proc.stderr
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    assert sorted(str(p.relative_to(project)) for p in project.rglob("*")) == before, "dry run wrote files"


def test_an_unquoted_path_really_would_have_failed(spaced_home, tmp_path):
    """The regression I-3 addresses: unquoted, a HOME with a space splits the script path."""
    proc = bash(f"python3 {EXT_PREFIX}/scripts/migrate.py --help", spaced_home, tmp_path)
    assert proc.returncode != 0
    proc = bash(f'python3 "{EXT_PREFIX}/scripts/migrate.py" --help', spaced_home, tmp_path)
    assert proc.returncode == 0, proc.stderr


def test_the_tilde_form_really_would_have_failed(gemini_home, tmp_path):
    """The regression the fix addresses: a quoted ~ is a literal directory name to the shell."""
    proc = bash('test -e "~/.gemini/extensions/archflow/scripts/validate_archflow.py"', gemini_home, tmp_path)
    assert proc.returncode != 0
    proc = bash(f'test -e "{EXT_PREFIX}/scripts/validate_archflow.py"', gemini_home, tmp_path)
    assert proc.returncode == 0


# ==========================================================================
# Cursor: the hook bridge finds the project from workspace_roots and, when sent, cwd
#
# Payload shapes follow Cursor's hook docs (https://cursor.com/docs/agent/hooks, "Hook
# Input/Output Schemas"): every hook gets the common fields, including `workspace_roots`; `cwd`
# (the shell's working directory) is sent on beforeShellExecution, preToolUse, postToolUse,
# postToolUseFailure and beforeReadFile only. Of the four events the bridge handles, only
# beforeShellExecution carries it. Project hooks run with the project root as their process cwd.
#
# Project choice, as the bridge implements it:
#   1. with a cwd, the nearest directory from it up to its workspace root (inclusive) that has
#      .archflow/, so a shell in a monorepo subdirectory is still inside the project and the git
#      guard still applies. The walk never leaves the workspace root, so a repo opened as the
#      workspace is judged on its own even if it sits inside an Archflow project. Only a cwd
#      outside every root is walked up without a bound;
#   2. with a cwd inside a workspace root that is not an Archflow project (and no Archflow
#      ancestor), that root: the command runs in a repo that never opted in, so it is a plain
#      workspace and the guard stays out, even if another root is an Archflow project;
#   3. otherwise (no cwd, or a cwd outside every root) the first workspace root that has
#      .archflow/, else workspace_roots[0], else the cwd, else the process cwd.
# HOME is never a project: ~/.archflow is the telemetry config dir.
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
    """A Cursor hook payload: the documented common fields plus the event's own fields."""
    payload = {
        "conversation_id": "c0ffee00-0000-4000-8000-000000000001",
        "generation_id": "c0ffee00-0000-4000-8000-000000000002",
        "model": "claude-4-sonnet",
        "model_id": "claude-4-sonnet",
        "model_params": [],
        "hook_event_name": event,
        "cursor_version": "1.7.0",
        "workspace_roots": [str(r) for r in roots],
        "user_email": None,
        "transcript_path": None,
    }
    payload.update({k: str(v) if isinstance(v, Path) else v for k, v in fields.items()})
    return payload


# Event-specific fields per the docs. beforeShellExecution's cwd is filled in per test.
EVENT_FIELDS = {
    "sessionStart": {"session_id": "s-1", "is_background_agent": False, "composer_mode": "agent"},
    "beforeSubmitPrompt": {"prompt": "/archflow:status", "attachments": []},
    "beforeShellExecution": {"command": "git push --force origin main", "sandbox": False},
    "stop": {"status": "completed", "loop_count": 0},
}
CWD_EVENTS = {"beforeShellExecution"}


def shell_payload(roots, cwd, command="git push --force origin main"):
    return cursor_payload("beforeShellExecution", roots, command=command, cwd=cwd, sandbox=False)


def bridge(event, payload, home, cwd, bridge_dir=CURSOR_DOT):
    script = bridge_dir / "archflow" / "hooks" / "cursor-bridge.mjs"
    proc = subprocess.run(
        ["node", str(script), event],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        cwd=str(cwd), env=clean_env(home), capture_output=True, text=True, timeout=20,
    )
    assert proc.returncode == 0, f"bridge exited {proc.returncode}: {proc.stderr}"
    return proc, (json.loads(proc.stdout) if proc.stdout.strip() else None)


def run_all_events(roots, home, cwd, bridge_dir, shell_cwd):
    """Every event, as Cursor sends it; `shell_cwd` is the terminal's directory."""
    results = {}
    for e in EVENT_FIELDS:
        fields = dict(EVENT_FIELDS[e], cwd=shell_cwd) if e in CWD_EVENTS else EVENT_FIELDS[e]
        results[e] = bridge(e, cursor_payload(e, roots, **fields), home, cwd, bridge_dir)
    return results


def test_only_the_documented_events_carry_cwd():
    for event, fields in EVENT_FIELDS.items():
        payload = cursor_payload(event, ["/x"], **(dict(fields, cwd="/x") if event in CWD_EVENTS else fields))
        assert ("cwd" in payload) == (event in CWD_EVENTS), event


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
    results = run_all_events([project], home, elsewhere, project / ".cursor", shell_cwd=project)
    assert_acted_on(project, results, home)


def test_multi_root_with_the_archflow_project_first(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    other = plain_folder(tmp_path / "shared-docs")
    results = run_all_events([project, other], home, elsewhere, project / ".cursor", shell_cwd=project)
    assert_acted_on(project, results, home)


def test_multi_root_with_the_archflow_project_not_first(cursor_env, tmp_path):
    # Previously the bridge took workspace_roots[0] blindly, so here every Archflow hook went
    # silent. It now prefers the first root that is an Archflow project.
    home, elsewhere = cursor_env
    other = plain_folder(tmp_path / "shared-docs")
    project = make_project(tmp_path / "shop-api")
    results = run_all_events([other, project], home, elsewhere, project / ".cursor", shell_cwd=project)
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
    results = run_all_events([a, b], home, elsewhere, CURSOR_DOT, shell_cwd=a)
    assert results["beforeSubmitPrompt"][1] == {"continue": True}
    # No project: every gate is open and nothing is denied.
    assert results["beforeShellExecution"][1] == {}
    assert results["stop"][1] == {}
    start = results["sessionStart"][1]
    assert "ARCHFLOW-INSTRUCTIONS" not in json.dumps(start)
    # Telemetry still runs in every workspace, and reports no project.
    for e in sent(home):
        assert e["properties"]["has_project"] is False


def test_shell_in_a_project_subdirectory_is_still_guarded(cursor_env, tmp_path):
    # A monorepo: the terminal is in packages/api, the project root holds .archflow/ and .git/.
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    sub = project / "packages" / "api"
    sub.mkdir(parents=True)
    _, out = bridge("beforeShellExecution", shell_payload([project], sub), home, elsewhere, project / ".cursor")
    assert out["permission"] == "deny", f"force push to main from a subdirectory was allowed: {out}"
    assert "shop-api" in out["agent_message"]


def test_shell_in_a_subdirectory_of_a_non_first_root_is_guarded(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    docs = plain_folder(tmp_path / "shared-docs")
    project = make_project(tmp_path / "shop-api")
    sub = project / "src"
    sub.mkdir()
    _, out = bridge("beforeShellExecution", shell_payload([docs, project], sub), home, elsewhere, project / ".cursor")
    assert out["permission"] == "deny"


def test_ordinary_commands_in_a_subdirectory_are_allowed(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    sub = project / "packages" / "api"
    sub.mkdir(parents=True)
    _, out = bridge("beforeShellExecution", shell_payload([project], sub, command="npm test"),
                    home, elsewhere, project / ".cursor")
    assert out == {"permission": "allow"}


def test_shell_in_a_non_archflow_root_is_a_plain_workspace(cursor_env, tmp_path):
    # Rule 2: the terminal is in `tools`, a workspace root that never opted in, while `shop-api`
    # (another root, on main) is an Archflow project. The push happens in `tools`, so the guard
    # must not judge it by shop-api's branch: it is allowed and nothing is blocked.
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    tools = plain_folder(tmp_path / "tools")
    for roots in ([project, tools], [tools, project]):
        _, out = bridge("beforeShellExecution", shell_payload(roots, tools), home, elsewhere, project / ".cursor")
        assert out == {}, f"roots={roots}: {out}"


def test_a_non_archflow_workspace_nested_in_an_archflow_project_is_left_alone(cursor_env, tmp_path):
    # outer-app is an Archflow project on main. vendor/lib is its own repo, with no .archflow/, and
    # is what the user opened in Cursor. The walk stops at that root, so the outer project's guard
    # does not judge a push in vendor/lib, matching sessionStart for the same workspace.
    home, elsewhere = cursor_env
    outer = make_project(tmp_path / "outer-app")
    lib = outer / "vendor" / "lib"
    (lib / ".git").mkdir(parents=True)
    (lib / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    for cwd in (lib, lib / "src"):
        cwd.mkdir(exist_ok=True)
        _, out = bridge("beforeShellExecution", shell_payload([lib], cwd), home, elsewhere, outer / ".cursor")
        assert out == {}, f"cwd={cwd}: {out}"
    _, start = bridge("sessionStart", cursor_payload("sessionStart", [lib], **EVENT_FIELDS["sessionStart"]),
                      home, elsewhere, outer / ".cursor")
    assert "ARCHFLOW-INSTRUCTIONS" not in json.dumps(start)


def test_shell_outside_every_root_walks_up_without_a_bound(cursor_env, tmp_path):
    # The terminal is in a subdirectory of an Archflow project that is not a workspace root.
    home, elsewhere = cursor_env
    root = make_project(tmp_path / "shop-api", branch="feature-x")
    there = make_project(tmp_path / "billing-api")
    sub = there / "packages" / "web"
    sub.mkdir(parents=True)
    _, out = bridge("beforeShellExecution", shell_payload([root], sub), home, elsewhere, root / ".cursor")
    assert out["permission"] == "deny"
    assert "billing-api" in out["agent_message"]


def test_shell_outside_every_root_falls_back_to_the_archflow_root(cursor_env, tmp_path):
    # Rule 3: a cwd that is in no workspace root and no Archflow project tells the bridge nothing,
    # so it uses the workspace's Archflow project, as for events without a cwd.
    home, elsewhere = cursor_env
    docs = plain_folder(tmp_path / "shared-docs")
    project = make_project(tmp_path / "shop-api")
    outside = plain_folder(tmp_path / "scratch")
    _, out = bridge("beforeShellExecution", shell_payload([docs, project], outside), home, elsewhere, project / ".cursor")
    assert out["permission"] == "deny"
    assert "shop-api" in out["agent_message"]


def test_shell_cwd_in_an_archflow_project_outside_the_roots_uses_that_project(cursor_env, tmp_path):
    # Rule 1 before rule 3: the terminal is in another Archflow project (on main) that is not a
    # workspace root, so that project is the one the command is about.
    home, elsewhere = cursor_env
    root = make_project(tmp_path / "shop-api", branch="feature-x")
    there = make_project(tmp_path / "billing-api")
    _, out = bridge("beforeShellExecution", shell_payload([root], there), home, elsewhere, root / ".cursor")
    assert out["permission"] == "deny"
    assert "billing-api" in out["agent_message"]


def test_home_is_never_taken_for_a_project(cursor_env, tmp_path):
    # ~/.archflow holds the telemetry config. A shell somewhere under HOME, with no project above
    # it, must not be read as an Archflow project rooted at HOME.
    home, elsewhere = cursor_env
    (home / ".archflow").mkdir()
    (home / ".archflow" / "config.json").write_text("{}")
    (home / ".git").mkdir()
    (home / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    sub = plain_folder(home / "code" / "scratch")
    _, out = bridge("beforeShellExecution", shell_payload([sub], sub), home, elsewhere)
    assert out == {}


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


def test_stop_relays_both_stdout_and_stderr_and_keeps_its_json(cursor_env, tmp_path):
    home, elsewhere = cursor_env
    project = make_project(tmp_path / "shop-api")
    (project / ".cursor" / "archflow" / "hooks" / "check-state.mjs").write_text(
        'process.stdout.write("STDOUT-ADVISORY\\n"); process.stderr.write("STDERR-NOISE\\n");\n'
    )
    proc, out = bridge("stop", cursor_payload("stop", [project], **EVENT_FIELDS["stop"]),
                       home, elsewhere, project / ".cursor")
    assert out == {}, "Cursor reads the stop hook's stdout as JSON; it must stay {}"
    assert "STDOUT-ADVISORY" in proc.stderr and "STDERR-NOISE" in proc.stderr, proc.stderr


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
