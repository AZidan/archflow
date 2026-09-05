#!/usr/bin/env python3
"""Validate a project's .archflow/ state files against their schemas.

The state files are the contract every Archflow agent reads. A field that drifts
from its schema is a bug that surfaces later as an agent doing the wrong thing,
usually somewhere unrelated. This catches it at the file.

Usage:
    python3 validate_archflow.py [PROJECT_DIR] [--schemas DIR] [--quiet] [--json]

Exit codes:
    0  everything valid (or nothing to validate)
    1  at least one violation
    2  could not run (missing schemas, unreadable YAML)

Depends only on PyYAML, which Archflow already requires for /archflow:migrate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("validate_archflow: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


# --------------------------------------------------------------------------
# The schema dialect
#
# These schemas are hand-written YAML, not JSON Schema. The subset in use:
#
#   $root / $root_is_list  which named definition validates the document
#   type                   string | number | boolean | object | array | "null",
#                          or a list of those
#   required               a list of key names (on an object definition), or
#                          the boolean false (on a property, meaning optional)
#   properties             map of name -> subschema
#   items                  subschema for array elements
#   enum                   list of permitted values
#   pattern                regex the string must fully match
#   $ref                   "#/definition_name"
#   format                 iso8601 (checked loosely; a date or datetime prefix)
#
# Anything else (description, example, default) is documentation and ignored.
# --------------------------------------------------------------------------

SCALARS = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}

# Files that are validated, and the schema each uses.
TARGETS = [
    ("current-phase.yaml", "current-phase-schema.yaml", False),
    ("roadmap.yaml",       "roadmap-schema.yaml",       False),
    ("backlog.yaml",       "backlog-schema.yaml",       False),
    ("history.yaml",       "history-schema.yaml",       False),
    ("releases/*.yaml",    "release-schema.yaml",       True),
    ("releases/archive/*.yaml", "release-schema.yaml",  True),
    ("autopilot/*.yaml",   "autopilot-schema.yaml",     True),
]


class Violation:
    __slots__ = ("path", "field", "message")

    def __init__(self, path: str, field: str, message: str):
        self.path, self.field, self.message = path, field, message

    def __str__(self) -> str:
        where = f"{self.path}" + (f" :: {self.field}" if self.field else "")
        return f"{where}\n      {self.message}"


def _type_name(value) -> str:
    if value is None:
        return "null"
    for name, py in SCALARS.items():
        if name == "integer":
            continue
        if isinstance(value, py) and not (name == "number" and isinstance(value, bool)):
            return name
    return type(value).__name__


def _matches_type(value, declared) -> bool:
    """`declared` is a type name or a list of them. "null" permits None."""
    if declared is None:
        return True
    names = declared if isinstance(declared, list) else [declared]
    for name in names:
        if name in (None, "null", "any"):
            if value is None or name == "any":
                return True
            continue
        py = SCALARS.get(name)
        if py is None:
            return True  # unknown type name: do not invent a failure
        if name == "number" and isinstance(value, bool):
            continue     # bool is an int in Python; do not accept it as a number
        if isinstance(value, py):
            return True
    return False


class Validator:
    def __init__(self, schema_doc: dict, schema_name: str):
        self.doc = schema_doc
        self.name = schema_name
        self.root = schema_doc.get("$root")
        self.root_is_list = bool(schema_doc.get("$root_is_list"))

    def resolve(self, node):
        """Follow a $ref, one hop at a time, guarding against a cycle."""
        seen = set()
        while isinstance(node, dict) and "$ref" in node:
            target = str(node["$ref"]).lstrip("#/")
            if target in seen:
                return {}
            seen.add(target)
            node = self.doc.get(target)
            if node is None:
                return {}
        return node if isinstance(node, dict) else {}

    def root_schema(self):
        if self.root:
            return self.doc.get(self.root)
        # no named definitions: the document itself is the schema
        return {k: v for k, v in self.doc.items() if not k.startswith("$")}

    def validate(self, data, file_label: str) -> list:
        schema = self.root_schema()
        if not schema:
            return [Violation(file_label, "", f"schema {self.name} declares no usable root")]
        if self.root_is_list:
            if not isinstance(data, list):
                return [Violation(file_label, "", f"expected a list of {self.root} entries, found {_type_name(data)}")]
            out = []
            for i, item in enumerate(data):
                out += self._check(item, schema, file_label, f"[{i}]")
            return out
        return self._check(data, schema, file_label, "")

    def _check(self, value, schema, label: str, path: str) -> list:
        schema = self.resolve(schema)
        if not schema:
            return []
        out = []

        declared = schema.get("type")
        # A property marked `required: false` may simply be absent; absence is
        # handled by the parent, so a present null is only an error when the
        # declared type does not admit null.
        if not _matches_type(value, declared):
            want = declared if isinstance(declared, str) else "/".join(str(t) for t in (declared or []))
            out.append(Violation(label, path or "(root)",
                                 f"expected {want}, found {_type_name(value)}"))
            return out  # a wrong type makes every nested check meaningless

        if value is None:
            return out

        enum = schema.get("enum")
        if enum is not None and value not in enum:
            shown = ", ".join(repr(e) for e in enum[:8]) + (" ..." if len(enum) > 8 else "")
            out.append(Violation(label, path or "(root)", f"{value!r} is not one of: {shown}"))

        pattern = schema.get("pattern")
        if pattern and isinstance(value, str) and not re.fullmatch(pattern, value):
            out.append(Violation(label, path or "(root)", f"{value!r} does not match {pattern}"))

        if schema.get("format") == "iso8601" and isinstance(value, str):
            if not re.match(r"^\d{4}-\d{2}-\d{2}([T ]|$)", value):
                out.append(Violation(label, path or "(root)", f"{value!r} is not an ISO-8601 date or datetime"))

        if isinstance(value, dict):
            out += self._check_object(value, schema, label, path)
        elif isinstance(value, list):
            items = schema.get("items")
            if items:
                for i, item in enumerate(value):
                    out += self._check(item, items, label, f"{path}[{i}]")
        return out

    def _check_object(self, value: dict, schema, label: str, path: str) -> list:
        out = []
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    out.append(Violation(label, f"{path}.{key}".lstrip("."), "required field is missing"))
        props = schema.get("properties") or {}
        for key, sub in props.items():
            if key in value:
                out += self._check(value[key], sub, label, f"{path}.{key}".lstrip("."))
        return out


def load_yaml(path: Path):
    try:
        with path.open() as fh:
            return yaml.safe_load(fh), None
    except yaml.YAMLError as exc:
        return None, f"YAML will not parse: {exc}"
    except OSError as exc:
        return None, f"cannot read: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate .archflow/ state files against their schemas.")
    ap.add_argument("project", nargs="?", default=".", help="project root (default: cwd)")
    ap.add_argument("--schemas", help="schema directory (default: <project>/.archflow/schemas)")
    ap.add_argument("--quiet", action="store_true", help="print only failures")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    args = ap.parse_args()

    project = Path(args.project).resolve()
    archflow = project / ".archflow"
    schema_dir = Path(args.schemas) if args.schemas else archflow / "schemas"

    if not archflow.is_dir():
        print(f"validate_archflow: no .archflow/ in {project}", file=sys.stderr)
        return 2
    if not schema_dir.is_dir():
        print(f"validate_archflow: no schemas at {schema_dir}", file=sys.stderr)
        return 2

    violations, checked, skipped = [], [], []

    for pattern, schema_file, is_glob in TARGETS:
        schema_path = schema_dir / schema_file
        if not schema_path.exists():
            skipped.append((pattern, f"schema {schema_file} not found"))
            continue
        schema_doc, err = load_yaml(schema_path)
        if err or not isinstance(schema_doc, dict):
            print(f"validate_archflow: {schema_path}: {err or 'not a mapping'}", file=sys.stderr)
            return 2
        validator = Validator(schema_doc, schema_file)

        paths = sorted(archflow.glob(pattern)) if is_glob else [archflow / pattern]
        for target in paths:
            if not target.exists():
                if not is_glob:
                    skipped.append((str(target.relative_to(project)), "not present"))
                continue
            data, err = load_yaml(target)
            rel = str(target.relative_to(project))
            if err:
                violations.append(Violation(rel, "", err))
                continue
            if data is None:
                skipped.append((rel, "empty file"))
                continue
            checked.append(rel)
            violations += validator.validate(data, rel)

    if args.as_json:
        print(json.dumps({
            "ok": not violations,
            "checked": checked,
            "skipped": [{"file": f, "reason": r} for f, r in skipped],
            "violations": [{"file": v.path, "field": v.field, "message": v.message} for v in violations],
        }, indent=2))
        return 1 if violations else 0

    if violations:
        print(f"\n  {len(violations)} violation(s) across {len(checked)} file(s)\n")
        current = None
        for v in violations:
            if v.path != current:
                print(f"  {v.path}")
                current = v.path
            field = v.field or "(root)"
            print(f"    {field}")
            print(f"      {v.message}")
        print()
        return 1

    if not args.quiet:
        if checked:
            print(f"  {len(checked)} state file(s) valid: " + ", ".join(checked))
        else:
            print("  no state files to validate")
        for f, r in skipped:
            print(f"  skipped {f} ({r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
