"""QA independent replay of autopilot resume as written after fix pass 10 (f074598), "current branch
only". Self-contained: real git repos, the rules implemented from plugin/commands/autopilot.md text.
Nothing is imported from tests/ or from earlier evidence scripts.

Run: python3 docs/qa-reports/S5-02-evidence/fp10_replay.py
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


def parked_here(repo):
    r = g(repo, "show", f"HEAD:{REL}", check=False)
    st = yaml.safe_load(r.stdout)["stories"] if r.returncode == 0 else {}
    return [s for s, v in st.items() if v["status"] == "parked"]


def pointers(repo):
    c = cur(repo)
    return sorted((l["run_id"], l["run_branch"]) for l in kept(repo).values()
                  if l["status"] in ("finished", "aborted") and l["release"] == "r1"
                  and any(q["state"] == "parked" for q in l["queue"])
                  and local(repo, l["run_branch"]) and l["run_branch"] != c)


def resume(repo):
    k = list(kept(repo).values())
    running = [l for l in k if l["status"] == "running"]
    pre = [l for l in k if l["status"] == "preflight"]
    p = parked_here(repo)
    if running:
        l = running[0]
        return ("continue", l["run_id"]) if local(repo, l["run_branch"]) else ("gone", l["run_id"])
    if pre and p: return ("ask-which", pre[0]["run_id"], p)
    if pre: return ("start", pre[0]["run_id"])
    if p: return ("ask", p, pointers(repo))
    return ("pointers", pointers(repo)) if pointers(repo) else ("nothing",)


def rid_key(r):
    y, m, d, n = r.split("-"); return (y, m, d, int(n))


def source_runs(repo, answered):
    """Every candidate for 'the kept ledger whose run_branch is the current branch', then the fallback."""
    k = list(kept(repo).values()); c = cur(repo)
    own = [l for l in k if l["run_branch"] == c]
    if own: return own
    cands = [l for l in k if l["status"] in ("finished", "aborted") and l["release"] == "r1"
             and any(q["id"] in answered and q["state"] == "parked" for q in l["queue"])]
    return [max(cands, key=lambda l: rid_key(l["run_id"]))] if cands else []


def follow_on(repo, answered, rid, outcome="done"):
    """Rule 2 'Some answered', step by step as written; returns (branch, src ids)."""
    srcs = source_runs(repo, answered); src = srcs[0] if srcs else None
    c = cur(repo)
    if any(l["run_branch"] == c for l in kept(repo).values()):
        rb = c
    else:
        base = src["base_branch"] if src else "r1"               # else Step 2a's answer
        rb = f"{base}-autopilot-{rid}"; co(repo, rb, new=True)  # cut from the current branch
    L = f".archflow/autopilot/{rid}.yaml"
    wr(repo, L, {"run_id": rid, "status": "running", **({"resumes": [src["run_id"]]} if src else {}),
                 "base_branch": src["base_branch"] if src else "r1", "run_branch": rb, "release": "r1",
                 "decisions": (src or {}).get("decisions", []) + [f"answer {s}" for s in answered],
                 "queue": [{"id": s, "state": "pending",
                            "branch": rd(repo, REL)["stories"][s]["parked"].get("branch", f"t/{s}")}
                           for s in answered]})
    for s in answered: setstory(repo, s, "in_progress")
    commit(repo, f"resume: follow-on {rid}")
    for s in answered:
        wip = f"t/{s}"
        if local(repo, wip):
            co(repo, wip)
            m = g(repo, "merge", "-q", "--no-edit", rb, check=False)
            if m.returncode:                                      # run branch's release file + ledgers win
                g(repo, "checkout", rb, "--", REL, ".archflow/autopilot/"); commit(repo, "merge run branch")
        else:
            co(repo, wip, new=True, start=rb)
        if outcome == "done":
            setstory(repo, s, "review"); commit(repo, f"{s} review"); co(repo, rb)
            g(repo, "merge", "-q", "--no-edit", wip); setstory(repo, s, "done"); commit(repo, f"{s} done")
        else:
            setstory(repo, s, "parked", parked={"question": f"{s} again?", "blocks_release": True, "branch": wip})
            commit(repo, "repark"); co(repo, rb); g(repo, "checkout", wip, "--", REL); commit(repo, "carry")
        d = rd(repo, L); [q.update(state=outcome) for q in d["queue"] if q["id"] == s]; wr(repo, L, d); commit(repo, "led")
    d = rd(repo, L); d["status"] = "finished"; wr(repo, L, d); commit(repo, f"finish {rid}")
    return rb, [s["run_id"] for s in srcs]


def waive(repo, s):
    if cur(repo) == "main": return None
    setstory(repo, s, "parked", **{"parked": {**rd(repo, REL)["stories"][s]["parked"], "blocks_release": False}})
    return commit(repo, f"waive {s}")


RUN = "r1-autopilot"

# ---- (1) AC1/AC2: the realistic end of a run ---------------------------------------------------
r = init(list("ABC")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked", "C": "failed"})
check("1a Step 4 leaves the user on the run branch", cur(r) == RUN)
check("1b 'Next: resume' works right there: B asked", resume(r) == ("ask", ["B"], []), resume(r))
co(r, "r1")
check("1c back on base_branch: nothing parked, resume names the run branch",
      resume(r) == ("pointers", [("2026-10-10-1", RUN)]), resume(r))
co(r, RUN)
rb, srcs = follow_on(r, ["B"], "2026-10-11-1")
check("1d follow-on builds on the current run branch, resumes [r1]", (rb, srcs) == (RUN, ["2026-10-10-1"]), (rb, srcs))
check("1e B done, C untouched on run branch", rd(r, REL)["stories"]["B"]["status"] == "done"
      and rd(r, REL)["stories"]["C"]["status"] == "review")
check("1f source ledger untouched", yaml.safe_load(g(r, "show", f"{RUN}:.archflow/autopilot/2026-10-10-1.yaml"))["status"] == "finished")
check("1g resume on run branch afterwards: nothing", resume(r) == ("nothing",), resume(r))
co(r, "r1")
check("1h KNOWN side effect: base still names the run branch (stale pointer, 'may')",
      resume(r) == ("pointers", [("2026-10-10-1", RUN)]), resume(r))
check("1i main untouched", g(r, "log", "--format=%s", "main") == "init")

# ---- (2) regressions ----------------------------------------------------------------------------
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "done"})
check("2a I-20: no parked stories -> nothing, no pointer (run branch)", resume(r) == ("nothing",), resume(r))
co(r, "r1"); check("2b no parked stories -> nothing (base)", resume(r) == ("nothing",), resume(r))
r = init(list("ABC")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked", "C": "done"}, end="aborted", stop_after=2)
check("2c aborted run: abort leaves user on run branch; only parked B asked (C not continued)",
      resume(r) == ("ask", ["B"], []), resume(r))
rb, srcs = follow_on(r, ["B"], "2026-10-11-1")
check("2d aborted ledger stays aborted, its pending C never queued",
      kept(r)["2026-10-10-1"]["status"] == "aborted" and
      [q["id"] for q in kept(r)["2026-10-11-1"]["queue"]] == ["B"] and rd(r, REL)["stories"]["C"]["status"] == "ready")
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "done"}, end="aborted", stop_after=1)
check("2e aborted run without parked stories -> nothing", resume(r) == ("nothing",), resume(r))
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "parked", "B": "done"})
co(r, RUN); srcs = source_runs(r, ["A"])
L = ".archflow/autopilot/2026-10-11-1.yaml"
wr(r, L, {"run_id": "2026-10-11-1", "status": "running", "resumes": ["2026-10-10-1"], "base_branch": "r1",
          "run_branch": RUN, "release": "r1", "queue": [{"id": "A", "state": "pending", "branch": "t/A"}]})
setstory(r, "A", "in_progress"); commit(r, "follow-on written, then the session dies")
check("2f interrupted follow-on is a running run for rule 1", resume(r) == ("continue", "2026-10-11-1"), resume(r))
co(r, "r1"); g(r, "branch", "-qD", RUN)
# t/A, cut while the run was running, also carries a `running` copy of r1's ledger (known since fix
# pass 3, line 356 of the report), so either running ledger may be the one reported gone.
check("2g gone running run -> 'gone', nothing else chosen", resume(r)[0] == "gone", resume(r))

# ---- (3) edge cases -----------------------------------------------------------------------------
# 3a on main after merge: parked visible on main; follow-on cut from main; nothing committed on main
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
co(r, "r1"); g(r, "merge", "-q", "--no-edit", RUN); co(r, "main"); g(r, "merge", "-q", "--no-edit", "r1")
g(r, "branch", "-qD", RUN)                                        # user deletes the merged run branch
main_head = g(r, "rev-parse", "main")
check("3a on main: B asked, no pointer", resume(r) == ("ask", ["B"], []), resume(r))
check("3b waiver on main commits nothing", waive(r, "B") is None and g(r, "rev-parse", "main") == main_head)
rb, srcs = follow_on(r, ["B"], "2026-10-11-1")
check("3c follow-on on new r1-autopilot-2026-10-11-1 cut from main, main unchanged",
      rb == "r1-autopilot-2026-10-11-1" and g(r, "rev-parse", "main") == main_head
      and ok(r, "merge-base", "--is-ancestor", main_head, rb), (rb, srcs))
co(r, "main")
check("3d DUPLICATE: back on main the finished follow-on is invisible; B asked again with no pointer",
      resume(r) == ("ask", ["B"], []), resume(r))

# 3e current branch is a WIP task branch (user checked out the WIP branch the report names)
r = init(list("ABC")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked", "C": "done"})
co(r, "t/B")
check("3e on the WIP branch: B asked and the run branch named", resume(r) == ("ask", ["B"], [("2026-10-10-1", RUN)]), resume(r))
rb, srcs = follow_on(r, ["B"], "2026-10-11-1")
st = rd(r, REL)["stories"]
check("3f follow-on branch is new, cut from t/B (not the run branch)", rb == "r1-autopilot-2026-10-11-1"
      and not ok(r, "merge-base", "--is-ancestor", g(r, "rev-parse", RUN), rb), rb)
check("3g DIVERGENCE: follow-on branch lacks C (done on the run branch after B parked)",
      st["C"]["status"] == "ready" and not os.path.exists(os.path.join(r, "C.code")), st)

# 3h story parked outside autopilot: no ledger
r = init(list("S")); co(r, "feat", new=True)
setstory(r, "S", "parked", parked={"question": "S?", "blocks_release": True}); commit(r, "manual park")
check("3h parked outside autopilot: asked, no source run", resume(r) == ("ask", ["S"], []) and source_runs(r, ["S"]) == [])
rb, srcs = follow_on(r, ["S"], "2026-10-11-1")
check("3i follow-on with no source: no resumes, new branch from feat (Step 2a supplies base)",
      srcs == [] and "resumes" not in kept(r)["2026-10-11-1"] and rb.endswith("-autopilot-2026-10-11-1"))

# 3j source ambiguity: follow-on re-parks on the same run branch, then resume there again
r = init(list("AB")); run(r, "2026-10-10-1", RUN, {"A": "done", "B": "parked"})
follow_on(r, ["B"], "2026-10-11-1", outcome="parked")
cands = [l["run_id"] for l in source_runs(r, ["B"])]
check("3j AMBIGUOUS: two kept ledgers have run_branch == current branch", len(cands) == 2, cands)
co(r, "r1")
check("3k base names the run branch once per run (two lines for one branch)",
      pointers(r) == [("2026-10-10-1", RUN), ("2026-10-11-1", RUN)], pointers(r))

n = sum(1 for _, p in results if p)
print(f"\n{n}/{len(results)} checks as expected (3d/3g/3j/3k assert the gaps, so PASS = gap reproduced)")
sys.exit(0 if n == len(results) else 1)
