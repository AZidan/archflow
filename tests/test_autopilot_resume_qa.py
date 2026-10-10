"""QA additions for S5-02 (`/archflow:autopilot resume` after a run finishes).

tests/test_autopilot_resume.py pins the happy paths. These cover what it does not:

- the follow-on run inherits the envelope instead of re-interviewing;
- the follow-on ledger validates as `preflight` too (a follow-on started with --plan);
- the old two-step "answer it, then resume" wording is gone from every surface the user reads;
- the Step 4 `Next:` rule is consistent with what `resume` accepts for EVERY way Step 4 is
  printed — including `abort`, which prints Step 4 for a run that resume then refuses (I-1).
"""

import re
from pathlib import Path

import pytest
import yaml

from test_autopilot_resume import (  # noqa: F401  (reuse the fixtures of the story's own suite)
    AUTOPILOT, STATUS, SCHEMA, RESUME, DONE, PARKED,
    ledger, project, validate, resume_rule, report_block, status_parked_case,
)

REPO = Path(__file__).resolve().parents[1]


def subcommand(name):
    body = AUTOPILOT.read_text()
    m = re.search(rf"^\*\*`{name}`\*\*.*?(?=^\*\*`|^---)", body, re.S | re.M)
    assert m, f"autopilot.md lost its `{name}` subcommand"
    return m.group(0)


# --------------------------------------------------------------------------
# The follow-on run carries the finished run's policy; it is not a new interview
# --------------------------------------------------------------------------

@pytest.mark.parametrize("carried", ["envelope", "stop conditions", "`parked_policy`", "`decisions[]`"])
def test_follow_on_run_carries_the_finished_runs_policy(carried):
    rule = re.sub(r"\s+", " ", resume_rule())
    assert carried in rule
    assert "Do not re-run the interview" in rule


def test_follow_on_run_reuses_wip_branches_and_the_run_branch():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "WIP task branch" in rule
    assert "`run_branch` if it still exists" in rule
    assert "`base_branch`" in rule, "a merged-and-deleted run branch must have a defined fallback"


def test_follow_on_run_id_follows_step_2c():
    """A follow-on run is a run: same id scheme, same ledger, same schema."""
    assert "per Step 2c" in resume_rule()


def test_schema_resumes_example_satisfies_its_own_pattern():
    field = yaml.safe_load(SCHEMA.read_text())["run"]["properties"]["resumes"]
    assert re.fullmatch(field["pattern"], field["example"])


def test_follow_on_run_in_preflight_validates(tmp_path):
    """`resume` writes the follow-on ledger per Step 2c, which may leave it `preflight`."""
    parent = ledger("2026-01-01-1", "finished", [DONE, PARKED], finished_at="2026-01-01T02:00:00Z")
    queued = {k: v for k, v in PARKED.items() if k != "park"}
    child = ledger("2026-01-02-1", "preflight", [dict(queued, order=1, state="pending")],
                   resumes="2026-01-01-1")
    code, data = validate(project(tmp_path, [parent, child]))
    assert code == 0, data["violations"]


# --------------------------------------------------------------------------
# No surface still tells the user to answer outside resume, then resume
# --------------------------------------------------------------------------

def test_status_no_longer_asks_the_user_to_answer_before_resume():
    case = status_parked_case()
    assert "ask the user to answer it, then" not in case


def test_readme_resume_line_matches_the_new_behaviour():
    readme = (REPO / "README.md").read_text()
    line = [l for l in readme.splitlines() if l.startswith(RESUME)]
    assert line and "finished" in line[0]


# --------------------------------------------------------------------------
# Every Step 4 report's Next: line must name a command that works for that run
# --------------------------------------------------------------------------

def test_next_line_without_parked_stories_does_not_name_resume():
    step4 = re.sub(r"\s+", " ", report_block())
    m = re.search(r"With nothing parked, write `(Next:[^`]*)`", step4)
    assert m, "Step 4 must say what Next: is when nothing is parked"
    assert RESUME not in m.group(1)


def test_abort_report_next_line_names_a_command_that_works_for_an_aborted_run():
    abort = subcommand("abort")
    resume = re.sub(r"\s+", " ", resume_rule())
    step4 = re.sub(r"\s+", " ", report_block())
    aborted_refused = "`aborted` run is never resumed" in resume
    abort_prints_step4 = "print Step 4" in abort
    parked_next_is_resume = "With parked stories it is the line above" in step4
    aborted_carve_out = re.search(r"abort", step4, re.I) is not None
    # Either resume accepts an aborted run's parked stories, or Step 4 carves abort out of the
    # "resume" Next: line. Today neither holds.
    assert not (aborted_refused and abort_prints_step4 and parked_next_is_resume
                and not aborted_carve_out)


# --------------------------------------------------------------------------
# Re-run after the fix pass (aed55f7)
# --------------------------------------------------------------------------

def test_abort_hands_its_parked_stories_to_resume_rule_2():
    """I-1, positively: the previous test passes once the refusal phrase is gone; this one checks
    that abort and rule 2 actually point at each other."""
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "`resume` picks them up in a follow-on run (rule 2)" in abort
    assert "Pick up parked stories from a finished or aborted run" in rule
    # the aborted record itself is never reopened
    assert "never reopen it, never change its `status`, never edit it" in rule


def test_follow_on_with_no_answers_writes_nothing():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "If nothing was answered, stop: write no ledger and change nothing" in rule


def test_parked_stories_of_another_release_are_named_not_edited():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "belong to a release that is no longer the active one, name them" in rule
    assert "change nothing" in rule


@pytest.mark.xfail(strict=True, reason=(
    "S5-02 I-5: with an interrupted `running` ledger present, resume continues that run and "
    "parked stories from another run 'wait for the next resume', but status case 3 still says "
    "resume asks the parked question, naming only the --plan exception. Remove this xfail once "
    "status case 3 (or resume) covers the running-ledger case."))
def test_status_parked_advice_covers_an_interrupted_running_run():
    rule = re.sub(r"\s+", " ", resume_rule())
    status = re.sub(r"\s+", " ", status_parked_case())
    assert "they wait for the next `resume`" in rule  # the precedence resume documents
    assert re.search(r"interrupted|`running`|still running|unfinished run", status), status
