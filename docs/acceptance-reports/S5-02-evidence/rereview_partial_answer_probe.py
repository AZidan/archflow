"""S5-02 re-review: run parks B and C; the user answers only C. The follow-on builds C and parks
nothing, so Step 4 (autopilot.md:297) writes 'Next: review {run-branch} and merge it yourself -
there is nothing for resume to pick up, and it would say so'. What does resume do next on that
branch? Uses the repo's replay model (tests/test_autopilot_resume_qa.py) for the git setup."""
import sys, importlib.util, tempfile, pathlib, yaml
sys.path.insert(0, "/Users/azidan/Work/Repos/AIProjects/archflow/tests")
spec = importlib.util.spec_from_file_location("h", "/Users/azidan/Work/Repos/AIProjects/archflow/tests/test_autopilot_resume_qa.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
repo = pathlib.Path(tempfile.mkdtemp())
h._replay(repo, {"A": "done", "B": "parked", "C": "parked"})
h._git(repo, "checkout", "-q", h.RUN)
print("resume after run 1 (user answers C only, leaves B):", h._resume(repo))
h._follow_on_builds(repo, "2026-10-11-1", h.RUN, "2026-10-10-1", "C", False)
fo = h._read(repo, ".archflow/autopilot/2026-10-11-1.yaml")
parked_by_follow_on = [q["id"] for q in fo["queue"] if q["state"] == "parked"]
print("follow-on", fo["status"], "queue:", [(q["id"], q["state"]) for q in fo["queue"]])
print("follow-on report PARKED section:", parked_by_follow_on, "-> Next line per :297 =",
      "resume" if parked_by_follow_on else "'review r1-autopilot and merge it yourself (nothing for resume to pick up)'")
print("release file on", h._current(repo), "B =", h._read(repo, h.REL)["stories"]["B"]["status"])
print("resume on the same branch now:", h._resume(repo))
