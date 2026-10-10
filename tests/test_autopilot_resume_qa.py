"""QA additions for S5-02 (`/archflow:autopilot resume` after a run finishes).

tests/test_autopilot_resume.py pins the happy paths. These cover what it does not:

- the follow-on run inherits the envelope instead of re-interviewing;
- the old two-step "answer it, then resume" wording is gone from every surface the user reads;
- the Step 4 `Next:` rule is consistent with what `resume` accepts for every way Step 4 is
  printed, including `abort`;
- a git replay of the commit rule and of resume's choice and rules (see the model section).
"""

import re
from pathlib import Path

import pytest
import yaml

from test_autopilot_resume import (  # noqa: F401  (reuse the fixtures of the story's own suite)
    AUTOPILOT, STATUS, SCHEMA, RESUME, DONE, PARKED,
    ledger, project, validate, resume_rule, report_block, status_parked_case,
    commit_rule_text, preflight_bullet, _git, _ok, _repo,
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
    """The follow-on builds on the current branch when it is a run branch, else on a new
    run branch cut from the current branch (which holds the parked state just read)."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "WIP task branch" in rule
    assert "the current branch if it is the `run_branch` of a kept ledger" in rule
    assert "`{base_branch}-autopilot-{run-id}`" in rule and "cut from the current branch" in rule
    assert "committing on it never is" in rule, "a branch may be cut from main, never committed on it"


def test_follow_on_run_id_follows_step_2c():
    """A follow-on run is a run: same id scheme, same ledger, same schema."""
    assert "per Step 2c" in resume_rule()


def test_schema_resumes_is_one_run_id():
    """`resumes` is the single run id rule 2 writes, in both schema mirrors."""
    for path in (SCHEMA, REPO / "plugin" / "skills" / "archflow" / "schemas" / "autopilot-schema.yaml"):
        field = yaml.safe_load(path.read_text())["run"]["properties"]["resumes"]
        assert field["type"] == "string" and "items" not in field
        assert re.fullmatch(field["pattern"], field["example"])
    assert "`resumes: {source run-id}`" in re.sub(r"\s+", " ", resume_rule())


def test_follow_on_ledger_is_written_running_before_any_story_work():
    """A follow-on written `preflight` that then enters Step 3's story loop skipped the
    `running` write, and an interrupted follow-on was refused as a planned run."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "`status: running` from the start" in rule
    assert "before any story work" in rule
    step3 = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("## Step 3", 1)[1].split("Then, for each", 1)[0])
    assert "a follow-on run is written `running` (rule 2)" in step3


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
# abort and rule 2
# --------------------------------------------------------------------------

def test_abort_hands_its_parked_stories_to_resume_rule_2():
    """abort and rule 2 point at each other."""
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


def test_parked_stories_of_another_release_are_not_read_or_edited():
    """Parked stories come from the active release file only; other releases are never edited."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "never reads or edits another release file" in rule
    assert "change nothing" in rule


def test_status_parked_advice_defers_to_resume_for_a_waiting_run():
    """status points at resume's own rules for a run that is also waiting, without restating them."""
    rule = re.sub(r"\s+", " ", resume_rule())
    status = re.sub(r"\s+", " ", status_parked_case())
    assert "they wait for the next `resume`" in rule  # the precedence resume documents
    assert "Its own rules cover a run that is also waiting" in status
    for restated in ("one to pick up", "continues it first", "/archflow:autopilot abort"):
        assert restated not in status, restated


def test_status_parked_advice_also_fires_on_an_other_run_branches_line():
    """On base_branch after a run, status gives the advice resume would: the pointer lines."""
    status = re.sub(r"\s+", " ", status_parked_case())
    assert "*Other run branches* rule" in status
    assert "**Other run branches.**" in resume_rule()


# --------------------------------------------------------------------------
# Step 4's closing write, the branch scan, the waiver
# --------------------------------------------------------------------------

def _closing_write():
    """The paragraph of Step 4 that sets `status: finished`, through the end of Step 4."""
    step4 = re.sub(r"\s+", " ", report_block())
    i = step4.find("`status: finished`")
    assert i != -1, "Step 4 no longer closes the run with `status: finished`"
    return step4[i:]


def test_step4_closing_write_exempts_abort():
    """abort prints Step 4; Step 4's closing `status: finished` must not apply to it,
    or an aborted run ends up `finished`. Fails if the exemption is removed."""
    closing = _closing_write()
    assert re.search(r"\*\*`abort`\*\*[^*]*stays `aborted`", closing), closing
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    assert "print Step 4" in abort
    assert re.search(r"skip\w* its closing status write", abort)
    assert "stays `aborted`" in abort


def test_step4_closing_write_exempts_report():
    """report reprints Step 4 and must never close (or re-close) a run."""
    closing = _closing_write()
    assert re.search(r"\*\*`report`\*\*[^*]*read-only", closing, re.I), closing
    report = re.sub(r"\s+", " ", subcommand("report"))
    assert "Read-only" in report and "closing status write" in report


def test_resume_scan_reads_committed_state_on_other_branches():
    """A run's ledger lives on its run branch; a user back on base_branch must still find it."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "current checkout first" in rule
    assert "git for-each-ref" in rule and "git show {branch}:" in rule
    assert "source branch" in rule
    assert "without checking anything out" in rule


def test_follow_on_checks_out_the_run_branch_before_writing():
    """Writing the ledger and release file before checkout dirties the tree."""
    rule = re.sub(r"\s+", " ", resume_rule())
    i_checkout = rule.index("check out the run branch")
    assert i_checkout < rule.index("Write a new ledger")
    assert i_checkout < rule.index("clear each answered story's `parked` block")
    assert "before writing anything" in rule


def test_a_waiver_on_an_unanswered_story_is_recorded():
    """The waiver only matters for a story that stays parked, so it must not be discarded
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
    """A --plan ledger has no run branch until Step 3 creates it."""
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
    """In both mirrors."""
    for path in (SCHEMA, REPO / "plugin" / "skills" / "archflow" / "schemas" / "autopilot-schema.yaml"):
        desc = re.sub(r"\s+", " ", yaml.safe_load(path.read_text())["run"]["properties"]["status"]["description"])
        m = re.search(rf"{status} — (.*?)(?= \w+ +—|$)", desc)
        assert m, (path, status)
        assert "never" in m.group(1) and "follow-on run" in m.group(1), (path, m.group(1))


# --------------------------------------------------------------------------
# Terminal writes are committed; current-checkout parked stories; the pointer
# --------------------------------------------------------------------------

def test_terminal_ledger_writes_are_committed():
    """Step 4's closing write, abort's `aborted` write and --plan's `preflight` ledger are committed:
    resume HALTs on a dirty tree, and the branch scan reads committed ledgers only."""
    closing = _closing_write()
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    plan = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### 2c.", 1)[1].split("---", 1)[0])
    assert re.search(r"[Cc]ommit", closing.split("Two callers", 1)[0]), closing
    assert re.search(r"[Cc]ommit", abort.split("print Step 4", 1)[0]), abort
    assert re.search(r"--plan`.{0,200}[Cc]ommit", plan), plan


def test_parked_stories_come_from_the_current_checkout_only():
    """User decision: no story status is read from another branch. Guards against the removed
    release-file combine, superseded-copy rule, status ranking, grouping and choose-a-run prompt."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "in the current checkout, and nowhere else" in rule
    assert "never reads another branch's copy of that file" in rule
    for gone in ("superseded", "`parked` < `in_progress`", "not asking it", "merge-base",
                 "Group the answered stories", "which to build now", "lacks its park"):
        assert gone not in rule, gone


def test_resume_names_other_run_branches_without_reading_them():
    """The pointer to parked work on other run branches is information only, one line per branch."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"\*\*Other run branches\.\*\*(.*)", rule)
    assert m, "resume lost its pointer to other run branches"
    text = m.group(1)
    assert "`Parked work from {run-id} may be on {run_branch}: check it out and run /archflow:autopilot resume there.`" in text
    assert "exists locally and is not the current branch" in text
    assert "information only" in text and "nothing is read from those branches' release files" in text
    assert "instead of `Nothing to resume.`" in text
    assert "one line per branch, naming the newest such run on it" in text
    assert "no newer follow-on has in its `queue[]`" in text


def test_terminal_ledger_commits_name_the_branch_they_land_on():
    """Each terminal write is committed on the branch the scan will read it from, and with
    the ledger alone (never sweeping in anything else)."""
    closing = _closing_write().split("Two callers", 1)[0]
    abort = re.sub(r"\s+", " ", subcommand("abort")).split("print Step 4", 1)[0]
    plan = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### 2c.", 1)[1].split("---", 1)[0])
    assert "ledger alone on the run branch" in closing, closing
    assert "ledger alone on the branch it lives on" in abort and "run branch" in abort, abort
    assert "Commit the ledger alone on `base_branch`" in plan and "ledger still `preflight` on `base_branch`" in plan, plan


def test_branch_scan_dedups_one_run_across_branches():
    """One run seen on several branches is kept once, by a stated rule, before choosing."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "always, from the committed `.archflow/` of every local branch" in rule
    assert "Keep one copy per `run_id`" in rule and "most advanced `status`" in rule
    assert rule.index("Keep one copy per `run_id`") < rule.index("Choose by it")


def test_waiver_path_records_on_the_current_branch_and_stops():
    """The parked state was just read from the current branch, so the waiver is recorded
    there (no re-read on another branch), the release file alone, and then resume stops."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"Nothing answered, some waived\*\* → (.*?)(?= - \*\*)", rule)
    assert m and "On the current branch" in m.group(1) and "commit only the release file" in m.group(1)
    assert "Then stop." in m.group(1)


def test_envelope_must_not_rule_admits_the_resume_waiver():
    """QA wording note: MUST NOT must not literally forbid the waiver MAY allows."""
    body = AUTOPILOT.read_text()
    must_not = re.sub(r"\s+", " ", body.split("**MUST NOT", 1)[1].split("## Subcommands", 1)[0])
    assert "Touch any story outside its queue," not in must_not
    assert "waiver" in must_not


# --------------------------------------------------------------------------
# One "where autopilot commits" rule
# --------------------------------------------------------------------------

def test_planned_run_ledger_reaches_the_run_branch():
    """Step 3 cuts the run branch from `base_branch`, so rule 1 starts a planned run there."""
    assert re.search(r"check out `base_branch` first", preflight_bullet())


def test_commit_rule_names_run_branch_then_base_branch_and_never_main():
    rule = commit_rule_text()
    assert rule.index("**The run branch**") < rule.index("**`base_branch`**") < rule.index("**Never `main`.**")
    assert "HALT before writing anything" in rule


def test_step_2c_checks_out_base_branch_before_writing_the_ledger():
    """The first ledger commit lands where Step 3 cuts from."""
    plan = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### 2c.", 1)[1].split("### Where", 1)[0])
    assert plan.index("Check out `base_branch`") < plan.index("create `.archflow/autopilot/{run-id}.yaml`")
    step3 = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("## Step 3", 1)[1].split("Then, for each", 1)[0])
    assert "`status: running` and commit it on the run branch" in step3


def test_parked_state_is_carried_onto_the_run_branch():
    """A parked block committed on the WIP task branch must reach the run branch, where
    resume's scan reads the release file."""
    rule = commit_rule_text()
    assert "git checkout {task-branch} -- .archflow/releases/{active_release}.yaml" in rule
    parking = re.sub(r"\s+", " ", AUTOPILOT.read_text().split("### Parking", 1)[1].split("### Stop", 1)[0])
    assert "carry the release file onto the run branch" in parking
    assert parking.count("carry the release file onto the run branch") == 2, "park and fail both carry"


def test_waiver_only_path_never_commits_on_main():
    """On main the waiver commits nothing and the user is told to check out a non-main branch."""
    rule = re.sub(r"\s+", " ", resume_rule())
    m = re.search(r"Nothing answered, some waived\*\* → (.*?)(?= - \*\*)", rule)
    assert m
    branch = m.group(1)
    assert "Never `main`: on `main`, commit nothing" in branch
    assert "check out a non-`main` branch" in branch


def test_abort_picks_the_current_run_by_the_resume_scan_and_checks_out_its_branch():
    abort = re.sub(r"\s+", " ", subcommand("abort")).split("print Step 4", 1)[0]
    assert "branch scan" in abort and "one-copy-per-run" in abort
    assert abort.index("Check out the branch that ledger lives on") < abort.index("Set `status: aborted`")
    assert "Nothing to abort." in abort


def test_abort_falls_back_to_base_branch_for_a_gone_run_branch_never_main():
    """Rule 1 sends a started run whose run branch is gone to abort, which must name a branch."""
    abort = re.sub(r"\s+", " ", subcommand("abort"))
    assert "its `run_branch` if that exists locally, else its `base_branch`" in abort
    assert "a started run whose run branch is gone" in abort and "never `main`" in abort
    assert "merged and deleted also land on `base_branch`" not in commit_rule_text()


def test_several_unfinished_ledgers_resolve_to_the_newest():
    """resume's current run is the one abort closes: newest running, else newest preflight."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "The **current run** is the newest `running` ledger, else the newest `preflight` one" in rule
    assert "closes the current run" in re.sub(r"\s+", " ", subcommand("abort"))


def test_follow_on_without_a_source_run_has_a_base_branch():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "With no source run, ask Step 2a's questions except the run branch one" in rule
    assert "`base_branch` is Step 2a's `{base-branch}`" in rule


def test_resume_refuses_on_a_wip_branch_and_skips_picked_up_stories():
    rule = re.sub(r"\s+", " ", resume_rule())
    assert ("`This is {story}'s WIP branch; check out {run_branch} and run /archflow:autopilot "
            "resume there.`") in rule
    assert rule.index("Not on a WIP branch") < rule.index("**Ask** every parked story")
    assert "`{story} was picked up by {run-id} on {run_branch}.`" in rule
    assert "newest kept ledger whose `run_branch` is the current branch" in rule


# --------------------------------------------------------------------------
# Replay model. The helpers below are an executable MODEL of the rules autopilot.md states
# (resume's scan, choice, rules 1-3 and the pointer; Step 2c-4's commits). They are not parsed
# from the doc, so the replay tests guard the user's decisions as modelled, run on real git;
# the doc-pin tests above tie each rule to its wording.
# --------------------------------------------------------------------------

RANK = {"preflight": 0, "running": 1, "finished": 2, "aborted": 2}
REL, LED = ".archflow/releases/r1.yaml", ".archflow/autopilot/2026-10-10-1.yaml"
RUN = "r1-autopilot"


def _write(repo, rel, data):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False))


def _read(repo, rel):
    return yaml.safe_load((repo / rel).read_text())


def _kept(repo):
    """resume's scan: every local branch, one copy per run_id (most advanced status, tie -> the
    copy on its own run_branch). Returns {run_id: (source_branch, ledger)}."""
    kept = {}
    for b in _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split():
        for p in _git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/").split():
            led = yaml.safe_load(_git(repo, "show", f"{b}:{p}"))
            old = kept.get(led["run_id"])
            if (old is None or RANK[led["status"]] > RANK[old[1]["status"]]
                    or (RANK[led["status"]] == RANK[old[1]["status"]] and b == led["run_branch"])):
                kept[led["run_id"]] = (b, led)
    return kept


def _ledgers(repo):
    return [led for b, led in _kept(repo).values()]


def _current(repo):
    return _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()


def _rid_key(rid):
    y, m, d, n = rid.split("-")
    return (y, m, d, int(n))


def _newest(leds):
    return max(leds, key=lambda l: _rid_key(l["run_id"])) if leds else None


def _local(repo, branch):
    return _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")


def _release_here(repo):
    r = _git(repo, "show", f"HEAD:{REL}", check=False)
    return (yaml.safe_load(r.stdout).get("stories") or {}) if not r.returncode else {}


def _picked_up(repo):
    """Parked here, but queued by a follow-on on another run branch: [(story, run_id, run_branch)]."""
    cur, out = _current(repo), []
    for s, v in _release_here(repo).items():
        if v["status"] != "parked":
            continue
        by = _newest([l for l in _ledgers(repo) if l.get("resumes") and l["run_branch"] != cur
                      and any(q["id"] == s for q in l["queue"])])
        if by:
            out.append((s, by["run_id"], by["run_branch"]))
    return out


def _parked_here(repo):
    """Stories still `status: parked` in the CURRENT checkout's release file, minus picked-up ones.
    No other branch's copy of the release file is read."""
    picked = {s for s, _, _ in _picked_up(repo)}
    return [s for s, v in _release_here(repo).items() if v["status"] == "parked" and s not in picked]


def _pointers(repo):
    """'Other run branches': one line per local run_branch (not the current one) of a kept
    finished/aborted ledger of the active release with a parked item no newer follow-on queued,
    naming the newest such run. Returns [(run_id, run_branch)]."""
    cur, leds = _current(repo), _ledgers(repo)

    def picked_later(led, s):
        return any(l.get("resumes") and _rid_key(l["run_id"]) > _rid_key(led["run_id"])
                   and any(q["id"] == s for q in l["queue"]) for l in leds)

    by_branch = {}
    for led in leds:
        if (led["status"] in ("finished", "aborted") and led["release"] == "r1"
                and any(q["state"] == "parked" and not picked_later(led, q["id"]) for q in led["queue"])
                and _local(repo, led["run_branch"]) and led["run_branch"] != cur):
            by_branch.setdefault(led["run_branch"], []).append(led)
    return sorted((_newest(v)["run_id"], b) for b, v in by_branch.items())


def _wip(repo):
    """Rule 2's guard: the current branch is a kept ledger's queue-item branch or a parked.branch.
    Returns (story, run_branch) or None."""
    cur, leds = _current(repo), _ledgers(repo)
    for s, v in _release_here(repo).items():
        mine = [l for l in leds if any(q["id"] == s and q.get("branch") == cur for q in l["queue"])]
        if not mine and v["status"] == "parked" and (v.get("parked") or {}).get("branch") == cur:
            mine = [l for l in leds if any(q["id"] == s for q in l["queue"])]
        if mine:
            return s, _newest(mine)["run_branch"]
    return None


def _source_run(repo, answered):
    """The newest kept ledger whose run_branch is the current branch, else the newest kept
    finished/aborted ledger of the active release whose queue parked any answered story."""
    leds, cur = _ledgers(repo), _current(repo)
    return _newest([l for l in leds if l["run_branch"] == cur]) or _newest(
        [l for l in leds if l["status"] in ("finished", "aborted") and l["release"] == "r1"
         and any(q["id"] in answered and q["state"] == "parked" for q in l["queue"])])


def _follow_on(repo, answered, run_id):
    """Rule 2 'Some answered': builds on the current branch if it is a kept ledger's run_branch, else
    on a new {base_branch}-autopilot-{run_id} cut from it. Returns (run_branch, cut_new, stories,
    resumes)."""
    src = _source_run(repo, answered)
    cur = _current(repo)
    if any(l["run_branch"] == cur for l in _ledgers(repo)):
        branch, new = cur, False
    else:
        base = src["base_branch"] if src else "r1"                # no source run: Step 2a's {base-branch}
        branch, new = f"{base}-autopilot-{run_id}", True
    return branch, new, list(answered), src["run_id"] if src else None


def _waive(repo, story):
    """Rule 2's waiver, nothing answered: on the current branch, never main. Returns the branch
    committed on, or None when nothing was committed."""
    if _current(repo) == "main":
        return None
    d = _read(repo, REL)
    assert d["stories"][story]["status"] == "parked"             # only parked stories are asked
    if d["stories"][story]["parked"].get("blocks_release") is False:
        return _current(repo)                                     # already waived: nothing to commit
    d["stories"][story]["parked"]["blocks_release"] = False
    _write(repo, REL, d)
    return _commit(repo, f"waive {story}")


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
    """What `/archflow:autopilot resume` decides: the current run (newest running, else newest
    preflight), the choice, and rules 1-3."""
    leds = _ledgers(repo)
    parked = _parked_here(repo)
    running = _newest([l for l in leds if l["status"] == "running"])
    preflight = _newest([l for l in leds if l["status"] == "preflight"])
    if running:
        if _local(repo, running["run_branch"]):
            return ("continue", running["run_id"])
        hit = _guard_hit(repo, running["run_branch"])            # not local: same checks as the guard
        if hit:
            return ("refuse", running["run_id"], hit)
        return ("gone", running["run_id"])                        # nothing else chosen this time
    if preflight and parked:
        return ("ask", preflight["run_id"], parked)
    if preflight:
        hit = _guard_hit(repo, preflight["run_branch"])
        return ("refuse", preflight["run_id"], hit) if hit else ("START planned run", preflight["run_id"])
    if parked:
        wip = _wip(repo)
        return ("wip", *wip) if wip else ("follow-on", parked)
    return ("nothing",)


def _init(repo, stories):
    _repo(repo)
    _write(repo, REL, {"stories": {s: {"status": "ready"} for s in stories}})
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", "init")


def _commit(repo, msg):
    """Commit everything, asserting the commit rule: never on main, and a clean tree after."""
    _git(repo, "add", "-A"); _git(repo, "commit", "-qm", msg)
    branch = _current(repo)
    assert branch != "main", f"{msg!r} committed on main"
    assert not _git(repo, "status", "--porcelain"), f"tree dirty after {msg!r}"
    return branch


def _ledger_set(repo, led=LED, **kw):
    d = _read(repo, led); d.update(kw); _write(repo, led, d)


def _plan(repo, stories, plan=False, run_id="2026-10-10-1", run=RUN):
    """Step 2c. Returns the branch the ledger was committed on."""
    if _local(repo, "r1"):
        _git(repo, "checkout", "-q", "r1")
    else:
        _git(repo, "checkout", "-qb", "r1")                      # base_branch from HEAD (absent)
    if not plan:
        _git(repo, "checkout", "-qb", run)                       # cut BEFORE the ledger is written
    _write(repo, f".archflow/autopilot/{run_id}.yaml",
           {"run_id": run_id, "status": "preflight", "base_branch": "r1",
            "run_branch": run, "release": "r1",
            "queue": [{"id": s, "state": "pending", "branch": f"t/{s}"} for s in stories]})
    return _commit(repo, "chore(autopilot): plan")


def _step3_and_run(repo, outcomes, abort_after=None, run_id="2026-10-10-1", run=RUN):
    """Step 3 (cut only if absent), then the story loop, then Step 4's finish (or abort)."""
    LED = f".archflow/autopilot/{run_id}.yaml"
    RUN = run
    if not _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{RUN}"):
        _git(repo, "checkout", "-q", "r1"); _git(repo, "checkout", "-qb", RUN)
    else:
        _git(repo, "checkout", "-q", RUN)
    if _read(repo, LED)["status"] != "running":                  # a resumed --plan run is already
        _ledger_set(repo, LED, status="running"); assert _commit(repo, "running") == RUN

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
        _ledger_set(repo, LED, status="aborted"); assert _commit(repo, "chore(autopilot): abort") == RUN
    else:
        _ledger_set(repo, LED, status="finished"); assert _commit(repo, "chore(autopilot): finish") == RUN
    _git(repo, "checkout", "-q", "r1")                           # the user goes back to base


def _replay(repo, outcomes, plan=False, abort_after=None):
    _init(repo, outcomes)
    _plan(repo, list(outcomes), plan=plan)
    if plan:
        assert _resume(repo) == ("START planned run", "2026-10-10-1")
        # Starting a planned run: `running`, committed alone on base_branch, before Step 3 cuts the run branch.
        _git(repo, "checkout", "-q", "r1")
        _ledger_set(repo, status="running"); assert _commit(repo, "chore(autopilot): start") == "r1"
    _step3_and_run(repo, outcomes, abort_after=abort_after)


def _with_origin(tmp_path, repo):
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", "main", "r1", RUN)
    return origin


# ---- the normal flow, end to end ----------------------------------------------------------

def test_replay_of_a_normal_run_commits_off_main_and_resume_finds_the_parked_story(tmp_path):
    """The user is back on base_branch r1, whose release file has no park (the run's
    state is on r1-autopilot, unmerged). resume asks nothing there and names the run branch; on the
    run branch it asks B."""
    _replay(tmp_path, {"A": "done", "B": "parked", "C": "failed"})
    assert _git(tmp_path, "log", "--format=%s", "main").split("\n")[0] == "init"
    assert _git(tmp_path, "ls-tree", "--name-only", "r1", ".archflow/autopilot/") == "", \
        "a started run left a ledger copy on base_branch"
    assert _parked_here(tmp_path) == []
    assert _resume(tmp_path) == ("nothing",)
    assert _pointers(tmp_path) == [("2026-10-10-1", RUN)]
    _git(tmp_path, "checkout", "-q", RUN)
    assert _parked_here(tmp_path) == ["B"]
    assert _resume(tmp_path) == ("follow-on", ["B"])
    assert _pointers(tmp_path) == []


def test_replay_follow_on_builds_the_answered_story_and_then_resume_has_nothing(tmp_path):
    """Rule 2 'Some answered', as written: check out the run branch first, new ledger + release file
    committed there, continue on the WIP branch after merging the run branch into it, finish."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked", "C": "failed"})
    _git(repo, "checkout", "-q", RUN)                             # the user runs resume on the run branch
    assert _resume(repo) == ("follow-on", ["B"])
    # the current branch is a run branch -> build on it, its ledger is the source
    assert _follow_on(repo, ["B"], "2026-10-11-1") == (RUN, False, ["B"], "2026-10-10-1")
    assert _read(repo, REL)["stories"]["B"]["status"] == "parked"
    child = ".archflow/autopilot/2026-10-11-1.yaml"
    # written `running` from the start; no hand-set `running` afterwards
    _write(repo, child, {"run_id": "2026-10-11-1", "status": "running", "resumes": "2026-10-10-1",
                         "base_branch": "r1", "run_branch": RUN, "release": "r1",
                         "queue": [{"id": "B", "state": "pending", "branch": "t/B"}]})
    d = _read(repo, REL); d["stories"]["B"] = {"status": "in_progress"}; _write(repo, REL, d)
    assert _commit(repo, "resume: follow-on") == RUN
    assert _resume(repo) == ("continue", "2026-10-11-1"), "an interrupted follow-on is a running run"
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


# ---- no resurrection: finished and aborted runs ------------------------------------------------

def test_a_finished_run_is_not_resurrected_from_the_preflight_copy_on_base_branch(tmp_path):
    """All done, run branch deleted unmerged -> nothing to resume."""
    _replay(tmp_path, {"A": "done", "B": "done"})
    _git(tmp_path, "branch", "-qD", RUN)
    assert _resume(tmp_path) == ("nothing",)


def test_fresh_clone_of_base_branch_resumes_nothing(tmp_path):
    """The run branch exists only as origin/r1-autopilot in a fresh clone."""
    repo = tmp_path / "w"
    _replay(repo, {"A": "done", "B": "done"})
    _with_origin(tmp_path, repo)
    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", "-q", "-b", "r1", str(tmp_path / "origin.git"), str(fresh))
    assert not _ok(fresh, "show-ref", "--verify", "--quiet", f"refs/heads/{RUN}")
    assert _resume(fresh) == ("nothing",)


@pytest.mark.parametrize("delete", [False, True])
def test_an_aborted_run_stays_aborted(tmp_path, delete):
    """Aborted before anything parked, with and without its run branch."""
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
    """On base_branch the aborted run's branch is named; on the run branch A is asked."""
    _replay(tmp_path, {"A": "parked", "B": "done"}, abort_after=1)
    assert _resume(tmp_path) == ("nothing",) and _pointers(tmp_path) == [("2026-10-10-1", RUN)]
    _git(tmp_path, "checkout", "-q", RUN)
    assert _resume(tmp_path) == ("follow-on", ["A"])
    assert _follow_on(tmp_path, ["A"], "2026-10-11-1") == (RUN, False, ["A"], "2026-10-10-1")
    assert _read(tmp_path, LED)["status"] == "aborted"


# ---- planned runs (--plan) and the guard ------------------------------------------------------

def test_planned_run_lifecycle_with_its_run_branch_present(tmp_path):
    """--plan on base_branch, started by resume (guard clear), finished: resume has nothing, because
    the finished copy on the run branch outranks the running copy left on base_branch."""
    _replay(tmp_path, {"A": "done"}, plan=True)
    assert yaml.safe_load(_git(tmp_path, "show", f"r1:{LED}"))["status"] == "running"
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
    assert _resume(repo) == ("gone", "2026-10-10-1")       # reported and stopped, never restarted


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


# ---- rule 1's `running` bullet when the run branch is missing ---------------------------------

def _start_planned_and_die(repo, stories):
    """--plan, resume starts it (rule 1: `running` committed alone on base_branch), Step 3 cuts the
    run branch, then the session dies before any story finishes."""
    _init(repo, stories)
    assert _plan(repo, stories, plan=True) == "r1"
    assert _resume(repo) == ("START planned run", "2026-10-10-1")
    _git(repo, "checkout", "-q", "r1")
    _ledger_set(repo, status="running"); assert _commit(repo, "chore(autopilot): start") == "r1"
    _git(repo, "checkout", "-qb", RUN)
    _git(repo, "checkout", "-q", "r1")


def test_interrupted_planned_run_continues_while_its_branch_exists(tmp_path):
    _start_planned_and_die(tmp_path, ["A", "B"])
    assert _resume(tmp_path) == ("continue", "2026-10-10-1")


def test_interrupted_run_whose_branch_the_user_deleted_is_not_continued_and_abort_closes_it(tmp_path):
    """The user threw the interrupted run away on purpose (branch deleted, no origin). resume must not
    continue or restart it; the documented `abort` (run_branch, else base_branch) closes it there,
    never on main, and resume then has nothing."""
    _start_planned_and_die(tmp_path, ["A", "B"])
    _git(tmp_path, "branch", "-qD", RUN)
    assert _resume(tmp_path) == ("gone", "2026-10-10-1")   # reported and stopped
    src, led = _kept(tmp_path)["2026-10-10-1"]
    assert (src, led["status"]) == ("r1", "running")
    target = RUN if _ok(tmp_path, "show-ref", "--verify", "--quiet", f"refs/heads/{RUN}") else led["base_branch"]
    _git(tmp_path, "checkout", "-q", target)
    _ledger_set(tmp_path, status="aborted"); assert _commit(tmp_path, "chore(autopilot): abort") == "r1"
    assert _resume(tmp_path) == ("nothing",)


def test_interrupted_run_branch_only_on_origin_is_refused_not_restarted(tmp_path):
    repo = tmp_path / "w"
    _start_planned_and_die(repo, ["A"])
    _with_origin(tmp_path, repo)
    _git(repo, "push", "-q", "origin", RUN)
    _git(repo, "branch", "-qD", RUN)
    assert _resume(repo) == ("refuse", "2026-10-10-1", f"refs/remotes/origin/{RUN}")


def test_gone_running_run_does_not_silently_start_an_older_planned_run(tmp_path):
    """Y was planned (--plan) first, X later; resume started X (the newest), which was interrupted and
    whose branch the user then deleted. The user runs resume expecting X. The running bullet says X
    is gone, then makes the choice again without it: the only candidate left is Y, 'Only one of the
    two -> that rule', and rule 1 starts Y's whole queue unattended in the same invocation. The
    choice's own principle (a preflight ledger must never be started silently instead of what the
    user came for) says this should ask or stop."""
    _init(tmp_path, ["A", "B"])
    _git(tmp_path, "checkout", "-qb", "r1")
    _write(tmp_path, ".archflow/autopilot/2026-10-09-1.yaml",
           {"run_id": "2026-10-09-1", "status": "preflight", "base_branch": "r1",
            "run_branch": "r1-autopilot-y", "release": "r1",
            "queue": [{"id": "B", "state": "pending"}]})
    _commit(tmp_path, "chore(autopilot): plan Y")
    _write(tmp_path, LED, {"run_id": "2026-10-10-1", "status": "running", "base_branch": "r1",
                           "run_branch": RUN, "release": "r1",
                           "queue": [{"id": "A", "state": "pending"}]})
    _commit(tmp_path, "chore(autopilot): start X")               # X started; its branch was cut,
    # interrupted, and then deleted by the user: no refs/heads/RUN, no origin.
    assert _resume(tmp_path)[0] != "START planned run"


# ---- several runs: parked stories come from the current checkout; other run branches are named --

ID1, ID2 = "2026-10-08-1", "2026-10-09-1"
RUN2 = "r1-overnight"


def _two_finished_runs(repo):
    """Run 1 parks B on r1-autopilot, run 2 parks D on r1-overnight; both finished, neither merged,
    the user back on base_branch r1."""
    _init(repo, ["A", "B", "C", "D"])
    _plan(repo, ["A", "B"], run_id=ID1)
    _step3_and_run(repo, {"A": "done", "B": "parked"}, run_id=ID1)
    _plan(repo, ["C", "D"], run_id=ID2, run=RUN2)
    _step3_and_run(repo, {"C": "done", "D": "parked"}, run_id=ID2, run=RUN2)


def _merge_taking(repo, ours_from):
    """Merge `ours_from` into the checked-out WIP branch; on a conflict take its release file and its
    copy of any ledger (rule 2), and nothing else may conflict."""
    if _git(repo, "merge", "--no-edit", ours_from, check=False).returncode:
        for path in _git(repo, "diff", "--name-only", "--diff-filter=U").split():
            assert path == REL or path.startswith(".archflow/autopilot/"), path
            _git(repo, "checkout", ours_from, "--", path); _git(repo, "add", path)
        _git(repo, "commit", "-qm", f"merge {ours_from}")


def test_pm_probe_two_finished_runs_merged_on_base_both_parked_stories_are_asked(tmp_path):
    """pm-reviewer's two-runs probe (I-25), current-branch form. Two finished runs merged onto r1
    each left a parked story in r1's release file. Every resume on r1 asks both, a waiver of D is
    recorded on r1 itself and never hides B, and status counts the same two."""
    repo = tmp_path
    _init(repo, ["A", "B", "C", "D"])
    _git(repo, "checkout", "-qb", "r1")
    _write(repo, REL, {"stories": {
        "A": {"status": "done"}, "B": {"status": "parked", "parked": {"question": "B?", "blocks_release": True}},
        "C": {"status": "done"}, "D": {"status": "parked", "parked": {"question": "D?", "blocks_release": True}}}})
    for rid, q in [(ID1, [{"id": "A", "state": "done"}, {"id": "B", "state": "parked"}]),
                   (ID2, [{"id": "C", "state": "done"}, {"id": "D", "state": "parked"}])]:
        _write(repo, f".archflow/autopilot/{rid}.yaml", {"run_id": rid, "status": "finished",
               "base_branch": "r1", "run_branch": "r1", "release": "r1", "queue": q})
    _commit(repo, "two finished runs merged onto r1")
    for n in range(3):                                            # three resumes, D waived each time
        assert _resume(repo) == ("follow-on", ["B", "D"]), f"resume #{n + 1}"
        assert _waive(repo, "D") == "r1"
        assert _pointers(repo) == []                              # both run_branches are r1, the current one
    status_lists = [s for s, v in _read(repo, REL)["stories"].items() if v["status"] == "parked"]
    assert status_lists == _parked_here(repo) == ["B", "D"]
    assert _read(repo, REL)["stories"]["D"]["parked"]["blocks_release"] is False
    assert _read(repo, REL)["stories"]["B"]["parked"]["blocks_release"] is True
    # both answered: one follow-on over both, built on r1 directly (it is these ledgers' run_branch)
    branch, new, stories, resumes = _follow_on(repo, ["B", "D"], "2026-10-11-1")
    assert (branch, new, stories, resumes) == ("r1", False, ["B", "D"], ID2)


def test_two_runs_park_b_and_d_each_run_branch_asks_its_own_and_points_at_the_other(tmp_path):
    """pm-reviewer's I-25 probe, current-branch form: two runs park B (on R1) and D (on R2). On R1
    resume asks B and points at R2; on R2 it asks D and points at R1; on base it asks nothing and
    points at both. Waiving one never hides the other, and nothing is lost."""
    repo = tmp_path
    _two_finished_runs(repo)
    ledgers_before = {b: _git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/")
                      for b in ("r1", RUN, RUN2)}
    assert _resume(repo) == ("nothing",)                          # r1's own release file has no park
    assert _pointers(repo) == [(ID1, RUN), (ID2, RUN2)]
    _git(repo, "checkout", "-q", RUN)
    assert _resume(repo) == ("follow-on", ["B"]) and _pointers(repo) == [(ID2, RUN2)]
    _git(repo, "checkout", "-q", RUN2)
    assert _resume(repo) == ("follow-on", ["D"]) and _pointers(repo) == [(ID1, RUN)]
    # nothing answered, D waived: recorded on the current branch (R2), no ledger written
    assert _waive(repo, "D") == RUN2
    assert {b: _git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/")
            for b in ("r1", RUN, RUN2)} == ledgers_before
    assert _resume(repo) == ("follow-on", ["D"]), "a waived story stays parked and is asked again"
    assert _read(repo, REL)["stories"]["D"]["parked"]["blocks_release"] is False
    _git(repo, "checkout", "-q", RUN)
    assert _resume(repo) == ("follow-on", ["B"]) and _pointers(repo) == [(ID2, RUN2)], \
        "waiving D must not hide B, nor the pointer to D's branch"
    assert _read(repo, REL)["stories"]["B"]["parked"]["blocks_release"] is True
    # B's follow-on: on R1, source run 1
    assert _follow_on(repo, ["B"], "2026-10-11-1") == (RUN, False, ["B"], ID1)
    _git(repo, "checkout", "-q", RUN2)
    assert _follow_on(repo, ["D"], "2026-10-11-1") == (RUN2, False, ["D"], ID2)
    assert _git(repo, "log", "--format=%s", "main").split("\n")[0] == "init"


def test_follow_on_on_one_run_branch_leaves_the_other_runs_park_where_it_was(tmp_path):
    """Build D's follow-on on R2 end to end; B on R1 is untouched and still asked there, the source
    ledgers stay finished records, and no branch other than R2 is written."""
    repo = tmp_path
    _two_finished_runs(repo)
    new_id = "2026-10-11-1"
    kept = _kept(repo)
    r1_tip, run_tip = _git(repo, "rev-parse", "r1"), _git(repo, "rev-parse", RUN)
    _git(repo, "checkout", "-q", RUN2)
    assert _follow_on(repo, ["D"], new_id) == (RUN2, False, ["D"], ID2)
    child = f".archflow/autopilot/{new_id}.yaml"
    _write(repo, child, {"run_id": new_id, "status": "running", "resumes": ID2,
                         "base_branch": "r1", "run_branch": RUN2, "release": "r1",
                         "queue": [{"id": "D", "state": "pending", "branch": "t/D"}]})
    d = _read(repo, REL); d["stories"]["D"] = {"status": "in_progress"}; _write(repo, REL, d)
    assert _commit(repo, "chore(autopilot): plan follow-on") == RUN2
    assert _resume(repo) == ("continue", new_id)                  # interrupted here -> rule 1
    _git(repo, "checkout", "-q", "t/D")
    _merge_taking(repo, RUN2)
    assert _read(repo, REL)["stories"]["D"]["status"] == "in_progress"
    d = _read(repo, REL); d["stories"]["D"] = {"status": "review"}; _write(repo, REL, d)
    _commit(repo, "D review")
    _git(repo, "checkout", "-q", RUN2); _git(repo, "merge", "-q", "--no-edit", "t/D")
    d = _read(repo, REL); d["stories"]["D"] = {"status": "done"}; _write(repo, REL, d)
    c = _read(repo, child); c["queue"][0]["state"] = "done"; c["status"] = "finished"; _write(repo, child, c)
    assert _commit(repo, "chore(autopilot): finish") == RUN2
    for rid in (ID1, ID2):                                        # sources stay finished records
        assert yaml.safe_load(_git(repo, "show", f"{kept[rid][0]}:.archflow/autopilot/{rid}.yaml")) == kept[rid][1]
    assert (_git(repo, "rev-parse", "r1"), _git(repo, "rev-parse", RUN)) == (r1_tip, run_tip)
    assert _resume(repo) == ("nothing",)                          # D is done on R2
    _git(repo, "checkout", "-q", RUN)
    assert _resume(repo) == ("follow-on", ["B"]), "B was never touched: still asked on R1"
    assert _git(repo, "log", "--format=%s", "main").split("\n")[0] == "init"


def test_run_merged_into_base_and_deleted_gets_a_new_named_branch_from_base(tmp_path):
    """The source run branch was merged into base_branch and deleted, so r1 has the park and the run's
    work. r1 is no ledger's run_branch: the follow-on cuts {base_branch}-autopilot-{run-id} from r1,
    and the newest run that parked B is its source."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    _git(repo, "merge", "-q", "--no-ff", "--no-edit", RUN); _git(repo, "branch", "-qD", RUN)
    assert _resume(repo) == ("follow-on", ["B"])
    assert _pointers(repo) == []                                  # the run branch is gone
    assert _follow_on(repo, ["B"], "2026-10-11-1") == (
        "r1-autopilot-2026-10-11-1", True, ["B"], "2026-10-10-1")
    assert (repo / "A.txt").exists(), "base_branch already holds the source run's work"


def test_i27_run_merged_into_main_its_parked_story_is_asked_on_main_and_never_written_on_main(tmp_path):
    """The run branch went into main and was deleted. On r1 nothing is parked and no run branch is
    left to name. On main B is asked: a waiver commits nothing there, and a follow-on cuts a new run
    branch from main and commits on that, never on main."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    _git(repo, "checkout", "-q", "main"); _git(repo, "merge", "-q", "--no-ff", "--no-edit", RUN)
    _git(repo, "branch", "-qD", RUN); _git(repo, "checkout", "-q", "r1")
    assert _resume(repo) == ("nothing",) and _pointers(repo) == []
    _git(repo, "checkout", "-q", "main")
    assert _resume(repo) == ("follow-on", ["B"])
    main_tip = _git(repo, "rev-parse", "main")
    assert _waive(repo, "B") is None                              # on main: commit nothing
    assert _git(repo, "rev-parse", "main") == main_tip and not _git(repo, "status", "--porcelain")
    branch, new, stories, resumes = _follow_on(repo, ["B"], "2026-10-11-1")
    assert (branch, new, stories, resumes) == ("r1-autopilot-2026-10-11-1", True, ["B"], "2026-10-10-1")
    _git(repo, "checkout", "-qb", branch)                         # cut from the current branch (main)
    d = _read(repo, REL); d["stories"]["B"] = {"status": "in_progress"}; _write(repo, REL, d)
    assert _commit(repo, "chore(autopilot): plan follow-on") == branch
    assert _git(repo, "rev-parse", "main") == main_tip


# ---- stories whose status differs between branches (I-29, I-30, I-32): only the current one counts --

def _in_progress_on_r1_then_parked_by_the_run(repo):
    _init(repo, ["A", "B"])
    _git(repo, "checkout", "-qb", "r1")
    d = _read(repo, REL); d["stories"]["B"] = {"status": "in_progress", "started": "by hand"}
    _write(repo, REL, d); _commit(repo, "B started on r1 before the run")
    _plan(repo, ["A", "B"])
    _step3_and_run(repo, {"A": "done", "B": "parked"})


def test_i29_story_queued_in_progress_and_parked_by_the_run_is_asked_on_the_run_branch(tmp_path):
    """Step 1 queues `in_progress` stories. One that was `in_progress` on r1 and that the run parks is
    `in_progress` on r1 and `parked` on the run branch. On r1 resume does not ask it and names the
    run branch; on the run branch it asks it."""
    repo = tmp_path
    _in_progress_on_r1_then_parked_by_the_run(repo)
    assert _resume(repo) == ("nothing",) and _pointers(repo) == [("2026-10-10-1", RUN)]
    _git(repo, "checkout", "-q", RUN)
    assert _resume(repo) == ("follow-on", ["B"])


def test_i30_leftover_subtask_branch_cut_before_the_park_does_not_hide_the_story(tmp_path):
    """A subtask branch left behind by a park mid-subtask holds an `in_progress` copy. It is never
    read: on the run branch B is asked, and the subtask branch is no run branch, so it is not named."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    ip = _git(repo, "log", "--format=%H", "--grep", "B in_progress", "t/B").split()[0]
    _git(repo, "branch", "t/B-1.1-sub", ip)
    _git(repo, "checkout", "-q", RUN)
    assert _resume(repo) == ("follow-on", ["B"]) and _pointers(repo) == []


def test_i32_base_commits_the_release_file_after_the_run_and_the_run_branch_still_asks_it(tmp_path):
    """I-32's shape: the I-29 setup plus a later release-file commit on r1 (a new story E). On r1,
    where B reads `in_progress`, resume does not ask B but names the run branch; on the run branch B
    is asked. No cross-branch comparison is made, so the later commit changes nothing."""
    repo = tmp_path
    _in_progress_on_r1_then_parked_by_the_run(repo)
    _git(repo, "checkout", "-q", "r1")
    d = _read(repo, REL); d["stories"]["E"] = {"status": "ready"}; _write(repo, REL, d)
    _commit(repo, "feat: add E to the release")                   # any later commit to the file on r1
    assert _resume(repo) == ("nothing",)
    assert _pointers(repo) == [("2026-10-10-1", RUN)]
    _git(repo, "checkout", "-q", RUN)
    assert _resume(repo) == ("follow-on", ["B"])
    assert _follow_on(repo, ["B"], "2026-10-11-1") == (RUN, False, ["B"], "2026-10-10-1")


# ---- picked-up stories, WIP branches, shared run branches, several unfinished runs -------------

def _follow_on_builds(repo, run_id, branch, source, story, new, outcome="done"):
    """Rule 2 'Some answered', end to end: check out (or cut) the run branch, write the follow-on
    ledger and the release file in one commit, build the story, finish."""
    _git(repo, "checkout", "-qb" if new else "-q", branch)
    child = f".archflow/autopilot/{run_id}.yaml"
    _write(repo, child, {"run_id": run_id, "status": "running", "resumes": source, "base_branch": "r1",
                         "run_branch": branch, "release": "r1",
                         "queue": [{"id": story, "state": "pending", "branch": f"t/{story}"}]})
    d = _read(repo, REL); d["stories"][story] = {"status": "in_progress"}; _write(repo, REL, d)
    assert _commit(repo, f"chore(autopilot): plan {run_id}") == branch
    d = _read(repo, REL)
    d["stories"][story] = ({"status": "done"} if outcome == "done"
                           else {"status": "parked", "parked": {"question": "again?", "blocks_release": True}})
    _write(repo, REL, d)
    c = _read(repo, child); c["queue"][0]["state"] = outcome; c["status"] = "finished"; _write(repo, child, c)
    assert _commit(repo, f"chore(autopilot): finish {run_id}") == branch


def test_a_story_picked_up_by_a_follow_on_elsewhere_is_not_asked_again_and_the_pointer_goes(tmp_path):
    """I-34, I-42: the run is merged into main (its branch kept). On main B is answered and a follow-on
    on a new branch builds it. Back on main and on the old run branch, B still reads `parked`, but it
    was picked up: it is not asked, and no pointer names the old run branch any more."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    _git(repo, "checkout", "-q", "main"); _git(repo, "merge", "-q", "--no-ff", "--no-edit", RUN)
    assert _resume(repo) == ("follow-on", ["B"])
    new_id = "2026-10-11-1"
    branch, new, _, source = _follow_on(repo, ["B"], new_id)
    assert (branch, new, source) == ("r1-autopilot-2026-10-11-1", True, "2026-10-10-1")
    _follow_on_builds(repo, new_id, branch, source, "B", new)
    for where in ("main", RUN, "r1"):
        _git(repo, "checkout", "-q", where)
        assert _resume(repo) == ("nothing",), where
        assert _pointers(repo) == [], where
    _git(repo, "checkout", "-q", "main")
    assert _picked_up(repo) == [("B", new_id, branch)]


def test_a_story_parked_again_by_its_follow_on_is_asked_on_that_follow_ons_branch(tmp_path):
    """The follow-on picked B up and parked it again: B is asked on the follow-on's branch, and from
    main the pointer names that branch."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    _git(repo, "checkout", "-q", "main"); _git(repo, "merge", "-q", "--no-ff", "--no-edit", RUN)
    branch = "r1-autopilot-2026-10-11-1"
    _follow_on_builds(repo, "2026-10-11-1", branch, "2026-10-10-1", "B", True, outcome="parked")
    assert _resume(repo) == ("follow-on", ["B"])
    _git(repo, "checkout", "-q", "main")
    assert _resume(repo) == ("nothing",) and _pointers(repo) == [("2026-10-11-1", branch)]


def test_resume_on_a_wip_branch_writes_nothing_and_names_the_run_branch(tmp_path):
    """I-35: the report names B's WIP branch; resume there must not cut a follow-on from it."""
    repo = tmp_path
    _replay(repo, {"A": "parked", "B": "done"})
    _git(repo, "checkout", "-q", "t/A")
    tip = _git(repo, "rev-parse", "HEAD")
    assert _parked_here(repo) == ["A"]
    assert _resume(repo) == ("wip", "A", RUN)
    assert _git(repo, "rev-parse", "HEAD") == tip and not _git(repo, "status", "--porcelain")


def test_two_ledgers_on_one_run_branch_the_newest_is_the_source_and_the_pointer_is_one_line(tmp_path):
    """I-36: run 1 parks B and C on R; a follow-on on R builds C and parks B again. On R the source of
    the next follow-on is the newest ledger; from r1 R is named once, by its newest run."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked", "C": "parked"})
    new_id = "2026-10-11-1"
    _follow_on_builds(repo, new_id, RUN, "2026-10-10-1", "C", False)
    d = _read(repo, REL)
    assert d["stories"]["B"]["status"] == "parked" and d["stories"]["C"]["status"] == "done"
    c = _read(repo, f".archflow/autopilot/{new_id}.yaml")
    c["queue"].append({"id": "B", "state": "parked", "branch": "t/B"})
    _write(repo, f".archflow/autopilot/{new_id}.yaml", c); _commit(repo, "follow-on parked B too")
    assert _resume(repo) == ("follow-on", ["B"])
    assert _source_run(repo, ["B"])["run_id"] == new_id
    _git(repo, "checkout", "-q", "r1")
    assert _pointers(repo) == [(new_id, RUN)]


def test_two_planned_runs_resume_starts_the_newest(tmp_path):
    """I-40: several `preflight` ledgers -> the newest is the current run, as for abort."""
    _init(tmp_path, ["A", "B"])
    _plan(tmp_path, ["A"], plan=True, run_id="2026-10-10-1", run="r1-autopilot-a")
    _plan(tmp_path, ["B"], plan=True, run_id="2026-10-10-2", run="r1-autopilot-b")
    assert _resume(tmp_path) == ("START planned run", "2026-10-10-2")
