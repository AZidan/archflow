#!/usr/bin/env python3
"""
/archflow migrate — deterministic v1.0 -> v2.0 roadmap migration engine.

Reconstructs REAL releases from git shipping evidence (a sprint is NOT a release),
routes done work into archived releases + history, the current release into the
active release, and everything else into the backlog as `ready` detailed stories.

Usage:
    python3 migrate.py [--path .] [--dry-run | --apply] [--active <sprint-id-or-slug>]

    --dry-run   (default) reconstruct + print the plan; write nothing.
    --apply     back up .archflow/ and write the v2.0 multi-file layout.
    --active    designate which in_progress sprint becomes the active release
                (required only when v1 has more than one in_progress sprint).

Non-destructive: only .archflow/ is touched; v1 files are backed up to
.archflow/backup-v1/. Run --dry-run first, confirm the timeline, then --apply.
"""
import argparse, os, re, shutil, subprocess, sys, collections

try:
    import yaml
except ImportError:
    sys.exit("ERROR: PyYAML required.  pip install pyyaml   (or: python3 -m pip install pyyaml)")

STRONG_CD = re.compile(r"buildspec|codebuild|cloudbuild|kubernetes/.*deployment|/k8s/|helm|/eks|"
                       r"infra/.*prod|docker-compose\.prod|deploy\.ya?ml|kustomiz", re.I)
STATUS_MAP = {"done": "done", "completed": "done", "in_progress": "in_progress",
              "partial-done": "in_progress", "review": "review",
              "backlog": "ready", "planned": "ready", "deferred": "ready"}
DONE = {"done", "completed"}
warnings = []


def git(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True).stdout


def slugify(s):
    s = s.split(":", 1)[-1] if ":" in s else s
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "release"


PROJECT_ROOT = "."   # set in main(); lets gate derivation check for real design artifacts


def gates_for(st):
    """Derive gates from scope: the story's assigned role + any real design artifact on disk."""
    a = (st.get("assigned") or "").lower()
    sid = st.get("id", "")
    has_artifact = bool(sid) and os.path.isdir(os.path.join(PROJECT_ROOT, "design-artifacts", sid))
    return {"needs_design": has_artifact or bool(re.search(r"ui|ux|frontend|mobile|design", a)),
            "needs_contract": bool(re.search(r"api|backend|frappe|contract|endpoint", a))}


def default_assigned(st):
    """Keep the v1 assignee if present; otherwise infer a consistent one from gates."""
    if st.get("assigned"):
        return st["assigned"]
    g = gates_for(st)
    if g["needs_contract"] and not g["needs_design"]:
        return "api-engineer"
    return "ui-engineer"


def readiness(status):
    if status not in STATUS_MAP:
        warnings.append(f"unknown story status '{status}' -> treated as 'ready'")
    return STATUS_MAP.get(status, "ready")


# ---- v1 parsing (variant A: epics/phases ; variant B: top-level sprints/inline) --------------
def load_v1(af):
    v1 = yaml.safe_load(open(os.path.join(af, "roadmap.yaml")))
    variant = "A" if "phases" in v1 or "epics" in v1 else ("B" if "sprints" in v1 else "unknown")
    stories, sprint_of, sprints = [], {}, []

    def keep(st):
        """Skip malformed stories (no usable id) rather than crashing."""
        sid = st.get("id")
        if not isinstance(sid, str) or not sid.strip():
            warnings.append(f"story with missing/invalid id skipped: {st.get('title', st)!r}")
            return False
        return True

    if variant == "A":
        # Stories are defined under epics; sprints (under phases) reference them by ID.
        by_id = {}
        for e in v1.get("epics", []):
            for st in e.get("stories", []):
                if keep(st):
                    stories.append(st); by_id[st["id"]] = st
                    sprint_of[st["id"]] = e.get("name", e.get("id", ""))
        # Flatten inner sprints into one list, each carrying RESOLVED story objects.
        for ph in v1.get("phases", []):
            for sp in ph.get("sprints", []):
                resolved = []
                for ref in sp.get("stories", []):
                    sid = ref if isinstance(ref, str) else ref.get("id")
                    if sid in by_id:
                        resolved.append(by_id[sid])
                        sprint_of[sid] = sp.get("name", sp.get("id", ""))
                sprints.append({"id": sp.get("id"), "name": sp.get("name", sp.get("id", "")),
                                "status": sp.get("status"), "goal": sp.get("goal", ""),
                                "stories": resolved})
    else:
        for s in v1.get("sprints", []):
            kept = [st for st in s.get("stories", []) if keep(st)]
            s["stories"] = kept
            sprints.append(s)
            for st in kept:
                stories.append(st); sprint_of[st["id"]] = s.get("name", s.get("id", ""))
    return v1, variant, stories, sprints, sprint_of


def sprint_status(s):
    st = s.get("status")
    if st:
        return st
    ss = [x.get("status") for x in s.get("stories", [])]
    if ss and all(x in DONE for x in ss):
        return "done"
    if any(x in ("in_progress", "partial-done") for x in ss):
        return "in_progress"
    return "planned"


# ---- release reconstruction from git ---------------------------------------------------------
def deploy_boundary(repo):
    cur, hits = None, []
    for line in git(repo, "log", "--diff-filter=A", "--format=COMMIT|%ad", "--date=short",
                    "--name-only").splitlines():
        if line.startswith("COMMIT|"):
            cur = line.split("|")[1]
        elif cur and STRONG_CD.search(line):
            hits.append(cur)
    return min(hits) if hits else None


def release_events(repo):
    branches = git(repo, "branch", "-a")
    prod = next((b.strip().lstrip("* ") for b in branches.splitlines()
                 if re.search(r"(^|/)prod$", b.strip())), None)
    if not prod:
        return (None, [])  # no prod branch -> continuous deploy (baseline + rolling)
    seen = {}
    for line in git(repo, "log", prod, "--format=%ad|%s", "--date=short").splitlines():
        if "|" in line:
            d, s = line.split("|", 1)
            if re.search(r"from .*/staging|staging'? into prod|release", s, re.I):
                seen.setdefault(d, s[:50])
    from datetime import date
    pd = lambda x: date(*map(int, x.split("-")))
    out = []
    for d in sorted(seen):                         # coalesce events within 5 days
        if out and (pd(d) - pd(out[-1][0])).days <= 5:
            continue
        out.append((d, seen[d]))
    return prod, out


def story_dates(repo):
    m = {}
    for line in git(repo, "log", "--all", "--format=%ad|%s", "--date=short").splitlines():
        if "|" in line:
            d, s = line.split("|", 1)
            for a, b in re.findall(r"[Ss](\d+)-(\d+)", s):
                k = f"S{a}-{b}"; m[k] = max(m.get(k, ""), d)
    return m


def build_windows(boundary, events):
    if not boundary:
        return [("baseline", "0000", "9999")]
    wins, prev = [("baseline", "0000", boundary)], boundary
    for d, _ in events:
        wins.append((f"release-{d}", prev, d)); prev = d
    wins.append(("continuously-deployed" if not events else f"post-{prev}", prev, "9999"))
    return wins


# ---- detail / write ---------------------------------------------------------------------------
def detail(st, status=None):
    return {"id": st["id"], "title": st.get("title", ""), "priority": st.get("priority", "Medium"),
            "status": status or readiness(st.get("status", "backlog")), "gates": gates_for(st),
            "assigned": default_assigned(st), "description": st.get("description", ""),
            "acceptance_criteria": st.get("acceptance_criteria", []), "subtasks": st.get("subtasks", [])}


def dump(obj, path):
    yaml.safe_dump(obj, open(path, "w"), sort_keys=False, width=100, allow_unicode=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--active", default=None, help="sprint id/slug to become the active (in_progress) release")
    a = ap.parse_args()
    apply = a.apply and not a.dry_run
    global PROJECT_ROOT
    repo, af = a.path, os.path.join(a.path, ".archflow")
    PROJECT_ROOT = a.path
    if not os.path.exists(os.path.join(af, "roadmap.yaml")):
        sys.exit(f"ERROR: {af}/roadmap.yaml not found")

    v1, variant, stories, sprints, sprint_of = load_v1(af)
    if str(v1.get("schema_version")) == "2.0":
        sys.exit("Already schema v2.0 — nothing to migrate.")

    # active sprint selection (one in_progress -> active release)
    inprog = [s for s in sprints if sprint_status(s) == "in_progress"]
    active_sprint = None
    if a.active:
        active_sprint = next((s for s in sprints if s.get("id") == a.active
                              or slugify(s.get("name", "")) == a.active), None)
    elif len(inprog) == 1:
        active_sprint = inprog[0]
    elif len(inprog) > 1:
        warnings.append(f"{len(inprog)} in_progress sprints — pass --active to pick the one being built: "
                        + ", ".join(s.get("id", "?") for s in inprog))
    active_ids = {st["id"] for st in active_sprint.get("stories", [])} if active_sprint else set()

    # reconstruct
    boundary = deploy_boundary(repo)
    prod, events = release_events(repo)
    landed = story_dates(repo)
    windows = build_windows(boundary, events)

    rel_buckets = collections.defaultdict(list)   # window label -> done stories
    active_stories, backlog = [], []
    for st in stories:
        st_status = st.get("status")
        if st_status in DONE:
            d = landed.get(st["id"])
            lab = "baseline"
            for L, lo, hi in windows:
                if lo < (d or "0001") <= hi:
                    lab = L; break
            rel_buckets[lab].append(st)
        elif st["id"] in active_ids:
            active_stories.append(st)
        else:
            b = detail(st, status="ready")
            b["target"] = slugify(sprint_of.get(st["id"], ""))
            backlog.append(b)

    datable = sum(1 for st in stories if st["id"] in landed)

    # ---- report ----
    print(f"\n=== /archflow migrate ({'APPLY' if apply else 'DRY-RUN'}) : {v1.get('project')} ===")
    print(f"variant: {variant}   stories: {len(stories)}   datable from git: {datable}/{len(stories)}")
    print(f"deploy boundary: {boundary or 'none'}   prod branch: {prod or 'none (continuous)'}   "
          f"release events: {len(events)}")
    print("reconstructed releases:")
    for L, lo, hi in windows:
        n = len(rel_buckets[L])
        if n:
            print(f"  {L:<26} {n:>3} done   e.g. {[s['id'] for s in rel_buckets[L][:4]]}")
    print(f"active release: {(active_sprint.get('id') if active_sprint else 'NONE')}"
          f"  ({len(active_stories)} stories)")
    print(f"backlog (ready, detailed): {len(backlog)}")
    if warnings:
        print("warnings:")
        for w in dict.fromkeys(warnings):
            print(f"  ! {w}")

    if not apply:
        print("\n(dry-run — nothing written. Review the timeline, then re-run with --apply"
              + (" --active <sprint>" if len(inprog) > 1 and not a.active else "") + ".)")
        return

    # ---- apply: backup entire .archflow/ (except the backup dir itself), then write ----
    bk = os.path.join(af, "backup-v1")
    if os.path.exists(bk):
        shutil.rmtree(bk)
    shutil.copytree(af, bk, ignore=shutil.ignore_patterns("backup-v1"))
    res = os.path.join(af, "releases"); arc = os.path.join(res, "archive")
    os.makedirs(arc, exist_ok=True)

    from datetime import date as _date
    today = _date(*[int(x) for x in git(repo, "log", "-1", "--format=%ad", "--date=short").strip().split("-")]) \
        if git(repo, "log", "-1", "--format=%ad", "--date=short").strip() else None

    def window_date(L, lo, hi, sts):
        """A schema-required date for the release. Never null."""
        if L.startswith("release-"):
            return L.replace("release-", "")
        # latest commit date among this window's done stories
        ds = [landed[s["id"]] for s in sts if s.get("id") in landed]
        if ds:
            return max(ds)
        if hi not in ("9999", "0000") and re.match(r"\d{4}-\d{2}-\d{2}", hi):
            return hi
        if boundary:                       # pre-release baseline: use the boundary date
            return boundary
        return today.isoformat() if today else "1970-01-01"

    shipped, history = [], []
    for L, lo, hi in windows:
        sts = rel_buckets[L]
        if not sts:
            continue
        rslug = slugify(L)
        released_at = window_date(L, lo, hi, sts)
        rel = {"id": rslug, "name": L, "goal": "", "status": "released",
               "version": f"v0-{rslug}", "released_at": released_at,
               "stories": [detail(s, status="done") for s in sts]}
        dump(rel, os.path.join(arc, rslug + ".yaml"))
        shipped.append({"id": rslug, "name": L, "version": f"v0-{rslug}",
                        "released_at": released_at, "file": f"releases/archive/{rslug}.yaml"})
        for s in sts:
            history.append({"story": s["id"], "release": rslug, "shipped_at": released_at,
                            "summary": s.get("title", ""), "touched": {"files": [], "endpoints": [], "screens": []},
                            "acceptance_criteria": [ac.get("text", "") for ac in s.get("acceptance_criteria", [])]})

    active_slug = None
    releases_index = []
    if active_sprint and active_stories:
        active_slug = slugify(active_sprint.get("name", active_sprint.get("id", "current")))
        rel = {"id": active_slug, "name": active_sprint.get("name", active_slug),
               "goal": (active_sprint.get("goal") or "").strip(), "status": "in_progress",
               "stories": [detail(s) for s in active_stories]}
        dump(rel, os.path.join(res, active_slug + ".yaml"))
        releases_index.append({"id": active_slug, "status": "in_progress", "file": f"releases/{active_slug}.yaml"})

    # epic labels — synthesized from every story's prefix (single helper, used for
    # grouping too, so no story lands under an unregistered epic label).
    def epic_of(sid):
        m = re.match(r"^S(\d+)-", sid or "")
        return "E" + m.group(1) if m else "E0"

    epic_names = {}
    for st in stories:
        key = epic_of(st.get("id"))
        epic_names.setdefault(key, (sprint_of.get(st.get("id"), "").split(":", 1)[-1].strip() or key))
    epic_key_order = sorted(epic_names, key=lambda x: (0, int(x[1:])) if x[1:].isdigit() else (1, 0))
    epics = [{"id": k, "name": epic_names[k], "scope": "both"} for k in epic_key_order]

    index = {"schema_version": "2.0", "project": v1.get("project"),
             "project_type": v1.get("project_type", "fullstack"), "mode": "full",
             "epics": epics, "active_release": active_slug,
             "releases": releases_index, "shipped": shipped}
    dump(index, os.path.join(af, "roadmap.yaml"))
    # group backlog by epic (E0 for any oddball id is registered above, so never dangling)
    bl_epics = collections.OrderedDict((k, []) for k in epic_key_order)
    for b in backlog:
        bl_epics.setdefault(epic_of(b["id"]), []).append(b)
    dump({"epics": [{"id": k, "stories": v} for k, v in bl_epics.items() if v]},
         os.path.join(af, "backlog.yaml"))
    dump(history, os.path.join(af, "history.yaml"))

    # update current-phase.yaml: add mode + active_release
    cp_path = os.path.join(af, "current-phase.yaml")
    if os.path.exists(cp_path):
        cp = yaml.safe_load(open(cp_path)) or {}
        cp["mode"] = "full"; cp["active_release"] = active_slug
        dump(cp, cp_path)

    print(f"\nAPPLIED. Wrote roadmap.yaml (index, {len(open(os.path.join(af,'roadmap.yaml')).readlines())} lines), "
          f"backlog.yaml ({len(backlog)}), {len(shipped)} archived releases, "
          f"{'1 active release, ' if active_slug else ''}history.yaml ({len(history)}).")
    print(f"Backup at {bk}. Review, then commit .archflow/. Use /archflow release + /archflow mode next.")


if __name__ == "__main__":
    main()
