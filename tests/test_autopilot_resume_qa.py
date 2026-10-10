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
    assert re.search(r"`run_branch` if it still exists", rule)
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
    """abort prints Step 4, whose Next: line (with parked stories) names resume — so resume must
    accept the parked stories of an aborted run, and Step 4 must say its Next: rule covers abort."""
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    rule = re.sub(r"\s+", " ", resume_rule())
    step4 = re.sub(r"\s+", " ", report_block())
    next_line = [l for l in report_block().splitlines() if l.startswith("Next:")][0]
    assert "print Step 4" in abort
    assert RESUME in next_line
    assert "`aborted`" in step4.split("Next:` line", 1)[1][:200], \
        "Step 4's Next: rule must say it has to work for an aborted run too"
    assert "`finished` or `aborted`" in rule, "resume must take an aborted run's parked stories"
    assert "Nothing to resume." in rule


# --------------------------------------------------------------------------
# Re-run after the fix pass (aed55f7)
# --------------------------------------------------------------------------

def test_abort_hands_its_parked_stories_to_resume_rule_2():
    """I-1, positively: the previous test passes once the refusal phrase is gone; this one checks
    that abort and rule 2 actually point at each other."""
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "follow-on run" in abort and "rule 2" in abort
    assert re.search(r"2\. \*\*[^*]*finished or aborted run", rule)
    # the aborted record itself is never reopened
    assert "never reopen it" in rule and "never change its `status`" in rule


def test_follow_on_with_no_answers_writes_nothing():
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"Nothing answered and nothing waived\*\* → (.*?)(?= - \*\*)", rule)
    assert m, "rule 2 must say what happens when nothing is answered or waived"
    assert "write no ledger" in m.group(1) and "change nothing" in m.group(1)


def test_parked_stories_of_another_release_are_named_not_edited():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert re.search(r"no longer the active one, name them", rule)
    assert "change nothing" in rule


def test_status_parked_advice_covers_an_interrupted_running_run():
    rule = re.sub(r"\s+", " ", resume_rule())
    status = re.sub(r"\s+", " ", status_parked_case())
    assert "they wait for the next `resume`" in rule  # the precedence resume documents
    assert re.search(r"interrupted|`running`|still running|unfinished run", status), status


# --------------------------------------------------------------------------
# Fix pass 2 (code review 7864959): I-6, I-7, I-8, I-10, I-11
# --------------------------------------------------------------------------

def _closing_write():
    """The paragraph of Step 4 that sets `status: finished`, through the end of Step 4."""
    step4 = re.sub(r"\s+", " ", report_block())
    i = step4.find("`status: finished`")
    assert i != -1, "Step 4 no longer closes the run with `status: finished`"
    return step4[i:]


def test_step4_closing_write_exempts_abort():
    """I-6: abort prints Step 4; Step 4's closing `status: finished` must not apply to it,
    or an aborted run ends up `finished`. Fails if the exemption is removed."""
    closing = _closing_write()
    assert re.search(r"\*\*`abort`\*\*[^*]*stays `aborted`", closing), closing
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    assert "print Step 4" in abort
    assert re.search(r"skip\w* its closing status write", abort)
    assert "stays `aborted`" in abort


def test_step4_closing_write_exempts_report():
    """I-6: report reprints Step 4 and must never close (or re-close) a run."""
    closing = _closing_write()
    assert re.search(r"\*\*`report`\*\*[^*]*read-only", closing, re.I), closing
    report = re.sub(r"\s+", " ", subcommand("report"))
    assert "Read-only" in report and "closing status write" in report


def test_resume_scan_reads_committed_state_on_other_branches():
    """I-7: the finished ledger and `parked` status live on the run branch; a user back on
    base_branch must still find them."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "current checkout first" in rule
    assert "git for-each-ref" in rule and "git show {branch}:" in rule
    assert "source branch" in rule
    assert "without checking anything out" in rule


def test_follow_on_checks_out_the_run_branch_before_writing():
    """I-7: writing the ledger and release file before checkout dirties the tree."""
    rule = re.sub(r"\s+", " ", resume_rule())
    i_checkout = rule.index("check out the run branch")
    assert i_checkout < rule.index("Write a new ledger")
    assert i_checkout < rule.index("clear each answered story's `parked` block")
    assert "before writing anything" in rule


def test_a_waiver_on_an_unanswered_story_is_recorded():
    """I-8: the waiver only matters for a story that stays parked, so it must not be discarded
    when nothing else was answered."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"Nothing answered, some waived\*\* → (.*?)(?= - \*\*)", rule)
    assert m, "rule 2 must handle waivers when nothing was answered"
    branch = m.group(1)
    assert "write no ledger" in branch
    assert "`parked.blocks_release: false`" in branch
    assert "stays `parked`" in branch
    # the authority envelope allows exactly this release-file write
    assert "`blocks_release` waiver" in AUTOPILOT.read_text().split("**MUST NOT")[0]


def test_resume_does_not_look_for_a_run_branch_on_a_preflight_ledger():
    """I-11: a --plan ledger has no run branch until Step 3 creates it."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"1\. \*\*Continue an unfinished run\.\*\*(.*?)2\. \*\*", rule)
    assert m
    rule1 = m.group(1)
    pre = rule1.index("`preflight`")
    run = rule1.index("**`running`** ledger")
    assert "no run branch yet" in rule1[pre:run]
    assert "Step 3" in rule1[pre:run]
    assert "verify the run branch" in rule1[run:], "the branch check belongs to `running` only"


@pytest.mark.parametrize("status", ["finished", "aborted"])
def test_schema_says_finished_and_aborted_parked_stories_can_be_picked_up(status):
    """I-10, in both mirrors."""
    for path in (SCHEMA, REPO / "plugin" / "skills" / "archflow" / "schemas" / "autopilot-schema.yaml"):
        desc = re.sub(r"\s+", " ", yaml.safe_load(path.read_text())["run"]["properties"]["status"]["description"])
        m = re.search(rf"{status} — (.*?)(?= \w+ +—|$)", desc)
        assert m, (path, status)
        assert "never" in m.group(1) and "follow-on run" in m.group(1), (path, m.group(1))


# --------------------------------------------------------------------------
# Re-run after fix pass 2 (6ad86a4): I-12, I-13, I-14 (fixed in fix pass 3)
# --------------------------------------------------------------------------

def test_terminal_ledger_writes_are_committed():
    """I-12: Step 4's closing write, abort's `aborted` write and --plan's `preflight` ledger are
    left uncommitted. resume HALTs on a dirty tree, and the cross-branch scan (I-7) reads the last
    COMMITTED ledger, which still says `running` - so a stashed `aborted` reads as resumable."""
    closing = _closing_write()
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    plan = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### 2c.", 1)[1].split("---", 1)[0])
    assert re.search(r"[Cc]ommit", closing.split("Two callers", 1)[0]), closing
    assert re.search(r"[Cc]ommit", abort.split("print Step 4", 1)[0]), abort
    assert re.search(r"--plan`.{0,200}[Cc]ommit", plan), plan


def test_branch_scan_does_not_stop_at_the_first_checkout_with_a_candidate():
    """I-13: 'If it holds no candidate, scan ... every local branch' lets a preflight ledger on
    the current branch hide a finished run's parked stories on its run branch, so the
    preflight-vs-parked question is never asked and the planned run starts (regresses I-3)."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "If it holds no candidate, scan" not in rule


def test_follow_on_stops_when_the_reread_drops_every_answer():
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"drop from the answers any story no longer `status: parked`\.(.{0,250})", rule)
    assert m
    assert re.search(r"[Nn]one (left|remain)|no answers? (left|remain)|stop", m.group(1)), m.group(1)


def test_terminal_ledger_commits_name_the_branch_they_land_on():
    """I-12: each terminal write is committed on the branch the scan will read it from, and with
    the ledger alone (never sweeping in anything else)."""
    closing = _closing_write().split("Two callers", 1)[0]
    abort = re.sub(r"\s+", " ", subcommand("abort")).split("print Step 4", 1)[0]
    plan = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### 2c.", 1)[1].split("---", 1)[0])
    assert "ledger alone on the run branch" in closing, closing
    assert "ledger alone on the branch it lives on" in abort and "run branch" in abort, abort
    assert re.search(r"--plan`.{0,120}ledger alone on the current branch", plan), plan


def test_branch_scan_dedups_one_run_across_branches():
    """I-13: one run seen on several branches is kept once, by a stated rule, before choosing."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "always, from the committed `.archflow/` of every local branch" in rule
    assert "Keep one copy per `run_id`" in rule and "most advanced `status`" in rule
    assert rule.index("Keep one copy per `run_id`") < rule.index("Choose between them")


def test_waiver_path_rereads_and_stops_when_nothing_is_still_parked():
    """I-14: the waiver path re-reads on the source branch and commits nothing if every waived
    story was resolved since."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"Nothing answered, some waived\*\* → (.*?)(?= - \*\*)", rule)
    assert m and "re-read the release file" in m.group(1) and "commit nothing" in m.group(1)


def test_envelope_must_not_rule_admits_the_resume_waiver():
    """QA wording note: MUST NOT must not literally forbid the waiver MAY allows."""
    body = AUTOPILOT.read_text()
    must_not = re.sub(r"\s+", " ", body.split("**MUST NOT", 1)[1].split("## Subcommands", 1)[0])
    assert "Touch any story outside its queue," not in must_not
    assert "waiver" in must_not


# --------------------------------------------------------------------------
# Re-run after fix pass 3 (96ea739): I-15 (strict xfail until fixed)
# --------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="I-15: a committed preflight ledger does not reach base_branch")
def test_planned_run_ledger_reaches_the_run_branch():
    """I-15: --plan now commits the preflight ledger on the CURRENT branch, but Step 3 cuts the run
    branch from `base_branch`. When the two differ (e.g. planned on main, base = release slug), the
    committed ledger is left behind on the planning branch; before 96ea739 the untracked file rode
    along on checkout. Rule 1's preflight path must say on which branch `running` is written and
    how the ledger reaches the run branch (or --plan must commit it on `base_branch`)."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"A \*\*`preflight`\*\* ledger is a planned run(.*?)A \*\*`running`\*\*", rule)
    assert m, "rule 1 lost its preflight bullet"
    assert re.search(r"source branch|planned on|base_branch`? (?:first|before)", m.group(1)), m.group(1)
