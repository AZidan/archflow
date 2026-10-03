"""scripts/build-adapters.mjs ships the hook runtime to every host through one helper.

S7-04: adding a hook must require only a HOOK_SCRIPTS entry. These tests hold that
structurally: every plugin hook is either in HOOK_SCRIPTS or declared Claude-only,
every adapter's hook root carries every HOOK_SCRIPTS file plus lib/, no host copies a
hook script outside copyHookRuntime, and the committed adapters match the plugin.
"""

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "scripts" / "build-adapters.mjs"
PLUGIN_HOOKS = REPO / "plugin" / "hooks"
ADAPTERS = REPO / "adapters"


def _hook_lists():
    proc = subprocess.run(
        ["node", str(BUILD), "--list-hooks"], capture_output=True, text=True, timeout=30, cwd=REPO
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    return data["hook_scripts"], data["claude_only_hooks"]


def _hosts():
    """Host names in the HOSTS table, in declaration order."""
    src = BUILD.read_text()
    table = src[src.index("const HOSTS = {"):]
    return re.findall(r"^  ([a-z]+): \{", table, re.M)


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
    hosts = _hosts()
    assert hosts, "could not read HOSTS from build-adapters.mjs"
    for host in hosts:
        roots = _hook_roots(host)
        assert len(roots) == 1, f"adapters/{host}: expected one hook runtime root, found {roots}"
        root = roots[0]
        missing = [f for f in scripts if not (root / "hooks" / f).is_file()]
        assert not missing, f"adapters/{host}: {root} lacks hooks {missing}"
        leaked = [f for f in claude_only if (root / "hooks" / f).exists()]
        assert not leaked, f"adapters/{host}: Claude-only hooks shipped: {leaked}"
        for lib in (REPO / "plugin" / "lib").iterdir():
            assert (root / "lib" / lib.name).is_file(), f"adapters/{host}: lib/{lib.name} missing"


# Where each host runs its hook scripts: the generated files (under adapters/<host>/) whose
# combined text must name every HOOK_SCRIPTS entry, and where in build-adapters.mjs to wire one.
HOOK_WIRING = {
    "codex": ([".codex/hooks.json"], "the `hooks` object in HOSTS.codex.emit"),
    "gemini": (["hooks/hooks.json"], "the `hooks` object in HOSTS.gemini.emit"),
    "copilot": ([".github/hooks/archflow.json"], "the archflow.json hooks in HOSTS.copilot.emit"),
    "cursor": (
        [".cursor/hooks.json", ".cursor/archflow/hooks/cursor-bridge.mjs"],
        "the CURSOR_BRIDGE script (and .cursor/hooks.json in HOSTS.cursor.emit for a new event)",
    ),
    "opencode": ([".opencode/plugins/archflow.ts"], "the OPENCODE_PLUGIN script"),
    "generic": (["AGENTS.archflow.md"], "the session-start instructions in HOSTS.generic.emit"),
}

# (host, script) pairs a host deliberately does not run. One-line reason each.
NOT_WIRED = {
    ("generic", "check-state.mjs"): "no lifecycle hooks, so there is no Stop event to run it on",
    ("generic", "guard-git.mjs"): "replaced by a real git pre-push hook (archflow-install-git-guard.sh)",
}


def _names(text, script):
    return re.search(r"(?<![\w.-])" + re.escape(script) + r"(?![\w.-])", text) is not None


def test_every_hook_script_is_wired_on_every_host():
    """Copying a hook is automatic; running it is a per-host edit this test asks for."""
    scripts, _ = _hook_lists()
    assert set(HOOK_WIRING) == set(_hosts()), "HOOK_WIRING must name every host in HOSTS"
    stale = [k for k in NOT_WIRED if k[0] not in HOOK_WIRING or k[1] not in scripts]
    assert not stale, f"NOT_WIRED entries for unknown hosts or scripts: {stale}"

    unwired = []
    for host, (files, where) in HOOK_WIRING.items():
        text = ""
        for rel in files:
            path = ADAPTERS / host / rel
            assert path.is_file(), f"adapters/{host}/{rel} is missing; regenerate the adapters"
            text += path.read_text()
        for script in scripts:
            if (host, script) not in NOT_WIRED and not _names(text, script):
                unwired.append(
                    f"{host}: {script} is copied but never run; wire it in {where} "
                    f"(scripts/build-adapters.mjs, generated as adapters/{host}/{files[-1]}), "
                    f"or add ({host!r}, {script!r}) to NOT_WIRED with a reason"
                )
    assert not unwired, "\n".join(unwired)


def test_cursor_events_route_through_the_bridge():
    hooks = json.loads((ADAPTERS / "cursor" / ".cursor" / "hooks.json").read_text())["hooks"]
    for event, handlers in hooks.items():
        for h in handlers:
            assert "cursor-bridge.mjs" in h["command"], f"cursor {event} bypasses the bridge: {h}"


def test_generic_names_the_session_start_scripts():
    text = (ADAPTERS / "generic" / "AGENTS.archflow.md").read_text()
    for script in ("check-upgrade.mjs", "telemetry.mjs"):
        assert _names(text, script), (
            f"generic: AGENTS.archflow.md no longer asks the agent to run {script}; "
            "fix the session-start instructions in HOSTS.generic.emit (scripts/build-adapters.mjs)"
        )


def test_hook_scripts_are_copied_only_by_the_helper():
    """A per-host cpSync of a hook script is the drift S7-04 removed."""
    src = BUILD.read_text()
    start = src.index("function copyHookRuntime(")
    end = src.index("\n}\n", start)
    outside = src[:start] + src[end:]
    scripts, _ = _hook_lists()
    offenders = [
        line.strip()
        for line in outside.splitlines()
        if "cpSync" in line and ('"hooks"' in line or any(f in line for f in scripts))
    ]
    assert not offenders, f"hook files copied outside copyHookRuntime: {offenders}"
    calls = len(re.findall(r"copyHookRuntime\(", outside))
    assert calls == len(_hosts()), f"{calls} copyHookRuntime calls for {len(_hosts())} hosts"


def test_adapters_match_the_plugin():
    proc = subprocess.run(
        ["node", str(BUILD), "--check"], capture_output=True, text=True, timeout=120, cwd=REPO
    )
    assert proc.returncode == 0, (
        "adapters/ is stale; run: node scripts/build-adapters.mjs\n" + proc.stdout + proc.stderr
    )
