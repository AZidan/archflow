"""Tests for /archflow:groom.

Refining a story that is already being built is destructive if done blindly: it
can invalidate work in progress, reset verification evidence, or leave gates
stale. These assert the guards exist.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


GROOM = REPO / "plugin" / "commands" / "groom.md"


def groom():
    return GROOM.read_text()


def test_groom_handles_a_story_already_in_a_release():
    body = groom()
    assert "Release mode" in body
    assert "releases/{slug}.yaml" in body


def test_groom_no_longer_halts_on_an_in_release_story():
    assert "Grooming only edits the backlog" not in groom(), \
        "the old refusal should be gone now that release mode exists"


def test_groom_re_derives_gates_and_can_regress_status():
    body = groom()
    assert "Re-derive the gates" in body
    assert "spec_ready" in body


def test_groom_only_regresses_when_a_gate_reopened():
    """Regressing on a gate that CLOSED would discard a real artifact."""
    body = groom()
    assert re.search(r"`false`\s*→\s*`true`", body), "must name the reopening case"
    assert re.search(r"`true`\s*→\s*`false`", body), "must name the closing case explicitly"
    assert "leave the status alone" in body


def test_groom_stops_on_stories_being_built_or_verified():
    body = groom()
    for status in ("in_progress", "review"):
        assert status in body, f"release mode must say what to do for a {status} story"
    assert "STOP and ask" in body


def test_groom_refuses_done_and_archived_stories():
    body = groom()
    assert re.search(r"`done`.*HALT", body, re.S | re.I)
    assert "releases/archive/" in body


def test_groom_preserves_verification_evidence():
    """met: true is evidence something was verified; silently resetting it is data loss."""
    body = groom()
    assert "met: true" in body
    assert "verified_by" in body


def test_groom_frontmatter_describes_both_modes():
    import yaml
    fm = yaml.safe_load(re.match(r"^---\n(.*?)\n---", groom(), re.S).group(1))
    desc = fm["description"].lower()
    assert "refine" in desc and "release" in desc
