#!/usr/bin/env python3
"""Detect and repair drift between a project's .archflow/ and the installed plugin.

A project's .archflow/ is a COPY of framework files made when it was set up. The
plugin then moves on. Nothing has ever reconciled the two, so a project that was
onboarded months ago is running against files that no longer match the agents
reading them.

This finds that drift and repairs the mechanical parts. It is deliberately
conservative: it renames, converts and copies, and it never invents project
content. Anything that needs a judgement is reported for a human.

Usage:
    python3 upgrade_archflow.py [PROJECT] [--apply] [--plugin-root DIR]
                                [--version V] [--json]

Dry-run by default: it prints what it would change and touches nothing.
--apply performs the repairs, backing up every modified file first.

Exit codes:
    0  nothing to do, or --apply succeeded
    1  drift found (dry-run only; this is the "there is work" signal)
    2  could not run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("upgrade_archflow: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

# Agents renamed between plugin versions. Old name -> new name.
RENAMED_AGENTS = {"pm-maestro-reviewer": "pm-reviewer"}

# Framework directories a project should carry a copy of.
FRAMEWORK_DIRS = ["phases", "schemas", "design-systems", "stacks"]
FRAMEWORK_FILES = ["workflow.md", "base-dsl-structure.yaml", "test-accounts.example.yaml",
                   "stack-detection.md"]

# tech_stack (pre-2.2.1) -> stack. The old block never had a reader; this is the
# only place its contents have ever been used.
TECH_STACK_MAP = {
    "language": ("language",),
    "backend": ("backend", "framework"),
    "database": ("backend", "database"),
    "frontend": ("web", "framework"),
}


class Finding:
    """A piece of drift, and WHO repairs it.

    fix_by distinguishes three cases that used to be collapsed into one boolean:
      "script" — this script repairs it under --apply
      "agent"  — /archflow:doctor --fix repairs it, but a script must not: it needs
                 to read and understand a hand-editable document
      "user"   — needs a decision nobody can make on the user's behalf
    `fixable` is kept for compatibility and means "the script does it".
    """

    def __init__(self, key, summary, detail, fixable=True, files=None, fix_by=None):
        self.key, self.summary, self.detail = key, summary, detail
        self.fixable = fixable
        self.fix_by = fix_by or ("script" if fixable else "user")
        self.files = files or []

    def as_dict(self):
        return {"key": self.key, "summary": self.summary, "detail": self.detail,
                "fixable": self.fixable, "fix_by": self.fix_by, "files": self.files}


def yaml_files(archflow: Path):
    for sub in ("releases", "releases/archive", "autopilot", ""):
        d = archflow / sub if sub else archflow
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.yaml")):
            if "schemas" in f.parts or "backup-" in str(f):
                continue
            yield f
    hist = archflow / "history.yaml"
    if hist.exists():
        yield hist


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def find_renamed_agents(archflow: Path):
    hits = {}
    for f in yaml_files(archflow):
        try:
            text = f.read_text()
        except OSError:
            continue
        for old in RENAMED_AGENTS:
            if old in text:
                hits.setdefault(old, []).append(str(f.relative_to(archflow.parent)))
    findings = []
    for old, files in hits.items():
        new = RENAMED_AGENTS[old]
        findings.append(Finding(
            f"renamed-agent:{old}",
            f"{len(files)} file(s) still name the retired agent {old!r}",
            f"It was renamed to {new!r}. A story with assigned: {old} dispatches an agent that no\n"
            f"longer exists, and verified_by: {old} now fails schema validation.",
            files=sorted(set(files)),
        ))
    return findings


def _settings_doc(archflow: Path):
    """Where settings live now, falling back to where they used to.

    A pre-2.1 project still has them in current-phase.yaml; a migrated one has
    project-settings.yaml. Reading both means the stack detectors keep working
    either side of the split.
    """
    # tech_stack FIRST, wherever it is. A half-migrated project can have stack: in
    # the settings file and a stranded tech_stack: still in the cursor; preferring
    # the settings file there hid the leftover from every detector.
    for name in ("current-phase.yaml", "project-settings.yaml"):
        path = archflow / name
        if not path.exists():
            continue
        try:
            doc = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and "tech_stack" in doc:
            return path, doc
    for name in ("project-settings.yaml", "current-phase.yaml"):
        path = archflow / name
        if not path.exists():
            continue
        try:
            doc = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict) and "stack" in doc:
            return path, doc
    # nothing carries a stack; report against the settings file if it exists
    for name in ("project-settings.yaml", "current-phase.yaml"):
        path = archflow / name
        if path.exists():
            try:
                doc = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError:
                doc = {}
            return path, (doc if isinstance(doc, dict) else {})
    return None, None


def find_tech_stack(archflow: Path):
    cp, doc = _settings_doc(archflow)
    if cp is None:
        return []
    if not isinstance(doc, dict) or "tech_stack" not in doc:
        return []
    if doc.get("stack"):
        return [Finding(
            "tech-stack-leftover",
            f"{cp.name} has both tech_stack: and stack:",
            "stack: is the one agents read. The tech_stack: block is dead and can be deleted.",
            files=[str(cp.relative_to(archflow.parent))],
        )]
    return [Finding(
        "tech-stack-convert",
        f"{cp.name} has tech_stack: but no stack:",
        "Agents read stack:. Without it each one stops and asks on its first dispatch. The old\n"
        "block holds most of the answer and converts cleanly.",
        files=[str(cp.relative_to(archflow.parent))],
    )]


def find_missing_stack(archflow: Path):
    cp, doc = _settings_doc(archflow)
    if cp is None:
        return []
    if not isinstance(doc, dict) or doc.get("tech_stack") or doc.get("stack"):
        return []
    return [Finding(
        "stack-absent",
        f"{cp.name} has no stack: block",
        "Agents carry no technology of their own. Each will detect from the repo and ASK on its\n"
        "first dispatch. Populate it with /archflow:onboard detection, or by hand from stacks/.",
        fixable=False,
        files=[str(cp.relative_to(archflow.parent))],
    )]


def find_missing_framework_files(archflow: Path, plugin_skill: Path):
    if not plugin_skill or not plugin_skill.is_dir():
        return []
    missing = []
    for d in FRAMEWORK_DIRS:
        src = plugin_skill / d
        if not src.is_dir():
            continue
        for f in sorted(src.glob("*")):
            if f.is_dir():
                continue
            dst = archflow / d / f.name
            if not dst.exists():
                missing.append(f"{d}/{f.name}")
    for name in FRAMEWORK_FILES:
        if (plugin_skill / name).exists() and not (archflow / name).exists():
            missing.append(name)
    if not missing:
        return []
    return [Finding(
        "missing-framework-files",
        f"{len(missing)} framework file(s) the plugin ships are absent from .archflow/",
        "These are copied at setup and never refreshed, so a project set up on an older plugin\n"
        "runs against files the agents no longer match. Agents told to read a missing design\n"
        "system stop rather than guess.",
        files=missing,
    )]


# Fields that moved out of current-phase.yaml in schema v2.1.
MOVED_TO_SETTINGS = ["project_type", "api_contract_path", "stack", "optional_agents"]


def find_split_project_settings(archflow: Path):
    """v2.0 kept settings and the phase cursor in one file. v2.1 splits them."""
    cp = archflow / "current-phase.yaml"
    if not cp.exists():
        return []
    try:
        doc = yaml.safe_load(cp.read_text()) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(doc, dict):
        return []
    stranded = [k for k in MOVED_TO_SETTINGS if k in doc]
    if not stranded:
        return []
    return [Finding(
        "split-project-settings",
        f"{len(stranded)} setting(s) still live in current-phase.yaml (schema v2.1 moved them)",
        "current-phase.yaml is a CURSOR, rewritten at every phase transition. Settings that change\n"
        "almost never belong in project-settings.yaml, or a real settings change is buried in phase\n"
        f"churn. Stranded: {', '.join(stranded)}.\n"
        "Repaired by /archflow:doctor --fix, which reads the file and moves the keys itself — a\n"
        "script cannot, because this file is hand-editable and its shape varies per project.",
        fixable=False, fix_by="agent",
        files=[str(cp.relative_to(archflow.parent))],
    )]


def find_roadmap_schema_version(archflow: Path):
    """roadmap.yaml carries the framework schema version. v2.1 moved it."""
    rm = archflow / "roadmap.yaml"
    if not rm.exists():
        return []
    try:
        doc = yaml.safe_load(rm.read_text()) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(doc, dict):
        return []
    found = doc.get("schema_version")
    if found in (None, "2.1"):
        return []
    if str(found).startswith("1."):
        return [Finding(
            "schema-v1",
            f"roadmap.yaml is schema_version {found!r} — a v1.0 project",
            "This needs /archflow:migrate, not this repair. It restructures the whole roadmap.",
            fixable=False,
            files=["`.archflow/roadmap.yaml`"],
        )]
    return [Finding(
        "roadmap-schema-version",
        f"roadmap.yaml is schema_version {found!r}, the framework is on 2.1",
        "2.1 split project settings out of current-phase.yaml. The data model is otherwise\n"
        "unchanged, so this is a one-line bump once the settings have been split.",
        files=[str(rm.relative_to(archflow.parent))],
    )]


def find_version_stamp(archflow: Path, version):
    cp = archflow / "current-phase.yaml"
    if not cp.exists() or not version:
        return []
    try:
        doc = yaml.safe_load(cp.read_text()) or {}
    except yaml.YAMLError:
        return []
    current = doc.get("plugin_version") if isinstance(doc, dict) else None
    if current == version:
        return []
    return [Finding(
        "version-stamp",
        f"plugin_version is {current!r}, installed plugin is {version!r}",
        "Without a stamp there is no signal that a project has fallen behind the plugin.",
        files=[str(cp.relative_to(archflow.parent))],
    )]


# --------------------------------------------------------------------------
# Repair
# --------------------------------------------------------------------------

_BACKED_UP = set()


def _atomic_write(path: Path, text: str):
    """Write via a temp file and rename, so an interrupt cannot leave a half file.

    The split rewrites two documents. Without this, an interrupt between them
    leaves both holding the settings — the exact duplicated state that the
    conflict check then refuses to resolve on the next run.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def backup(path: Path, archflow: Path, stamp: str):
    """Copy a file aside before its first modification in this run.

    Once only: two repairs can touch the same file, and backing up the second
    time would capture the already-repaired content, leaving no way back.
    """
    key = str(path)
    if key in _BACKED_UP:
        return
    dest = archflow / f"backup-upgrade-{stamp}" / path.relative_to(archflow)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    _BACKED_UP.add(key)


def apply_renames(archflow: Path, stamp: str):
    changed = []
    for f in yaml_files(archflow):
        try:
            text = f.read_text()
        except OSError:
            continue
        new = text
        for old, repl in RENAMED_AGENTS.items():
            new = re.sub(rf"(?<![\w-]){re.escape(old)}(?![\w-])", repl, new)
        if new != text:
            backup(f, archflow, stamp)
            _atomic_write(f, new)
            changed.append(str(f.relative_to(archflow.parent)))
    return changed


def apply_tech_stack(archflow: Path, stamp: str):
    cp, _ = _settings_doc(archflow)
    if cp is None:
        return None
    text = cp.read_text()
    doc = yaml.safe_load(text) or {}
    old = doc.get("tech_stack")
    if not isinstance(old, dict):
        return None

    # The old tech_stack was FREE TEXT. Real projects wrote things like
    # "NestJS + PostgreSQL" and "Next.js + React + Tailwind CSS" into a single field.
    # Mapping those 1:1 into a structured field produces a value that is not null, so
    # no agent will ask about it, and not a framework name either, so every agent
    # misreads it. An honest null is better: the agent asks with the repo in front of
    # it. The original text is preserved in notes: so nothing is lost.
    def compound(v):
        return isinstance(v, str) and re.search(r"\s\+\s|,", v)

    stack, unclear = {}, {}
    for src_key, path in TECH_STACK_MAP.items():
        val = old.get(src_key)
        if val in (None, "", "null"):
            continue
        if compound(val):
            unclear[src_key] = val
            continue
        if len(path) == 1:
            stack[path[0]] = val
        else:
            stack.setdefault(path[0], {})[path[1]] = val

    lines = ["stack:",
             "  # Converted from the retired tech_stack: block by /archflow:doctor --fix.",
             "  # Fields the old block could not express are null: agents will ask when they need",
             "  # them. See .archflow/schemas/project-settings-schema.yaml."]
    if unclear:
        lines += ["  #",
                  "  # Some old values were compound free text and could not be mapped to a single",
                  "  # field. They are in notes: below — split them into fields and delete the note."]
    if "language" in stack:
        lines.append(f"  language: {stack['language']}")
    if "backend" in stack:
        b = stack["backend"]
        lines.append("  backend: {" + ", ".join(f"{k}: {v}" for k, v in b.items()) +
                     ", orm: null, auth: null}")
    if "web" in stack:
        w = stack["web"]
        lines.append("  web: {" + ", ".join(f"{k}: {v}" for k, v in w.items()) +
                     ", language: null, styling: null, state: null}")
    lines += ["  test: {unit: null, integration: null, e2e: null}",
              "  ci: null", "  hosting: null", "  package_manager: null"]

    if unclear:
        note = "; ".join(f"{k}: {v}" for k, v in unclear.items())
        lines.append(f'  notes: "unmapped from the old tech_stack: {note}"')
    block = "\n".join(lines) + "\n"

    # Replace the tech_stack block in place, preserving everything around it.
    pattern = re.compile(r"^tech_stack:\s*\n(?:[ \t]+\S.*\n|[ \t]*\n)*", re.M)
    if not pattern.search(text):
        return None
    backup(cp, archflow, stamp)
    _atomic_write(cp, pattern.sub(block, text, count=1))
    return str(cp.relative_to(archflow.parent))


def apply_missing_files(archflow: Path, plugin_skill: Path, missing):
    copied = []
    for rel in missing:
        src, dst = plugin_skill / rel, archflow / rel
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied


def apply_roadmap_schema_version(archflow: Path, stamp: str):
    """Bump roadmap.yaml to 2.1. Only safe once the settings split is done.

    A one-line, one-key edit on a known field, done by text substitution so the rest
    of the file — comments, ordering, everything — is untouched.
    """
    if (archflow / "current-phase.yaml").exists():
        try:
            cp = yaml.safe_load((archflow / "current-phase.yaml").read_text()) or {}
        except yaml.YAMLError:
            return None
        if isinstance(cp, dict) and any(k in cp for k in MOVED_TO_SETTINGS):
            return None  # split first; claiming 2.1 while still v2.0-shaped would lie
    rm = archflow / "roadmap.yaml"
    text = rm.read_text()
    # Column 0 only. `\s*` here would match an INDENTED schema_version inside a
    # nested block and, with count=1, rewrite that instead of the real top-level
    # key — corrupting unrelated data while reporting success.
    new, n = re.subn(r'^(schema_version:\s*)["\']?[0-9.]+["\']?',
                     r'\1"2.1"', text, count=1, flags=re.M)
    if not n:
        return None
    backup(rm, archflow, stamp)
    _atomic_write(rm, new)
    return str(rm.relative_to(archflow.parent))


def apply_version_stamp(archflow: Path, version: str, stamp: str):
    cp = archflow / "current-phase.yaml"
    if not cp.exists():
        return None
    text = cp.read_text()
    backup(cp, archflow, stamp)
    if re.search(r"^plugin_version:.*$", text, re.M):
        text = re.sub(r"^plugin_version:.*$", f'plugin_version: "{version}"', text, count=1, flags=re.M)
    else:
        # Anchor on a field the cursor actually still has. project_type moved out in
        # v2.1, and the split runs before this, so anchoring there never matched.
        text, n = re.subn(r"^(phase_file:.*\n)", rf'\1plugin_version: "{version}"\n',
                          text, count=1, flags=re.M)
        if not n:
            text = text.rstrip("\n") + f'\nplugin_version: "{version}"\n'
    _atomic_write(cp, text)
    return str(cp.relative_to(archflow.parent))


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Detect and repair .archflow/ drift after a plugin upgrade.")
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--apply", action="store_true", help="perform the repairs (default: dry run)")
    ap.add_argument("--plugin-root", help="the installed plugin directory")
    ap.add_argument("--version", help="installed plugin version, for the stamp")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    archflow = project / ".archflow"
    if not archflow.is_dir():
        print(f"upgrade_archflow: no .archflow/ in {project}", file=sys.stderr)
        return 2

    plugin_root = Path(args.plugin_root).resolve() if args.plugin_root else None
    plugin_skill = plugin_root / "skills" / "archflow" if plugin_root else None
    version = args.version
    if not version and plugin_root:
        manifest = plugin_root / ".claude-plugin" / "plugin.json"
        if manifest.exists():
            try:
                version = json.loads(manifest.read_text()).get("version")
            except (OSError, ValueError):
                version = None

    findings = (find_renamed_agents(archflow)
                + find_split_project_settings(archflow)
                + find_roadmap_schema_version(archflow)
                + find_tech_stack(archflow)
                + find_missing_stack(archflow)
                + find_missing_framework_files(archflow, plugin_skill)
                + find_version_stamp(archflow, version))

    if not args.apply:
        if args.as_json:
            print(json.dumps({"drift": bool(findings),
                              "findings": [f.as_dict() for f in findings]}, indent=2))
        elif findings:
            print(f"\n  {len(findings)} item(s) of drift between this project and the plugin\n")
            for f in findings:
                mark = {"script": "fix", "agent": "fix", "user": "manual"}[f.fix_by]
                print(f"  [{mark}] {f.summary}")
                for line in f.detail.splitlines():
                    print(f"        {line}")
                for name in f.files[:8]:
                    print(f"        - {name}")
                if len(f.files) > 8:
                    print(f"        ... and {len(f.files) - 8} more")
                print()
            print("  Run /archflow:doctor --fix to apply the repairable items.\n")
        else:
            print("  .archflow/ is in step with the installed plugin")
        return 1 if findings else 0

    # --apply
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    actions, deferred = [], []
    keys = {f.key.split(":")[0] for f in findings}

    if "renamed-agent" in keys:
        for c in apply_renames(archflow, stamp):
            actions.append(f"renamed the retired agent in {c}")
    # Order matters: convert tech_stack -> stack BEFORE the split, so the resulting
    # stack: block is moved along with the other settings instead of being stranded
    # in the cursor by a later pass.
    if any(f.key == "tech-stack-convert" for f in findings):
        r = apply_tech_stack(archflow, stamp)
        if r:
            actions.append(f"converted tech_stack: to stack: in {r}")
    if "missing-framework-files" in keys and plugin_skill:
        missing = next(f.files for f in findings if f.key == "missing-framework-files")
        copied = apply_missing_files(archflow, plugin_skill, missing)
        if copied:
            actions.append(f"copied {len(copied)} missing framework file(s) from the plugin")
    if "roadmap-schema-version" in keys:
        r = apply_roadmap_schema_version(archflow, stamp)
        if r:
            actions.append(f"bumped schema_version to 2.1 in {r}")
        else:
            deferred.append(
                "roadmap.yaml stays at schema_version 2.0 until the settings split is done — "
                "bumping first would claim 2.1 on a file that is still v2.0-shaped")
    if "version-stamp" in keys and version:
        r = apply_version_stamp(archflow, version, stamp)
        if r:
            actions.append(f"stamped plugin_version: {version} in {r}")

    manual = [f for f in findings if f.fix_by == "user"]
    by_agent = [f for f in findings if f.fix_by == "agent"]

    if args.as_json:
        print(json.dumps({"applied": actions,
                          "deferred": deferred,
                          "manual": [f.as_dict() for f in manual],
                          "backup": f".archflow/backup-upgrade-{stamp}" if actions else None}, indent=2))
        return 0

    if actions:
        print("\n  Applied:")
        for a in actions:
            print(f"    - {a}")
        print(f"\n  Originals backed up to .archflow/backup-upgrade-{stamp}/")
    else:
        print("  nothing to apply")
    if deferred:
        print("\n  Deferred until the steps above are done:")
        for d in deferred:
            print(f"    - {d}")
    if by_agent:
        print("\n  Still to do, following /archflow:doctor --fix:")
        for f in by_agent:
            print(f"    - {f.summary}")
    if manual:
        print("\n  Needs a decision only you can make:")
        for f in manual:
            print(f"    - {f.summary}")
            for line in f.detail.splitlines():
                print(f"      {line}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
