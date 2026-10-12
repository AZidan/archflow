"""QA independent replay of autopilot resume rule 2 as written after fix pass 8 (26d1a36).
Real git repos; the doc's combine/ledger rules are implemented here from the text, not imported."""
import subprocess, tempfile, yaml, os, sys
REL = ".archflow/releases/r1.yaml"
RANK = {s: i for i, s in enumerate(["backlog","spec_ready","design_ready","contract_ready","ready",
                                     "parked","in_progress","review","done"])}
LRANK = {"preflight": 0, "running": 1, "finished": 2, "aborted": 2}
results = []

def g(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    if check and r.returncode: raise RuntimeError(f"git {a}: {r.stderr}")
    return r.stdout.strip() if check else r
def ok(repo, *a): return g(repo, *a, check=False).returncode == 0
def rd(repo, p): return yaml.safe_load(open(os.path.join(repo, p)))
def wr(repo, p, d):
    os.makedirs(os.path.dirname(os.path.join(repo, p)), exist_ok=True)
    yaml.safe_dump(d, open(os.path.join(repo, p), "w"), sort_keys=False)
_t = [1700000000]
def commit(repo, msg):
    _t[0] += 10; env = dict(os.environ, GIT_AUTHOR_DATE=f"{_t[0]} +0000", GIT_COMMITTER_DATE=f"{_t[0]} +0000")
    subprocess.run(["git","-C",repo,"add","-A"], check=True)
    subprocess.run(["git","-C",repo,"commit","-qm",msg,"--allow-empty"], check=True, env=env)
    return g(repo, "rev-parse", "--abbrev-ref", "HEAD")
def co(repo, b, new=False): g(repo, "checkout", "-q", *(["-b"] if new else []), b)
def setstory(repo, s, status, **kw):
    d = rd(repo, REL); d["stories"][s] = {"status": status, **kw}; wr(repo, REL, d)

def init(stories, pre=None):
    repo = tempfile.mkdtemp()
    g(repo, "init", "-q", "-b", "main"); g(repo, "config", "user.email", "q@a"); g(repo, "config", "user.name", "qa")
    wr(repo, REL, {"stories": {s: {"status": (pre or {}).get(s, "ready")} for s in stories}})
    commit(repo, "init"); return repo

def run(repo, rid, rb, outcomes, end="finished", base="r1"):
    """Step 2c + Step 3 + Step 4 as written: base from HEAD if absent, run branch cut before ledger,
    each story in_progress on its task branch first, park/fail committed on task branch then carried."""
    co(repo, base, new=not ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{base}"))
    co(repo, rb, new=True)
    L = f".archflow/autopilot/{rid}.yaml"
    wr(repo, L, {"run_id": rid, "status": "preflight", "base_branch": base, "run_branch": rb, "release": "r1",
                 "queue": [{"id": s, "state": "pending", "branch": f"t/{s}"} for s in outcomes]}); commit(repo, "plan")
    d = rd(repo, L); d["status"] = "running"; wr(repo, L, d); commit(repo, "running")
    for s, o in outcomes.items():
        co(repo, rb); co(repo, f"t/{s}", new=not ok(repo,"show-ref","--verify","--quiet",f"refs/heads/t/{s}"))
        if o == "subtask-park":   # agent was on a subtask branch cut after in_progress
            setstory(repo, s, "in_progress"); commit(repo, "ip")
            co(repo, f"t/{s}-1.1-sub", new=True); open(os.path.join(repo, f"{s}.sub"), "w").write("x"); commit(repo, "sub wip")
            co(repo, f"t/{s}"); o = "parked"
        else:
            setstory(repo, s, "in_progress"); commit(repo, "ip")
        if o == "done":
            setstory(repo, s, "review"); commit(repo, "review")
            co(repo, rb); g(repo, "merge", "-q", "--no-edit", f"t/{s}"); setstory(repo, s, "done"); commit(repo, "done")
            g(repo, "branch", "-qD", f"t/{s}")
        else:
            open(os.path.join(repo, f"{s}.wip"), "w").write("w"); commit(repo, "wip")
            if o == "parked": setstory(repo, s, "parked", parked={"question": f"{s}?", "blocks_release": True})
            else: setstory(repo, s, "review")
            commit(repo, o); co(repo, rb); g(repo, "checkout", f"t/{s}", "--", REL); commit(repo, "carry")
        d = rd(repo, L); [q.update(state=o) for q in d["queue"] if q["id"] == s]; wr(repo, L, d); commit(repo, "led")
    d = rd(repo, L)
    if d["status"] != end: d["status"] = end; wr(repo, L, d); commit(repo, end)
    co(repo, base)

def branches(repo):
    cur = g(repo, "rev-parse", "--abbrev-ref", "HEAD")
    return cur, [cur] + [b for b in g(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split() if b != cur]

def kept_ledgers(repo):
    cur, bs = branches(repo); k = {}
    for b in bs:
        names = g(repo, "ls-tree", "--name-only", b, ".archflow/autopilot/").split()
        for n in names:
            led = yaml.safe_load(g(repo, "show", f"{b}:{n}"))
            key = (LRANK[led["status"]], b == led["run_branch"], b == cur)
            if led["run_id"] not in k or key > k[led["run_id"]][0]: k[led["run_id"]] = (key, b, led)
    return {r: (b, l) for r, (_, b, l) in k.items()}

def combine(repo):
    cur, bs = branches(repo); best = {}; parked_somewhere = set()
    for b in bs:
        r = g(repo, "show", f"{b}:{REL}", check=False)
        if r.returncode: continue
        ct = int(g(repo, "log", "-1", "--format=%ct", b, "--", REL) or 0)
        for s, st in yaml.safe_load(r.stdout)["stories"].items():
            if st["status"] == "parked": parked_somewhere.add(s)
            key = (RANK[st["status"]], ct, b == cur)
            if s not in best or key > best[s][0]: best[s] = (key, b, st)
    return {s: (b, st) for s, (_, b, st) in best.items()}, parked_somewhere

def resume(repo):
    k = kept_ledgers(repo)
    running = [l for b, l in k.values() if l["status"] == "running"]
    pre = [l for b, l in k.values() if l["status"] == "preflight"]
    comb, ps = combine(repo)
    offered = sorted(s for s, (b, st) in comb.items() if st["status"] == "parked")
    not_asked = {s: f"{comb[s][1]['status']} on {comb[s][0]}" for s in ps if s not in offered}
    if running:
        l = running[0]
        if not ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{l['run_branch']}"):
            return ("stop: branch gone", l["run_id"])
        return ("continue", l["run_id"])
    if pre and offered: return ("ask which", pre[0]["run_id"], offered)
    if pre: return ("start plan", pre[0]["run_id"])
    if offered: return ("ask", offered, not_asked)
    return ("nothing", not_asked)

def source_run(repo, s):
    c = [l for b, l in kept_ledgers(repo).values() if l["release"] == "r1"
         and any(q["id"] == s and q["state"] == "parked" for q in l["queue"])]
    return max(c, key=lambda l: l["run_id"]) if c else None

def waive(repo, s):
    src = source_run(repo, s)
    tgt = src["run_branch"] if ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{src['run_branch']}") else src["base_branch"]
    assert tgt != "main"; co(repo, tgt); d = rd(repo, REL)
    if d["stories"][s]["status"] != "parked": return None
    d["stories"][s]["parked"]["blocks_release"] = False; wr(repo, REL, d); b = commit(repo, f"waive {s}"); co(repo, "r1"); return b

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(("PASS " if cond else "FAIL ") + name, detail)

# 1. I-25 two finished runs, unmerged
r = init(list("ABCD")); run(r, "2026-10-08-1", "r1-autopilot", {"A": "done", "B": "parked"})
run(r, "2026-10-09-1", "r1-overnight", {"C": "done", "D": "parked"})
check("I-25 two finished runs: both asked", resume(r)[:2] == ("ask", ["B", "D"]), resume(r))
check("I-25 waive D lands on D's run branch", waive(r, "D") == "r1-overnight")
check("I-25 after waiving D, B and D still asked", resume(r)[:2] == ("ask", ["B", "D"]), resume(r))
check("I-25 D's kept copy is the waived one", combine(r)[0]["D"][1]["parked"]["blocks_release"] is False)
check("I-25 waive B lands on B's run branch", waive(r, "B") == "r1-autopilot")
check("I-25 3rd resume still asks both", resume(r)[:2] == ("ask", ["B", "D"]))
check("I-25 main untouched", g(r, "log", "--format=%s", "main") == "init")

# 1b. finished + aborted, three runs
r = init(list("ABCDEF")); run(r, "2026-10-07-1", "x1", {"A": "parked"})
run(r, "2026-10-08-1", "x2", {"B": "done", "C": "parked"}, end="aborted")
run(r, "2026-10-09-1", "x3", {"D": "parked", "E": "done"})
check("three runs (one aborted): all parked asked", resume(r)[:2] == ("ask", ["A", "C", "D"]), resume(r))

# 2. no resurrection
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "done"})
check("finished no-parked: nothing", resume(r)[0] == "nothing", resume(r))
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "failed"}, end="aborted")
check("aborted no-parked: nothing (failed B not resurrected)", resume(r)[0] == "nothing", resume(r))
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"}, end="aborted")
k = kept_ledgers(r); check("aborted with parked: only B asked, ledger stays aborted",
      resume(r)[:2] == ("ask", ["B"]) and k["2026-10-08-1"][1]["status"] == "aborted")
# running, branch gone (I-20/I-24 shape)
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done"}, end="running")
g(r, "branch", "-qD", "x1")
check("running copy only on base? (none committed on base for a started run) -> nothing",
      resume(r)[0] == "nothing", resume(r))
# I-23 shape: --plan run started on base, then branch gone
r = init(list("AB")); co(r, "r1", new=True)
wr(r, ".archflow/autopilot/2026-10-08-1.yaml", {"run_id": "2026-10-08-1", "status": "running", "base_branch": "r1",
   "run_branch": "x1", "release": "r1", "queue": [{"id": "A", "state": "pending"}]}); commit(r, "start")
wr(r, ".archflow/autopilot/2026-10-07-1.yaml", {"run_id": "2026-10-07-1", "status": "preflight", "base_branch": "r1",
   "run_branch": "x0", "release": "r1", "queue": [{"id": "B", "state": "pending"}]}); commit(r, "older plan")
check("I-23/I-24 started --plan run, branch gone -> stop, older plan not started",
      resume(r)[0] == "stop: branch gone", resume(r))

# 3. I-29 probes
r = init(list("AB"), pre={"B": "in_progress"}); co(r, "r1", new=True)
run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
res = resume(r)
check("PROBE in_progress-queued story parked by the run is asked", res[:2] == ("ask", ["B"]), res)
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "subtask-park"})
res = resume(r)
check("PROBE story parked while a subtask branch (cut after in_progress) remains is asked", res[:2] == ("ask", ["B"]), res)

print(f"\n{sum(c for _, c, _ in results)}/{len(results)} passed")
