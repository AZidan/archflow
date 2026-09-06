"""Guards on what gets injected into every session.

`.archflow/instructions.md` is `cat`-ed by a SessionStart hook on every startup,
resume and compact. Every line in it is paid for repeatedly and forever, by every
user, in every session. That makes it the one file in the repo where size is a
correctness property rather than a matter of taste.

The split into a small core plus an on-demand reference only holds if something
stops the core growing back.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / ".archflow" / "instructions.md"
REFERENCE = REPO / ".archflow" / "reference.md"

# Rough but stable: characters / 4. Good enough to catch drift, and it does not
# pull in a tokenizer dependency for a guard rail.
def tokens(path):
    return len(path.read_text()) // 4


def test_core_stays_small():
    """It was 5,739 tokens before the split. The budget is what keeps it down."""
    assert tokens(CORE) < 1600, (
        f"instructions.md is ~{tokens(CORE)} tokens and is injected every session. "
        "Move detail to reference.md rather than growing the core."
    )


def test_core_is_shorter_than_the_reference():
    """If the core outgrows the reference, the split has stopped meaning anything."""
    assert tokens(CORE) < tokens(REFERENCE)


def test_core_points_at_the_reference():
    assert "reference.md" in CORE.read_text()


def test_reference_exists_in_both_mirrors():
    assert REFERENCE.exists()
    assert (REPO / "plugin" / "skills" / "archflow" / "reference.md").exists()


def test_nothing_was_lost_in_the_split():
    """Every concept the framework depends on must still be findable."""
    both = CORE.read_text() + "\n" + REFERENCE.read_text()
    required = [
        # state
        "current-phase.yaml", "roadmap.yaml", "backlog.yaml", "history.yaml",
        "releases/archive", "current-feature.yaml", "design-system.yaml",
        "project-context.md", "api_contract_path", "plugin_version",
        # pipeline
        "spec_ready", "design_ready", "contract_ready", "in_progress", "parked",
        "needs_design", "needs_contract",
        # modes and types
        "quick", "full", "fullstack", "frontend_only", "backend_only", "mobile",
        # the rules that must never quietly vanish
        "SACRED", "Anti-patterns", "Component vocabulary", "untrusted_external_content",
        "guard-git", "check-state", "stack:",
    ]
    missing = [r for r in required if r not in both]
    assert not missing, f"the split lost: {missing}"


def test_every_agent_and_command_is_documented():
    both = CORE.read_text() + "\n" + REFERENCE.read_text()
    for agent in sorted(p.stem for p in (REPO / "plugin" / "agents").glob("*.md")):
        assert agent in both, f"agent {agent} appears in neither the core nor the reference"
    for cmd in sorted(p.stem for p in (REPO / "plugin" / "commands").glob("*.md")):
        assert f"/archflow:{cmd}" in both, f"command /archflow:{cmd} is undocumented"


def test_core_carries_the_rules_that_bind_every_action():
    """These cannot wait for someone to read the reference."""
    core = CORE.read_text()
    for phrase in ("approval", "main", "design-system.yaml", "stack:", "api-contract.md"):
        assert phrase in core, f"the core must state the rule involving {phrase!r}"


def test_phase_files_can_reach_the_reference():
    for phase in sorted((REPO / ".archflow" / "phases").glob("*.md")):
        assert "reference.md" in phase.read_text(), f"{phase.name} has no route to the detail"


def test_no_agent_prescribing_language_leaked_into_the_docs():
    """AF-32 applies to the framework files too, not only the agents."""
    both = CORE.read_text() + "\n" + REFERENCE.read_text()
    banned = re.compile(r"\b(NestJS|PostgreSQL|MySQL|Tailwind|SwiftUI|Jetpack Compose)\b", re.I)
    hits = banned.findall(both)
    assert not hits, f"framework docs still name a stack: {sorted(set(hits))}"
