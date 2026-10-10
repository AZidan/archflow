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
    assert "Commit the ledger alone on `base_branch`" in plan and "ledger still `preflight` on `base_branch`" in plan, plan


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
# Re-run after fix pass 3 (96ea739): I-15 (fixed in fix pass 4)
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Fix pass 4: one "where autopilot commits" rule (I-15..I-18)
# --------------------------------------------------------------------------

def commit_rule():
    body = AUTOPILOT.read_text()
    m = re.search(r"^### Where autopilot commits\n(.*?)(?=^---|^### )", body, re.S | re.M)
    assert m, "autopilot.md lost its 'Where autopilot commits' rule"
    return re.sub(r"\s+", " ", m.group(1))


def test_commit_rule_names_run_branch_then_base_branch_and_never_main():
    rule = commit_rule()
    assert rule.index("**The run branch**") < rule.index("**`base_branch`**") < rule.index("**Never `main`.**")
    assert "HALT before writing anything" in rule


def test_step_2c_checks_out_base_branch_before_writing_the_ledger():
    """I-15 and the normal-run carry-over gap: the first ledger commit lands where Step 3 cuts from."""
    plan = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### 2c.", 1)[1].split("### Where", 1)[0])
    assert plan.index("Check out `base_branch`") < plan.index("create `.archflow/autopilot/{run-id}.yaml`")
    step3 = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("## Step 3", 1)[1].split("Then, for each", 1)[0])
    assert "`status: running` and commit it on the run branch" in step3


def test_parked_state_is_carried_onto_the_run_branch():
    """I-16: a parked block committed on the WIP task branch must reach the run branch, where
    resume's scan reads the release file."""
    rule = commit_rule()
    assert "git checkout {task-branch} -- .archflow/releases/{active_release}.yaml" in rule
    parking = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### Parking", 1)[1].split("### Stop", 1)[0])
    assert "carry the release file onto the run branch" in parking
    assert parking.count("carry the release file onto the run branch") == 2, "park and fail both carry"


def test_waiver_only_path_never_commits_on_main():
    """I-17: after a merge the source branch can be main; the waiver commits on run_branch or
    base_branch only."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"Nothing answered, some waived\*\* → (.*?)(?= - \*\*)", rule)
    assert m
    branch = m.group(1)
    assert "`run_branch`, else its `base_branch`" in branch and "never `main`" in branch
    assert "source branch if it is not the current one" not in branch


def test_abort_picks_the_current_run_by_the_resume_scan_and_checks_out_its_branch():
    """I-18."""
    abort = re.sub(r"\s+", " ", subcommand("abort")).split("print Step 4", 1)[0]
    assert "branch scan" in abort and "one-copy-per-run" in abort
    assert abort.index("Check out the branch that ledger lives on") < abort.index("Set `status: aborted`")
    assert "Nothing to abort." in abort


# --------------------------------------------------------------------------
# Re-run after fix pass 4 (ec0bfb6) and fix pass 5 (ca3ecdb): a git replay of the commit rule
# as now written, resume's scan + choice + planned-run guard, and the I-20 reproductions
# --------------------------------------------------------------------------

import shutil
import subprocess

RANK = {"preflight": 0, "running": 1, "finished": 2, "aborted": 2}
REL, LED = ".archflow/releases/r1.yaml", ".archflow/autopilot/2026-10-10-1.yaml"
RUN = "r1-autopilot"


def _git(repo, *args, check=True):
    r = subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True)
    return r.stdout if check else r


def _ok(repo, *args):
    return _git(repo, *args, check=False).returncode == 0


def _write(repo, rel, data):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False))


def _read(repo, rel):
    return yaml.safe_load((repo / rel).read_text())


def _kept(repo):
    """resume's scan as written: every local branch, one copy per run_id (most advanced status,
    tie -> the copy on its own run_branch). Returns {run_id: (source_branch, ledger)}."""
    kept = {}
    for b in _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split():
        for p in _git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/").split():
            led = yaml.safe_load(_git(repo, "show", f"{b}:{p}"))
            old = kept.get(led["run_id"])
            if (old is None or RANK[led["status"]] > RANK[old[1]["status"]]
                    or (RANK[led["status"]] == RANK[old[1]["status"]] and b == led["run_branch"])):
                kept[led["run_id"]] = (b, led)
    return kept


def _scan(repo):
    kept = _kept(repo)
    unfinished = [led["run_id"] for b, led in kept.values() if led["status"] in ("preflight", "running")]
    parked = []
    for b, led in kept.values():
        if led["status"] in ("finished", "aborted"):
            rel = yaml.safe_load(_git(repo, "show", f"{b}:{REL}"))
            parked += [q["id"] for q in led["queue"]
                       if q["state"] == "parked" and rel["stories"][q["id"]]["status"] == "parked"]
    return unfinished, parked


def _guard_hit(repo, run_branch):
    """Rule 1's planned-run guard, the three documented checks in order."""
    if _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{run_branch}"):
        return f"refs/heads/{run_branch}"
    if _ok(repo, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{run_branch}"):
        return f"refs/remotes/origin/{run_branch}"
    if _ok(repo, "remote", "get-url", "origin") and \
            _ok(repo, "ls-remote", "--exit-code", "--heads", "origin", run_branch):
        return f"origin {run_branch}"
    return None


def _resume(repo):
    """What `/archflow:autopilot resume` decides, per the choice and rules 1-3 as written."""
    kept = _kept(repo)
    _, parked = _scan(repo)
    running = [led for b, led in kept.values() if led["status"] == "running"]
    preflight = [led for b, led in kept.values() if led["status"] == "preflight"]
    if running:
        led = running[0]
        if not _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{led['run_branch']}"):
            return ("stop: run branch missing", led["run_id"])
        return ("continue", led["run_id"])
    if preflight and parked:
        return ("ask", preflight[0]["run_id"], parked)
    if preflight:
        led = preflight[0]
        hit = _guard_hit(repo, led["run_branch"])
        return ("refuse", led["run_id"], hit) if hit else ("START planned run", led["run_id"])
    if parked:
        return ("follow-on", parked)
    return ("nothing",)


def _init(repo, stories):
    if not shutil.which("git"):
        pytest.skip("git not on PATH")
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "qa@example.com")
    _git(repo, "config", "user.name", "qa")
    _write(repo, REL, {"stories": {s: {"status": "ready"} for s in stories}})
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")


def _commit(repo, msg):
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", msg)
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    assert branch != "main", f"{msg!r} committed on main"
    assert not _git(repo, "status", "--porcelain"), f"tree dirty after {msg!r}"
    return branch


def _ledger_set(repo, **kw):
    d = _read(repo, LED); d.update(kw); _write(repo, LED, d)


def _plan(repo, stories, plan=False):
    """Step 2c as written in ca3ecdb. Returns the branch the ledger was committed on."""
    _git(repo, "checkout", "-qb", "r1")                          # base_branch from HEAD (absent)
    if not plan:
        _git(repo, "checkout", "-qb", RUN)                       # cut BEFORE the ledger is written
    _write(repo, LED, {"run_id": "2026-10-10-1", "status": "preflight", "base_branch": "r1",
                       "run_branch": RUN, "release": "r1",
                       "queue": [{"id": s, "state": "pending"} for s in stories]})
    return _commit(repo, "chore(autopilot): plan")


def _step3_and_run(repo, outcomes, abort_after=None):
    """Step 3 (cut only if absent), then the story loop, then Step 4's finish (or abort)."""
    if not _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{RUN}"):
        _git(repo, "checkout", "-q", "r1"); _git(repo, "checkout", "-qb", RUN)
    else:
        _git(repo, "checkout", "-q", RUN)
    _ledger_set(repo, status="running"); assert _commit(repo, "running") == RUN

    def story(s, status, **extra):
        d = _read(repo, REL); d["stories"][s] = {"status": status, **extra}; _write(repo, REL, d)

    def queue_set(s, state):
        d = _read(repo, LED)
        for q in d["queue"]:
            if q["id"] == s:
                q["state"] = state
        _write(repo, LED, d)

    for i, (s, outcome) in enumerate(outcomes.items()):
        if abort_after is not None and i == abort_after:
            break
        _git(repo, "checkout", "-qb", f"t/{s}", RUN)
        story(s, "in_progress"); _commit(repo, f"{s} in_progress")
        (repo / f"{s}.txt").write_text(s); story(s, "review"); _commit(repo, f"{s} review")
        if outcome == "done":
            _git(repo, "checkout", "-q", RUN); _git(repo, "merge", "-q", "--no-edit", f"t/{s}")
            story(s, "done"); _git(repo, "branch", "-qD", f"t/{s}")
        else:
            story(s, outcome, **({"parked": {"question": "q?", "blocks_release": True}}
                                 if outcome == "parked" else {}))
            _commit(repo, f"wip: {s} {outcome}")
            before = yaml.safe_load(_git(repo, "show", f"{RUN}:{REL}"))["stories"]
            _git(repo, "checkout", "-q", RUN)
            _git(repo, "checkout", f"t/{s}", "--", REL)          # the carry-over
            after = _read(repo, REL)["stories"]
            assert {k for k in after if after[k] != before[k]} == {s}, "carry touched another story"
        queue_set(s, outcome); assert _commit(repo, f"{s} ledger") == RUN
    if abort_after is not None:
        _ledger_set(repo, status="aborted"); assert _commit(repo, "chore(autopilot): abort") == RUN
    else:
        _ledger_set(repo, status="finished"); assert _commit(repo, "chore(autopilot): finish") == RUN
    _git(repo, "checkout", "-q", "r1")                           # the user goes back to base


def _replay(repo, outcomes, plan=False, abort_after=None):
    _init(repo, outcomes)
    _plan(repo, list(outcomes), plan=plan)
    if plan:
        assert _resume(repo) == ("START planned run", "2026-10-10-1")
    _step3_and_run(repo, outcomes, abort_after=abort_after)


def _with_origin(tmp_path, repo):
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", "main", "r1", RUN)
    return origin


# ---- the normal flow, end to end ----------------------------------------------------------

def test_replay_of_a_normal_run_commits_off_main_and_resume_finds_the_parked_story(tmp_path):
    _replay(tmp_path, {"A": "done", "B": "parked", "C": "failed"})
    assert _git(tmp_path, "log", "--format=%s", "main").split("\n")[0] == "init"
    assert _git(tmp_path, "ls-tree", "--name-only", "r1", ".archflow/autopilot/") == "", \
        "a started run left a ledger copy on base_branch"
    assert _scan(tmp_path) == ([], ["B"])
    assert _resume(tmp_path) == ("follow-on", ["B"])


def test_replay_follow_on_builds_the_answered_story_and_then_resume_has_nothing(tmp_path):
    """Rule 2 'Some answered', as written: check out the run branch first, new ledger + release file
    committed there, continue on the WIP branch after merging the run branch into it, finish."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked", "C": "failed"})
    _git(repo, "checkout", "-q", RUN)                             # first, before writing anything
    assert _read(repo, REL)["stories"]["B"]["status"] == "parked"
    child = ".archflow/autopilot/2026-10-11-1.yaml"
    _write(repo, child, {"run_id": "2026-10-11-1", "status": "preflight", "resumes": "2026-10-10-1",
                         "base_branch": "r1", "run_branch": RUN, "release": "r1",
                         "queue": [{"id": "B", "state": "pending", "branch": "t/B"}]})
    d = _read(repo, REL); d["stories"]["B"] = {"status": "in_progress"}; _write(repo, REL, d)
    assert _commit(repo, "resume: follow-on") == RUN
    c = _read(repo, child); c["status"] = "running"; _write(repo, child, c); _commit(repo, "running")
    _git(repo, "checkout", "-q", "t/B")
    r = _git(repo, "merge", "--no-edit", RUN, check=False)
    if r.returncode:                                              # take the run branch's release file
        _git(repo, "checkout", RUN, "--", REL); _git(repo, "add", REL)
        _git(repo, "commit", "-qm", "merge run branch")
    assert _read(repo, REL)["stories"]["B"]["status"] == "in_progress"
    d = _read(repo, REL); d["stories"]["B"] = {"status": "review"}; _write(repo, REL, d); _commit(repo, "B review")
    _git(repo, "checkout", "-q", RUN); _git(repo, "merge", "-q", "--no-edit", "t/B")
    d = _read(repo, REL); d["stories"]["B"] = {"status": "done"}; _write(repo, REL, d)
    c = _read(repo, child); c["queue"][0]["state"] = "done"; c["status"] = "finished"; _write(repo, child, c)
    _commit(repo, "chore(autopilot): finish 2026-10-11-1")
    stories = _read(repo, REL)["stories"]
    assert stories == {"A": {"status": "done"}, "B": {"status": "done"}, "C": {"status": "failed"}}
    assert _read(repo, LED)["status"] == "finished", "the source ledger was edited"
    _git(repo, "checkout", "-q", "r1")
    assert _resume(repo) == ("nothing",)
    assert _git(repo, "log", "--format=%s", "main").split("\n")[0] == "init"


# ---- I-20 reproductions, against ca3ecdb ------------------------------------------------------

def test_a_finished_run_is_not_resurrected_from_the_preflight_copy_on_base_branch(tmp_path):
    """I-20 scenario A: all done, run branch deleted unmerged -> nothing to resume."""
    _replay(tmp_path, {"A": "done", "B": "done"})
    _git(tmp_path, "branch", "-qD", RUN)
    assert _resume(tmp_path) == ("nothing",)


def test_i20_fresh_clone_of_base_branch_resumes_nothing(tmp_path):
    """I-20 scenario B: the run branch exists only as origin/r1-autopilot in a fresh clone."""
    repo = tmp_path / "w"
    _replay(repo, {"A": "done", "B": "done"})
    _with_origin(tmp_path, repo)
    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", "-q", "-b", "r1", str(tmp_path / "origin.git"), str(fresh))
    assert not _ok(fresh, "show-ref", "--verify", "--quiet", f"refs/heads/{RUN}")
    assert _resume(fresh) == ("nothing",)


@pytest.mark.parametrize("delete", [False, True])
def test_i20_an_aborted_run_stays_aborted(tmp_path, delete):
    """I-20 scenario C: aborted before anything parked, with and without its run branch."""
    _replay(tmp_path, {"A": "done", "B": "done"}, abort_after=1)
    if delete:
        _git(tmp_path, "branch", "-qD", RUN)
    assert _resume(tmp_path) == ("nothing",)


def test_an_aborted_planned_run_that_never_started_stays_aborted(tmp_path):
    _init(tmp_path, ["A"])
    assert _plan(tmp_path, ["A"], plan=True) == "r1"
    _ledger_set(tmp_path, status="aborted"); assert _commit(tmp_path, "chore(autopilot): abort") == "r1"
    assert _resume(tmp_path) == ("nothing",)


def test_an_aborted_run_with_a_parked_story_hands_it_to_rule_2(tmp_path):
    _replay(tmp_path, {"A": "parked", "B": "done"}, abort_after=1)
    assert _resume(tmp_path) == ("follow-on", ["A"])


# ---- planned runs (--plan) and the guard ------------------------------------------------------

def test_planned_run_lifecycle_with_its_run_branch_present(tmp_path):
    """--plan on base_branch, started by resume (guard clear), finished: resume has nothing, because
    the finished copy on the run branch outranks the preflight copy left on base_branch."""
    _replay(tmp_path, {"A": "done"}, plan=True)
    assert yaml.safe_load(_git(tmp_path, "show", f"r1:{LED}"))["status"] == "preflight"
    assert _resume(tmp_path) == ("nothing",)


def test_planned_run_branch_deleted_locally_but_on_origin_is_refused(tmp_path):
    repo = tmp_path / "w"
    _replay(repo, {"A": "done"}, plan=True)
    _with_origin(tmp_path, repo)
    _git(repo, "branch", "-qD", RUN)
    assert _resume(repo)[0] == "refuse"


def test_planned_run_merged_on_origin_and_pulled_is_not_restarted(tmp_path):
    """The usual 'review it and merge it yourself' flow: merged (here into main on origin, like a
    PR), branch deleted everywhere, main pulled -> the finished copy on main wins."""
    repo = tmp_path / "w"
    _replay(repo, {"A": "done"}, plan=True)
    origin = _with_origin(tmp_path, repo)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    _git(other, "config", "user.email", "qa@example.com"); _git(other, "config", "user.name", "qa")
    _git(other, "merge", "-q", "--no-edit", f"origin/{RUN}")
    _git(other, "push", "-q", "origin", "main", f":{RUN}")
    _git(repo, "fetch", "-q", "--prune", "origin"); _git(repo, "branch", "-qD", RUN)
    _git(repo, "checkout", "-q", "main"); _git(repo, "merge", "-q", "--ff-only", "origin/main")
    _git(repo, "checkout", "-q", "r1")
    assert _resume(repo) == ("nothing",)


@pytest.mark.xfail(strict=True, reason="I-23: a started --plan run's preflight copy on base_branch "
                   "restarts the queue once its run branch is gone locally and on origin")
@pytest.mark.parametrize("how", ["discarded", "merged-on-origin-not-pulled", "aborted-discarded"])
def test_started_planned_run_is_not_restarted_once_its_run_branch_is_gone_everywhere(tmp_path, how):
    """g1. The run finished (nothing parked), or was aborted. Its branch is then deleted locally and on origin
    without the finished ledger reaching any local branch: either the user discarded the night's
    work, or merged it as a PR on origin (auto-delete branch), pruned, and has not pulled main yet.
    No guard check hits, the preflight copy on base_branch is the only copy, and 'Only one of the
    two -> that rule' sends it to rule 1, which starts the whole queue again unattended."""
    repo = tmp_path / "w"
    _replay(repo, {"A": "done", "B": "done"}, plan=True,
            abort_after=1 if how == "aborted-discarded" else None)
    origin = _with_origin(tmp_path, repo)
    if how == "merged-on-origin-not-pulled":
        other = tmp_path / "other"
        _git(tmp_path, "clone", "-q", str(origin), str(other))
        _git(other, "config", "user.email", "qa@example.com"); _git(other, "config", "user.name", "qa")
        _git(other, "merge", "-q", "--no-edit", f"origin/{RUN}")
        _git(other, "push", "-q", "origin", "main")
    _git(repo, "push", "-q", "origin", f":{RUN}")
    _git(repo, "fetch", "-q", "--prune", "origin"); _git(repo, "branch", "-qD", RUN)
    assert _resume(repo) == ("nothing",)


# ---- g2: a normal run that dies before Step 3's `running` commit -----------------------------

def test_g2_run_dead_before_running_is_refused_and_abort_clears_it(tmp_path):
    """Step 2c committed `preflight` on the run branch, then the session died. resume's guard
    refuses (the run branch exists); `abort` - documented to take the newest preflight/running
    ledger and commit `aborted` on the branch it lives on - clears it, after which resume has
    nothing and a new run is unobstructed."""
    _init(tmp_path, ["A"])
    assert _plan(tmp_path, ["A"]) == RUN
    _git(tmp_path, "checkout", "-q", "r1")
    assert _resume(tmp_path) == ("refuse", "2026-10-10-1", f"refs/heads/{RUN}")
    src, led = _kept(tmp_path)["2026-10-10-1"]                    # abort: same scan, one copy
    assert src == RUN
    _git(tmp_path, "checkout", "-q", src)
    _ledger_set(tmp_path, status="aborted"); assert _commit(tmp_path, "chore(autopilot): abort") == RUN
    assert _resume(tmp_path) == ("nothing",)
