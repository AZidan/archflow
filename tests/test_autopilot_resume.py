"""`/archflow:autopilot resume` on a run that has already finished (S5-02).

A run that empties its queue is set `finished`, yet its report told the user to
answer the parked questions and then run `resume`, which only read `preflight` /
`running` ledgers. Parked stories left by a finished run had no way back.

The fix: `resume` falls back to the newest FINISHED or ABORTED run (of the active
release) that still has parked stories and starts a follow-on run over them
(`resumes: <run-id>`), leaving that ledger untouched. An aborted run's queue is never
continued, and a run with nothing still parked is never restarted.

The behaviour lives in markdown, so the tests pin the documented contract — the
report, the resume rule and /archflow:status must agree — and check that the
code that keys on ledger status (validator, git guard) handles both ledgers of a
follow-on run correctly.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
AUTOPILOT = REPO / "plugin" / "commands" / "autopilot.md"
STATUS = REPO / "plugin" / "commands" / "status.md"
SCHEMA = REPO / ".archflow" / "schemas" / "autopilot-schema.yaml"
VALIDATOR = REPO / "plugin" / "scripts" / "validate_archflow.py"
GUARD = REPO / "plugin" / "hooks" / "guard-git.mjs"

RESUME = "/archflow:autopilot resume"


def section(text, start, end):
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j]


def resume_rule():
    body = AUTOPILOT.read_text()
    return section(body, "**`resume`**", "**`report`**")


def report_block():
    body = AUTOPILOT.read_text()
    step4 = section(body, "## Step 4", "## Hard constraints")
    return step4


def status_parked_case():
    body = STATUS.read_text()
    m = re.search(r"^3\. a `parked` story.*?(?=^4\. )", body, re.S | re.M)
    assert m, "status.md lost its parked-story case"
    return m.group(0)


# --------------------------------------------------------------------------
# One command, named the same way everywhere
# --------------------------------------------------------------------------

def test_report_next_line_names_resume_for_parked_stories():
    next_lines = [l for l in report_block().splitlines() if l.startswith("Next:")]
    assert next_lines, "the Step 4 report has no Next: line"
    assert RESUME in next_lines[0]


def test_report_next_line_no_longer_promises_a_dead_end():
    """The old line told the user to answer first, then resume — which did nothing after `finished`."""
    assert "Next: answer the parked questions, then" not in AUTOPILOT.read_text()


def test_report_says_next_line_must_work_after_finished():
    step4 = report_block()
    assert "finished" in step4
    assert "nothing parked" in step4.lower()


def test_status_parked_advice_names_the_same_command():
    case = status_parked_case()
    assert RESUME in case
    assert "finished" in case, "status must say resume works after the run has finished"


def test_report_and_status_agree():
    """Both surfaces point the user at the exact same command form."""
    next_line = [l for l in report_block().splitlines() if l.startswith("Next:")][0]
    assert RESUME in next_line and RESUME in status_parked_case()


# --------------------------------------------------------------------------
# The selection rule: finished+parked yes; finished-without-parked and aborted no
# --------------------------------------------------------------------------

def test_resume_still_continues_an_unfinished_run_first():
    rule = resume_rule()
    assert "`preflight` or `running`" in rule
    assert rule.index("`preflight` or `running`") < rule.index("`finished`")


def test_resume_picks_up_a_finished_run_with_parked_stories():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "`finished`" in rule
    assert "`parked`" in rule
    assert "still `status: parked`" in rule
    assert "follow-on run" in rule


def test_a_finished_ledger_is_never_reopened():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "never reopen it" in rule
    assert "resumes:" in rule


def test_a_finished_run_without_parked_stories_is_not_resurrected():
    rule = resume_rule()
    assert "Nothing to resume." in rule
    assert "no parked stories" in rule


def test_an_aborted_run_stays_aborted_but_its_parked_stories_come_back():
    """I-1: abort prints the Step 4 report, whose Next: line names resume.

    The aborted ledger is a record and keeps its status; only its still-parked stories return.
    """
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "`finished` or `aborted`" in rule
    assert "stays `aborted`" in rule
    assert "never change its `status`" in rule
    assert re.search(r"aborted run's queue is (never|not) continued", rule)


def test_resume_only_considers_the_active_release():
    """I-2: a parked story in a shipped/archived release is never edited by resume."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert re.search(r"`release`[^.]*`active_release`", rule)
    assert re.search(r"`status: parked` in `\.archflow/releases/\{active_release\}\.yaml`", rule)
    assert "another release file" in rule


def test_resume_checks_prerequisites_before_writing_state():
    """I-2: resume writes a ledger and a release file, so the preflight checks come first."""
    rule = re.sub(r"\s+", " ", resume_rule())
    i = rule.index("Prerequisites")
    assert i < rule.index("Write a new ledger")
    assert re.search(r"HALT on any failure before checking out", rule)


def test_a_planned_run_never_silently_outranks_parked_stories():
    """I-3: a never-started --plan ledger and parked stories both present -> ask, never default."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert re.search(r"`preflight` ledger and parked stories both → ask", rule)
    assert "Never default" in rule
    assert "one to pick up" in re.sub(r"\s+", " ", status_parked_case())


def test_answered_story_leaves_parked_via_in_progress():
    """release-schema: parked clears back to in_progress once the question is answered."""
    rule = resume_rule()
    assert "`in_progress`" in rule
    assert "unanswered stays `parked`" in rule


def test_usage_line_matches_the_rule():
    usage = [l for l in AUTOPILOT.read_text().splitlines()
             if l.startswith(RESUME + " ")]
    assert usage and "finished" in usage[0]


# --------------------------------------------------------------------------
# Schema: the follow-on link
# --------------------------------------------------------------------------

def test_schema_documents_resumes():
    run = yaml.safe_load(SCHEMA.read_text())["run"]
    field = run["properties"]["resumes"]
    assert field["required"] is False
    assert field["pattern"] == run["properties"]["run_id"]["pattern"]
    assert "resumes" not in run["required"]


# --------------------------------------------------------------------------
# Code that keys on ledger status
# --------------------------------------------------------------------------

ENVELOPE = {"merge_to_run_branch": True, "merge_to_main": False,
            "open_pr": False, "run_qa": True, "run_acceptance": True}


def ledger(run_id, status, queue, **extra):
    d = {"run_id": run_id, "status": status, "started_at": "2026-01-01T00:00:00Z",
         "base_branch": "feature-x", "run_branch": "feature-x-autopilot", "release": "r1",
         "envelope": ENVELOPE, "queue": queue}
    d.update(extra)
    return d


PARKED = {"story_id": "S1-02", "title": "t", "order": 2, "state": "parked",
          "branch": "f/s1-02",
          "park": {"question": "q?", "context": "c", "options": ["a", "b"],
                   "at": "2026-01-01T01:00:00Z"}}
DONE = {"story_id": "S1-01", "title": "t", "order": 1, "state": "done"}


def project(tmp_path, ledgers):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: refs/heads/feature-x\n")
    af = tmp_path / ".archflow"
    (af / "autopilot").mkdir(parents=True)
    (af / "schemas").mkdir()
    for s in (REPO / ".archflow" / "schemas").glob("*.yaml"):
        (af / "schemas" / s.name).write_text(s.read_text())
    for d in ledgers:
        (af / "autopilot" / f"{d['run_id']}.yaml").write_text(yaml.safe_dump(d, sort_keys=False))
    return tmp_path


def validate(proj):
    proc = subprocess.run([sys.executable, str(VALIDATOR), str(proj), "--json"],
                          capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def guard(cmd, proj):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(proj)})
    return subprocess.run(["node", str(GUARD)], input=payload, capture_output=True, text=True).returncode


def test_follow_on_run_validates_and_finished_parent_stays_a_record(tmp_path):
    parent = ledger("2026-01-01-1", "finished", [DONE, PARKED],
                    finished_at="2026-01-01T02:00:00Z")
    queued = {k: v for k, v in PARKED.items() if k != "park"}
    child = ledger("2026-01-02-1", "running", [dict(queued, order=1, state="pending")],
                   resumes="2026-01-01-1")
    code, data = validate(project(tmp_path, [parent, child]))
    assert code == 0, data["violations"]
    assert any("2026-01-02-1" in f for f in data["checked"])
    assert any("historical record" in s["reason"] for s in data["skipped"])


def test_a_malformed_resumes_link_is_caught(tmp_path):
    child = ledger("2026-01-02-1", "running", [DONE], resumes="last night")
    code, data = validate(project(tmp_path, [child]))
    assert code == 1
    assert any("resumes" in v["field"] for v in data["violations"])


def test_finished_run_with_parked_stories_does_not_arm_the_guard(tmp_path):
    """Before resume starts the follow-on run, nothing is running — the guard stays out."""
    proj = project(tmp_path, [ledger("2026-01-01-1", "finished", [DONE, PARKED])])
    assert guard("git push origin main", proj) == 0


def test_follow_on_run_arms_the_guard(tmp_path):
    """The follow-on run is a real run and gets the same protection."""
    proj = project(tmp_path, [
        ledger("2026-01-01-1", "finished", [DONE, PARKED]),
        ledger("2026-01-02-1", "running", [DONE], resumes="2026-01-01-1"),
    ])
    assert guard("git push origin main", proj) == 2


def test_aborted_run_with_parked_stories_does_not_arm_the_guard(tmp_path):
    proj = project(tmp_path, [ledger("2026-01-01-1", "aborted", [DONE, PARKED])])
    assert guard("git push origin main", proj) == 0


def test_follow_on_from_an_aborted_run_validates_and_the_parent_stays_aborted(tmp_path):
    parent = ledger("2026-01-01-1", "aborted", [DONE, PARKED], finished_at="2026-01-01T02:00:00Z")
    queued = {k: v for k, v in PARKED.items() if k != "park"}
    child = ledger("2026-01-02-1", "running", [dict(queued, order=1, state="pending")],
                   resumes="2026-01-01-1")
    code, data = validate(project(tmp_path, [parent, child]))
    assert code == 0, data["violations"]
    assert any("2026-01-02-1" in f for f in data["checked"])
    assert not any("2026-01-01-1" in f for f in data["checked"]), "aborted ledger is a record"


def test_follow_on_from_an_aborted_run_arms_the_guard(tmp_path):
    proj = project(tmp_path, [
        ledger("2026-01-01-1", "aborted", [DONE, PARKED]),
        ledger("2026-01-02-1", "running", [DONE], resumes="2026-01-01-1"),
    ])
    assert guard("git push origin main", proj) == 2
