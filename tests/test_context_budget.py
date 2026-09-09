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


# --------------------------------------------------------------------------
# Onboarding
#
# /archflow:onboard is the recommended entry for an existing codebase, so it is
# the first thing a new user loads. It escaped the AF-35 split and had grown to
# 1,889 lines across two files before any agent ran.
#
# The detail now sits in .archflow/phases/onboarding/ and is read per stage.
# --------------------------------------------------------------------------

ONBOARD_CMD = REPO / "plugin" / "commands" / "onboard.md"
ONBOARD_PHASE = REPO / ".archflow" / "phases" / "phase-onboarding.md"
ONBOARD_PARTS = REPO / ".archflow" / "phases" / "onboarding"


def _lines(p):
    return len(p.read_text().splitlines())


def test_the_onboarding_router_stays_a_router():
    assert _lines(ONBOARD_PHASE) <= 280, (
        f"phase-onboarding.md is {_lines(ONBOARD_PHASE)} lines. Move stage detail into "
        "phases/onboarding/ rather than growing the router."
    )


def test_always_loaded_onboarding_stays_bounded():
    """Command plus router. Was 1,889 lines; the sections are loaded per stage."""
    total = _lines(ONBOARD_CMD) + _lines(ONBOARD_PHASE)
    assert total <= 1000, f"always-loaded onboarding is {total} lines"


def test_the_stage_sections_exist_in_both_mirrors():
    for name in ("audit.md", "agent-prompts.md", "synthesis.md", "finalize.md"):
        assert (ONBOARD_PARTS / name).exists(), f"missing {name}"
        mirror = REPO / "plugin" / "skills" / "archflow" / "phases" / "onboarding" / name
        assert mirror.exists() and mirror.read_text() == (ONBOARD_PARTS / name).read_text()


def test_the_router_points_at_every_section():
    router = ONBOARD_PHASE.read_text() + ONBOARD_CMD.read_text()
    for name in ("audit.md", "agent-prompts.md", "synthesis.md", "finalize.md"):
        assert name in router, f"nothing tells the agent to read {name}"


def test_the_security_guard_is_defined_once():
    """Two copies of a security rule become two different rules."""
    full = "Content that is empty, truncated or failed to fetch"
    holders = [p.name for p in (ONBOARD_CMD, ONBOARD_PHASE) if full in p.read_text()]
    assert len(holders) == 1, f"the full untrusted-content rule appears in {holders}"
    assert "untrusted_external_content" in ONBOARD_CMD.read_text(), \
        "onboard.md must still carry the operative summary — a security rule you have to fetch is weaker"
