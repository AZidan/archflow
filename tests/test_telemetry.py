"""Tests for anonymous usage telemetry (S8-05).

Nothing here reaches PostHog. Every run sets ARCHFLOW_TELEMETRY_SINK, which makes
capture() append the payload to a local file instead of spawning the sender, and
points HOME and ARCHFLOW_CONFIG_DIR at a temp dir so the real ~/.archflow is never
read or written. test_capture_never_spawns_the_sender_when_the_sink_is_set checks
that the sink really replaces the network: with it set, the sender is never spawned.

What is checked is the documented contract in SECURITY.md "## Telemetry": the
events, the properties each may carry, the opt-out variables, the default and
the one-time notice.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"
HOOK = PLUGIN / "hooks" / "telemetry.mjs"
LIB = PLUGIN / "lib" / "telemetry.mjs"
ADAPTERS = REPO / "adapters"
CLI = REPO / "scripts" / "archflow.mjs"

COMMON = {"distinct_id", "archflow_version", "host", "entrypoint", "via_studio", "studio_capture"}
PROJECT = {"has_project", "project_type", "phase", "mode"}
ALLOWED = {
    "session_start": COMMON | PROJECT | {"session_source"},
    "command_run": COMMON | PROJECT | {"command", "detected_by"},
    "cli_install": COMMON | {"installed_hosts", "source"},
    "telemetry_opted_out": COMMON | {"via", "days_since_notice"},
    "telemetry_opted_in": COMMON | {"via", "days_since_notice"},
}
INTERNAL = {"$process_person_profile"}  # PostHog flag, a constant set by capture() itself

# Where each adapter keeps its hook runtime, and how its hooks name it.
ADAPTER_ROOTS = {
    "codex": ADAPTERS / "codex" / ".codex" / "archflow",
    "copilot": ADAPTERS / "copilot" / ".github" / "archflow",
    "cursor": ADAPTERS / "cursor" / ".cursor" / "archflow",
    "gemini": ADAPTERS / "gemini",
    "opencode": ADAPTERS / "opencode" / ".opencode" / "archflow",
    "generic": ADAPTERS / "generic" / ".agents" / "archflow",
}

SECRET = "zz-acme-secret-project"


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "home"
    h.mkdir()
    return h


@pytest.fixture
def project(tmp_path):
    p = tmp_path / SECRET
    (p / ".archflow").mkdir(parents=True)
    (p / ".archflow" / "current-phase.yaml").write_text("phase: 3\nphase_file: phases/phase-3.md\nmode: quick\n")
    (p / ".archflow" / "project-settings.yaml").write_text("project_type: fullstack\n")
    return p


def base_env(home, **extra):
    """A clean env: nothing inherited that could disable telemetry or name a Studio/host.

    CLAUDECODE=1 stands in for the marker Claude Code writes into every hook process, so an
    unset ARCHFLOW_HOST reads as Claude Code. Pass CLAUDECODE=None to drop it (a host that
    loads the Claude plugin without being Claude Code, such as Copilot)."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CLAUDE", "STUDIO_", "ARCHFLOW_"))
        and k not in ("CI", "DO_NOT_TRACK")
    }
    env.update(
        HOME=str(home),
        ARCHFLOW_CONFIG_DIR=str(home / ".archflow"),
        ARCHFLOW_TELEMETRY_SINK=str(home / "sink.jsonl"),
        CLAUDECODE="1",
    )
    for k, v in extra.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = str(v)
    return env


def sent(home):
    sink = home / "sink.jsonl"
    if not sink.exists():
        return []
    return [json.loads(line) for line in sink.read_text().splitlines() if line.strip()]


def config(home):
    path = home / ".archflow" / "config.json"
    return json.loads(path.read_text()) if path.exists() else {}


def hook(home, cwd, args=(), payload=None, root=PLUGIN, script=None, **env):
    proc = subprocess.run(
        ["node", str(script or root / "hooks" / "telemetry.mjs"), *args],
        input=json.dumps(payload if payload is not None else {"cwd": str(cwd)}),
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(cwd),
        env=base_env(home, CLAUDE_PLUGIN_ROOT=root, **env),
    )
    assert proc.returncode == 0, proc.stderr
    return proc


def lib_capture(home, event, props, **env):
    """capture() called directly, as the CLI and the hook do."""
    code = f"import {{ capture }} from {json.dumps(LIB.as_uri())};\ncapture({json.dumps(event)}, {json.dumps(props)});\n"
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        capture_output=True, text=True, timeout=15, env=base_env(home, **env),
    )
    assert proc.returncode == 0, proc.stderr
    return sent(home)


def assert_allowed(event):
    props = set(event["properties"])
    extra = props - ALLOWED[event["event"]] - INTERNAL
    assert not extra, f"{event['event']} carries properties not on the allow-list: {extra}"


def assert_no_leak(events, *needles):
    blob = json.dumps(events)
    for n in needles:
        assert n not in blob, f"{n!r} leaked into a telemetry payload"


# --------------------------------------------------------------------------
# The allow-list
# --------------------------------------------------------------------------

def test_lib_allow_list_matches_this_test():
    """The lib's EVENT_PROPERTIES and SECURITY.md's documented list are the same set."""
    code = (
        f"import {{ EVENT_PROPERTIES }} from {json.dumps(LIB.as_uri())};\n"
        "console.log(JSON.stringify(Object.fromEntries(Object.entries(EVENT_PROPERTIES).map(([k, v]) => [k, Object.keys(v).sort()]))));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True).stdout
    assert {k: set(v) for k, v in json.loads(out).items()} == ALLOWED


@pytest.mark.parametrize("event", sorted(ALLOWED))
def test_unknown_properties_are_dropped(home, event):
    props = {
        "command": "archflow:status",
        "project_name": SECRET,
        "path": "/Users/someone/" + SECRET,
        "prompt": "do the secret thing",
        "args": ["--token", "hunter2"],
    }
    events = lib_capture(home, event, props)
    assert len(events) == 1 and events[0]["event"] == event
    assert_allowed(events[0])
    assert_no_leak(events, SECRET, "hunter2", "secret thing")


def test_an_event_not_on_the_list_is_not_sent(home):
    assert lib_capture(home, "custom_event", {"host": "claude"}) == []


def test_command_run_without_a_valid_command_is_not_sent(home):
    assert lib_capture(home, "command_run", {"command": f"archflow:status {SECRET}"}) == []


def test_cli_install_hosts_and_source_are_checked(home):
    events = lib_capture(home, "cli_install", {
        "host": "cli", "archflow_version": "2.5.0",
        "installed_hosts": ["codex", SECRET], "source": f"/tmp/{SECRET}",
    })
    p = events[0]["properties"]
    assert p["installed_hosts"] == ["codex"]
    assert p["source"] == "other"
    assert_no_leak(events, SECRET)


# --------------------------------------------------------------------------
# No names, paths, contents, prompts or arguments
# --------------------------------------------------------------------------

def test_session_start_carries_no_path_or_project_name(home, project):
    (project / ".archflow" / "project-context.md").write_text(f"# {SECRET} context\n")
    hook(home, project, payload={"cwd": str(project), "source": "startup", "transcript_path": f"/x/{SECRET}"})
    events = sent(home)
    assert [e["event"] for e in events] == ["session_start"]
    assert_allowed(events[0])
    assert_no_leak(events, SECRET, str(project))
    p = events[0]["properties"]
    assert (p["has_project"], p["project_type"], p["phase"], p["mode"], p["session_source"]) == (
        True, "fullstack", "3", "quick", "startup")


def test_command_hook_never_sends_arguments(home, project):
    hook(home, project, ["--command-run"], {
        "cwd": str(project), "command_name": "archflow:groom", "command_input": f"S1-01 {SECRET} --token hunter2",
    })
    events = [e for e in sent(home) if e["event"] == "command_run"]
    assert len(events) == 1 and events[0]["properties"]["command"] == "archflow:groom"
    assert_allowed(events[0])
    assert_no_leak(sent(home), SECRET, "hunter2", str(project))


@pytest.mark.parametrize("host", ["codex", "copilot", "cursor", "gemini"])
def test_prompt_hook_sends_only_the_command_name(home, project, host):
    prompt = f"/archflow-groom S1-01 for {SECRET}, password hunter2"
    if host == "codex":
        prompt = "$" + prompt[1:]
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": prompt},
         root=ADAPTER_ROOTS[host], ARCHFLOW_HOST=host)
    events = sent(home)
    assert len(events) == 1
    assert events[0]["properties"]["command"] == "archflow:groom"
    assert events[0]["properties"]["host"] == host
    assert events[0]["properties"]["detected_by"] == "prompt_prefix"
    assert_allowed(events[0])
    assert_no_leak(events, SECRET, "hunter2", "S1-01")


def test_a_prompt_that_only_mentions_a_command_sends_nothing(home, project):
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": f"please run /archflow-status on {SECRET}"},
         root=ADAPTER_ROOTS["codex"], ARCHFLOW_HOST="codex")
    assert sent(home) == []


# --------------------------------------------------------------------------
# Values read from the user's YAML or the host are validated
# --------------------------------------------------------------------------

def test_hand_edited_yaml_values_are_sent_as_null(home, project):
    (project / ".archflow" / "current-phase.yaml").write_text(f"phase: {SECRET}\nmode: {SECRET}\n")
    (project / ".archflow" / "project-settings.yaml").write_text(f"project_type: {SECRET}\n")
    hook(home, project, payload={"cwd": str(project), "source": SECRET})
    events = sent(home)
    p = events[0]["properties"]
    assert (p["project_type"], p["phase"], p["mode"]) == (None, None, None)
    assert p["session_source"] == "other"
    assert_no_leak(events, SECRET)


@pytest.mark.parametrize("phase", ["1", "2", "2.25", "2.5", "3", "4", "5", "6"])
def test_every_framework_phase_is_accepted(home, project, phase):
    (project / ".archflow" / "current-phase.yaml").write_text(f'phase: "{phase}"\nmode: full\n')
    hook(home, project)
    p = sent(home)[0]["properties"]
    assert p["phase"] == phase and p["mode"] == "full"


@pytest.mark.parametrize("value", ["7", "2.7", "3a", "-1"])
def test_unknown_phase_is_null(home, project, value):
    (project / ".archflow" / "current-phase.yaml").write_text(f"phase: {value}\n")
    hook(home, project)
    assert sent(home)[0]["properties"]["phase"] is None


@pytest.mark.parametrize("ptype", ["fullstack", "frontend_only", "backend_only", "mobile"])
def test_known_project_types_pass(home, project, ptype):
    (project / ".archflow" / "project-settings.yaml").write_text(f"project_type: {ptype}\n")
    hook(home, project)
    assert sent(home)[0]["properties"]["project_type"] == ptype


@pytest.mark.parametrize("source", ["startup", "resume", "clear", "compact"])
def test_known_session_sources_pass(home, project, source):
    hook(home, project, payload={"cwd": str(project), "source": source})
    assert sent(home)[0]["properties"]["session_source"] == source


def test_unknown_host_and_odd_entrypoint_are_masked(home, project):
    hook(home, project, ARCHFLOW_HOST=SECRET, CLAUDE_CODE_ENTRYPOINT=f"/path/{SECRET}")
    events = sent(home)
    assert events[0]["properties"]["host"] == "other"
    assert events[0]["properties"]["entrypoint"] == "other"
    assert_no_leak(events, SECRET)


# --------------------------------------------------------------------------
# Opt-out variables
# --------------------------------------------------------------------------

@pytest.mark.parametrize("var", ["DO_NOT_TRACK", "CI", "ARCHFLOW_TELEMETRY_DISABLED"])
@pytest.mark.parametrize("value", ["1", "true", "yes", "anything"])
def test_disabling_variables_send_nothing(home, project, var, value):
    out = hook(home, project, **{var: value}).stdout
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"}, **{var: value})
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": "/archflow-status"},
         root=ADAPTER_ROOTS["cursor"], ARCHFLOW_HOST="cursor", **{var: value})
    hook(home, project, ["--disable"], **{var: value})
    assert sent(home) == []
    assert out == "", "no notice is shown while telemetry is disabled"


@pytest.mark.parametrize("var", ["DO_NOT_TRACK", "CI", "ARCHFLOW_TELEMETRY_DISABLED"])
@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "FALSE", " Off "])
def test_falsy_values_leave_telemetry_on(home, project, var, value):
    hook(home, project, **{var: value})
    assert [e["event"] for e in sent(home)] == ["session_start"]


def test_opt_out_sends_one_final_event_then_nothing(home, project):
    hook(home, project, ["--disable"])
    hook(home, project)
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"})
    events = sent(home)
    assert [e["event"] for e in events] == ["telemetry_opted_out"]
    assert_allowed(events[0])
    assert config(home)["telemetryEnabled"] is False


# --------------------------------------------------------------------------
# On by default, on every host
# --------------------------------------------------------------------------

def test_default_is_on_with_a_fresh_config(home, project):
    assert not (home / ".archflow").exists()
    status = hook(home, project, ["--status"]).stdout
    assert status.startswith("on"), status
    hook(home, project)
    assert [e["event"] for e in sent(home)] == ["session_start"]


@pytest.mark.parametrize("host", sorted(ADAPTER_ROOTS))
def test_every_adapter_sends_by_default(home, project, host):
    root = ADAPTER_ROOTS[host]
    hook(home, project, root=root, ARCHFLOW_HOST=host)
    events = sent(home)
    assert [e["event"] for e in events] == ["session_start"], host
    assert events[0]["properties"]["host"] == host
    assert re.fullmatch(r"\d+\.\d+\.\d+.*", events[0]["properties"]["archflow_version"] or ""), host


def test_cursor_bridge_sends_by_default(home, tmp_path):
    """End to end through the generated bridge, which sets ARCHFLOW_HOST itself. A plain folder,
    so the bridge skips the upgrade check and makes no GitHub request."""
    bridge = ADAPTER_ROOTS["cursor"] / "hooks" / "cursor-bridge.mjs"
    plain = tmp_path / "plain"
    plain.mkdir()
    hook(home, plain, ["sessionStart"], {"workspace_roots": [str(plain)]}, script=bridge)
    hook(home, plain, ["beforeSubmitPrompt"], {"workspace_roots": [str(plain)], "prompt": "/archflow-status now"},
         script=bridge)
    events = sent(home)
    assert [e["event"] for e in events] == ["session_start", "command_run"]
    assert {e["properties"]["host"] for e in events} == {"cursor"}


@pytest.mark.parametrize("host,event_file", [
    ("codex", ADAPTERS / "codex" / ".codex" / "hooks.json"),
    ("gemini", ADAPTERS / "gemini" / "hooks" / "hooks.json"),
    ("copilot", ADAPTERS / "copilot" / ".github" / "hooks" / "archflow.json"),
    ("cursor", ADAPTERS / "cursor" / ".cursor" / "hooks.json"),
])
def test_host_wiring_runs_telemetry_without_an_opt_in(host, event_file):
    """No adapter gates telemetry behind a flag: the session hook is wired unconditionally."""
    if not event_file.exists():
        pytest.skip(f"{event_file} not generated")
    text = event_file.read_text()
    assert ("telemetry.mjs" in text) or ("cursor-bridge.mjs" in text), host
    assert "ARCHFLOW_TELEMETRY" not in text, f"{host} wiring touches the telemetry switch"


def test_cli_install_sends_by_default(home, tmp_path):
    target = tmp_path / SECRET
    target.mkdir()
    proc = subprocess.run(
        ["node", str(CLI), "install", "--bundled", "--host", "codex", "--yes", "--no-guard", "--dir", str(target)],
        capture_output=True, text=True, timeout=60, env=base_env(home),
    )
    assert proc.returncode == 0, proc.stderr
    events = sent(home)
    assert [e["event"] for e in events] == ["cli_install"]
    assert_allowed(events[0])
    p = events[0]["properties"]
    assert p["host"] == "cli" and p["installed_hosts"] == ["codex"] and p["source"] == "bundled with this package"
    assert_no_leak(events, SECRET)
    assert "anonymous usage telemetry" in proc.stdout


# --------------------------------------------------------------------------
# The one-time notice
# --------------------------------------------------------------------------

def test_notice_is_printed_once(home, project):
    first = hook(home, project).stdout
    second = hook(home, project).stdout
    assert "anonymous usage telemetry" in first
    assert "/archflow:telemetry off" in first
    assert second == ""
    assert "noticeShownAt" in config(home)


def test_notice_names_what_is_sent():
    code = f"import {{ NOTICE }} from {json.dumps(LIB.as_uri())}; process.stdout.write(NOTICE);"
    notice = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True).stdout
    flat = " ".join(notice.split())
    for word in ("commands", "host", "entrypoint", "Studio", "version", "project type", "phase", "mode",
                 "hosts installed"):
        assert word in flat, f"notice does not mention {word}"
    for never in ("project names", "file paths", "file contents", "prompts", "command arguments"):
        assert never in flat
    assert "?" not in notice, "the notice is a statement, not a question"


def test_notice_is_not_printed_when_disabled_by_config(home, project):
    hook(home, project, ["--disable"])
    (home / "sink.jsonl").unlink(missing_ok=True)
    cfg = config(home)
    cfg.pop("noticeShownAt", None)
    (home / ".archflow" / "config.json").write_text(json.dumps(cfg))
    assert hook(home, project).stdout == ""
    assert sent(home) == []


def test_command_hook_prints_the_notice_when_it_runs_first(home, project):
    out = hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"}).stdout
    assert "anonymous usage telemetry" in out
    assert hook(home, project).stdout == ""


# --------------------------------------------------------------------------
# The notice in the shape each host surfaces, marked shown only when emitted
# --------------------------------------------------------------------------

def _session_start_output(home, project, host):
    root = ADAPTER_ROOTS.get(host, PLUGIN)
    return hook(home, project, payload={"cwd": str(project), "source": "startup"}, root=root, ARCHFLOW_HOST=host).stdout


def test_copilot_session_start_notice_is_json_additional_context(home, project):
    out = _session_start_output(home, project, "copilot")
    doc = json.loads(out)  # Copilot drops non-JSON SessionStart output
    assert set(doc) == {"additionalContext"}
    assert "anonymous usage telemetry" in doc["additionalContext"]
    assert "/archflow-telemetry off" in doc["additionalContext"]
    assert "noticeShownAt" in config(home)


def test_gemini_session_start_notice_is_hook_specific_json(home, project):
    doc = json.loads(_session_start_output(home, project, "gemini"))
    assert doc["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "anonymous usage telemetry" in doc["hookSpecificOutput"]["additionalContext"]
    assert "noticeShownAt" in config(home)


@pytest.mark.parametrize("host", ["claude", "codex", "cursor", "opencode", "generic"])
def test_plain_text_hosts_get_the_notice_as_text(home, project, host):
    out = _session_start_output(home, project, host)
    assert out.startswith("Archflow sends anonymous usage telemetry")
    assert "noticeShownAt" in config(home)


def test_copilot_prints_nothing_once_the_notice_was_shown(home, project):
    _session_start_output(home, project, "copilot")
    assert _session_start_output(home, project, "copilot") == ""


def test_notice_not_marked_shown_when_host_format_is_unknown(home, project):
    """An unrecognised host gets no output, so the notice must stay pending, not be recorded."""
    out = hook(home, project, ARCHFLOW_HOST="some-new-host").stdout
    assert out == ""
    assert "noticeShownAt" not in config(home)
    # The event itself is still sent (host masked), and a later known host shows the notice.
    assert sent(home)[0]["properties"]["host"] == "other"
    assert "anonymous usage telemetry" in _session_start_output(home, project, "copilot")
    assert "noticeShownAt" in config(home)


def test_notice_not_marked_shown_when_stdout_cannot_be_written(home, project):
    """stdout is a pipe nobody reads (EPIPE): nothing was emitted, so nothing is recorded."""
    r, w = os.pipe()
    os.close(r)
    try:
        proc = subprocess.run(
            ["node", str(HOOK)], input=json.dumps({"cwd": str(project)}).encode(), stdout=w,
            stderr=subprocess.PIPE, cwd=str(project), timeout=15,
            env=base_env(home, CLAUDE_PLUGIN_ROOT=PLUGIN),
        )
    finally:
        os.close(w)
    assert proc.returncode == 0, proc.stderr
    assert "noticeShownAt" not in config(home)
    assert len(sent(home)) == 1, "the event still goes out; only the notice stays pending"


def test_prompt_hook_never_marks_the_notice_shown(home, project):
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": "/archflow-status"},
         root=ADAPTER_ROOTS["copilot"], ARCHFLOW_HOST="copilot")
    assert "noticeShownAt" not in config(home)


def test_copilot_loading_the_claude_plugin_directly_keeps_the_notice_pending(home, project):
    """No ARCHFLOW_HOST and no Claude Code markers: the format is unknown, so print nothing and
    do not record the notice as shown (Copilot would drop plain text)."""
    out = hook(home, project, CLAUDECODE=None, CLAUDE_CODE_ENTRYPOINT=None).stdout
    assert out == ""
    assert "noticeShownAt" not in config(home)
    assert [e["event"] for e in sent(home)] == ["session_start"]
    assert sent(home)[0]["properties"]["entrypoint"] is None


@pytest.mark.parametrize("marker", [{"CLAUDECODE": "1"}, {"CLAUDE_CODE_ENTRYPOINT": "cli", "CLAUDECODE": None}])
def test_either_claude_code_marker_is_enough_for_the_plain_notice(home, project, marker):
    out = hook(home, project, **marker).stdout
    assert out.startswith("Archflow sends anonymous usage telemetry")
    assert "noticeShownAt" in config(home)


# --------------------------------------------------------------------------
# A config.json that cannot be read
# --------------------------------------------------------------------------

BAD_CONFIGS = ["{not json", "null", "[]", '"on"', "42", ""]


def write_config(home, text):
    (home / ".archflow").mkdir(exist_ok=True)
    path = home / ".archflow" / "config.json"
    path.write_text(text)
    return path


@pytest.mark.parametrize("text", BAD_CONFIGS)
def test_unreadable_config_disables_telemetry_and_is_never_overwritten(home, project, text):
    path = write_config(home, text)
    out = hook(home, project).stdout
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"})
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": "/archflow-status"},
         root=ADAPTER_ROOTS["cursor"], ARCHFLOW_HOST="cursor")
    assert sent(home) == []
    assert out == "", "no notice while the config is unreadable"
    assert path.read_text() == text, "the unreadable file must be left exactly as it was"


@pytest.mark.parametrize("text", BAD_CONFIGS)
def test_status_says_the_config_is_unreadable(home, project, text):
    write_config(home, text)
    out = hook(home, project, ["--status"]).stdout
    assert out.startswith("off") and "could not be read" in out


@pytest.mark.parametrize("flag", ["--enable", "--disable"])
def test_consent_change_with_unreadable_config_changes_nothing(home, project, flag):
    path = write_config(home, "null")
    out = hook(home, project, [flag]).stdout
    assert "Nothing was changed" in out and "could not be read" in out
    assert path.read_text() == "null"
    assert sent(home) == []


@pytest.mark.parametrize("args", [["telemetry"], ["telemetry", "off"], ["telemetry", "on"]])
def test_cli_telemetry_with_unreadable_config(home, args):
    path = write_config(home, "null")
    proc = subprocess.run(["node", str(CLI), *args], capture_output=True, text=True, timeout=30, env=base_env(home))
    assert proc.returncode == 0, proc.stderr
    assert "could not be read" in proc.stdout
    assert path.read_text() == "null"
    assert sent(home) == []


def test_cli_install_with_unreadable_config_succeeds_and_sends_nothing(home, tmp_path):
    path = write_config(home, "null")
    target = tmp_path / "proj"
    target.mkdir()
    proc = subprocess.run(
        ["node", str(CLI), "install", "--bundled", "--host", "codex", "--yes", "--no-guard", "--dir", str(target)],
        capture_output=True, text=True, timeout=60, env=base_env(home),
    )
    assert proc.returncode == 0, proc.stderr
    assert "could not be read" in proc.stdout
    assert sent(home) == []
    assert path.read_text() == "null"


# --------------------------------------------------------------------------
# A malformed stored id is replaced
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad_id", ["anonymous", SECRET, "", 42])
def test_invalid_stored_distinct_id_is_replaced(home, project, bad_id):
    write_config(home, json.dumps({"distinctId": bad_id, "noticeShownAt": "2026-01-01T00:00:00.000Z"}))
    hook(home, project)
    hook(home, project)
    ids = [e["properties"]["distinct_id"] for e in sent(home)]
    assert len(ids) == 2 and ids[0] == ids[1] and UUID.match(ids[0])
    assert config(home)["distinctId"] == ids[0]
    assert_no_leak(sent(home), SECRET)


OPT_OUT = {
    "claude": "/archflow:telemetry off",
    "gemini": "/archflow:telemetry off",
    "codex": "$archflow-telemetry off",
    "generic": "$archflow-telemetry off",
    "copilot": "/archflow-telemetry off",
    "cursor": "/archflow-telemetry off",
    "opencode": "/archflow-telemetry off",
}


@pytest.mark.parametrize("host", sorted(OPT_OUT))
def test_notice_names_the_hosts_own_opt_out_command(home, project, host):
    out = _session_start_output(home, project, host)
    if host == "copilot":
        text = json.loads(out)["additionalContext"]
    elif host == "gemini":
        text = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    else:
        text = out
    assert f"that {OPT_OUT[host]} turns it off" in text, f"{host}: {out!r}"
    others = {c for h, c in OPT_OUT.items() if c != OPT_OUT[host]}
    assert not any(c in text for c in others), f"{host} names another host's command"


@pytest.mark.parametrize("host", sorted(OPT_OUT))
def test_opt_out_command_exists_in_that_hosts_adapter(host):
    """The command the notice names is one the host really ships."""
    name = {
        "claude": PLUGIN / "commands" / "telemetry.md",
        "gemini": ADAPTERS / "gemini" / "commands" / "archflow" / "telemetry.toml",
        "codex": ADAPTERS / "codex" / ".agents" / "skills" / "archflow-telemetry",
        "generic": ADAPTERS / "generic" / ".agents" / "skills" / "archflow-telemetry",
        "copilot": ADAPTERS / "copilot" / ".github" / "skills" / "archflow-telemetry",
        "cursor": ADAPTERS / "cursor" / ".cursor" / "commands" / "archflow-telemetry.md",
        "opencode": ADAPTERS / "opencode" / ".opencode" / "commands" / "archflow-telemetry.md",
    }[host]
    assert name.exists(), f"{host}: {name} not found, so {OPT_OUT[host]!r} would not work"


def test_unknown_host_falls_back_to_the_cli_opt_out():
    code = (
        f"import {{ optOutLine }} from {json.dumps(LIB.as_uri())};\n"
        "process.stdout.write(optOutLine('some-new-host') + '|' + optOutLine(undefined));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True).stdout
    assert out.count("npx archflow telemetry off") == 2


def test_generic_session_start_resolves_the_version_without_plugin_root(home, tmp_path):
    """AGENTS.md runs the hook with only ARCHFLOW_HOST=generic set; the version must still resolve."""
    proj = tmp_path / "proj"
    shutil.copytree(ADAPTERS / "generic" / ".agents", proj / ".agents", symlinks=True)
    env = base_env(home, ARCHFLOW_HOST="generic", CLAUDECODE=None)
    assert "CLAUDE_PLUGIN_ROOT" not in env
    proc = subprocess.run(
        "node .agents/archflow/hooks/telemetry.mjs </dev/null",
        shell=True, cwd=str(proj), capture_output=True, text=True, timeout=15, env=env,
    )
    assert proc.returncode == 0, proc.stderr
    events = sent(home)
    assert [e["event"] for e in events] == ["session_start"]
    expected = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]
    assert events[0]["properties"]["archflow_version"] == expected
    assert events[0]["properties"]["host"] == "generic"
    assert "$archflow-telemetry off" in proc.stdout


def test_security_md_documents_every_named_property():
    """The payload in SECURITY.md is complete: each property it names literally, plus the PostHog flag."""
    text = (REPO / "SECURITY.md").read_text()
    section = text[text.index("## Telemetry"):text.index("## Credentials")]
    for name in ("via_studio", "studio_capture", "session_source", "detected_by", "$process_person_profile",
                 "session_start", "command_run", "cli_install", "telemetry_opted_out", "telemetry_opted_in"):
        assert name in section, f"SECURITY.md telemetry section does not name {name}"


# --------------------------------------------------------------------------
# The id is minted on the first event, whichever hook sends it
# --------------------------------------------------------------------------

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.mark.parametrize("host", ["codex", "copilot", "cursor", "gemini"])
def test_prompt_hook_first_on_a_fresh_machine_mints_the_id(home, project, host):
    out = hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": "/archflow-status"},
               root=ADAPTER_ROOTS[host], ARCHFLOW_HOST=host).stdout
    assert out == "", "prompt hooks print nothing; on some hosts stdout is model context or must be JSON"
    first = sent(home)[0]["properties"]["distinct_id"]
    assert first != "anonymous" and UUID.match(first)
    assert config(home)["distinctId"] == first
    # The notice was not shown yet, so the next session start shows it, and the id is kept.
    notice = hook(home, project, root=ADAPTER_ROOTS[host], ARCHFLOW_HOST=host).stdout
    assert "anonymous usage telemetry" in notice
    assert {e["properties"]["distinct_id"] for e in sent(home)} == {first}


def test_session_start_first_mints_the_id(home, project):
    hook(home, project)
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"})
    ids = {e["properties"]["distinct_id"] for e in sent(home)}
    assert len(ids) == 1 and UUID.match(ids.pop())


# --------------------------------------------------------------------------
# Command names are checked against the shipped list
# --------------------------------------------------------------------------

def test_opencode_unknown_archflow_command_is_not_reported(home, project):
    """OpenCode's plugin passes command.executed names to --command-run as archflow:<name>."""
    root = ADAPTER_ROOTS["opencode"]
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": f"archflow:{SECRET}"},
         root=root, ARCHFLOW_HOST="opencode")
    assert [e for e in sent(home) if e["event"] == "command_run"] == []
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"},
         root=root, ARCHFLOW_HOST="opencode")
    runs = [e for e in sent(home) if e["event"] == "command_run"]
    assert len(runs) == 1 and runs[0]["properties"]["command"] == "archflow:status"
    assert runs[0]["properties"]["host"] == "opencode"
    assert_no_leak(sent(home), SECRET)


def test_opencode_plugin_routes_commands_through_the_checked_hook():
    plugin = (ADAPTERS / "opencode" / ".opencode" / "plugins" / "archflow.ts").read_text()
    assert '["--command-run"]' in plugin
    assert "lib/commands.json" in plugin or "commands.json" in plugin


def test_claude_unknown_archflow_command_is_not_reported(home, project):
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:my-own-command"})
    assert [e for e in sent(home) if e["event"] == "command_run"] == []


def test_telemetry_command_itself_is_never_reported(home, project):
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:telemetry"})
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": "/archflow-telemetry off"},
         root=ADAPTER_ROOTS["cursor"], ARCHFLOW_HOST="cursor")
    assert [e for e in sent(home) if e["event"] == "command_run"] == []


# --------------------------------------------------------------------------
# The sink really replaces the network
# --------------------------------------------------------------------------

def test_capture_never_spawns_the_sender_when_the_sink_is_set(home):
    """Guard on this file's own safety: with the sink set, capture() must not spawn --send."""
    code = (
        "import cp from 'node:child_process';\n"
        "import { syncBuiltinESMExports } from 'node:module';\n"
        "let spawned = 0; cp.spawn = () => { spawned++; return { unref() {} }; }; syncBuiltinESMExports();\n"
        f"const {{ capture }} = await import({json.dumps(LIB.as_uri())});\n"
        "capture('session_start', {});\n"
        "process.stdout.write(String(spawned));\n"
    )
    proc = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True,
                          timeout=15, env=base_env(home))
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0"
    assert len(sent(home)) == 1
