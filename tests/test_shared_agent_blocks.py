"""Blocks that are deliberately duplicated across agent files must stay identical.

An agent file IS that agent's prompt, and a subagent inherits nothing. So a rule the
agent must follow is inlined, not referenced — a referenced rules file is a Read the
agent can skip, and the rules that get skipped under pressure are the ones that matter
(a reviewer deciding whether to quietly close its own finding).

The cost of that choice is copies, and copies drift. That is what killed the root
agents/ tree. These tests are the price of keeping the copies: the design-system gate
sat in three agent files unguarded until now, and the issues protocol added a fourth
block on the same terms.

Only project-specific DATA is referenced (design-system.yaml, the stack, the contract).
Rules are inlined and pinned here.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENTS = REPO / "plugin" / "agents"


def block(agent: str, heading: str, last_line: str) -> str:
    """The shared block, from `heading` through `last_line` inclusive.

    Bounded by an explicit sentinel rather than "the next ## heading": two of these
    agents continue with **bold** pseudo-headings, so a heading-delimited slice
    swallows the section after the block and reports drift that is not there.
    """
    body = (AGENTS / f"{agent}.md").read_text()
    start = body.index(heading)
    end = body.index(last_line, start) + len(last_line)
    return body[start:end]


# --------------------------------------------------------------------------
# The design-system review gate
# --------------------------------------------------------------------------

DESIGN_GATE = "## 🎨 Design System Compliance (a MANDATORY review gate)"
DESIGN_AGENTS = ("qa-engineer", "code-reviewer", "a11y-expert")
DESIGN_END = "finding — the project has no design system set and every screen is an independent guess."


def test_every_reviewer_carries_the_design_system_gate():
    for agent in DESIGN_AGENTS:
        assert DESIGN_GATE in (AGENTS / f"{agent}.md").read_text(), \
            f"{agent} reviews UI code without the design-system gate"


def test_the_design_system_gate_is_identical_everywhere():
    blocks = {a: block(a, DESIGN_GATE, DESIGN_END) for a in DESIGN_AGENTS}
    base = blocks["qa-engineer"]
    differing = [a for a, b in blocks.items() if b != base]
    assert not differing, (
        f"the design-system gate has drifted in: {differing}. "
        "It is duplicated on purpose; keep the copies byte-identical."
    )


def test_the_gate_references_the_data_rather_than_inlining_it():
    """The design system itself is per-project, so it is READ, never copied in."""
    body = block("qa-engineer", DESIGN_GATE, DESIGN_END)
    assert ".archflow/design-system.yaml" in body
    assert ".archflow/design-systems/{design_system}.md" in body


# --------------------------------------------------------------------------
# The issues protocol (ADR 004)
# --------------------------------------------------------------------------

ISSUES = "## 🐞 Record findings as issues, not as a message"
ISSUE_AGENTS = ("qa-engineer", "pm-reviewer", "code-reviewer", "a11y-expert")
ISSUES_END = "Do not renumber or edit issues you did not write."


def normalised(agent: str) -> str:
    """The block with its two per-agent substitutions folded out."""
    body = block(agent, ISSUES, ISSUES_END)
    body = body.replace(f"found_by: {agent}", "found_by: {AGENT}")
    return re.sub(r'report: "[^"]+"', 'report: "{REPORT}"', body)


def test_the_issues_protocol_is_identical_everywhere():
    blocks = {a: normalised(a) for a in ISSUE_AGENTS}
    base = blocks["qa-engineer"]
    differing = [a for a, b in blocks.items() if b != base]
    assert not differing, (
        f"the issues protocol has drifted in: {differing}. "
        "Only found_by and the report path may differ between agents."
    )


def test_only_two_things_vary_between_the_copies():
    """If a third substitution appears, this block wants to become a real template."""
    for agent in ISSUE_AGENTS:
        body = block(agent, ISSUES, ISSUES_END)
        assert f"found_by: {agent}" in body, f"{agent} does not stamp its own findings"
        assert re.search(r'report: "docs/', body), f"{agent} names no report to point at"


def test_the_rule_that_stops_a_reviewer_marking_its_own_work_done():
    """The line most likely to be skipped if it were behind a Read instead of inline."""
    for agent in ISSUE_AGENTS:
        body = block(agent, ISSUES, ISSUES_END)
        assert "You do not close issues, and you do not defer them." in body
        assert "stopped being a check" in body


def test_the_protocol_is_inlined_not_referenced():
    """A pointer to a rules file is a Read an agent can skip. These rules may not be."""
    for agent in ISSUE_AGENTS:
        body = block(agent, ISSUES, ISSUES_END)
        assert "severity: blocking" in body, \
            f"{agent} only points at the issue rules instead of carrying them"
