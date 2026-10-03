"""Tests for the telemetry opt-out/in command (S8-06).

`npx archflow telemetry [on|off|status]` (scripts/archflow.mjs) and `/archflow:telemetry [on|off|status]`
on every host (plugin/commands/telemetry.md and the per-host copies build-adapters.mjs generates).

Nothing here reaches PostHog: every process runs with the helpers from test_telemetry.py, which
set ARCHFLOW_TELEMETRY_SINK and point HOME and ARCHFLOW_CONFIG_DIR at a temp dir.
"""

import json
import re
import shutil
import subprocess

import pytest

from test_telemetry import (  # noqa: F401  (home, project are fixtures)
    ADAPTERS,
    CLI,
    PLUGIN,
    assert_allowed,
    base_env,
    config,
    home,
    hook,
    project,
    sent,
    write_config,
)

OLD_NOTICE = "2026-01-01T00:00:00.000Z"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def cli(home, *args, **env):
    return subprocess.run(
        ["node", str(CLI), "telemetry", *args],
        capture_output=True, text=True, timeout=30, env=base_env(home, **env),
    )


def events(home):
    return [e["event"] for e in sent(home)]


def later_activity(home, project):
    """A session start, a command hook and a prompt hook: everything that sends while on."""
    hook(home, project)
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:status"})
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": "/archflow-status"},
         root=ADAPTERS / "cursor" / ".cursor" / "archflow", ARCHFLOW_HOST="cursor")


# --------------------------------------------------------------------------
# npx archflow telemetry
# --------------------------------------------------------------------------

@pytest.mark.parametrize("args", [[], ["status"]])
def test_cli_status_on_a_fresh_machine(home, args):
    proc = cli(home, *args)
    assert proc.returncode == 0, proc.stderr
    assert "on (default)" in proc.stdout
    assert "archflow telemetry off" in proc.stdout
    assert sent(home) == []
    assert not (home / ".archflow" / "config.json").exists(), "showing the setting writes nothing"


def test_cli_off_sends_one_opted_out_event_then_nothing(home, project):
    proc = cli(home, "off")
    assert proc.returncode == 0, proc.stderr
    assert "Anonymous usage telemetry is now OFF." in proc.stdout
    assert "One final event recorded the opt-out" in proc.stdout
    cfg = config(home)
    assert cfg["telemetryEnabled"] is False
    assert ISO.match(cfg["consentChangedAt"])
    out = sent(home)
    assert [e["event"] for e in out] == ["telemetry_opted_out"]
    assert_allowed(out[0])
    assert out[0]["properties"]["via"] == "cli" and out[0]["properties"]["host"] == "cli"

    later_activity(home, project)
    cli(home, "status")
    assert events(home) == ["telemetry_opted_out"], "nothing is sent after the opt-out"


def test_cli_off_twice_sends_one_event_and_keeps_the_change_time(home):
    cli(home, "off")
    first = config(home)["consentChangedAt"]
    proc = cli(home, "off")
    assert proc.returncode == 0, proc.stderr
    assert "now OFF" in proc.stdout and "One final event" not in proc.stdout
    assert events(home) == ["telemetry_opted_out"]
    assert config(home)["consentChangedAt"] == first


def test_cli_on_after_off_sends_opted_in_and_resumes(home, project):
    cli(home, "off")
    proc = cli(home, "on")
    assert proc.returncode == 0, proc.stderr
    assert "Anonymous usage telemetry is now ON." in proc.stdout
    assert config(home)["telemetryEnabled"] is True
    out = sent(home)
    assert [e["event"] for e in out] == ["telemetry_opted_out", "telemetry_opted_in"]
    assert_allowed(out[1])
    assert out[1]["properties"]["via"] == "cli"
    assert out[0]["properties"]["distinct_id"] == out[1]["properties"]["distinct_id"]
    hook(home, project)
    assert events(home)[-1] == "session_start"


def test_cli_on_when_already_on_sends_nothing(home):
    proc = cli(home, "on")
    assert proc.returncode == 0, proc.stderr
    assert "now ON" in proc.stdout
    assert sent(home) == []
    assert "consentChangedAt" not in config(home), "repeating the default is not a change"


@pytest.mark.parametrize("var", ["DO_NOT_TRACK", "CI", "ARCHFLOW_TELEMETRY_DISABLED"])
def test_cli_sends_nothing_when_disabled_by_the_environment(home, var):
    assert cli(home, "off", **{var: "1"}).returncode == 0
    assert config(home)["telemetryEnabled"] is False, "the choice is still stored"
    assert cli(home, "on", **{var: "1"}).returncode == 0
    assert config(home)["telemetryEnabled"] is True
    assert sent(home) == []
    status = cli(home, **{var: "1"}).stdout
    assert f"off ({var} is set" in status
    assert "archflow telemetry on" not in status, "`on` cannot take effect while the variable is set"


def env_on_message(var):
    return (f"Your choice (on) is saved, but anonymous usage telemetry stays OFF while {var} is set; "
            "nothing is sent.\n")


@pytest.mark.parametrize("var", ["DO_NOT_TRACK", "CI", "ARCHFLOW_TELEMETRY_DISABLED"])
def test_on_while_disabled_by_the_environment_says_it_stays_off(home, project, var):
    """The CLI and the host command print the same truthful line, and still store the choice."""
    write_config(home, json.dumps({"telemetryEnabled": False}))
    proc = cli(home, "on", **{var: "1"})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == env_on_message(var)
    assert "now ON" not in proc.stdout
    assert config(home)["telemetryEnabled"] is True

    write_config(home, json.dumps({"telemetryEnabled": False}))
    out = hook(home, project, ["--enable", "--host", "cursor"], **{var: "1"}).stdout
    assert out == env_on_message(var)
    assert config(home)["telemetryEnabled"] is True
    assert sent(home) == []


@pytest.mark.parametrize("args", [[], ["status"]])
def test_cli_status_suggests_the_other_setting_when_it_can_take_effect(home, args):
    assert "`archflow telemetry off` to turn it off" in cli(home, *args).stdout
    cli(home, "off")
    assert "`archflow telemetry on` to turn it on" in cli(home, *args).stdout, "off by choice: `on` works"


# --------------------------------------------------------------------------
# "since" is the last consent change, not the notice
# --------------------------------------------------------------------------

def _since(text):
    m = re.search(r"since ([0-9T:.\-]+Z)", text)
    return m and m.group(1)


def test_status_after_opt_out_shows_when_it_was_turned_off(home, project):
    write_config(home, json.dumps({"noticeShownAt": OLD_NOTICE}))
    cli(home, "off")
    cfg = config(home)
    assert cfg["noticeShownAt"] == OLD_NOTICE, "noticeShownAt keeps its meaning"
    assert cfg["consentChangedAt"] != OLD_NOTICE
    hook_status = hook(home, project, ["--status"]).stdout
    cli_status = cli(home).stdout
    assert hook_status.startswith("off") and _since(hook_status) == cfg["consentChangedAt"]
    assert _since(cli_status) == cfg["consentChangedAt"]


def test_status_before_any_change_is_since_the_notice(home, project):
    write_config(home, json.dumps({"noticeShownAt": OLD_NOTICE}))
    assert hook(home, project, ["--status"]).stdout == f"on (since {OLD_NOTICE})\n"


def test_status_after_opt_in_shows_when_it_was_turned_back_on(home, project):
    write_config(home, json.dumps({"noticeShownAt": OLD_NOTICE, "telemetryEnabled": False,
                                   "consentChangedAt": OLD_NOTICE}))
    hook(home, project, ["--enable"])
    changed = config(home)["consentChangedAt"]
    assert changed != OLD_NOTICE
    assert hook(home, project, ["--status"]).stdout == f"on (since {changed})\n"


# --------------------------------------------------------------------------
# The command's --host
# --------------------------------------------------------------------------

@pytest.mark.parametrize("given,expected", [("copilot", "copilot"), ("gemini", "gemini"), ("nonsense", "other")])
def test_hook_consent_change_carries_the_given_host(home, project, given, expected):
    hook(home, project, ["--disable", "--host", given])
    out = sent(home)
    assert [e["event"] for e in out] == ["telemetry_opted_out"]
    assert out[0]["properties"]["host"] == expected
    assert out[0]["properties"]["via"] == "command"


# --------------------------------------------------------------------------
# Every host's command file runs the right thing
# --------------------------------------------------------------------------

# host -> (generated file, the adapter subtree a user installs, where it lands relative to the
#          install base, and whether that base is HOME (Gemini extension) or the project root)
HOST_FILES = {
    "claude": (PLUGIN / "commands" / "telemetry.md", None, None, None),
    "codex": (ADAPTERS / "codex" / ".agents" / "skills" / "archflow-telemetry" / "SKILL.md",
              ADAPTERS / "codex" / ".codex", ".codex", "project"),
    "generic": (ADAPTERS / "generic" / ".agents" / "skills" / "archflow-telemetry" / "SKILL.md",
                ADAPTERS / "generic" / ".agents", ".agents", "project"),
    "copilot": (ADAPTERS / "copilot" / ".github" / "skills" / "archflow-telemetry" / "SKILL.md",
                ADAPTERS / "copilot" / ".github", ".github", "project"),
    "cursor": (ADAPTERS / "cursor" / ".cursor" / "commands" / "archflow-telemetry.md",
               ADAPTERS / "cursor" / ".cursor", ".cursor", "project"),
    "opencode": (ADAPTERS / "opencode" / ".opencode" / "commands" / "archflow-telemetry.md",
                 ADAPTERS / "opencode" / ".opencode", ".opencode", "project"),
    "gemini": (ADAPTERS / "gemini" / "commands" / "archflow" / "telemetry.toml",
               ADAPTERS / "gemini", ".gemini/extensions/archflow", "home"),
}


def command_lines(text):
    """{'status': line, 'enable': line, 'disable': line} from the fenced commands in the file."""
    lines = {}
    for line in text.splitlines():
        m = re.match(r'^node "[^"]*hooks/telemetry\.mjs" --(status|enable|disable)\b', line)
        if m:
            assert m.group(1) not in lines, f"two {m.group(1)} lines"
            lines[m.group(1)] = line
    return lines


@pytest.mark.parametrize("host", sorted(HOST_FILES))
def test_host_command_file_names_status_on_and_off(host):
    path = HOST_FILES[host][0]
    lines = command_lines(path.read_text())
    assert set(lines) == {"status", "enable", "disable"}, f"{host}: {lines}"
    for line in lines.values():
        assert "~" not in line, f"{host}: ~ does not expand inside quotes: {line}"
    if host == "gemini":
        assert all('"$HOME/.gemini/extensions/archflow/hooks/telemetry.mjs"' in line for line in lines.values())
    if host != "claude":
        assert f"--enable --host {host}" in lines["enable"] and f"--disable --host {host}" in lines["disable"]
        assert "--host" not in lines["status"]


HINT_FILES = {
    "claude": PLUGIN / "commands" / "telemetry.md",
    "codex": ADAPTERS / "codex" / ".agents" / "skills" / "archflow-telemetry" / "SKILL.md",
}
SKILL_LISTINGS = [PLUGIN / "skills" / "archflow" / "SKILL.md"] + [
    ADAPTERS / h / p / "skills" / "archflow" / "SKILL.md"
    for h, p in [("codex", ".agents"), ("generic", ".agents"), ("copilot", ".github"),
                 ("cursor", ".cursor"), ("opencode", ".opencode"), ("gemini", ".")]
]


@pytest.mark.parametrize("path", list(HINT_FILES.values()) + SKILL_LISTINGS, ids=lambda p: str(p.relative_to(PLUGIN.parent)))
def test_argument_hints_list_status(path):
    text = path.read_text()
    assert "telemetry" in text
    assert "[on|off]" not in text, f"{path}: hint omits status"
    assert "[on|off|status]" in text


@pytest.mark.parametrize("host", sorted(HOST_FILES))
def test_host_command_file_says_relay_verbatim_and_matches_the_notice_code(host):
    text = HOST_FILES[host][0].read_text()
    assert "**verbatim**" in text, host
    # (a): the notice is keyed on noticeShownAt, not on the file being absent.
    assert "noticeShownAt" in text, host
    assert "no `~/.archflow/config.json` yet" not in text, host


def _install(host, tmp_path):
    """The host's tree laid out as the user has it; returns (cwd, extra env)."""
    _, subtree, dest, base = HOST_FILES[host]
    proj = tmp_path / "proj"
    proj.mkdir()
    if host == "claude":
        return proj, {"CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
    root = (tmp_path / "home" if base == "home" else proj) / dest
    shutil.copytree(subtree, root, symlinks=True)
    return proj, {}


@pytest.mark.parametrize("host", sorted(HOST_FILES))
def test_host_command_lines_work_when_run(home, tmp_path, host):
    """Run each line exactly as the host's file writes it, in a shell, from the project root."""
    lines = command_lines(HOST_FILES[host][0].read_text())
    proj, extra = _install(host, tmp_path)
    env = base_env(home, CLAUDECODE=None, **extra)
    if host != "claude":
        env.pop("CLAUDE_PLUGIN_ROOT", None)

    def run(kind):
        proc = subprocess.run(["bash", "-c", lines[kind]], cwd=str(proj), capture_output=True,
                              text=True, timeout=15, env=env)
        assert proc.returncode == 0, f"{host} {kind}: {proc.stderr}"
        assert "Cannot find module" not in proc.stderr
        return proc.stdout

    assert run("status") == "on (default)\n"
    out = run("disable")
    assert out == "Anonymous usage telemetry is now OFF. One final event recorded the opt-out; nothing else will be sent.\n"
    assert config(home)["telemetryEnabled"] is False
    assert run("status").startswith(f"off (since {config(home)['consentChangedAt']})")
    assert run("enable") == "Anonymous usage telemetry is now ON.\n"
    assert config(home)["telemetryEnabled"] is True

    got = sent(home)
    assert [e["event"] for e in got] == ["telemetry_opted_out", "telemetry_opted_in"], host
    for e in got:
        assert_allowed(e)
        assert e["properties"]["host"] == host, f"{host}: attributed to {e['properties']['host']}"
        assert e["properties"]["via"] == "command"
        assert re.fullmatch(r"\d+\.\d+\.\d+.*", e["properties"]["archflow_version"] or ""), host
