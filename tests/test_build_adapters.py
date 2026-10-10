"""scripts/build-adapters.mjs ships the hook runtime to every host through one helper.

S7-04: adding a hook must require only a HOOK_SCRIPTS entry. These tests hold that
structurally: every plugin hook is either in HOOK_SCRIPTS or declared Claude-only,
every adapter's hook root carries every HOOK_SCRIPTS file plus lib/, no host copies a
hook script outside copyHookRuntime, every host (and Claude Code itself) runs every hook
it ships, and the committed adapters match the plugin.
"""

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "scripts" / "build-adapters.mjs"
PLUGIN_HOOKS = REPO / "plugin" / "hooks"
ADAPTERS = REPO / "adapters"


def _build_info():
    """HOOK_SCRIPTS, CLAUDE_ONLY_HOOKS and the host names, as build-adapters.mjs reports them."""
    proc = subprocess.run(
        ["node", str(BUILD), "--list-hooks"], capture_output=True, text=True, timeout=30, cwd=REPO
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _hook_lists():
    info = _build_info()
    return info["hook_scripts"], info["claude_only_hooks"]


def _hosts():
    hosts = _build_info()["hosts"]
    assert hosts, "build-adapters.mjs --list-hooks reported no hosts"
    return hosts


def _hook_roots(host):
    """Directories in adapters/<host>/ that copyHookRuntime populated (it alone writes lib/commands.json)."""
    return sorted(p.parent.parent for p in (ADAPTERS / host).rglob("lib/commands.json"))


def test_every_hook_script_exists_in_the_plugin():
    scripts, claude_only = _hook_lists()
    assert scripts, "HOOK_SCRIPTS is empty"
    missing = [f for f in scripts + claude_only if not (PLUGIN_HOOKS / f).is_file()]
    assert not missing, f"listed in build-adapters.mjs but absent from plugin/hooks/: {missing}"


def test_no_plugin_hook_is_silently_left_out():
    scripts, claude_only = _hook_lists()
    both = set(scripts) & set(claude_only)
    assert not both, f"in both HOOK_SCRIPTS and CLAUDE_ONLY_HOOKS: {sorted(both)}"
    unlisted = sorted(
        p.name for p in PLUGIN_HOOKS.glob("*.mjs") if p.name not in set(scripts) | set(claude_only)
    )
    assert not unlisted, (
        f"plugin/hooks/ has {unlisted} in neither HOOK_SCRIPTS nor CLAUDE_ONLY_HOOKS "
        "(scripts/build-adapters.mjs); add it to one so adapters do not silently lose it"
    )


def test_every_host_ships_the_full_hook_runtime():
    scripts, claude_only = _hook_lists()
    for host in _hosts():
        roots = _hook_roots(host)
        assert len(roots) == 1, f"adapters/{host}: expected one hook runtime root, found {roots}"
        root = roots[0]
        missing = [f for f in scripts if not (root / "hooks" / f).is_file()]
        assert not missing, f"adapters/{host}: {root} lacks hooks {missing}"
        leaked = [f for f in claude_only if (root / "hooks" / f).exists()]
        assert not leaked, f"adapters/{host}: Claude-only hooks shipped: {leaked}"
        for lib in (REPO / "plugin" / "lib").iterdir():
            assert (root / "lib" / lib.name).is_file(), f"adapters/{host}: lib/{lib.name} missing"


# --- Wiring: a copied hook must also be RUN by each host ---------------------------------
#
# Each host lists the files that run its hook scripts, how to read each one, and where to
# make the per-host edit. Only invocation sites count, never comments or prose:
#   json — the `command` / `bash` strings of the parsed hooks file
#   code — quoted string literals ("x.mjs") after // and /* */ comments are stripped
#   md   — a `node <path>/x.mjs` invocation the agent is told to run
# Paths are relative to the repo; "claude" is the plugin itself.
HOOK_WIRING = {
    "claude": [("plugin/hooks/hooks.json", "json", "plugin/hooks/hooks.json")],
    "codex": [("adapters/codex/.codex/hooks.json", "json", "the `hooks` object in HOSTS.codex.emit")],
    "gemini": [("adapters/gemini/hooks/hooks.json", "json", "the `hooks` object in HOSTS.gemini.emit")],
    "copilot": [
        ("adapters/copilot/.github/hooks/archflow.json", "json", "the archflow.json hooks in HOSTS.copilot.emit")
    ],
    "cursor": [
        ("adapters/cursor/.cursor/hooks.json", "json", "the .cursor/hooks.json events in HOSTS.cursor.emit"),
        ("adapters/cursor/.cursor/archflow/hooks/cursor-bridge.mjs", "code", "the CURSOR_BRIDGE script"),
    ],
    "opencode": [("adapters/opencode/.opencode/plugins/archflow.ts", "code", "the OPENCODE_PLUGIN script")],
    "generic": [("adapters/generic/AGENTS.archflow.md", "md", "the session-start instructions in HOSTS.generic.emit")],
}

# (host, script) pairs a host deliberately does not run. One-line reason each.
NOT_WIRED = {
    ("generic", "check-state.mjs"): "no lifecycle hooks, so there is no Stop event to run it on",
    ("generic", "guard-git.mjs"): "replaced by a real git pre-push hook (archflow-install-git-guard.sh)",
}


def _script_re(script):
    return r"(?<![\w.-])" + re.escape(script) + r"(?![\w.-])"


def _json_commands(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("command", "bash") and isinstance(v, str):
                yield v
            else:
                yield from _json_commands(v)
    elif isinstance(node, list):
        for v in node:
            yield from _json_commands(v)


def _strip_comments(code):
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    return re.sub(r"(?m)(?<![:\"'\\])//.*$", "", code)


def _invokes(path, kind, script):
    text = path.read_text()
    if kind == "json":
        return any(re.search(_script_re(script), c) for c in _json_commands(json.loads(text)))
    if kind == "code":
        return re.search(r"[\"'`]" + re.escape(script) + r"[\"'`]", _strip_comments(text)) is not None
    if kind == "md":
        return re.search(r"\bnode\s+\S*/" + re.escape(script) + r"(?![\w.-])", text) is not None
    raise ValueError(kind)


def _required(host):
    scripts, claude_only = _hook_lists()
    return scripts + claude_only if host == "claude" else scripts


def test_every_hook_script_is_wired_on_every_host():
    """Copying a hook is automatic; running it is a per-host edit this test asks for."""
    scripts, claude_only = _hook_lists()
    assert set(HOOK_WIRING) == set(_hosts()) | {"claude"}, "HOOK_WIRING must name claude + every host in HOSTS"
    stale = [k for k in NOT_WIRED if k[0] not in HOOK_WIRING or k[1] not in _required(k[0])]
    assert not stale, f"NOT_WIRED entries for unknown hosts or scripts: {stale}"

    unwired = []
    for host, files in HOOK_WIRING.items():
        for rel, _, _ in files:
            assert (REPO / rel).is_file(), f"{rel} is missing; regenerate the adapters"
        for script in _required(host):
            if (host, script) in NOT_WIRED:
                continue
            if not any(_invokes(REPO / rel, kind, script) for rel, kind, _ in files):
                where = " or ".join(f"{w} ({rel})" for rel, _, w in files)
                src = "" if host == "claude" else " in scripts/build-adapters.mjs, then regenerate"
                unwired.append(
                    f"{host}: {script} is never run; wire it in {where}{src}, "
                    f"or add ({host!r}, {script!r}) to NOT_WIRED with a reason"
                )
    assert not unwired, "\n".join(unwired)


def test_cursor_events_route_through_the_bridge():
    hooks = json.loads((ADAPTERS / "cursor" / ".cursor" / "hooks.json").read_text())["hooks"]
    for event, handlers in hooks.items():
        for h in handlers:
            assert "cursor-bridge.mjs" in h["command"], f"cursor {event} bypasses the bridge: {h}"


def test_generic_names_the_session_start_scripts():
    path = ADAPTERS / "generic" / "AGENTS.archflow.md"
    for script in ("check-upgrade.mjs", "telemetry.mjs"):
        assert _invokes(path, "md", script), (
            f"generic: AGENTS.archflow.md no longer asks the agent to run {script}; "
            "fix the session-start instructions in HOSTS.generic.emit (scripts/build-adapters.mjs)"
        )


# Anything that reads from plugin/hooks, or copies the whole plugin tree (which includes it).
HOOK_SOURCE = re.compile(r"""join\(\s*PLUGIN\s*,\s*["'`]hooks["'`]|\b(?:cpSync|copyTree)\(\s*PLUGIN\s*[,)]""")


def test_hook_scripts_are_copied_only_by_the_helper():
    """A per-host copy of the hooks dir, by any route, is the drift S7-04 removed."""
    src = BUILD.read_text()
    start = src.index("function copyHookRuntime(")
    end = src.index("\n}\n", start)
    outside = src[:start] + src[end:]
    offenders = [line.strip() for line in outside.splitlines() if HOOK_SOURCE.search(line)]
    assert not offenders, f"plugin/hooks read or copied outside copyHookRuntime: {offenders}"
    calls = len(re.findall(r"\bcopyHookRuntime\(", outside))
    assert calls == len(_hosts()), f"{calls} copyHookRuntime calls for {len(_hosts())} hosts"


def test_adapters_match_the_plugin():
    proc = subprocess.run(
        ["node", str(BUILD), "--check"], capture_output=True, text=True, timeout=120, cwd=REPO
    )
    assert proc.returncode == 0, (
        "adapters/ is stale; run: node scripts/build-adapters.mjs\n" + proc.stdout + proc.stderr
    )


# --------------------------------------------------------------------------
# ${CLAUDE_PLUGIN_ROOT} paths resolve on every host
# --------------------------------------------------------------------------

# What each host's vocab turns ${CLAUDE_PLUGIN_ROOT} into, and where a command file lands. A host
# has exactly two rewrites of that variable (commandPathRule, then the root), so every path derived
# from it starts with one of these two prefixes. Gemini's root is the installed extension; inside
# the package it is the adapter's own top level.
PLUGIN_ROOTS = {
    "codex": (".codex/archflow", r"\.agents/skills/archflow-(?:[a-z-]+|<name>)/SKILL\.md"),
    "generic": (".agents/archflow", r"\.agents/skills/archflow-(?:[a-z-]+|<name>)/SKILL\.md"),
    "copilot": (".github/archflow", r"\.github/skills/archflow-(?:[a-z-]+|<name>)/SKILL\.md"),
    "cursor": (".cursor/archflow", r"\.cursor/commands/archflow-(?:[a-z-]+|<name>)\.md"),
    "opencode": (".opencode/archflow", r"\.opencode/commands/archflow-(?:[a-z-]+|<name>)\.md"),
    "gemini": ("$HOME/.gemini/extensions/archflow", None),
}
PROSE = {".md", ".toml", ".mdc", ".yaml", ".yml", ".json", ".ts"}


def _generated_text(host):
    """(relative path, text) for every generated text file, not following the in-adapter symlinks
    (they point back at the skill tree, which is scanned once on its own)."""
    root = ADAPTERS / host
    for path in sorted(root.rglob("*")):
        if path.suffix not in PROSE or not path.is_file():
            continue
        if any((root / p).is_symlink() for p in path.relative_to(root).parents):
            continue
        yield path.relative_to(root), path.read_text()


def _derived_paths(host, text):
    prefix, command = PLUGIN_ROOTS[host]
    patterns = [re.escape(prefix) + r"(?:/[^\s`\"'(),;*]*)?"]
    if command:
        patterns.append(command)
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            yield m.group(0).rstrip(".:")


def _resolve(host, path):
    prefix, _ = PLUGIN_ROOTS[host]
    path = path.replace("<name>", "help")
    if host == "gemini":
        path = path[len(prefix):].lstrip("/")
    return ADAPTERS / host / path


def test_every_plugin_root_host_is_covered():
    assert sorted(PLUGIN_ROOTS) == sorted(_hosts()), "add the new host to PLUGIN_ROOTS"


def test_every_plugin_root_path_resolves_in_its_adapter():
    """S2-06 I-2: ${CLAUDE_PLUGIN_ROOT}/commands/<n>.md used to become <host>/archflow/commands/<n>.md,
    which no adapter generates (commands ship in each host's own layout). Every path derived from the
    plugin root, in every generated file, must name a file or directory the adapter really has."""
    dead = []
    for host in sorted(PLUGIN_ROOTS):
        seen = 0
        for rel, text in _generated_text(host):
            for path in _derived_paths(host, text):
                seen += 1
                if not _resolve(host, path).exists():
                    dead.append(f"adapters/{host}/{rel}: {path}")
        assert seen, f"found no plugin-root paths in adapters/{host}; is PLUGIN_ROOTS stale?"
    assert not dead, "plugin-root paths that point at nothing:\n" + "\n".join(sorted(set(dead)))


def test_no_generated_prompt_keeps_the_claude_only_root():
    """${CLAUDE_PLUGIN_ROOT} is set only for Claude Code plugins. A prompt that still carries it
    tells the host's model to read a path it cannot resolve."""
    left = []
    for host in sorted(PLUGIN_ROOTS):
        for rel, text in _generated_text(host):
            if rel.suffix in {".md", ".toml", ".mdc"} and "${CLAUDE_PLUGIN_ROOT}" in text:
                left.append(f"adapters/{host}/{rel}")
    assert not left, "unrewritten ${CLAUDE_PLUGIN_ROOT}:\n" + "\n".join(left)
