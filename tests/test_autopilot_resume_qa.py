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
    """Fix pass 8: `resumes` is a list of run ids (one follow-on can pick up several runs' parked
    stories); a single string stays valid. Each example element must match the items pattern."""
    field = yaml.safe_load(SCHEMA.read_text())["run"]["properties"]["resumes"]
    assert isinstance(field["example"], list) and field["example"]
    assert all(re.fullmatch(field["items"]["pattern"], rid) for rid in field["example"])
    assert field["items"]["pattern"] == field["pattern"]


def test_follow_on_run_from_two_sources_validates(tmp_path):
    """Fix pass 8 (I-26, I-25): the follow-on ledger is written `running` from the start, and its
    `resumes` lists every source run."""
    p1 = ledger("2026-01-01-1", "finished", [DONE, PARKED], finished_at="2026-01-01T02:00:00Z")
    p2 = ledger("2026-01-01-2", "aborted", [dict(PARKED, story_id="S1-03")],
                finished_at="2026-01-01T03:00:00Z")
    queued = {k: v for k, v in PARKED.items() if k != "park"}
    child = ledger("2026-01-02-1", "running", [dict(queued, order=1, state="pending"),
                                               dict(queued, story_id="S1-03", order=2, state="pending")],
                   resumes=["2026-01-01-1", "2026-01-01-2"])
    code, data = validate(project(tmp_path, [p1, p2, child]))
    assert code == 0, data["violations"]


def test_a_malformed_run_id_in_a_resumes_list_is_caught(tmp_path):
    child = ledger("2026-01-02-1", "running", [DONE], resumes=["2026-01-01-1", "last night"])
    code, data = validate(project(tmp_path, [child]))
    assert code == 1
    assert any("resumes[1]" in v["field"] for v in data["violations"])


def test_follow_on_ledger_is_written_running_before_any_story_work():
    """I-26: a follow-on written `preflight` that then enters Step 3's story loop skipped the
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


def test_parked_stories_of_another_release_are_not_read_or_edited():
    """Fix pass 8: parked stories now come from the active release file only, so other releases'
    parked stories are no longer named (that needed a ledger scan); they are still never edited."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "never reads or edits another release file" in rule
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


def test_a_story_resolved_on_another_copy_is_named_with_its_branch_not_asked():
    """Fix pass 8 (I-27): the re-read-and-drop step is gone (a new run branch cut from base_branch
    can hold a stale copy, which made "resolved since" false). The combine across every copy
    decides instead, and the message names the status and the branch it was found on."""
    rule = re.sub(r"\s+", " ", resume_rule())
    assert "drop from the answers" not in rule
    assert ("`backlog` < `spec_ready` < `design_ready` < `contract_ready` < `ready` < `parked` < "
            "`in_progress` < `review` < `done`") in rule
    assert "`{id} is {status} on {branch}, not asking it.`" in rule


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


STORY_RANK = {s: i for i, s in enumerate(
    ["backlog", "spec_ready", "design_ready", "contract_ready", "ready", "parked",
     "in_progress", "review", "done"])}


def _combined(repo):
    """Rule 2's combine as written (fix pass 9): every copy of the active release file (current
    checkout first, then every local branch). First drop each superseded copy: its branch's last
    commit to the file is an ancestor of another copy's branch whose own last commit differs (I-29,
    I-30); branches sharing a last commit hold one copy; two copies that would drop each other both
    stay. Then one copy per story: the most advanced status; on a tie, the branch that committed the
    file last, then the current checkout's (then scan order). Returns {story: (status, branch, story_dict)}."""
    current = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    branches = [current] + [b for b in _git(repo, "for-each-ref", "--format=%(refname:short)",
                                            "refs/heads").split() if b != current]
    copies = {}
    for b in branches:
        r = _git(repo, "show", f"{b}:{REL}", check=False)
        if r.returncode:
            continue
        sha, ct = _git(repo, "log", "-1", "--format=%H %ct", b, "--", REL).split()
        copies[b] = (sha, int(ct), yaml.safe_load(r.stdout).get("stories") or {})

    def drops(x, y):                                              # y supersedes x
        return copies[x][0] != copies[y][0] and _ok(repo, "merge-base", "--is-ancestor", copies[x][0], y)

    live = [b for b in copies if not any(drops(b, o) and not drops(o, b) for o in copies if o != b)]
    best = {}
    for b in live:
        _, ct, stories = copies[b]
        for s, story in stories.items():
            key = (STORY_RANK.get(story["status"], -1), ct, b == current)
            if s not in best or key > best[s][0]:
                best[s] = (key, story["status"], b, story)
    return {s: v[1:] for s, v in best.items()}


def _offered(repo):
    return [s for s, (status, _, _) in _combined(repo).items() if status == "parked"]


def _not_asked(repo):
    """Stories parked on some copy but further along on the kept one: `{id} is {status} on {branch}`."""
    parked_somewhere = set()
    for b in _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split():
        r = _git(repo, "show", f"{b}:{REL}", check=False)
        if not r.returncode:
            parked_somewhere |= {s for s, v in yaml.safe_load(r.stdout)["stories"].items()
                                 if v["status"] == "parked"}
    return {s: (st, b) for s, (st, b, _) in _combined(repo).items()
            if s in parked_somewhere and st != "parked"}


def _scan(repo):
    kept = _kept(repo)
    unfinished = [led["run_id"] for b, led in kept.values() if led["status"] in ("preflight", "running")]
    return unfinished, _offered(repo)            # ledgers never select parked stories


def _rid_key(rid):
    y, m, d, n = rid.split("-")
    return (y, m, d, int(n))


def _source_run(repo, story):
    """The newest kept ledger (date, then sequence) of the active release that parked the story."""
    cands = [led for b, led in _kept(repo).values() if led["release"] == "r1"
             and any(q["id"] == story and q["state"] == "parked" for q in led["queue"])]
    return max(cands, key=lambda l: _rid_key(l["run_id"])) if cands else None


def _local(repo, branch):
    return _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")


def _base_parked(repo, base, story):
    r = _git(repo, "show", f"{base}:{REL}", check=False)
    return not r.returncode and \
        (yaml.safe_load(r.stdout)["stories"].get(story) or {}).get("status") == "parked"


def _follow_on_groups(repo, answered, run_id):
    """Rule 2 'Some answered' (fix pass 9, I-31): group the answered stories by source run. A group
    builds on its source run_branch if still local, else on a new {base_branch}-autopilot-{run_id}
    cut from base_branch, and then only stories parked on base_branch's copy; the rest are named
    and left parked. Returns ([(run_branch, cut_new, stories, resumes)], [left parked]); with
    several groups the user picks one, and the others are asked again next resume."""
    groups, skipped = {}, []
    for s in answered:
        src = _source_run(repo, s)
        groups.setdefault(src["run_id"] if src else None, (src, []))[1].append(s)
    out = []
    for rid, (src, stories) in groups.items():
        if src and _local(repo, src["run_branch"]):
            out.append((src["run_branch"], False, stories, [rid]))
            continue
        base = src["base_branch"] if src else "r1"                # no source run: Step 2a's answer
        keep = [s for s in stories if _base_parked(repo, base, s)]
        skipped += [s for s in stories if s not in keep]
        if keep:
            out.append((f"{base}-autopilot-{run_id}", True, keep, [rid] if rid else []))
    return out, skipped


def _waive(repo, story):
    """Rule 2's waiver: the source run's run_branch, else its base_branch, never main; re-read the
    release file there; record only if still parked. Returns the branch committed on, or None."""
    src = _source_run(repo, story)
    target = src["run_branch"] if _local(repo, src["run_branch"]) else src["base_branch"]
    assert target != "main"
    _git(repo, "checkout", "-q", target)
    d = _read(repo, REL)
    if d["stories"][story]["status"] != "parked":
        return None
    if d["stories"][story]["parked"].get("blocks_release") is False:
        return target                                             # already waived: nothing to commit
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
    """What `/archflow:autopilot resume` decides, per the choice and rules 1-3 as written."""
    kept = _kept(repo)
    _, parked = _scan(repo)
    running = [led for b, led in kept.values() if led["status"] == "running"]
    preflight = [led for b, led in kept.values() if led["status"] == "preflight"]
    if running:
        led = running[0]
        if _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{led['run_branch']}"):
            return ("continue", led["run_id"])
        hit = _guard_hit(repo, led["run_branch"])                # not local: same checks as the guard
        if hit:
            return ("refuse", led["run_id"], hit)
        # gone everywhere: never continued, and nothing else is chosen in this invocation (I-24):
        # the user closes it with abort, then runs resume again
        return ("gone", led["run_id"])
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


def _ledger_set(repo, led=LED, **kw):
    d = _read(repo, led); d.update(kw); _write(repo, led, d)


def _plan(repo, stories, plan=False, run_id="2026-10-10-1", run=RUN):
    """Step 2c as written in ca3ecdb. Returns the branch the ledger was committed on."""
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
        # Rule 1 (I-23 fix): `running`, committed alone on base_branch, before Step 3 cuts the run branch.
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
    # one source run whose run branch still exists -> build on it (fix pass 8 branch rule)
    assert _follow_on_groups(repo, ["B"], "2026-10-11-1") == ([(RUN, False, ["B"], ["2026-10-10-1"])], [])
    _git(repo, "checkout", "-q", RUN)                             # first, before writing anything
    assert _read(repo, REL)["stories"]["B"]["status"] == "parked"
    child = ".archflow/autopilot/2026-10-11-1.yaml"
    # I-26: written `running` from the start, `resumes` a list; no hand-set `running` afterwards
    _write(repo, child, {"run_id": "2026-10-11-1", "status": "running", "resumes": ["2026-10-10-1"],
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
    assert _resume(repo) == ("gone", "2026-10-10-1")       # reported and stopped, never restarted (I-24)


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


# ---- fix pass 6 (b220c36): rule 1's `running` bullet when the run branch is missing --------------

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
    assert _resume(tmp_path) == ("gone", "2026-10-10-1")   # reported and stopped (I-24)
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


# ---- fix pass 8: parked stories come from the release file, across every copy (I-25..I-27) ------

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
    """pm-reviewer's two_runs_probe.py as a test (I-25). Two finished runs on r1 each left a parked
    story. The old rule asked only the newest run's (D) and, once D was waived, never reached B,
    while status listed both. Now every resume asks both, and status counts the same two."""
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
        _git(repo, "checkout", "-q", "r1")
    status_lists = [s for s, v in _read(repo, REL)["stories"].items() if v["status"] == "parked"]
    assert status_lists == _offered(repo) == ["B", "D"]
    assert _combined(repo)["D"][2]["parked"]["blocks_release"] is False
    assert _combined(repo)["B"][2]["parked"]["blocks_release"] is True


def test_two_runs_park_b_and_d_resume_asks_both_and_a_waiver_hides_neither(tmp_path):
    repo = tmp_path
    _two_finished_runs(repo)
    assert _scan(repo) == ([], ["B", "D"])
    assert _resume(repo) == ("follow-on", ["B", "D"])
    assert [_source_run(repo, s)["run_id"] for s in ("B", "D")] == [ID1, ID2]
    # nothing answered, D waived: recorded on D's source run branch, no ledger written
    ledgers_before = {b: _git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/")
                      for b in ("r1", RUN, RUN2)}
    assert _waive(repo, "D") == RUN2
    _git(repo, "checkout", "-q", "r1")
    assert {b: _git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/")
            for b in ("r1", RUN, RUN2)} == ledgers_before
    assert _resume(repo) == ("follow-on", ["B", "D"]), "waiving D must not hide B (nor D)"
    assert _combined(repo)["D"][1] == RUN2 and _combined(repo)["D"][2]["parked"]["blocks_release"] is False
    assert _offered(repo) == ["B", "D"]                            # what status case 3 counts
    # answering only B: its one source run branch exists -> build on it
    assert _follow_on_groups(repo, ["B"], "2026-10-11-1") == ([(RUN, False, ["B"], [ID1])], [])
    assert _git(repo, "log", "--format=%s", "main").split("\n")[0] == "init"


def test_two_runs_follow_on_answering_both_builds_one_run_and_asks_the_other_again(tmp_path):
    """I-31: answers spanning two source runs whose branches exist -> the user picks one run; only its
    story is built, on its own run branch; the other stays parked and the next resume asks it."""
    repo = tmp_path
    _two_finished_runs(repo)
    new_id = "2026-10-11-1"
    groups, skipped = _follow_on_groups(repo, ["B", "D"], new_id)
    assert groups == [(RUN, False, ["B"], [ID1]), (RUN2, False, ["D"], [ID2])] and skipped == []
    kept = _kept(repo)
    # the user picks run 2: build D on RUN2, one commit before any story work, no ledgers copied
    _git(repo, "checkout", "-q", RUN2)
    child = f".archflow/autopilot/{new_id}.yaml"
    _write(repo, child, {"run_id": new_id, "status": "running", "resumes": [ID2],
                         "base_branch": "r1", "run_branch": RUN2, "release": "r1",
                         "queue": [{"id": "D", "state": "pending", "branch": "t/D"}]})
    d = _read(repo, REL); d["stories"]["D"] = {"status": "in_progress"}; _write(repo, REL, d)
    assert _commit(repo, "chore(autopilot): plan follow-on") == RUN2
    assert _resume(repo) == ("continue", new_id)                  # I-26: interrupted here -> rule 1
    _git(repo, "checkout", "-q", "t/D")
    _merge_taking(repo, RUN2)
    assert _read(repo, REL)["stories"]["D"]["status"] == "in_progress"
    d = _read(repo, REL); d["stories"]["D"] = {"status": "review"}; _write(repo, REL, d)
    _commit(repo, "D review")
    _git(repo, "checkout", "-q", RUN2); _git(repo, "merge", "-q", "--no-edit", "t/D")
    d = _read(repo, REL); d["stories"]["D"] = {"status": "done"}; _write(repo, REL, d)
    c = _read(repo, child); c["queue"][0]["state"] = "done"; c["status"] = "finished"; _write(repo, child, c)
    assert _commit(repo, "chore(autopilot): finish") == RUN2
    assert not _ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/r1-autopilot-{new_id}")
    for rid in (ID1, ID2):                                        # sources stay finished records
        assert yaml.safe_load(_git(repo, "show", f"{kept[rid][0]}:.archflow/autopilot/{rid}.yaml")) == kept[rid][1]
    assert _read(repo, f".archflow/autopilot/{ID2}.yaml")["status"] == "finished"
    _git(repo, "checkout", "-q", "r1")
    assert _resume(repo) == ("follow-on", ["B"]), "B's answer was not recorded: asked again"
    assert _combined(repo)["D"][:2] == ("done", RUN2) and _not_asked(repo) == {}   # no copy parks D now
    assert _follow_on_groups(repo, ["B"], "2026-10-12-1") == ([(RUN, False, ["B"], [ID1])], [])
    assert _git(repo, "log", "--format=%s", "main").split("\n")[0] == "init"


def test_run_merged_into_base_and_deleted_gets_a_new_named_branch_from_base(tmp_path):
    """I-31: the source run branch was merged into base_branch and deleted, so r1 has the park and the
    run's work: the follow-on cuts {base_branch}-autopilot-{run-id} from r1 for that story only."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    _git(repo, "merge", "-q", "--no-ff", "--no-edit", RUN); _git(repo, "branch", "-qD", RUN)
    assert _resume(repo) == ("follow-on", ["B"])
    assert _follow_on_groups(repo, ["B"], "2026-10-11-1") == (
        [("r1-autopilot-2026-10-11-1", True, ["B"], ["2026-10-10-1"])], [])
    assert (repo / "A.txt").exists(), "base_branch already holds the source run's work"


def test_i27_run_merged_into_main_its_parked_story_is_still_offered_and_never_written_on_main(tmp_path):
    """I-27: the run branch went into main (not base_branch) and was deleted. base_branch's copy is
    stale; the old rule re-read it and said "resolved since". The combine finds B parked on main."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    _git(repo, "checkout", "-q", "main"); _git(repo, "merge", "-q", "--no-ff", "--no-edit", RUN)
    _git(repo, "branch", "-qD", RUN); _git(repo, "checkout", "-q", "r1")
    assert _resume(repo) == ("follow-on", ["B"])
    assert _combined(repo)["B"][:2] == ("parked", "main")
    main_tip, r1_tip = _git(repo, "rev-parse", "main"), _git(repo, "rev-parse", "r1")
    assert _waive(repo, "B") is None                              # not parked on r1: commit nothing,
    assert (_git(repo, "rev-parse", "main"), _git(repo, "rev-parse", "r1")) == (main_tip, r1_tip)
    _git(repo, "checkout", "-q", "r1")                            # and say it is parked on main
    # I-31: its run branch is gone and r1 lacks the park -> named and left parked, never built on r1
    assert _follow_on_groups(repo, ["B"], "2026-10-11-1") == ([], ["B"])



# ---- QA re-run after fix pass 8: stale lower-ranked copies outrank a later `parked` (I-29, I-30) --

def test_i29_story_queued_in_progress_and_parked_by_the_run_is_still_asked(tmp_path):
    """Step 1 queues `in_progress` stories. One that was `in_progress` on base_branch when the run
    started and that the run parks is `parked` on the run branch but still `in_progress` on r1, a copy
    from before the park (an ancestor of it). `parked` < `in_progress`, so resume says
    "B is in_progress on r1, not asking it." and "Nothing to resume.", and status case 3 does not
    list it, while the run's report said PARKED B / Next: resume."""
    repo = tmp_path
    _init(repo, ["A", "B"])
    _git(repo, "checkout", "-qb", "r1")
    d = _read(repo, REL); d["stories"]["B"] = {"status": "in_progress", "started": "by hand"}
    _write(repo, REL, d); _commit(repo, "B started on r1 before the run")
    _plan(repo, ["A", "B"])
    _step3_and_run(repo, {"A": "done", "B": "parked"})
    assert _resume(repo) == ("follow-on", ["B"]), (_resume(repo), _not_asked(repo))


def test_i30_leftover_subtask_branch_cut_before_the_park_does_not_hide_the_story(tmp_path):
    """workflow.md cuts subtask branches off the task branch after `in_progress` is committed and
    deletes them only after merging. A story parked mid-subtask can leave one behind; its copy
    (`in_progress`, an ancestor of the task branch's `parked` commit) outranks the park."""
    repo = tmp_path
    _replay(repo, {"A": "done", "B": "parked"})
    ip = _git(repo, "log", "--format=%H", "--grep", "B in_progress", "t/B").split()[0]
    _git(repo, "branch", "t/B-1.1-sub", ip)
    assert _resume(repo) == ("follow-on", ["B"]), (_resume(repo), _not_asked(repo))


# ---- QA re-run after fix pass 9: whole-file supersession misses a stale story on a moved copy (I-32) --

@pytest.mark.xfail(strict=True, reason="I-32: one later release-file commit on base_branch revives I-29")
def test_i32_story_queued_in_progress_parked_then_base_commits_the_release_file_is_still_asked(tmp_path):
    """The I-29 shape plus one ordinary step: back on r1 after the run, the user records an issue or
    adds a story, committing the release file. r1's last commit to it is no longer an ancestor of the
    run branch, so r1's copy is not superseded, and its B, unchanged since before the run and still
    `in_progress`, outranks the run's `parked`: "B is in_progress on r1, not asking it." again."""
    repo = tmp_path
    _init(repo, ["A", "B"])
    _git(repo, "checkout", "-qb", "r1")
    d = _read(repo, REL); d["stories"]["B"] = {"status": "in_progress", "started": "by hand"}
    _write(repo, REL, d); _commit(repo, "B started on r1 before the run")
    _plan(repo, ["A", "B"])
    _step3_and_run(repo, {"A": "done", "B": "parked"})
    _git(repo, "checkout", "-q", "r1")
    d = _read(repo, REL); d["stories"]["E"] = {"status": "ready"}; _write(repo, REL, d)
    _commit(repo, "feat: add E to the release")                   # any later commit to the file on r1
    assert _resume(repo) == ("follow-on", ["B"]), (_resume(repo), _not_asked(repo))
