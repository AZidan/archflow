"""Guards on api_contract_path actually being a setting.

The field existed and two agents resolved through it while the two most bound to
the contract — api-engineer and api-contract-architect — hardcoded the default.
On a project that configured a different path, the architect wrote the contract
where it was told and api-engineer read the default and found nothing. Silent,
and on the one artifact the framework calls sacred.

It was also write-once: set at setup, with no way to change it afterwards, which
makes a setting a decoration.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS = REPO / "plugin" / "agents"
CONTRACT_CMD = REPO / "plugin" / "commands" / "contract.md"

# Every agent that reads or writes the contract must resolve the path.
CONTRACT_AGENTS = ["api-engineer", "api-contract-architect", "ui-engineer", "qa-engineer"]
# doc-writer only ever refers to the contract; it must not name a literal path either.
CONTRACT_AWARE = CONTRACT_AGENTS + ["doc-writer"]


def body(name):
    return (AGENTS / f"{name}.md").read_text()


def test_every_contract_agent_resolves_the_path():
    for name in CONTRACT_AGENTS:
        assert "api_contract_path" in body(name), \
            f"{name} does not resolve api_contract_path and will assume the default"


def _contract_files():
    """Everything that reads or writes the contract, not just agents.

    The earlier version globbed plugin/agents/ only, so phase-2.5 — the phase that
    CREATES the contract — hardcoded the path five times, including a literal
    `git add docs/api-contract.md` that stages nothing on a configured project.
    """
    out = {}
    for name in CONTRACT_AWARE:
        out[f"agents/{name}.md"] = body(name)
    for path in (REPO / ".archflow" / "phases").glob("*.md"):
        out[f"phases/{path.name}"] = path.read_text()
    for path in (REPO / "plugin" / "commands").glob("*.md"):
        out[f"commands/{path.name}"] = path.read_text()
    # The repo root too — README.md listed the literal path in a table and was
    # unscanned, inconsistent with the sibling test which added root *.md for
    # exactly this reason.
    for path in REPO.glob("*.md"):
        if path.name != "CHANGELOG.md":
            out[path.name] = path.read_text()
    return out


def test_nothing_hardcodes_the_default_as_an_instruction():
    """Only the line that DEFINES resolution may name the default.

    The earlier version excused any line where `api_contract_path` also appeared,
    which is exactly the weak parenthetical form the offenders used — so it could
    not tell a resolution rule from a hardcoded path with a footnote.
    """
    offenders = []
    for label, text in _contract_files().items():
        for i, line in enumerate(text.splitlines(), 1):
            if "docs/api-contract.md" not in line:
                continue
            # Legitimate shapes: the default AS A VALUE, or as one candidate among
            # several. What is banned is instructing an agent to use it as THE path.
            if re.search(r"[Dd]efault(s)? (to|is) `?docs/api-contract\.md", line):
                continue
            if re.search(r"api_contract_path:\s*[\"']?docs/api-contract\.md", line):
                continue          # writing the default into a template
            if "api_contract_path" in line and "configurable" in line:
                continue          # naming the default while pointing at the setting
            if re.search(r"(swagger|openapi|\betc\b|May be|Scan for)", line, re.I):
                continue          # a list of candidate locations, not an instruction
            if re.match(r"^\s*[│├└─]", line):
                continue          # a directory-tree illustration
            offenders.append(f"{label}:{i}: {line.strip()[:90]}")
    assert not offenders, "hardcoded contract path:\n" + "\n".join(offenders)


def test_the_weak_agents_got_the_strong_rule():
    """Resolving must be an instruction, not a parenthetical afterthought."""
    for name in ("ui-engineer", "qa-engineer", "api-engineer", "api-contract-architect"):
        text = body(name)
        assert re.search(r"\bresolve\b", text, re.I) and "api_contract_path" in text, \
            f"{name} has no explicit instruction to resolve api_contract_path"


def test_the_path_can_be_changed_after_setup():
    cmd = CONTRACT_CMD.read_text()
    assert "path <path>" in cmd, "no way to change api_contract_path after setup"
    fm = re.match(r"^---\n(.*?)\n---", cmd, re.S).group(1)
    assert "path" in re.search(r"argument-hint:\s*(.+)", fm).group(1), \
        "the argument-hint does not advertise the path form"


def test_relocation_distinguishes_pointing_from_moving():
    """Pointing at an existing contract and moving one are different operations."""
    cmd = CONTRACT_CMD.read_text()
    assert re.search(r"already exists", cmd)
    assert re.search(r"does not exist", cmd)
    assert re.search(r"\bmv\b", cmd), "relocation must actually move the file"


def test_relocation_asks_before_moving_a_file():
    """Match the shape of a choice prompt, not its exact wording."""
    cmd = CONTRACT_CMD.read_text()
    assert re.search(r"\[[^\]]*Move[^\]]*/[^\]]*Cancel[^\]]*\]", cmd), \
        "relocation must offer an explicit choice before moving a file"


def test_relocation_warns_about_references_it_cannot_fix():
    cmd = CONTRACT_CMD.read_text()
    assert "outside Archflow" in cmd
