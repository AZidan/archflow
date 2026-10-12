"""S5-02 probe: two finished runs in one release each leave a parked story.
Applies resume's candidate rule literally (autopilot.md:353-357: 'the newest ledger whose status is
finished or aborted, whose release is active, and whose queue[] holds an item parked whose story is
still parked'), then rule 2 ('ask each still-parked story' of THAT ledger), across 3 resumes in which
the user waives D (rule 2 'Nothing answered, some waived') because D waits on a vendor."""
import sys, importlib.util, pathlib
sys.path.insert(0, "/Users/azidan/Work/Repos/AIProjects/archflow/tests")
spec = importlib.util.spec_from_file_location("h", "/Users/azidan/Work/Repos/AIProjects/archflow/tests/test_autopilot_resume_qa.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
import tempfile, yaml
repo = pathlib.Path(tempfile.mkdtemp())
h._init(repo, ["A", "B", "C", "D"])
h._git(repo, "checkout", "-qb", "r1")
rel = {"stories": {"A": {"status": "done"}, "B": {"status": "parked", "parked": {"question": "B?", "blocks_release": True}},
                   "C": {"status": "done"}, "D": {"status": "parked", "parked": {"question": "D?", "blocks_release": True}}}}
h._write(repo, h.REL, rel)
for rid, q in [("2026-10-08-1", [{"id": "A", "state": "done"}, {"id": "B", "state": "parked"}]),
               ("2026-10-09-1", [{"id": "C", "state": "done"}, {"id": "D", "state": "parked"}])]:
    h._write(repo, f".archflow/autopilot/{rid}.yaml", {"run_id": rid, "status": "finished", "base_branch": "r1",
             "run_branch": "r1", "release": "r1", "queue": q})
h._commit(repo, "two finished runs merged onto r1")

def doc_literal_candidate():
    kept = h._kept(repo)
    cands = []
    for b, led in kept.values():
        if led["status"] not in ("finished", "aborted") or led["release"] != "r1": continue
        r = yaml.safe_load(h._git(repo, "show", f"{b}:{h.REL}"))
        still = [q["id"] for q in led["queue"] if q["state"] == "parked" and r["stories"][q["id"]]["status"] == "parked"]
        if still: cands.append((led["run_id"], still))
    return max(cands) if cands else None

print("status case 3 would list parked:", [s for s, v in h._read(repo, h.REL)["stories"].items() if v["status"] == "parked"])
print("harness _scan (all ledgers):", h._scan(repo)[1])
asked=set()
for n in range(1, 4):
    c = doc_literal_candidate(); asked.update(c[1] if c else [])
    print(f"resume #{n}: doc-literal candidate ledger + questions asked = {c}")
    # user cannot answer D yet (vendor), waives it so the release can ship -> D stays parked
    d = h._read(repo, h.REL); d["stories"]["D"]["parked"]["blocks_release"] = False; h._write(repo, h.REL, d)
    if h._git(repo, "status", "--porcelain"): h._commit(repo, "waive D")
print("B ever asked:", "B" in asked)
