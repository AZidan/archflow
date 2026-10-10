"""QA independent replay of autopilot resume as written after fix pass 11 (e96165e). Self-contained:
real git repos, the rules implemented from plugin/commands/autopilot.md text (picked-up skip,
newer-follow-on pointer suppression, one pointer line per branch, WIP-branch guard, newest-ledger
source / current run, abort's base_branch fallback). Nothing is imported from tests/ or from earlier
evidence scripts.

Run: python3 docs/qa-reports/S5-02-evidence/fp11_replay.py
"""
import os, subprocess, sys, tempfile, yaml

REL = ".archflow/releases/r1.yaml"
LRANK = {"preflight": 0, "running": 1, "finished": 2, "aborted": 2}
results = []
_t = [1700000000]


def g(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {a}: {r.stderr}")
    return r.stdout.strip() if check else r


def ok(repo, *a): return g(repo, *a, check=False).returncode == 0
def rd(repo, p): return yaml.safe_load(open(os.path.join(repo, p)))
def cur(repo): return g(repo, "rev-parse", "--abbrev-ref", "HEAD")
def local(repo, b): return ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{b}")


def wr(repo, p, d):
    os.makedirs(os.path.dirname(os.path.join(repo, p)), exist_ok=True)
    yaml.safe_dump(d, open(os.path.join(repo, p), "w"), sort_keys=False)


def commit(repo, msg, allow_main=False):
    _t[0] += 10
    env = dict(os.environ, GIT_AUTHOR_DATE=f"{_t[0]} +0000", GIT_COMMITTER_DATE=f"{_t[0]} +0000")
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", msg], check=True, env=env)
    b = cur(repo)
    if not allow_main:
        assert b != "main", f"{msg!r} committed on main"
    return b


def co(repo, b, new=False, start=None):
    g(repo, "checkout", "-q", *(["-b"] if new else []), b, *([start] if start else []))


def setstory(repo, s, status, **kw):
    d = rd(repo, REL); d["stories"][s] = {"status": status, **kw}; wr(repo, REL, d)


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   -> {detail}"))


def init(stories):
    repo = tempfile.mkdtemp()
    g(repo, "init", "-q", "-b", "main"); g(repo, "config", "user.email", "q@a"); g(repo, "config", "user.name", "qa")
    wr(repo, REL, {"stories": {s: {"status": "ready"} for s in stories}})
    commit(repo, "init", allow_main=True)
    return repo


def run(repo, rid, rb, outcomes, end="finished", base="r1", stop_after=None):
    """Step 2c + 3 + 4 as written. Step 4 'commit the ledger alone on the run branch, push, stop':
    the user is left ON THE RUN BRANCH. abort also checks out the run branch and stays there."""
    co(repo, base, new=not local(repo, base)); co(repo, rb, new=True)
    L = f".archflow/autopilot/{rid}.yaml"
    wr(repo, L, {"run_id": rid, "status": "running", "base_branch": base, "run_branch": rb, "release": "r1",
                 "decisions": [], "queue": [{"id": s, "state": "pending", "branch": f"t/{s}"} for s in outcomes]})
    commit(repo, f"plan {rid}")
    for i, (s, o) in enumerate(outcomes.items()):
        if stop_after is not None and i == stop_after:
            break
        co(repo, rb); co(repo, f"t/{s}", new=not local(repo, f"t/{s}"))
        setstory(repo, s, "in_progress"); commit(repo, f"{s} ip")
        open(os.path.join(repo, f"{s}.code"), "w").write(s); commit(repo, f"{s} code")
        if o == "done":
            co(repo, rb); g(repo, "merge", "-q", "--no-edit", f"t/{s}"); setstory(repo, s, "done")
            commit(repo, f"{s} done"); g(repo, "branch", "-qD", f"t/{s}")
        else:
            if o == "parked":
                setstory(repo, s, "parked", parked={"question": f"{s}?", "blocks_release": True, "branch": f"t/{s}"})
            else:
                setstory(repo, s, "review")
            commit(repo, f"{s} {o}"); co(repo, rb); g(repo, "checkout", f"t/{s}", "--", REL); commit(repo, "carry")
        d = rd(repo, L); [q.update(state=o) for q in d["queue"] if q["id"] == s]; wr(repo, L, d); commit(repo, "led")
    if end:
        d = rd(repo, L); d["status"] = end; wr(repo, L, d); commit(repo, f"{end} {rid}")
    assert cur(repo) == rb




def rid_key(r):
    y, m, d, n = r.split("-"); return (y, m, d, int(n))


def newest(ls): return max(ls, key=lambda l: rid_key(l["run_id"])) if ls else None


def kept(repo):
    """Ledger scan: current checkout + every local branch, one copy per run_id, most advanced status,
    tie -> copy on its own run_branch, else the current checkout's."""
    c = cur(repo); k = {}
    for b in [c] + [x for x in g(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split() if x != c]:
        for n in g(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/").split():
            led = yaml.safe_load(g(repo, "show", f"{b}:{n}"))
            key = (LRANK[led["status"]], b == led["run_branch"], b == c)
            if led["run_id"] not in k or key > k[led["run_id"]][0]:
                k[led["run_id"]] = (key, b, led)
    return {r: led for r, (_, b, led) in k.items()}


def release_here(repo):
    r = g(repo, "show", f"HEAD:{REL}", check=False)
    return yaml.safe_load(r.stdout)["stories"] if r.returncode == 0 else {}


def picked_up(repo):
    """'Drop any that a follow-on whose run_branch is not the current branch has in its queue[]'."""
    c, out = cur(repo), []
    for s, v in release_here(repo).items():
        if v["status"] != "parked": continue
        by = newest([l for l in kept(repo).values() if l.get("resumes") and l["run_branch"] != c
                     and any(q["id"] == s for q in l["queue"])])
        if by: out.append((s, by["run_id"], by["run_branch"]))
    return out


def parked_here(repo):
    p = {s for s, _, _ in picked_up(repo)}
    return [s for s, v in release_here(repo).items() if v["status"] == "parked" and s not in p]


def pointers(repo):
    """One line per local run_branch (not current) of a finished/aborted r1 ledger with a parked item
    that no NEWER follow-on has in its queue; names the newest such run on the branch."""
    c, ls = cur(repo), list(kept(repo).values())
    later = lambda led, s: any(l.get("resumes") and rid_key(l["run_id"]) > rid_key(led["run_id"])
                               and any(q["id"] == s for q in l["queue"]) for l in ls)
    by = {}
    for l in ls:
        if (l["status"] in ("finished", "aborted") and l["release"] == "r1"
                and any(q["state"] == "parked" and not later(l, q["id"]) for q in l["queue"])
                and local(repo, l["run_branch"]) and l["run_branch"] != c):
            by.setdefault(l["run_branch"], []).append(l)
    return sorted((newest(v)["run_id"], b) for b, v in by.items())


def wip(repo):
    """Rule 2 guard: current branch is a queue item's branch in a kept ledger, or a parked story's
    parked.branch -> (story, run_branch of the newest kept ledger that queued it)."""
    c, ls = cur(repo), list(kept(repo).values())
    hits = {q["id"] for l in ls for q in l["queue"] if q.get("branch") == c}
    hits |= {s for s, v in release_here(repo).items() if v["status"] == "parked"
             and (v.get("parked") or {}).get("branch") == c}
    for s in sorted(hits):
        l = newest([l for l in ls if any(q["id"] == s for q in l["queue"])])
        return s, (l["run_branch"] if l else None)
    return None


def current_run(repo):
    ls = list(kept(repo).values())
    return newest([l for l in ls if l["status"] == "running"]) or newest([l for l in ls if l["status"] == "preflight"])


def resume(repo):
    cr = current_run(repo); p = parked_here(repo)
    if cr and cr["status"] == "running":
        return ("continue", cr["run_id"]) if local(repo, cr["run_branch"]) else ("gone", cr["run_id"])
    if cr and p: return ("ask-which", cr["run_id"], p)
    if cr: return ("start", cr["run_id"])
    if p:
        w = wip(repo)
        if w: return ("wip",) + w
        return ("ask", p, pointers(repo))
    return ("pointers", pointers(repo)) if pointers(repo) else ("nothing",)


def source_run(repo, answered):
    ls, c = list(kept(repo).values()), cur(repo)
    return newest([l for l in ls if l["run_branch"] == c]) or newest(
        [l for l in ls if l["status"] in ("finished", "aborted") and l["release"] == "r1"
         and any(q["id"] in answered and q["state"] == "parked" for q in l["queue"])])


def follow_on(repo, answered, rid, outcome="done", end="finished"):
    src = source_run(repo, answered); c = cur(repo)
    if any(l["run_branch"] == c for l in kept(repo).values()):
        rb = c
    else:
        base = src["base_branch"] if src else "r1"               # else Step 2a's {base-branch}
        rb = f"{base}-autopilot-{rid}"; co(repo, rb, new=True)
    L = f".archflow/autopilot/{rid}.yaml"
    rel = rd(repo, REL)["stories"]
    wr(repo, L, {"run_id": rid, "status": "running", **({"resumes": src["run_id"]} if src else {}),
                 "base_branch": src["base_branch"] if src else "r1", "run_branch": rb, "release": "r1",
                 "decisions": (src or {}).get("decisions", []) + [f"answer {s}" for s in answered],
                 "queue": [{"id": s, "state": "pending", "branch": rel[s]["parked"].get("branch", f"t/{s}")}
                           for s in answered]})
    for s in answered: setstory(repo, s, "in_progress")
    commit(repo, f"resume: follow-on {rid}")
    if outcome is None:                                              # interrupted / aborted before story work
        if end:
            d = rd(repo, L); d["status"] = end; wr(repo, L, d); commit(repo, f"{end} {rid}")
        return rb, src and src["run_id"]
    for s in answered:
        w = f"t/{s}"
        if local(repo, w):
            co(repo, w)
            if g(repo, "merge", "-q", "--no-edit", rb, check=False).returncode:
                g(repo, "checkout", rb, "--", REL, ".archflow/autopilot/"); commit(repo, "merge run branch")
        else:
            co(repo, w, new=True, start=rb)
        if outcome == "done":
            setstory(repo, s, "review"); commit(repo, f"{s} review"); co(repo, rb)
            g(repo, "merge", "-q", "--no-edit", w); setstory(repo, s, "done"); commit(repo, f"{s} done")
        else:
            setstory(repo, s, "parked", parked={"question": f"{s} again?", "blocks_release": True, "branch": w})
            commit(repo, "repark"); co(repo, rb); g(repo, "checkout", w, "--", REL); commit(repo, "carry")
        d = rd(repo, L); [q.update(state=outcome) for q in d["queue"] if q["id"] == s]; wr(repo, L, d); commit(repo, "led")
    d = rd(repo, L); d["status"] = end; wr(repo, L, d); commit(repo, f"{end} {rid}")
    return rb, src and src["run_id"]


def abort(repo):
    """Closes the current run: run_branch if local, else base_branch, never main; neither -> nothing."""
    cr = current_run(repo)
    if not cr: return ("nothing-to-abort",)
    for b in (cr["run_branch"], cr["base_branch"]):
        if b != "main" and local(repo, b):
            co(repo, b); L = f".archflow/autopilot/{cr['run_id']}.yaml"
            led = dict(cr, status="aborted"); wr(repo, L, led); commit(repo, f"abort {cr['run_id']}")
            return ("aborted", cr["run_id"], b)
    return ("told-user", cr["run_id"])


RUN = "r1-autopilot"

# ---- (1) AC1/AC2 and I-42: the realistic end of a run --------------------------------------------
r = init(list("ABC")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked", "C": "failed"})
check("1a Step 4 leaves the user on the run branch; 'Next: resume' asks B there",
      cur(r) == RUN and resume(r) == ("ask", ["B"], []), resume(r))
co(r, "r1")
check("1b base: nothing parked, one pointer to the run branch", resume(r) == ("pointers", [("2026-10-10-1", RUN)]), resume(r))
co(r, RUN); rb, src = follow_on(r, ["B"], "2026-10-11-1")
check("1c follow-on on the run branch, resumes is the single string r1", (rb, src) == (RUN, "2026-10-10-1")
      and kept(r)["2026-10-11-1"]["resumes"] == "2026-10-10-1", (rb, src))
check("1d B done, C untouched, source ledger still finished", rd(r, REL)["stories"]["B"]["status"] == "done"
      and rd(r, REL)["stories"]["C"]["status"] == "review" and kept(r)["2026-10-10-1"]["status"] == "finished")
check("1e run branch afterwards: nothing", resume(r) == ("nothing",), resume(r))
co(r, "r1")
check("1f I-42: base no longer points at the run branch once a newer follow-on queued B", resume(r) == ("nothing",), resume(r))
check("1g main untouched", g(r, "log", "--format=%s", "main") == "init")

# ---- (2) regressions ----------------------------------------------------------------------------
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "done"})
check("2a no parked stories -> nothing (run branch)", resume(r) == ("nothing",), resume(r))
co(r, "r1"); check("2b no parked stories -> nothing (base)", resume(r) == ("nothing",), resume(r))
r = init(list("ABC")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked", "C": "done"}, end="aborted", stop_after=2)
check("2c aborted run: only parked B asked", resume(r) == ("ask", ["B"], []), resume(r))
follow_on(r, ["B"], "2026-10-11-1")
check("2d aborted ledger stays aborted, pending C never queued", kept(r)["2026-10-10-1"]["status"] == "aborted"
      and [q["id"] for q in kept(r)["2026-10-11-1"]["queue"]] == ["B"] and rd(r, REL)["stories"]["C"]["status"] == "ready")
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "done"}, end="aborted", stop_after=1)
check("2e aborted run without parked stories -> nothing", resume(r) == ("nothing",), resume(r))
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "parked", "B": "done"})
follow_on(r, ["A"], "2026-10-11-1", outcome=None, end=None)
check("2f interrupted follow-on is the current running run (rule 1)", resume(r) == ("continue", "2026-10-11-1"), resume(r))
co(r, "r1"); g(r, "branch", "-qD", RUN)
# Both ledgers on RUN are gone with it; t/A (cut while r1 was running) still holds r1's `running` copy.
check("2g gone running run -> 'gone', nothing else chosen", resume(r) == ("gone", "2026-10-10-1"), resume(r))
a = abort(r)
check("2h I-39: abort of a run whose branch is gone commits on base_branch r1, never main",
      a == ("aborted", "2026-10-10-1", "r1") and g(r, "log", "--format=%s", "main") == "init", a)
check("2i the aborted copy wins the scan: the run stays aborted, resume has nothing",
      kept(r)["2026-10-10-1"]["status"] == "aborted" and resume(r) == ("nothing",), resume(r))
# two planned runs and a planned + running mix
r = init(list("AB")); co(r, "r1", new=True)
for rid, rb in (("2026-10-10-1", "r1-autopilot"), ("2026-10-10-2", "r1-overnight")):
    wr(r, f".archflow/autopilot/{rid}.yaml", {"run_id": rid, "status": "preflight", "base_branch": "r1",
       "run_branch": rb, "release": "r1", "queue": [{"id": "A", "state": "pending", "branch": "t/A"}]}); commit(r, f"plan {rid}")
check("2j I-40: two planned runs -> resume starts the newest", resume(r) == ("start", "2026-10-10-2"), resume(r))
check("2k abort closes the same run, on base_branch (no run branch yet)", abort(r) == ("aborted", "2026-10-10-2", "r1"))
check("2l then the older planned run is current", resume(r) == ("start", "2026-10-10-1"), resume(r))
# never main: abort on a run whose run branch is gone and base_branch is absent -> commits nothing
r = init(list("AB")); co(r, "zz", new=True)
wr(r, ".archflow/autopilot/2026-10-10-1.yaml", {"run_id": "2026-10-10-1", "status": "running", "base_branch": "gone-base",
   "run_branch": "gone-run", "release": "r1", "queue": []}); commit(r, "stray running copy")
head = {b: g(r, "rev-parse", b) for b in ("main", "zz")}
check("2m abort with neither run_branch nor base_branch local commits nothing anywhere",
      abort(r) == ("told-user", "2026-10-10-1") and all(g(r, "rev-parse", b) == h for b, h in head.items()))

# ---- (3) the fixed gaps -------------------------------------------------------------------------
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
co(r, "r1"); g(r, "merge", "-q", "--no-edit", RUN); co(r, "main"); g(r, "merge", "-q", "--no-edit", "r1")
g(r, "branch", "-qD", RUN); main_head = g(r, "rev-parse", "main")
check("3a on main after merge: B asked, no pointer", resume(r) == ("ask", ["B"], []), resume(r))
rb, src = follow_on(r, ["B"], "2026-10-11-1")
check("3b follow-on cut from main as r1-autopilot-2026-10-11-1, main unchanged",
      rb == "r1-autopilot-2026-10-11-1" and g(r, "rev-parse", "main") == main_head, rb)
co(r, "main")
check("3c I-34: back on main B is reported picked up, not asked; no pointer; nothing",
      picked_up(r) == [("B", "2026-10-11-1", rb)] and resume(r) == ("nothing",), (picked_up(r), resume(r)))

r = init(list("ABC")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked", "C": "done"})
co(r, "t/B"); h = {b: g(r, "rev-parse", b) for b in ("t/B", RUN)}
check("3d I-35: on B's WIP branch resume stops and names the run branch, writes nothing",
      resume(r) == ("wip", "B", RUN) and {b: g(r, "rev-parse", b) for b in h} == h, resume(r))

r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
follow_on(r, ["B"], "2026-10-11-1", outcome="parked")
check("3e I-36: two ledgers share the run branch -> the newest (the follow-on) is the source",
      source_run(r, ["B"])["run_id"] == "2026-10-11-1")
check("3f deviation 1: B re-parked by its follow-on ON THIS branch is asked here", resume(r) == ("ask", ["B"], []), resume(r))
co(r, "r1")
check("3g I-36: base prints one pointer line for the branch, naming the newest run",
      pointers(r) == [("2026-10-11-1", RUN)], pointers(r))

# ---- (4) the deviations elsewhere ---------------------------------------------------------------
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
co(r, "r1"); g(r, "merge", "-q", "--no-edit", RUN); co(r, "main"); g(r, "merge", "-q", "--no-edit", "r1"); g(r, "branch", "-qD", RUN)
X, _ = follow_on(r, ["B"], "2026-10-11-1", outcome="parked")    # re-parked on the new branch X
co(r, "main")
check("4a deviation 1+2: on main B is picked up by 11-1, and the pointer names 11-1 on X (its own park is not "
      "suppressed by itself: 'newer' is what keeps it)",
      picked_up(r) == [("B", "2026-10-11-1", X)] and resume(r) == ("pointers", [("2026-10-11-1", X)]), resume(r))
co(r, X)
check("4b on X: B asked (follow-on's own branch), source is 11-1", resume(r) == ("ask", ["B"], [])
      and source_run(r, ["B"])["run_id"] == "2026-10-11-1", resume(r))
follow_on(r, ["B"], "2026-10-12-1"); co(r, "main")
check("4c after a newer follow-on builds B on X: main reports B picked up by 12-1, no pointer, nothing",
      picked_up(r) == [("B", "2026-10-12-1", X)] and resume(r) == ("nothing",), (picked_up(r), resume(r)))

# ---- (5) probes ---------------------------------------------------------------------------------
# 5a the user aborts a follow-on cut from main before it reaches B
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
co(r, "r1"); g(r, "merge", "-q", "--no-edit", RUN); co(r, "main"); g(r, "merge", "-q", "--no-edit", "r1"); g(r, "branch", "-qD", RUN)
X, _ = follow_on(r, ["B"], "2026-10-11-1", outcome=None, end="aborted"); co(r, "main")
check("5a aborted follow-on: main reports B picked up by it; on X B is in_progress (aborted queue not continued)",
      picked_up(r) == [("B", "2026-10-11-1", X)] and resume(r) == ("nothing",)
      and yaml.safe_load(g(r, "show", f"{X}:{REL}"))["stories"]["B"]["status"] == "in_progress", resume(r))
# 5b the user rejects the follow-on's work: deletes its run branch unmerged, keeps the WIP branch
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
co(r, "r1"); g(r, "merge", "-q", "--no-edit", RUN); co(r, "main"); g(r, "merge", "-q", "--no-edit", "r1"); g(r, "branch", "-qD", RUN)
X, _ = follow_on(r, ["B"], "2026-10-11-1"); co(r, "main"); g(r, "branch", "-qD", X)
r1 = resume(r)
a = abort(r)                                                      # as resume tells the user to
r2 = resume(r)
check("5b GAP: run branch deleted unmerged -> 'gone' -> abort (on base r1) -> B hidden on main as picked up "
      "by a run whose branch no longer exists; never asked again, no pointer",
      r1 == ("gone", "2026-10-11-1") and a[0] == "aborted" and r2 == ("nothing",)
      and picked_up(r) == [("B", "2026-10-11-1", X)] and rd(r, REL)["stories"]["B"]["status"] == "parked"
      and not local(r, X), (r1, a, r2, picked_up(r)))

n = sum(1 for _, p in results if p)
print(f"\n{n}/{len(results)} checks as expected (5b asserts a gap, so PASS = gap reproduced)")
sys.exit(0 if n == len(results) else 1)
