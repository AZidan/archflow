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
