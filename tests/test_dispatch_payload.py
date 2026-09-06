"""Guards on what a Phase 3 dispatch carries.

A subagent inherits nothing from the orchestrator's session, so anything it needs
must be in its own prompt. That payload used to be re-assembled by hand in four
per-project-type templates, and it failed exactly as you would expect: the
design-system rule was stated in the rules and absent from the templates, which
is the bug AF-13 fixed.

These tests assert the payload is defined once and stays complete.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHASE3 = REPO / ".archflow" / "phases" / "phase-3-implementation.md"


def text():
    return PHASE3.read_text()


def test_the_payload_is_defined():
    assert "## 📦 The dispatch payload" in text()


def test_payload_names_every_required_element():
    body = text()
    for element in (
        "description",            # intent
        "acceptance_criteria",    # definition of done
        "subtasks",
        "design-system.yaml",     # the design system line
        "stack:",                 # the stack line
        "api_contract_path",      # the contract
        "contract_endpoints",     # this story's operations
        "design_artifact",
    ):
        assert element in body, f"the dispatch payload does not mention {element}"


def test_payload_states_the_scope_and_stop_rules():
    body = text()
    assert "this story only" in body.lower()
    assert re.search(r"do not mark .*done", body, re.I)
    assert re.search(r"do not merge", body, re.I)


def test_the_design_system_line_is_not_restated_per_type():
    """One definition. Two copies of a payload become two different payloads."""
    occurrences = text().count("Design system: read .archflow/design-system.yaml")
    assert occurrences <= 2, (
        f"the design-system line appears {occurrences} times in phase-3. "
        "Define it once in the payload; per-type sections say only which agent and where output goes."
    )


def test_dispatch_reads_from_the_release_file_not_from_context():
    body = text()
    assert "releases/{active_release}.yaml" in body
    assert re.search(r"never from (memory|what happens to be)", body, re.I), (
        "the payload must say it is assembled from the release file, not from session context"
    )


def test_per_type_section_does_not_re_specify_the_payload():
    """It should carry only the agent and the output location."""
    body = text()
    start = body.index("## 🎯 Per type")
    section = body[start:start + 1400]
    assert "Everything else comes from the payload above" in section


def test_phase3_mirrors_match():
    other = REPO / "plugin" / "skills" / "archflow" / "phases" / "phase-3-implementation.md"
    assert other.read_text() == PHASE3.read_text()
