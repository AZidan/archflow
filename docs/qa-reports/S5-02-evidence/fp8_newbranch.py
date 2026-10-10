import sys, os; sys.argv=["x"]
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fp8_replay.py")).read().split("# 1. I-25")[0]
exec(src)
# done stories leave a code file
_orig = run
r = init(list("ABCD"))
def run2(repo, rid, rb, outcomes):
    run(repo, rid, rb, outcomes)
    co(repo, rb); [open(os.path.join(repo, f"{s}.code"), "w").write("c") for s, o in outcomes.items() if o == "done"]
    commit(repo, "code"); co(repo, "r1")
# A done before B parks (t/B cut from x1 after A merged) -- add code before B by ordering
run(r, "2026-10-08-1", "x1", {"A": "done", "B": "parked"})
run(r, "2026-10-09-1", "x2", {"C": "done", "D": "parked"})
# user answers B and D; several source branches -> cut NEW from r1, Proceed on both unmerged
NEW = "r1-autopilot-2026-10-11-1"
unmerged = [b for b in ("x1", "x2") if not ok(r, "merge-base", "--is-ancestor", b, "r1")]
print("unmerged asked about:", unmerged)
co(r, NEW, new=True); setstory(r, "B", "in_progress"); setstory(r, "D", "in_progress"); commit(r, "follow-on")
for s in "BD":
    co(r, f"t/{s}"); m = g(r, "merge", "--no-edit", NEW, check=False)
    if m.returncode:
        for p in g(r, "diff", "--name-only", "--diff-filter=U").split():
            g(r, "checkout", NEW, "--", p); g(r, "add", p)
        g(r, "commit", "-qm", "merge")
    setstory(r, s, "done"); commit(r, f"{s} done")
    co(r, NEW); m = g(r, "merge", "--no-edit", f"t/{s}", check=False); print("merge", s, m.returncode)
# what did NEW pick up from the 'left behind' source run branches?
log = g(r, "log", "--format=%s", NEW)
print("NEW contains x1's A commits:", ok(r, "merge-base", "--is-ancestor", g(r,"rev-parse","x1~3"), NEW))
rel = rd(r, REL)["stories"]; print("NEW release file:", {k: v["status"] for k, v in rel.items()})
print("A done-commit on NEW history:", "done" in log, "| x1 ledger on NEW:", os.path.exists(os.path.join(r, ".archflow/autopilot/2026-10-08-1.yaml")))
