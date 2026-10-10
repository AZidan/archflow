"""QA independent replay of autopilot resume rule 2 as written after fix pass 9 (79d0e64).
Reuses fp8_replay.py's git scaffolding (run(), kept_ledgers(), waive()) and replaces the combine
with the fix pass 9 text: drop superseded copies, then rank. Nothing is imported from the tests."""
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp8_replay.py")).read()
exec(src.split("# 1. I-25")[0])


def combine(repo):
    """autopilot.md 'Parked stories' (fix pass 9). Superseded: branch's last commit to the file is an
    ancestor of another copy's branch whose own last commit differs. Mutual drops both stay."""
    cur, bs = branches(repo); copies = {}
    for b in bs:
        r = g(repo, "show", f"{b}:{REL}", check=False)
        if r.returncode: continue
        sha, ct = g(repo, "log", "-1", "--format=%H %ct", b, "--", REL).split()
        copies[b] = (sha, int(ct), yaml.safe_load(r.stdout)["stories"])
    def drops(x, y):
        return copies[x][0] != copies[y][0] and ok(repo, "merge-base", "--is-ancestor", copies[x][0], y)
    live = [b for b in copies if not any(drops(b, o) and not drops(o, b) for o in copies if o != b)]
    best, ps = {}, set()
    for b in live:
        _, ct, stories = copies[b]
        for s, st in stories.items():
            if st["status"] == "parked": ps.add(s)
            key = (RANK[st["status"]], ct, b == cur)
            if s not in best or key > best[s][0]: best[s] = (key, b, st)
    # a story parked only on a dropped copy is silently gone: report it too
    for b in copies:
        if b not in live:
            for s, st in copies[b][2].items():
                if st["status"] == "parked": ps.add(s)
    return {s: (b, st) for s, (_, b, st) in best.items()}, ps


def groups(repo, answered, new_id):
    """'Some answered' (fix pass 9): group by source run; existing run_branch -> build there; else a
    new {base}-autopilot-{id} from base, only for stories parked on base's copy; rest skipped."""
    out, skipped, by = [], [], {}
    for s in answered:
        srun = source_run(repo, s); by.setdefault(srun["run_id"] if srun else None, (srun, []))[1].append(s)
    for rid, (srun, ss) in by.items():
        if srun and ok(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{srun['run_branch']}"):
            out.append((srun["run_branch"], False, ss)); continue
        base = srun["base_branch"] if srun else "r1"
        bc = yaml.safe_load(g(repo, "show", f"{base}:{REL}"))["stories"]
        keep = [s for s in ss if bc.get(s, {}).get("status") == "parked"]
        skipped += [s for s in ss if s not in keep]
        if keep: out.append((f"{base}-autopilot-{new_id}", True, keep))
    return out, skipped


def add_story(repo, branch, sid):
    """an ordinary later commit to the release file on a branch (/archflow:feature adding a story)."""
    co(repo, branch); d = rd(repo, REL); d["stories"][sid] = {"status": "ready"}; wr(repo, REL, d)
    commit(repo, f"feat: add {sid}")


def merge(repo, other):
    """merge `other` into the checked-out branch; a release-file conflict is resolved the way a user
    would: the other side's stories, plus any story only this side added."""
    m = g(repo, "merge", "-q", "--no-edit", other, check=False)
    if m.returncode == 0: return
    mine = yaml.safe_load(g(repo, "show", f"HEAD:{REL}"))["stories"]
    theirs = yaml.safe_load(g(repo, "show", f"{other}:{REL}"))["stories"]
    for k2, v in mine.items(): theirs.setdefault(k2, v)
    wr(repo, REL, {"stories": theirs})
    for p2 in g(repo, "diff", "--name-only", "--diff-filter=U").split():
        if p2 != REL: g(repo, "checkout", "--theirs", "--", p2)
    commit(repo, f"merge {other}")


# ---- (1) I-25, I-29, I-30 as filed ------------------------------------------------------------
r = init(list("ABCD")); run(r, "2026-10-08-1", "r1-autopilot", {"A": "done", "B": "parked"})
run(r, "2026-10-09-1", "r1-overnight", {"C": "done", "D": "parked"})
check("I-25 two finished runs: both asked", resume(r)[:2] == ("ask", ["B", "D"]), resume(r))
check("I-25 waive D lands on D's run branch", waive(r, "D") == "r1-overnight")
check("I-25 after waiving D, B and D still asked", resume(r)[:2] == ("ask", ["B", "D"]), resume(r))
check("I-25 D's kept copy is the waived one", combine(r)[0]["D"][1]["parked"]["blocks_release"] is False)
check("I-25 waive B lands on B's run branch", waive(r, "B") == "r1-autopilot")
check("I-25 3rd resume still asks both", resume(r)[:2] == ("ask", ["B", "D"]))
check("I-25 main untouched", g(r, "log", "--format=%s", "main") == "init")
gr = groups(r, ["B", "D"], "2026-10-11-1")
check("I-31 answers span two runs -> two groups, each on its own run branch",
      gr == ([("r1-autopilot", False, ["B"]), ("r1-overnight", False, ["D"])], []), gr)

r = init(list("ABCDEF")); run(r, "2026-10-07-1", "x1", {"A": "parked"})
run(r, "2026-10-08-1", "x2", {"B": "done", "C": "parked"}, end="aborted")
run(r, "2026-10-09-1", "x3", {"D": "parked", "E": "done"})
check("three runs (one aborted): all parked asked", resume(r)[:2] == ("ask", ["A", "C", "D"]), resume(r))

r = init(list("AB"), pre={"B": "in_progress"}); co(r, "r1", new=True)
run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
check("I-29 story queued in_progress and parked by the run is asked", resume(r)[:2] == ("ask", ["B"]), resume(r))
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "subtask-park"})
check("I-30 leftover subtask branch does not hide the park", resume(r)[:2] == ("ask", ["B"]), resume(r))

# ---- (2) no resurrection, guards ----------------------------------------------------------------
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "done"})
check("finished no-parked: nothing", resume(r)[0] == "nothing", resume(r))
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "failed"}, end="aborted")
check("aborted no-parked: nothing (failed B not resurrected)", resume(r)[0] == "nothing", resume(r))
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"}, end="aborted")
k = kept_ledgers(r); check("aborted with parked: only B asked, ledger stays aborted",
      resume(r)[:2] == ("ask", ["B"]) and k["2026-10-08-1"][1]["status"] == "aborted")
r = init(list("AB")); co(r, "r1", new=True)
wr(r, ".archflow/autopilot/2026-10-08-1.yaml", {"run_id": "2026-10-08-1", "status": "running", "base_branch": "r1",
   "run_branch": "x1", "release": "r1", "queue": [{"id": "A", "state": "pending"}]}); commit(r, "start")
wr(r, ".archflow/autopilot/2026-10-07-1.yaml", {"run_id": "2026-10-07-1", "status": "preflight", "base_branch": "r1",
   "run_branch": "x0", "release": "r1", "queue": [{"id": "B", "state": "pending"}]}); commit(r, "older plan")
check("I-23/I-24 started --plan run, branch gone -> stop, older plan not started",
      resume(r)[0] == "stop: branch gone", resume(r))

# ---- (3) ancestry rule scrutiny -------------------------------------------------------------------
# 3a. run merged into base AFTER a later change on base: base's merge commit supersedes the run copy
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
add_story(r, "r1", "E"); merge(r, "x1")
c, _ = combine(r)
check("3a merged into base after a later base change: B asked from r1",
      resume(r)[:2] == ("ask", ["B"]) and c["B"][0] == "r1", (resume(r), c["B"][0]))
# 3b. post-merge main supersedes the run branch (run kept); follow-on builds on the run branch
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
add_story(r, "main", "M1"); merge(r, "x1"); co(r, "r1")
c, _ = combine(r)
check("3b post-merge main copy supersedes x1, B still asked (from main)",
      resume(r)[:2] == ("ask", ["B"]) and c["B"][0] == "main", (resume(r), c["B"][0]))
check("3b follow-on builds on x1 (still local), never main", groups(r, ["B"], "2026-10-11-1") == ([("x1", False, ["B"])], []))
# 3c. waiver commit on the run branch after base merged it: waived copy is the kept one
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
g(r, "merge", "-q", "--no-edit", "x1"); waive(r, "B"); c, _ = combine(r)
check("3c waiver on x1 after base merged it: still asked, waived copy kept",
      resume(r)[:2] == ("ask", ["B"]) and c["B"][1]["parked"]["blocks_release"] is False, c["B"][0])
# 3d. squash merge into base: neither copy superseded, both parked, newer squash copy kept
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
g(r, "merge", "-q", "--squash", "x1"); commit(r, "squash x1")
check("3d squash-merged into base: B asked", resume(r)[:2] == ("ask", ["B"]), resume(r))
# 3e. PROBE: I-29 shape + one ordinary later release-file commit on base (no merge)
r = init(list("AB"), pre={"B": "in_progress"}); co(r, "r1", new=True)
run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"}); add_story(r, "r1", "E")
res = resume(r)
check("PROBE 3e I-29 shape, then /archflow:feature adds a story on r1: B still asked",
      res[:2] == ("ask", ["B"]), res)
# 3f. PROBE: I-30 shape where the subtask branch committed the release file itself (subtask status)
r = init(list("AB"))
run(r, "2026-10-08-1", "x1", {"A": "done"})                      # a normal run first, then hand-built
co(r, "x1"); co(r, "t/B", new=True); setstory(r, "B", "in_progress"); commit(r, "ip")
co(r, "t/B-1.1-sub", new=True); setstory(r, "B", "in_progress", subtasks={"1.1": "completed"}); commit(r, "subtask 1.1 done")
co(r, "t/B"); open(os.path.join(r, "B.wip"), "w").write("w"); commit(r, "wip")
setstory(r, "B", "parked", parked={"question": "B?", "blocks_release": True}); commit(r, "park")
co(r, "x1"); g(r, "checkout", "t/B", "--", REL); commit(r, "carry"); co(r, "r1")
res = resume(r)
check("PROBE 3f subtask branch that committed subtask status before the park: B still asked",
      res[:2] == ("ask", ["B"]), res)

# ---- (4) one-run-at-a-time flow ---------------------------------------------------------------
# run merged into base and deleted -> new named branch from base for that story
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
g(r, "merge", "-q", "--no-edit", "x1"); g(r, "branch", "-qD", "x1")
check("4a run merged into base, deleted -> new r1-autopilot-{id} from r1",
      groups(r, ["B"], "2026-10-11-1") == ([("r1-autopilot-2026-10-11-1", True, ["B"])], []))
# run merged into main and deleted -> base lacks the park -> named, left parked, nothing built
r = init(list("AB")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
co(r, "main"); g(r, "merge", "-q", "--no-edit", "x1"); g(r, "branch", "-qD", "x1"); co(r, "r1")
check("4b run merged into main, deleted -> base lacks park, left parked",
      resume(r)[:2] == ("ask", ["B"]) and groups(r, ["B"], "2026-10-11-1") == ([], ["B"]))
# two groups sharing one run branch: follow-on on x1 re-parks B, D still from run 1
r = init(list("ABD")); run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked", "D": "parked"})
co(r, "x1"); L = ".archflow/autopilot/2026-10-11-1.yaml"
wr(r, L, {"run_id": "2026-10-11-1", "status": "finished", "resumes": ["2026-10-08-1"], "base_branch": "r1",
          "run_branch": "x1", "release": "r1", "queue": [{"id": "B", "state": "parked", "branch": "t/B"}]})
setstory(r, "B", "parked", parked={"question": "B again?", "blocks_release": True}); commit(r, "follow-on re-parks B")
co(r, "r1"); gr = groups(r, ["B", "D"], "2026-10-12-1")
check("4c NOTE answers from a follow-on and its source on the same run branch form two groups",
      len(gr[0]) == 2 and {x[0] for x in gr[0]} == {"x1"}, gr)

print(f"\n{sum(c for _, c, _ in results)}/{len(results)} passed")
