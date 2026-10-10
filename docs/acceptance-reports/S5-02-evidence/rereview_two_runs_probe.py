"""S5-02 re-review probe: I-25's two-runs scenario under the "current branch only" rules.

Independent of the repo's replay model: the git plumbing and the resume rules below are written
from plugin/commands/autopilot.md (Subcommands: Ledgers, Parked stories, rule 2/3, Other run
branches; Step 1.3's queue; Step 2c/Step 3/Step 4's branch moves), not imported from
tests/test_autopilot_resume_qa.py. Real git, one temp repo.

Journey: run 1 parks B on r1-autopilot. The user stays where Step 4 left them (the run branch) and
starts run 2 there; Step 1 builds the queue from that checkout, Step 2c checks out base r1 and cuts
r1-overnight; run 2 parks D. Then resume is walked on each branch, D is waived three times, B is
answered, and the pointers are re-checked. A second section shows what plain /archflow:autopilot
queues when started from base r1 after run 1 (Step 1.3, unchanged by this story).

Usage: python3 rereview_two_runs_probe.py [--mutate-no-pointer]
"""
import subprocess, sys, tempfile, pathlib, yaml

MUTATE = "--mutate-no-pointer" in sys.argv
REL = ".archflow/releases/r1.yaml"
RANK = {"preflight": 0, "running": 1, "finished": 2, "aborted": 2}


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {a}: {r.stderr}")
    return r.stdout.strip()


def ok(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True).returncode == 0


def rd(repo, p):
    return yaml.safe_load((repo / p).read_text())


def wr(repo, p, d):
    (repo / p).parent.mkdir(parents=True, exist_ok=True)
    (repo / p).write_text(yaml.safe_dump(d, sort_keys=False))


def commit(repo, msg):
    git(repo, "add", "-A"); git(repo, "commit", "-qm", msg)
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") != "main", f"{msg} on main"


def cur(repo):
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD")


def set_story(repo, s, **v):
    d = rd(repo, REL); d["stories"][s] = v; wr(repo, REL, d)


# ---- the doc's rules, written from autopilot.md -------------------------------------------
def kept(repo):
    """Ledgers: current checkout first, then every local branch; one copy per run_id, most
    advanced status; tie -> copy on its own run_branch, else the current checkout's."""
    out = {}
    here = cur(repo)
    for b in [here] + [x for x in git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split() if x != here]:
        for p in git(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/").split():
            led = yaml.safe_load(git(repo, "show", f"{b}:{p}"))
            o = out.get(led["run_id"])
            if o is None or RANK[led["status"]] > RANK[o[1]["status"]] or (
                    RANK[led["status"]] == RANK[o[1]["status"]] and b == led["run_branch"] and o[0] != led["run_branch"]):
                out[led["run_id"]] = (b, led)
    return [l for _, l in out.values()]


def key(rid):
    y, m, d, n = rid.split("-"); return (y, m, d, int(n))


def live_follow_on(repo, l):
    return bool(l.get("resumes")) and l["status"] != "aborted" and ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{l['run_branch']}")


def parked_here(repo):
    """Parked stories: this checkout's release file only, minus those a live follow-on on another
    run branch queued."""
    rel = yaml.safe_load(git(repo, "show", f"HEAD:{REL}"))["stories"]
    leds = kept(repo)
    out = []
    for s, v in rel.items():
        if v["status"] != "parked":
            continue
        if any(live_follow_on(repo, l) and l["run_branch"] != cur(repo) and any(q["id"] == s for q in l["queue"]) for l in leds):
            continue
        out.append(s)
    return out


def pointers(repo):
    """Other run branches: kept finished/aborted ledger of the active release with a parked item
    no newer live follow-on queued; its run_branch exists locally and is not current."""
    if MUTATE:
        return []
    leds = kept(repo)
    by = {}
    for l in leds:
        if l["status"] not in ("finished", "aborted") or l["release"] != "r1":
            continue
        unpicked = [q for q in l["queue"] if q["state"] == "parked" and not any(
            live_follow_on(repo, n) and key(n["run_id"]) > key(l["run_id"]) and any(x["id"] == q["id"] for x in n["queue"])
            for n in leds)]
        if unpicked and l["run_branch"] != cur(repo) and ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{l['run_branch']}"):
            by.setdefault(l["run_branch"], []).append(l["run_id"])
    return sorted((max(v, key=key), b) for b, v in by.items())


def step1_queue(repo):
    rel = rd(repo, REL)["stories"]
    return [s for s, v in rel.items() if v["status"] in ("spec_ready", "design_ready", "contract_ready", "ready", "in_progress")]


# ---- a run, per Step 2c / 3 / 4 --------------------------------------------------------------
def run(repo, rid, run_branch, outcomes):
    git(repo, "checkout", "-q", "r1")                              # Step 2c: check out base_branch
    git(repo, "checkout", "-qb", run_branch)                       # cut the run branch, then ledger
    lp = f".archflow/autopilot/{rid}.yaml"
    wr(repo, lp, {"run_id": rid, "status": "preflight", "base_branch": "r1", "run_branch": run_branch,
                  "release": "r1", "queue": [{"id": s, "state": "pending", "branch": f"t/{s}"} for s in outcomes]})
    commit(repo, f"chore(autopilot): plan {rid}")
    l = rd(repo, lp); l["status"] = "running"; wr(repo, lp, l); commit(repo, "running")
    for s, o in outcomes.items():
        git(repo, "checkout", "-qb", f"t/{s}", run_branch)
        set_story(repo, s, status="in_progress"); commit(repo, f"{s} in_progress")
        (repo / f"{s}.txt").write_text(s)
        if o == "done":
            set_story(repo, s, status="review"); commit(repo, f"{s} review")
            git(repo, "checkout", "-q", run_branch); git(repo, "merge", "-q", "--no-edit", f"t/{s}")
            set_story(repo, s, status="done"); git(repo, "branch", "-qD", f"t/{s}")
        else:
            set_story(repo, s, status="parked", parked={"question": f"{s}?", "blocks_release": True, "branch": f"t/{s}"})
            commit(repo, f"wip: {s}")
            git(repo, "checkout", "-q", run_branch); git(repo, "checkout", f"t/{s}", "--", REL)
        l = rd(repo, lp)
        for q in l["queue"]:
            if q["id"] == s:
                q["state"] = o
        wr(repo, lp, l); commit(repo, f"{s} ledger")
    l = rd(repo, lp); l["status"] = "finished"; wr(repo, lp, l); commit(repo, f"chore(autopilot): finish {rid}")
    # Step 4 stops here: the user is left on the run branch


def show(repo, label):
    print(f"  [{label}] on {cur(repo)}: resume asks {parked_here(repo)}; points at {pointers(repo)}")


repo = pathlib.Path(tempfile.mkdtemp())
git(repo, "init", "-q", "-b", "main"); git(repo, "config", "user.email", "p@x"); git(repo, "config", "user.name", "p")
wr(repo, REL, {"stories": {s: {"status": "ready"} for s in "ABCD"}})
git(repo, "add", "-A"); git(repo, "commit", "-qm", "init"); git(repo, "checkout", "-qb", "r1")

print("== Section 1: I-25 two-runs scenario, current-branch rules")
run(repo, "2026-10-08-1", "r1-autopilot", {"A": "done", "B": "parked"})
print("after run 1, user on", cur(repo), "-> Step 1 queue for run 2 built here:", step1_queue(repo))
run(repo, "2026-10-09-1", "r1-overnight", {"C": "done", "D": "parked"})
fails = []
show(repo, "after run 2")
if parked_here(repo) != ["D"] or ("2026-10-08-1", "r1-autopilot") not in pointers(repo):
    fails.append("run-2 branch must ask D and point at run 1's branch")
for n in range(1, 4):
    d = rd(repo, REL); d["stories"]["D"]["parked"]["blocks_release"] = False; wr(repo, REL, d)
    if git(repo, "status", "--porcelain"):
        commit(repo, "waive D (rule 2: nothing answered, some waived)")
    show(repo, f"resume #{n}, D waived")
    if ("2026-10-08-1", "r1-autopilot") not in pointers(repo):
        fails.append(f"resume #{n}: B's branch not named")
git(repo, "checkout", "-q", "r1"); show(repo, "base")
git(repo, "checkout", "-q", "r1-autopilot"); show(repo, "run 1 branch")
if parked_here(repo) != ["B"]:
    fails.append("run-1 branch must ask B")
# B answered -> follow-on on r1-autopilot (it is a kept ledger's run_branch), builds B
fo = ".archflow/autopilot/2026-10-11-1.yaml"
wr(repo, fo, {"run_id": "2026-10-11-1", "status": "running", "resumes": "2026-10-08-1", "base_branch": "r1",
              "run_branch": "r1-autopilot", "release": "r1", "queue": [{"id": "B", "state": "pending", "branch": "t/B"}]})
set_story(repo, "B", status="in_progress"); commit(repo, "follow-on plan")
git(repo, "checkout", "-q", "t/B"); git(repo, "merge", "-q", "--no-edit", "-X", "theirs", "r1-autopilot")
set_story(repo, "B", status="review"); commit(repo, "B review")
git(repo, "checkout", "-q", "r1-autopilot"); git(repo, "merge", "-q", "--no-edit", "t/B")
set_story(repo, "B", status="done"); l = rd(repo, fo); l["queue"][0]["state"] = "done"; l["status"] = "finished"; wr(repo, fo, l)
commit(repo, "follow-on finish")
show(repo, "run 1 branch after B's follow-on")
git(repo, "checkout", "-q", "r1-overnight"); show(repo, "run 2 branch after B's follow-on")
if ("2026-10-08-1", "r1-autopilot") in pointers(repo):
    fails.append("stale pointer to run 1 after B was built")
print("main tip:", git(repo, "log", "-1", "--format=%s", "main"))
print("SECTION 1:", "PASS" if not fails else f"FAIL {fails}")

print("== Section 2: plain /archflow:autopilot started from base r1 after run 1 (Step 1.3)")
repo2 = pathlib.Path(tempfile.mkdtemp())
git(repo2, "init", "-q", "-b", "main"); git(repo2, "config", "user.email", "p@x"); git(repo2, "config", "user.name", "p")
wr(repo2, REL, {"stories": {s: {"status": "ready"} for s in "ABCD"}})
git(repo2, "add", "-A"); git(repo2, "commit", "-qm", "init"); git(repo2, "checkout", "-qb", "r1")
repo = repo2
run(repo, "2026-10-08-1", "r1-autopilot", {"A": "done", "B": "parked"})
git(repo, "checkout", "-q", "r1")
print("on r1: Step 1 queue =", step1_queue(repo), "; resume asks", parked_here(repo), "; points at", pointers(repo))
print("t/B (B's WIP) exists:", ok(repo, "show-ref", "--verify", "--quiet", "refs/heads/t/B"))
