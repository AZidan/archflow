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


# --------------------------------------------------------------------------
# Fix pass 5: I-20 (no stale `preflight` copy on base_branch, and the planned-run guard),
# I-21 (a remote-only base_branch counts as existing), I-22 (no undefined conflict rule)
# --------------------------------------------------------------------------

import shutil

import pytest


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True)


def _repo(path, branch="main"):
    if not shutil.which("git"):
        pytest.skip("git not on PATH")
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", branch)
    _git(path, "config", "user.email", "qa@example.com")
    _git(path, "config", "user.name", "qa")
    return path


def _commit(repo, msg, files):
    for rel, data in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data if isinstance(data, str) else yaml.safe_dump(data, sort_keys=False))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", msg)


def _ledgers_on(repo, branch):
    return _git(repo, "ls-tree", "--name-only", branch, ".archflow/autopilot/").stdout.split()


def plan_section():
    return _flat(AUTOPILOT.read_text().split("### 2c.", 1)[1].split("### Where", 1)[0])


def preflight_bullet():
    rule = _flat(resume_rule())
    m = re.search(r"A \*\*`preflight`\*\* ledger is a planned run(.*?)A \*\*`running`\*\*", rule)
    assert m, "rule 1 lost its preflight bullet"
    return m.group(1)


def test_a_run_that_starts_now_cuts_its_run_branch_before_writing_the_ledger():
    plan = plan_section()
    assert plan.index("Check out `base_branch`") < plan.index("cuts its run branch") \
        < plan.index("create `.archflow/autopilot/{run-id}.yaml`")
    assert "Commit the ledger alone on the run branch" in plan
    assert "No copy of a started run's ledger is committed on `base_branch`" in plan
    assert "This is the only ledger autopilot commits on `base_branch`" in plan


def test_step_3_cuts_the_run_branch_only_when_it_does_not_exist_yet():
    step3 = _flat(AUTOPILOT.read_text().split("## Step 3", 1)[1].split("```", 1)[0])
    assert "only when the run branch does not exist yet" in step3
    assert "by Step 2c for a run that starts now" in step3


def test_replay_a_started_run_leaves_no_ledger_on_base_branch(tmp_path):
    """I-20 as git: Step 2c as now written. Once the run branch is gone, nothing on base_branch
    can be mistaken for a planned run."""
    repo = _repo(tmp_path / "w")
    _commit(repo, "init", {"README": "x"})
    _git(repo, "checkout", "-qb", "r1")                       # base_branch
    _git(repo, "checkout", "-qb", "r1-autopilot")             # 2c cuts the run branch first
    led = ".archflow/autopilot/2026-10-10-1.yaml"
    base = {"run_id": "2026-10-10-1", "base_branch": "r1", "run_branch": "r1-autopilot"}
    for status in ("preflight", "running", "finished"):
        _commit(repo, status, {led: dict(base, status=status)})
    _git(repo, "checkout", "-q", "r1")
    _git(repo, "branch", "-qD", "r1-autopilot")               # deleted unmerged
    for b in _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout.split():
        assert _ledgers_on(repo, b) == [], f"{b} still holds a ledger copy resume could restart"


def _guard_commands():
    """The fetch-free and remote checks rule 1's preflight path documents, in order."""
    cmds = re.findall(r"`(git [^`]*\{run_branch\}[^`]*)`", preflight_bullet())
    assert [c.split()[1] for c in cmds] == ["show-ref", "show-ref", "ls-remote"], cmds
    assert "refs/heads/{run_branch}" in cmds[0] and "refs/remotes/origin/{run_branch}" in cmds[1]
    return cmds


def _planned_run_refused(repo, run_branch):
    return any(_git(repo, *c.replace("{run_branch}", run_branch).split()[1:], check=False).returncode == 0
               for c in _guard_commands())


def test_planned_run_guard_is_documented_before_step_3():
    bullet = preflight_bullet()
    assert "**Refuse to start it if its `run_branch` already exists**, locally or on `origin`" in bullet
    assert bullet.index("Refuse to start it") < bullet.index("go to Step 3")
    assert "write nothing" in bullet and "and stop" in bullet


@pytest.fixture
def planned(tmp_path):
    """A --plan ledger on base_branch r1, an origin, and a working clone."""
    seed = _repo(tmp_path / "seed")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _commit(seed, "init", {"README": "x"})
    _git(seed, "checkout", "-qb", "r1")
    _commit(seed, "chore(autopilot): plan 2026-10-10-1", {".archflow/autopilot/2026-10-10-1.yaml": {
        "run_id": "2026-10-10-1", "status": "preflight", "base_branch": "r1", "run_branch": "r1-autopilot"}})
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "main", "r1")
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    return origin, seed, work


def test_planned_run_with_no_run_branch_anywhere_is_started(planned):
    _, _, work = planned
    assert not _planned_run_refused(work, "r1-autopilot")


def test_planned_run_refused_when_run_branch_exists_locally(planned):
    _, _, work = planned
    _git(work, "branch", "r1-autopilot", "origin/r1")
    assert _planned_run_refused(work, "r1-autopilot")


def test_planned_run_refused_when_run_branch_is_only_on_origin(planned):
    """Fresh clone: the run started elsewhere and its branch is only origin/r1-autopilot."""
    origin, seed, _ = planned
    _git(seed, "checkout", "-qb", "r1-autopilot")
    _git(seed, "push", "-q", "origin", "r1-autopilot")
    fresh = origin.parent / "fresh"
    _git(origin.parent, "clone", "-q", str(origin), str(fresh))
    assert _git(fresh, "show-ref", "--verify", "--quiet", "refs/heads/r1-autopilot", check=False).returncode
    assert _planned_run_refused(fresh, "r1-autopilot")


def test_planned_run_refused_when_origin_has_the_branch_but_no_tracking_ref_yet(planned):
    """No fetch since the run started elsewhere: only ls-remote sees it."""
    _, seed, work = planned
    _git(seed, "checkout", "-qb", "r1-autopilot")
    _git(seed, "push", "-q", "origin", "r1-autopilot")
    assert _git(work, "show-ref", "--verify", "--quiet",
                "refs/remotes/origin/r1-autopilot", check=False).returncode
    assert _planned_run_refused(work, "r1-autopilot")


def commit_rule_text():
    body = AUTOPILOT.read_text()
    return _flat(re.search(r"^### Where autopilot commits\n(.*?)(?=^---|^### )", body, re.S | re.M).group(1))


def test_base_branch_bullet_reserves_base_branch_for_plan_ledgers():
    rule = commit_rule_text()
    assert "**`base_branch`** for a `--plan` ledger only" in rule
    assert "Once the run branch exists, the ledger is only ever written there" in rule


def test_remote_only_base_branch_counts_as_existing_and_is_tracked(tmp_path):
    """I-21: origin/{base_branch} exists, no local branch, HEAD has moved on. Following the
    documented checks, the local branch tracks origin; it is never cut from HEAD."""
    rule = commit_rule_text()
    assert "exists neither as a local branch nor as `origin/{base_branch}`" in rule
    assert "never a new one cut from HEAD" in rule
    track = re.search(r"`(git checkout --track origin/\{base_branch\})`", rule).group(1)
    checks = [c.replace("{base_branch}", "r1") for c in
              re.findall(r"refs/(?:heads|remotes/origin)/\{base_branch\}", rule)]
    assert checks == ["refs/heads/r1", "refs/remotes/origin/r1"]

    if not shutil.which("git"):
        pytest.skip("git not on PATH")
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    seed = _repo(tmp_path / "seed")
    _commit(seed, "init", {"README": "x"})
    _git(seed, "checkout", "-qb", "r1")
    _commit(seed, "on r1", {"r1.txt": "r1"})
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "main", "r1")
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", "-b", "main", str(origin), str(work))
    _git(work, "config", "user.email", "qa@example.com"); _git(work, "config", "user.name", "qa")
    _commit(work, "local only", {"main.txt": "m"})

    exists = [_git(work, "show-ref", "--verify", "--quiet", r, check=False).returncode == 0 for r in checks]
    assert exists == [False, True], "a remote-only base_branch must count as existing"
    _git(work, *track.replace("{base_branch}", "r1").split()[1:])
    assert _git(work, "rev-parse", "r1").stdout == _git(work, "rev-parse", "origin/r1").stdout
    assert _git(work, "rev-parse", "--abbrev-ref", "r1@{upstream}").stdout.strip() == "origin/r1"


def test_no_undefined_release_file_conflict_rule():
    """I-22: the only conflict rule left names its side."""
    body = _flat(AUTOPILOT.read_text())
    assert "side written last" not in body
    assert "taking the run branch's release file on a conflict there" in body
