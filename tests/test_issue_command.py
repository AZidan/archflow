"""Guards on /archflow:issue.

The command is a front door into `issues[]`, and a front door is exactly how the
release file could turn into the bug tracker ADR 004 was written to prevent. So most
of these test the ROUTING and the REFUSALS, not the happy path — what the command
declines to write matters more than what it writes.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CMD = REPO / "plugin" / "commands" / "issue.md"


def body():
    """The command text with whitespace collapsed.

    Every assertion below is on prose, and prose gets rewrapped. Matching the raw
    file makes a test fail when a sentence moves across a line break, which is not
    a defect in anything.
    """
    return re.sub(r"\s+", " ", CMD.read_text())


def raw():
    return CMD.read_text()


def frontmatter():
    return yaml.safe_load(raw().split("---", 2)[1])


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------

def test_frontmatter_parses_and_describes_the_command():
    fm = frontmatter()
    assert fm["description"]
    assert "argument-hint" in fm


def test_it_dispatches_on_the_story_id_pattern_from_the_schema():
    """If this drifts from the schema, a story id falls through to the wrong mode."""
    schema = yaml.safe_load((REPO / ".archflow" / "schemas" / "release-schema.yaml").read_text())
    assert schema["story"]["properties"]["id"]["pattern"] in body()


def test_it_states_which_mode_it_entered():
    assert re.search(r"[Ss]tate the mode", body())


def test_it_refuses_to_guess_on_an_unrecognised_argument():
    assert "Do not guess" in body()


def test_it_has_all_four_modes():
    text = body()
    for mode in ("List all", "List one story", "**Add**", "**Defer**"):
        assert mode in text, f"the mode table is missing {mode}"


# --------------------------------------------------------------------------
# Routing — the part that keeps this from becoming a bug tracker
# --------------------------------------------------------------------------

def test_routing_happens_before_writing():
    text = body()
    assert "Routing is this command's first job" in text
    assert text.index("### 2a. Route it first") < text.index("### 2b. Write it")


def test_it_sends_non_defects_to_the_feature_command():
    """New scope, shipped bugs and ideas belong in the backlog, not a release file."""
    text = body()
    assert "/archflow:feature" in text
    assert "bug tracker" in text


def test_only_a_story_in_the_build_loop_may_take_an_issue():
    text = body()
    for status in ("in_progress", "review", "parked"):
        assert status in text
    assert "has not been built yet" in text, \
        "a story that was never built cannot have a defect; that is scope"


def test_a_story_outside_the_active_release_is_refused():
    text = body()
    assert "not in the active release" in text
    assert "Do not pull it in" in text


def test_no_active_release_is_a_stop_not_a_guess():
    assert "`active_release` is null" in body()


# --------------------------------------------------------------------------
# The `done` story — the case that would write an invalid release file
# --------------------------------------------------------------------------

def test_a_done_story_is_never_reopened_silently():
    text = body()
    assert "Never silently reopen a story" in text
    assert "would fail `validate_archflow.py`" in text


def test_it_offers_both_readings_of_a_defect_on_a_done_story():
    text = body()
    start = text.index("### 2c. When the story is already `done`")
    section = text[start:text.index("## Step 3", start)]
    assert "regression" in section and "status: review" in section
    assert "/archflow:feature" in section, "new scope on a closed story has nowhere to go"


# --------------------------------------------------------------------------
# Defer — the verb reserved for a human
# --------------------------------------------------------------------------

def test_defer_is_documented_as_human_only():
    text = body()
    assert "reserved for a human" in text
    assert "stopped being a check" in text


def test_defer_refuses_a_blocking_issue():
    text = body()
    start = text.index("## Step 3 — Defer")
    section = text[start:]
    assert "Refuse on `blocking`" in section
    assert "separate, deliberate decision" in section, \
        "offering to downgrade in the same breath makes the refusal meaningless"


def test_defer_writes_the_backlog_stub_before_the_pointer():
    """A deferred_to pointing at nothing fails validation and is unrecoverable."""
    text = body()
    start = text.index("## Step 3 — Defer")
    section = text[start:]
    assert "the stub before the pointer" in section
    assert section.index("backlog stub FIRST") < section.index("deferred_to")


def test_the_deferred_issue_stays_as_a_tombstone():
    assert "tombstone" in body()


# --------------------------------------------------------------------------
# What it must never do
# --------------------------------------------------------------------------

def test_it_never_marks_an_issue_fixed():
    assert "It never marks an issue `fixed`" in body()


def test_it_never_marks_a_story_done():
    assert "It never marks a story `done`" in body()


def test_it_stamps_findings_as_human():
    assert "found_by: human" in body()


def test_a_human_finding_carries_no_report_pointer():
    """`report` points at a reviewing agent's report; there is none behind a human's."""
    assert "Do not write a `report` path" in body()


def test_severity_is_asked_not_defaulted():
    text = body()
    assert "Severity is a real question, not a default" in text
    assert "blocking" in text and "minor" in text
