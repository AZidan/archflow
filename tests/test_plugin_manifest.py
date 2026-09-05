"""Cheap structural checks on what actually ships."""

import json
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
AGENTS = REPO / "plugin" / "agents"
COMMANDS = REPO / "plugin" / "commands"


def _frontmatter(path):
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    assert m, f"{path.name} has no YAML frontmatter"
    return yaml.safe_load(m.group(1))


def test_every_agent_has_valid_frontmatter():
    for path in sorted(AGENTS.glob("*.md")):
        fm = _frontmatter(path)
        assert fm.get("name") == path.stem, f"{path.name}: name does not match filename"
        assert fm.get("description"), f"{path.name}: no description"


def test_every_command_has_a_description():
    for path in sorted(COMMANDS.glob("*.md")):
        fm = _frontmatter(path)
        assert fm.get("description"), f"{path.name}: no description"


def test_agent_descriptions_stay_short():
    """Descriptions load into every session. They are not documentation."""
    for path in sorted(AGENTS.glob("*.md")):
        desc = _frontmatter(path)["description"]
        assert len(desc) <= 400, f"{path.name}: description is {len(desc)} chars"
        assert "<example>" not in desc, f"{path.name}: example blocks belong in the body, not the index"


def test_no_agent_prescribes_a_technology():
    """AF-32. Agents read stack: from current-phase.yaml; they carry no stack.

    Detection lists are legitimate, so this checks the imperative forms only.
    """
    banned = re.compile(
        r"\b(?:use|using|build\s+with|implement\s+(?:in|with)|write\s+in)\s+"
        r"(?:the\s+)?(NestJS|PostgreSQL|MySQL|MongoDB|TypeORM|Prisma|Tailwind|"
        r"SwiftUI|Jetpack\s+Compose|React\s+Native|React|Vue|Angular|Express|"
        r"Jest|Detox|XCTest|Espresso|Cypress|Playwright|GitHub\s+Actions|"
        r"Firebase|Fastlane)\b",
        re.I,
    )
    offenders = []
    for path in sorted(AGENTS.glob("*.md")):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if banned.search(line):
                offenders.append(f"{path.name}:{i}: {line.strip()[:90]}")
    assert not offenders, "agents must not prescribe a technology:\n" + "\n".join(offenders)


def test_no_author_specific_paths_or_credentials_ship():
    leaked = []
    for path in sorted(REPO.glob("plugin/**/*.md")):
        text = path.read_text()
        for needle in ("/Users/", "Admin12345", "aegis.ai"):
            if needle in text:
                leaked.append(f"{path.relative_to(REPO)} contains {needle!r}")
    assert not leaked, "\n".join(leaked)


def test_external_installs_are_pinned():
    """An unpinned git ref runs whatever is on main at install time."""
    unpinned = []
    pat_git = re.compile(r"git\+https://[^\s\"']+?\.git(?!@)")
    pat_npx = re.compile(r"github:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    for path in list(REPO.glob("plugin/**/*.md")) + list(REPO.glob("plugin/**/*.yaml")):
        text = path.read_text()
        for m in pat_git.finditer(text):
            unpinned.append(f"{path.relative_to(REPO)}: {m.group(0)}")
        for m in pat_npx.finditer(text):
            # the ref must be pinned with #<sha> immediately after the repo name
            if not text[m.end():m.end() + 1] == "#":
                unpinned.append(f"{path.relative_to(REPO)}: {m.group(0)}")
    assert not unpinned, "unpinned external installs:\n" + "\n".join(unpinned)


def test_marketplace_and_plugin_manifests_agree():
    marketplace = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    plugin = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text())
    entry = next(p for p in marketplace["plugins"] if p["name"] == plugin["name"])
    assert entry["version"] == plugin["version"], "marketplace and plugin versions disagree"


def test_agent_count_claims_match_reality():
    actual = len(list(AGENTS.glob("*.md")))
    plugin = (REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text()
    assert f"{actual} specialized agents" in plugin, f"plugin.json does not say {actual} agents"


# --------------------------------------------------------------------------
# Release hygiene (AF-30)
# --------------------------------------------------------------------------

def test_hygiene_files_exist():
    for name in ("CHANGELOG.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "LICENSE"):
        assert (REPO / name).exists(), f"{name} is missing"


def test_changelog_has_a_section_for_the_current_version():
    """The release workflow builds its notes from this section. No section, no release."""
    version = json.loads((REPO / "plugin" / ".claude-plugin" / "plugin.json").read_text())["version"]
    changelog = (REPO / "CHANGELOG.md").read_text()
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", changelog, re.S | re.M)
    assert m, f"CHANGELOG.md has no section for {version}"
    assert m.group(1).strip(), f"the {version} section is empty"


def test_changelog_keeps_an_unreleased_section():
    assert "## [Unreleased]" in (REPO / "CHANGELOG.md").read_text()


def test_release_workflow_verifies_the_tag_against_the_manifests():
    wf = (REPO / ".github" / "workflows" / "release.yml").read_text()
    assert "plugin.json" in wf and "marketplace.json" in wf, \
        "the release workflow must refuse a tag that disagrees with the manifests"
