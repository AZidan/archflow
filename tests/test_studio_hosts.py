"""S6-04: Archflow Studio on every host.

Studio's bundle (plugin/server/server.mjs + plugin/dist, ~6.5 MB of prebuilt output) ships ONCE:
in the plugin, and in the npm package that carries the adapters. No adapter holds a copy;
`npx archflow install` places it under each host's plugin root, which is where that host's studio
command launches it. These tests pin each half of that: every adapter ships the command and points
it at the right place, the installer puts the bundle exactly there, and nothing duplicates it.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ADAPTERS = REPO / "adapters"
PLUGIN = REPO / "plugin"
CLI = REPO / "scripts" / "archflow.mjs"
SERVER = PLUGIN / "server" / "server.mjs"
DIST = PLUGIN / "dist"

# host -> (the studio command file in its adapter, the plugin root its install launches from)
STUDIO_COMMANDS = {
    "codex": (".agents/skills/archflow-studio/SKILL.md", ".codex/archflow"),
    "generic": (".agents/skills/archflow-studio/SKILL.md", ".agents/archflow"),
    "copilot": (".github/skills/archflow-studio/SKILL.md", ".github/archflow"),
    "cursor": (".cursor/commands/archflow-studio.md", ".cursor/archflow"),
    "opencode": (".opencode/commands/archflow-studio.md", ".opencode/archflow"),
    "gemini": ("commands/archflow/studio.toml", "$HOME/.gemini/extensions/archflow"),
}
PROJECT_HOSTS = sorted(h for h in STUDIO_COMMANDS if h != "gemini")


def _hosts():
    out = subprocess.run(["node", str(REPO / "scripts" / "build-adapters.mjs"), "--list-hooks"],
                         capture_output=True, text=True, check=True, cwd=REPO).stdout
    return json.loads(out)["hosts"]


def command_text(host):
    return (ADAPTERS / host / STUDIO_COMMANDS[host][0]).read_text()


def launch_lines(text):
    """The `nohup node "<path>"` line(s) a studio command runs."""
    return re.findall(r'nohup node "([^"]+)"', text)


def install(home, project, *hosts, extra=()):
    """Run the installer from this checkout's bundled copy, with no host CLI on PATH (so Gemini
    falls back to copying the extension under HOME, and nothing touches the real machine)."""
    env = {
        "HOME": str(home),
        "PATH": f"{Path(shutil.which('node')).parent}:/usr/bin:/bin",
        "DO_NOT_TRACK": "1",
        "ARCHFLOW_CONFIG_DIR": str(home / ".archflow"),
    }
    return subprocess.run(
        ["node", str(CLI), "install", "--bundled", "--host", ",".join(hosts), "--yes", "--no-guard",
         "--dir", str(project), *extra],
        capture_output=True, text=True, timeout=120, env=env,
    )


@pytest.fixture
def target(tmp_path):
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir()
    project.mkdir()
    return home, project


# --------------------------------------------------------------------------
# The bundle exists, and is the one the plugin serves
# --------------------------------------------------------------------------

def test_the_plugin_ships_the_bundle():
    assert SERVER.is_file() and SERVER.stat().st_size > 1_000_000, "plugin/server/server.mjs is missing or truncated"
    index = (DIST / "index.html").read_text()
    for ref in re.findall(r'(?:src|href)="/?(assets/[^"]+)"', index):
        assert (DIST / ref).is_file(), f"dist/index.html loads {ref}, which is not shipped"


def test_every_host_is_covered():
    assert sorted(STUDIO_COMMANDS) == sorted(_hosts()), "add the new host to STUDIO_COMMANDS"


# --------------------------------------------------------------------------
# Every adapter ships /archflow:studio, launching from its own plugin root
# --------------------------------------------------------------------------

@pytest.mark.parametrize("host", sorted(STUDIO_COMMANDS))
def test_every_adapter_ships_the_studio_command(host):
    path = ADAPTERS / host / STUDIO_COMMANDS[host][0]
    assert path.is_file(), f"adapters/{host} does not ship the studio command ({path.relative_to(ADAPTERS)})"


@pytest.mark.parametrize("host", sorted(STUDIO_COMMANDS))
def test_studio_launches_the_server_from_the_hosts_own_root(host):
    root = STUDIO_COMMANDS[host][1]
    text = command_text(host)
    assert launch_lines(text) == [f"{root}/server/server.mjs"], (
        f"{host}: studio must launch {root}/server/server.mjs, found {launch_lines(text)}")
    assert f'test -f "{root}/server/server.mjs"' in text, f"{host}: the bundle check looks somewhere else"
    assert "${CLAUDE_PLUGIN_ROOT}" not in text and "plugins/cache" not in text


@pytest.mark.parametrize("host", sorted(STUDIO_COMMANDS))
def test_studio_names_the_host_it_runs_in(host):
    """The command compares Studio's resolved host with its own id, so that id must be this host's."""
    text = command_text(host)
    assert f"This host's id, `{host}`" in text
    assert "This host's id, `claude`" not in text


def test_the_claude_command_launches_from_the_plugin_root():
    text = (PLUGIN / "commands" / "studio.md").read_text()
    assert launch_lines(text) == ["${CLAUDE_PLUGIN_ROOT}/server/server.mjs"]
    assert "This host's id, `claude`" in text


@pytest.mark.parametrize("path", [PLUGIN / "commands" / "studio.md"]
                         + [ADAPTERS / h / c for h, (c, _) in sorted(STUDIO_COMMANDS.items())],
                         ids=lambda p: str(p.relative_to(REPO)))
def test_no_studio_command_says_forwarding_is_unbuilt_or_claude_only(path):
    text = path.read_text().lower()
    for stale in ("not built yet", "claude code only", "only on claude code", "build:plugin", "sync:plugin"):
        assert stale not in text, f"{path.relative_to(REPO)} still says {stale!r}"
    assert "forward" in text


# --------------------------------------------------------------------------
# One copy: no adapter carries the bundle, the package carries it once
# --------------------------------------------------------------------------

def test_no_adapter_carries_a_copy_of_the_bundle():
    copies = [p for p in ADAPTERS.rglob("*") if p.name == "server.mjs" or (p.is_dir() and p.name == "dist")]
    assert not copies, "the Studio bundle belongs in plugin/ only:\n" + "\n".join(map(str, copies))


def test_the_package_ships_the_bundle_once():
    files = json.loads((REPO / "package.json").read_text())["files"]
    assert "plugin/server/server.mjs" in files and "plugin/dist" in files
    proc = subprocess.run(["npm", "pack", "--dry-run", "--json"], capture_output=True, text=True,
                          cwd=REPO, timeout=120)
    if proc.returncode != 0:
        pytest.skip(f"npm pack unavailable: {proc.stderr.strip()[:200]}")
    packed = [f["path"] for f in json.loads(proc.stdout)[0]["files"]]
    assert packed.count("plugin/server/server.mjs") == 1
    assert sum(p.endswith("/server.mjs") for p in packed) == 1, "a second server.mjs is in the package"
    assert "plugin/dist/index.html" in packed and sum(p.endswith("dist/index.html") for p in packed) == 1


# --------------------------------------------------------------------------
# The installer puts the bundle where each host's command looks
# --------------------------------------------------------------------------

def assert_bundle_at(root):
    assert (root / "server" / "server.mjs").read_bytes() == SERVER.read_bytes()
    shipped = sorted(p.relative_to(DIST) for p in DIST.rglob("*") if p.is_file() and p.name != ".DS_Store")
    placed = sorted(p.relative_to(root / "dist") for p in (root / "dist").rglob("*") if p.is_file())
    assert placed == shipped


@pytest.mark.parametrize("host", PROJECT_HOSTS)
def test_install_places_the_bundle_where_the_command_launches_it(host, target):
    home, project = target
    proc = install(home, project, host)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    root = STUDIO_COMMANDS[host][1]
    (launch,) = launch_lines((project / STUDIO_COMMANDS[host][0]).read_text())
    assert (project / launch).is_file(), f"{host}: the installed command launches {launch}, which is not there"
    assert_bundle_at(project / root)
    assert "(Archflow Studio)" in proc.stdout


@pytest.mark.parametrize("host", PROJECT_HOSTS)
def test_install_keeps_the_bundle_out_of_the_teams_commits(host, target):
    home, project = target
    assert install(home, project, host).returncode == 0
    ignore = (project / STUDIO_COMMANDS[host][1] / ".gitignore").read_text().splitlines()
    assert "/server/" in ignore and "/dist/" in ignore


def test_install_places_the_bundle_in_the_gemini_extension(target):
    home, project = target
    proc = install(home, project, "gemini")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ext = home / ".gemini" / "extensions" / "archflow"
    (launch,) = launch_lines((ext / STUDIO_COMMANDS["gemini"][0]).read_text())
    assert launch == "$HOME/.gemini/extensions/archflow/server/server.mjs"
    assert (home / launch.replace("$HOME/", "")).is_file()
    assert_bundle_at(ext)


def test_reinstall_replaces_dist_instead_of_piling_up_old_builds(target):
    home, project = target
    assert install(home, project, "codex").returncode == 0
    stale = project / ".codex" / "archflow" / "dist" / "assets" / "index-OLDBUILD.js"
    stale.write_text("// a previous build's hashed asset\n")
    ignore = project / ".codex" / "archflow" / ".gitignore"
    ignore.write_text("/server/\n/dist/\nlocal-notes.txt\n")
    assert install(home, project, "codex").returncode == 0
    assert not stale.exists(), "an upgrade must not leave a previous build's assets behind"
    assert_bundle_at(project / ".codex" / "archflow")
    assert "local-notes.txt" in ignore.read_text(), "the .gitignore merge dropped a user's line"


def test_dry_run_reports_the_bundle_and_writes_nothing(target):
    home, project = target
    proc = install(home, project, "codex", "gemini", extra=("--dry-run",))
    assert proc.returncode == 0, proc.stderr
    assert ".codex/archflow/server/server.mjs, .codex/archflow/dist/ (Archflow Studio)" in proc.stdout
    # via the gemini CLI when one is on PATH, else a direct copy; either way the bundle is named
    assert re.search(r"→ ~/\.gemini/extensions/archflow \((Gemini extension: )?adapter \+ Studio bundle\)", proc.stdout), proc.stdout
    assert "/archflow/server/server.mjs, " in proc.stdout and "gemini-extension" in proc.stdout
    assert not any(project.iterdir()) and not (home / ".gemini").exists() and not (home / ".cache").exists()


def test_a_release_without_the_bundle_installs_and_says_so(target, tmp_path):
    """A source that predates S6-04 (no plugin/server) must not fail the install."""
    home, project = target
    pkg = tmp_path / "pkg"
    for rel in ("adapters/codex", "scripts", "plugin/lib", "plugin/.claude-plugin", "plugin/scripts"):
        shutil.copytree(REPO / rel, pkg / rel, symlinks=True)
    proc = subprocess.run(
        ["node", str(pkg / "scripts" / "archflow.mjs"), "install", "--bundled", "--host", "codex",
         "--yes", "--no-guard", "--dir", str(project)],
        capture_output=True, text=True, timeout=120,
        env={"HOME": str(home), "PATH": os.environ["PATH"], "DO_NOT_TRACK": "1",
             "ARCHFLOW_CONFIG_DIR": str(home / ".archflow")},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "skip  Archflow Studio bundle" in proc.stdout
    assert not (project / ".codex" / "archflow" / "server").exists()


# --------------------------------------------------------------------------
# Fix pass 1 (S6-04 I-1, I-3, I-4)
# --------------------------------------------------------------------------

LATEST = "npx archflow@latest install"


def _without_latest(text):
    """Every `npx archflow install` spelled without `@latest` (the --host form is fine: it is the
    first-time install line, not the missing-bundle remedy)."""
    return re.findall(r"npx archflow install(?! --host)", text)


@pytest.mark.parametrize("host", sorted(STUDIO_COMMANDS))
def test_the_missing_bundle_remedy_fetches_the_current_installer(host):
    """I-3: a cached pre-2.5.0 installer brings the studio command without the bundle, so the
    remedy must be `@latest`, or it reruns the same cached installer forever."""
    text = command_text(host)
    assert LATEST in text, f"{host}: the studio command's missing-bundle step must say `{LATEST}`"
    assert not _without_latest(text), f"{host}: the studio command still says `npx archflow install`"


def test_the_plugin_studio_command_says_latest():
    text = (PLUGIN / "commands" / "studio.md").read_text()
    assert LATEST in text and not _without_latest(text)


@pytest.mark.parametrize("host", sorted(STUDIO_COMMANDS))
def test_every_adapter_readme_studio_row_says_latest(host):
    readme = (ADAPTERS / host / "README.md").read_text()
    (row,) = [l for l in readme.splitlines() if l.startswith("| `/archflow:studio` |")]
    assert LATEST in row and not _without_latest(row), f"{host}: README Studio row: {row}"


def _fake_gemini(bin_dir, *, installed=False, uninstall_ok=True):
    """A `gemini` on PATH that behaves like the real one for the calls the installer makes:
    `extensions install <path>` copies <path> to ~/.gemini/extensions/archflow and records the call,
    or says "already installed" when that directory exists; `extensions uninstall archflow` removes
    it (or fails, with uninstall_ok=False). Every call is appended to bin_dir/calls.log."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "gemini"
    ext = '"$HOME/.gemini/extensions/archflow"'
    script.write_text(f"""#!/bin/sh
echo "$*" >> "{bin_dir}/calls.log"
if [ "$2" = "install" ]; then
  if [ -d {ext} ]; then echo "Extension archflow is already installed." >&2; exit 1; fi
  mkdir -p "$HOME/.gemini/extensions" && cp -R "$3" {ext} && echo "Extension archflow installed." && exit 0
fi
if [ "$2" = "uninstall" ]; then
  {"rm -rf " + ext + ' && echo "Extension archflow uninstalled." && exit 0' if uninstall_ok else 'echo "uninstall: permission denied" >&2; exit 1'}
fi
if [ "$2" = "update" ]; then echo "update must not be called" >&2; exit 3; fi
exit 2
""")
    script.chmod(0o755)
    return bin_dir


def _seed_installed_extension(home):
    """An extension a 2.4.0 install left: no server/ or dist/."""
    ext = home / ".gemini" / "extensions" / "archflow"
    (ext / "commands").mkdir(parents=True)
    (ext / "gemini-extension.json").write_text('{"name": "archflow", "version": "2.4.0"}\n')
    return ext


def _install_with_path(home, project, path_prefix, *hosts, extra=()):
    env = {
        "HOME": str(home),
        "PATH": f"{path_prefix}:{Path(shutil.which('node')).parent}:/usr/bin:/bin",
        "DO_NOT_TRACK": "1",
        "ARCHFLOW_CONFIG_DIR": str(home / ".archflow"),
    }
    return subprocess.run(
        ["node", str(CLI), "install", "--bundled", "--host", ",".join(hosts), "--yes", "--no-guard",
         "--dir", str(project), *extra],
        capture_output=True, text=True, timeout=120, env=env,
    )


def _version():
    return json.loads((REPO / "package.json").read_text())["version"]


def _seed_old_staged(home, tmp_path):
    cache = home / ".cache" / "archflow" / "gemini-extension"
    old = cache / "0.0.1" / "archflow"
    old.mkdir(parents=True)
    (old / "marker.txt").write_text("an older version's staged copy\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("not ours\n")
    (cache / "linked").symlink_to(outside, target_is_directory=True)
    return cache, outside


def test_gemini_install_removes_older_staged_copies(target, tmp_path):
    """I-1: each version stages ~11 MB under ~/.cache/archflow/gemini-extension/<version>/. After a
    successful install only the current one stays; a symlink there is never followed or removed."""
    home, project = target
    cache, outside = _seed_old_staged(home, tmp_path)
    proc = _install_with_path(home, project, _fake_gemini(tmp_path / "bin"), "gemini")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (cache / "0.0.1").exists(), "an older version's staged copy was left behind"
    assert (cache / _version() / "archflow" / "server" / "server.mjs").is_file(), "the current staged copy was removed"
    assert (cache / "linked").is_symlink() and (outside / "keep.txt").is_file(), "a symlink was followed or removed"
    assert f"remove {cache / '0.0.1'}" in proc.stdout


def test_gemini_already_installed_reinstalls_from_the_staged_copy(target, tmp_path):
    """I-6: upgrading from 2.4.0 (extension already installed, no bundle). The installer uninstalls
    and installs from the staged copy, never `gemini extensions update` (which re-reads the source
    Gemini recorded first, without the bundle). The bundle lands in the extension, and older staged
    copies are pruned because Gemini's recorded source is now the current one."""
    home, project = target
    cache, outside = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    calls = (bin_dir / "calls.log").read_text().splitlines()
    assert calls == [f"extensions install {staged}", "extensions uninstall archflow", f"extensions install {staged}"], calls
    assert_bundle_at(ext)
    assert "gemini extensions uninstall archflow" in proc.stdout
    assert f"run   gemini extensions install {staged} → Extension archflow installed. (adapter + Studio bundle)" in proc.stdout
    assert "extensions update" not in proc.stdout
    assert not (cache / "0.0.1").exists(), "an older version's staged copy was left behind"
    assert (staged / "server" / "server.mjs").is_file()
    assert (cache / "linked").is_symlink() and (outside / "keep.txt").is_file()


def test_gemini_uninstall_failure_falls_back_to_a_direct_copy(target, tmp_path):
    """I-6: if the uninstall fails, the staged copy (bundle included) is copied straight into
    ~/.gemini/extensions/archflow, and the report says copy, not install."""
    home, project = target
    cache, _ = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    bin_dir = _fake_gemini(tmp_path / "bin", uninstall_ok=False)
    proc = _install_with_path(home, project, bin_dir, "gemini")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "uninstall failed" in proc.stdout
    staged = cache / _version() / "archflow"
    assert f"copy  {staged} → ~/.gemini/extensions/archflow (Gemini extension: adapter + Studio bundle)" in proc.stdout
    assert "run   gemini extensions install" not in proc.stdout
    assert_bundle_at(ext)
    assert not (cache / "0.0.1").exists()


def test_gemini_dry_run_reports_the_reinstall_and_writes_nothing(target, tmp_path):
    home, project = target
    cache, _ = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini", extra=("--dry-run",))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert "run   gemini extensions uninstall archflow (already installed; reinstalling from the staged copy)" in proc.stdout
    assert f"run   gemini extensions install {staged} → ~/.gemini/extensions/archflow (adapter + Studio bundle)" in proc.stdout
    assert not (bin_dir / "calls.log").exists(), "the dry run ran gemini"
    assert not (ext / "server").exists() and not staged.exists()
    assert (cache / "0.0.1" / "archflow" / "marker.txt").is_file()


def test_gemini_dry_run_reports_the_staged_source_and_the_prune_and_writes_nothing(target, tmp_path):
    """I-4 + I-1: the dry run names the staged copy the real run installs from, lists the older
    staged copies it would remove, and touches nothing."""
    home, project = target
    cache, _ = _seed_old_staged(home, tmp_path)
    proc = _install_with_path(home, project, _fake_gemini(tmp_path / "bin"), "gemini", extra=("--dry-run",))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert f"run   gemini extensions install {staged} → ~/.gemini/extensions/archflow (adapter + Studio bundle)" in proc.stdout
    assert "adapters/gemini" not in proc.stdout, "the dry run names the package copy, not the staged one"
    assert f"remove {cache / '0.0.1'}" in proc.stdout
    assert (cache / "0.0.1" / "archflow" / "marker.txt").is_file(), "the dry run deleted something"
    assert not staged.exists(), "the dry run staged a copy"
    assert not (home / ".gemini").exists()


@pytest.mark.parametrize("existing, verb", [
    (None, "write"),
    ("local-notes.txt\n", "merge"),
    ("/server/\n/dist/\n", "keep "),
])
def test_dry_run_gitignore_verb_matches_the_real_run(target, existing, verb):
    """I-4: the dry run's .gitignore verb is the one the real run takes, and it writes nothing."""
    home, project = target
    ignore = project / ".codex" / "archflow" / ".gitignore"
    if existing is not None:
        ignore.parent.mkdir(parents=True)
        ignore.write_text(existing)
    line = f"{verb} .codex/archflow/.gitignore"
    dry = install(home, project, "codex", extra=("--dry-run",))
    assert dry.returncode == 0, dry.stderr
    assert line in dry.stdout, dry.stdout
    assert (ignore.read_text() if ignore.exists() else None) == existing, "the dry run wrote the .gitignore"
    real = install(home, project, "codex")
    assert real.returncode == 0, real.stderr
    assert line in real.stdout, real.stdout


def test_the_guide_and_site_name_the_generic_host():
    """I-2: the generic AGENTS.md package ships `$archflow-studio`; the docs that list Studio's
    forward-mode hosts must say so."""
    guide = (REPO / "docs" / "guides" / "studio.md").read_text()
    (row,) = [l for l in guide.splitlines() if l.startswith("| ") and "`$archflow-studio`" in l]
    assert "AGENTS.md" in row
    assert "AGENTS.md" in [p for p in (REPO / "README.md").read_text().split("\n\n") if "forward mode: you compose" in p][0]
    assert "AGENTS.md + Agent Skills agent composes each prompt" in (REPO / "docs" / "index.html").read_text()
