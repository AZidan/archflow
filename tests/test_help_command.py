"""QA coverage for /archflow:help (S2-06) beyond test_command_registration.py.

test_command_registration.py already guards help.md against plugin/commands/ and the status trim.
These cover the acceptance criteria it does not reach: telemetry recognising help on every host,
every adapter generating help, and the site and docs guides listing it.

Nothing here reaches PostHog: the hook runs with the sink helpers from test_telemetry.py.
"""

import json
import re
from pathlib import Path

import pytest

from test_telemetry import (  # noqa: F401  (home, project are fixtures)
    ADAPTER_ROOTS,
    assert_allowed,
    home,
    hook,
    project,
    sent,
)

REPO = Path(__file__).resolve().parent.parent
COMMANDS = REPO / "plugin" / "commands"
ADAPTERS = REPO / "adapters"
DOCS = REPO / "docs"


def shipped():
    return sorted(p.stem for p in COMMANDS.glob("*.md"))


def command_runs(home):
    return [e for e in sent(home) if e["event"] == "command_run"]


# --------------------------------------------------------------------------
# Telemetry: no hand-kept allowlist, so help must be recognised from the shipped list
# --------------------------------------------------------------------------

def test_claude_code_reports_help_from_the_command_files(home, project):
    """The Claude Code plugin ships no commands.json; knownCommands() reads plugin/commands/*.md."""
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:help"})
    runs = command_runs(home)
    assert len(runs) == 1 and runs[0]["properties"]["command"] == "archflow:help"
    assert_allowed(runs[0])


@pytest.mark.parametrize("host", ["codex", "copilot", "cursor", "gemini", "generic"])
def test_prompt_hosts_report_help_from_their_commands_json(home, project, host):
    prompt = "$archflow-help release" if host in ("codex", "generic") else "/archflow-help release"
    hook(home, project, ["--prompt"], {"cwd": str(project), "prompt": prompt},
         root=ADAPTER_ROOTS[host], ARCHFLOW_HOST=host)
    runs = command_runs(home)
    assert len(runs) == 1, f"{host}: help was not recognised from {ADAPTER_ROOTS[host] / 'lib' / 'commands.json'}"
    assert runs[0]["properties"]["command"] == "archflow:help"
    assert "release" not in json.dumps(runs), "the argument leaked into the payload"


def test_opencode_reports_help_by_name(home, project):
    hook(home, project, ["--command-run"], {"cwd": str(project), "command_name": "archflow:help"},
         root=ADAPTER_ROOTS["opencode"], ARCHFLOW_HOST="opencode")
    runs = command_runs(home)
    assert len(runs) == 1 and runs[0]["properties"]["command"] == "archflow:help"


@pytest.mark.parametrize("host", sorted(ADAPTER_ROOTS))
def test_every_adapter_commands_json_matches_the_plugin(host):
    listed = json.loads((ADAPTER_ROOTS[host] / "lib" / "commands.json").read_text())
    assert sorted(listed) == shipped(), f"{host} commands.json drifted from plugin/commands/"


# --------------------------------------------------------------------------
# Every host adapter generates help
# --------------------------------------------------------------------------

HELP_FILES = {
    "codex": ADAPTERS / "codex" / ".agents" / "skills" / "archflow-help" / "SKILL.md",
    "copilot": ADAPTERS / "copilot" / ".github" / "skills" / "archflow-help" / "SKILL.md",
    "generic": ADAPTERS / "generic" / ".agents" / "skills" / "archflow-help" / "SKILL.md",
    "cursor": ADAPTERS / "cursor" / ".cursor" / "commands" / "archflow-help.md",
    "opencode": ADAPTERS / "opencode" / ".opencode" / "commands" / "archflow-help.md",
    "gemini": ADAPTERS / "gemini" / "commands" / "archflow" / "help.toml",
}


@pytest.mark.parametrize("host", sorted(HELP_FILES))
def test_every_adapter_ships_help(host):
    body = HELP_FILES[host].read_text()
    assert "## How Archflow works" in body
    assert "/archflow:help" not in body or host == "gemini", f"{host} help kept Claude Code invocation syntax"


# --------------------------------------------------------------------------
# Site and docs guides
# --------------------------------------------------------------------------

def site_commands_section():
    html = (DOCS / "index.html").read_text()
    start = html.index("Plus the rest")
    # the featured command cards sit just above the "Plus the rest" line, in the same section
    section_start = html.rfind("<section", 0, start)
    section_end = html.index("</section>", start)
    return html[section_start:section_end]


def test_site_names_every_shipped_command():
    section = site_commands_section()
    named = set(re.findall(r"/archflow:([a-z][a-z-]*)", section))
    named |= set(re.findall(r'font-mono text-xs">([a-z][a-z-]*)<', section))
    missing = sorted(set(shipped()) - named)
    assert not missing, f"docs/index.html commands section omits: {missing}"


def test_site_states_no_total_command_count():
    html = (DOCS / "index.html").read_text()
    words = r"(?:\d+|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
    hits = re.findall(rf"\b{words}\s+(?:slash\s+)?commands\b", html, re.I)
    assert not hits, f"docs/index.html states a command count, which drifts: {hits}"


@pytest.mark.parametrize("guide", ["new-project.md", "existing-codebase.md"])
def test_getting_started_guides_point_at_help(guide):
    assert "/archflow:help" in (DOCS / "guides" / guide).read_text()
