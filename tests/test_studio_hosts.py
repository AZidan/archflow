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


def _node_only_bin(home):
    """A PATH dir holding only `node`. Node's own bin dir often holds other global CLIs, a real
    `gemini` among them, which must never run from the suite."""
    d = home.parent / "node-only-bin"
    d.mkdir(exist_ok=True)
    if not (d / "node").exists():
        (d / "node").symlink_to(shutil.which("node"))
    return d


def install(home, project, *hosts, extra=()):
    """Run the installer from this checkout's bundled copy, with no host CLI on PATH (so Gemini
    falls back to copying the extension under HOME, and nothing touches the real machine)."""
    env = {
        "HOME": str(home),
        "PATH": f"{_node_only_bin(home)}:/usr/bin:/bin",
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
    # no gemini CLI on this PATH, so a direct copy; the bundle is named
    assert re.search(r"→ ~/\.gemini/extensions/archflow \(Gemini extension: adapter \+ Studio bundle; no gemini CLI on PATH\)", proc.stdout), proc.stdout
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


def _fake_gemini(bin_dir, *, answer="y"):
    """A `gemini` on PATH that behaves like the real 0.63 CLI for the calls the installer makes.
    `extensions install <path>` first asks to trust the folder and continue; on any answer but "y"
    it prints the prompt and exits 0 having installed nothing, as the real CLI does when a prompt is
    declined or unanswered. On "y" it says "already installed" (exit 1) when
    ~/.gemini/extensions/archflow exists, else copies <path> there. `extensions list` names archflow
    when that directory exists. The answer is fixed per fake (tests have no terminal). Every call is
    appended to bin_dir/calls.log."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "gemini"
    ext = '"$HOME/.gemini/extensions/archflow"'
    script.write_text(f"""#!/bin/sh
echo "$*" >> "{bin_dir}/calls.log"
if [ "$2" = "install" ]; then
  printf 'The extension source at "%s" is not trusted.\\nDo you want to trust this folder and continue with the installation? [y/N]: ' "$3"
  if [ "{answer}" != "y" ]; then echo; exit 0; fi
  echo y
  if [ -d {ext} ]; then echo "Extension archflow is already installed." >&2; exit 1; fi
  mkdir -p "$HOME/.gemini/extensions" && cp -R "$3" {ext} && echo "Extension archflow installed successfully and enabled." && exit 0
fi
if [ "$2" = "list" ]; then
  if [ -d {ext} ]; then echo "archflow"; echo " Path: $HOME/.gemini/extensions/archflow"; else echo "No extensions installed."; fi
  exit 0
fi
if [ "$2" = "uninstall" ]; then echo "uninstall must not be called" >&2; exit 3; fi
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


def _install_with_path(home, project, path_prefix, *hosts, extra=(), tty=True):
    """Run the installer with `path_prefix` (a fake gemini) on PATH. `tty` stands in for an
    interactive stdin through ARCHFLOW_TEST_STDIN_TTY, since the suite has no terminal."""
    env = {
        "HOME": str(home),
        "PATH": f"{path_prefix}:{_node_only_bin(home)}:/usr/bin:/bin",
        "DO_NOT_TRACK": "1",
        "ARCHFLOW_CONFIG_DIR": str(home / ".archflow"),
        "ARCHFLOW_TEST_STDIN_TTY": "1" if tty else "0",
    }
    return subprocess.run(
        ["node", str(CLI), "install", "--bundled", "--host", ",".join(hosts), "--yes", "--no-guard",
         "--dir", str(project), *extra],
        capture_output=True, text=True, timeout=120, env=env, stdin=subprocess.DEVNULL,
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


def _calls(bin_dir):
    log = bin_dir / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_gemini_install_removes_older_staged_copies(target, tmp_path):
    """I-1: each version stages ~11 MB under ~/.cache/archflow/gemini-extension/<version>/. After a
    confirmed install only the current one stays; a symlink there is never followed or removed."""
    home, project = target
    cache, outside = _seed_old_staged(home, tmp_path)
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert _calls(bin_dir) == [f"extensions install {staged}", "extensions list"]
    assert f"run   gemini extensions install {staged} → installed, confirmed in `gemini extensions list`" in proc.stdout
    assert "Installed." in proc.stdout
    assert_bundle_at(home / ".gemini" / "extensions" / "archflow")
    assert not (cache / "0.0.1").exists(), "an older version's staged copy was left behind"
    assert (staged / "server" / "server.mjs").is_file(), "the current staged copy was removed"
    assert (cache / "linked").is_symlink() and (outside / "keep.txt").is_file(), "a symlink was followed or removed"
    assert f"remove {cache / '0.0.1'}" in proc.stdout


def test_gemini_install_tells_the_user_gemini_will_ask(target, tmp_path):
    """I-7: Gemini's trust and consent prompts are the user's to answer. The installer says they
    are coming, passes the terminal through, and never answers them itself."""
    home, project = target
    proc = _install_with_path(home, project, _fake_gemini(tmp_path / "bin"), "gemini")
    assert "Gemini asks you to trust the extension folder" in proc.stdout
    assert "Do you want to trust this folder and continue with the installation?" in proc.stdout, "the prompt did not reach the terminal"
    src = (REPO / "scripts" / "archflow.mjs").read_text()
    assert "GEMINI_CLI_TRUST_WORKSPACE" not in src and "--consent" not in src, "the installer must not answer Gemini's prompts"


def test_gemini_already_installed_reinstalls_from_the_staged_copy(target, tmp_path):
    """I-6/I-7: upgrading from 2.4.0 (extension installed, no bundle). The old extension is moved
    aside, the staged copy installed and confirmed, then the old copy removed. No uninstall and no
    `gemini extensions update` (which re-reads the source Gemini recorded first, without the bundle)."""
    home, project = target
    cache, outside = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert _calls(bin_dir) == [f"extensions install {staged}", "extensions list"]
    assert_bundle_at(ext)
    assert not (home / ".gemini" / "archflow-extension.previous").exists(), "the old copy was left aside"
    assert "move  ~/.gemini/extensions/archflow → ~/.gemini/archflow-extension.previous (already installed)" in proc.stdout
    assert "remove ~/.gemini/archflow-extension.previous (the new install is confirmed)" in proc.stdout
    assert "uninstall" not in proc.stdout and "extensions update" not in proc.stdout
    assert "Installed." in proc.stdout
    assert not (cache / "0.0.1").exists(), "an older version's staged copy was left behind"
    assert (cache / "linked").is_symlink() and (outside / "keep.txt").is_file()


def test_gemini_declined_upgrade_keeps_the_old_extension_and_says_so(target, tmp_path):
    """I-7: Gemini exits 0 when its prompt is declined. The installer must not believe the exit
    code: the old extension is put back untouched, nothing is pruned, the report says the install
    did not complete, and the run neither prints "Installed." nor exits 0."""
    home, project = target
    cache, _ = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    manifest = (ext / "gemini-extension.json").read_text()
    bin_dir = _fake_gemini(tmp_path / "bin", answer="n")
    proc = _install_with_path(home, project, bin_dir, "gemini")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert f"fail  gemini extensions install {staged} (declined or cancelled" in proc.stdout
    assert "the previous extension is back in place" in proc.stdout
    assert "Gemini CLI: install not completed (declined or cancelled); Studio bundle not installed." in proc.stdout
    assert "npx archflow@latest install --host gemini" in proc.stdout
    assert "Installed." not in proc.stdout and "Not fully installed:" in proc.stdout
    assert (ext / "gemini-extension.json").read_text() == manifest and (ext / "commands").is_dir(), "the old extension was lost"
    assert not (ext / "server").exists()
    assert not (home / ".gemini" / "archflow-extension.previous").exists()
    assert (cache / "0.0.1" / "archflow" / "marker.txt").is_file(), "pruned after an install that did not land"
    assert "uninstall" not in " ".join(_calls(bin_dir))


def test_gemini_declined_fresh_install_installs_nothing_and_says_so(target, tmp_path):
    home, project = target
    bin_dir = _fake_gemini(tmp_path / "bin", answer="n")
    proc = _install_with_path(home, project, bin_dir, "gemini")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "install not completed (declined or cancelled)" in proc.stdout
    assert "Installed." not in proc.stdout
    assert not (home / ".gemini" / "extensions" / "archflow").exists()


def test_gemini_without_a_terminal_prints_the_command_and_changes_nothing(target, tmp_path):
    """I-7: with no terminal (CI, piped) Gemini's prompts cannot be answered, so the installer does
    not run the install. It names the exact command, leaves any installed extension alone, keeps the
    staged copy that command installs from, and exits 1 instead of claiming an install."""
    home, project = target
    cache, _ = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini", tty=False)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert _calls(bin_dir) == [], "gemini ran without a terminal"
    assert f"skip  gemini extensions install {staged} (no terminal to answer Gemini's trust and consent prompts; the installed extension is left as it is)" in proc.stdout
    assert f"todo  run in a terminal: gemini extensions install {staged}" in proc.stdout
    assert "Installed." not in proc.stdout and "Not fully installed:" in proc.stdout
    assert not (ext / "server").exists() and (ext / "gemini-extension.json").is_file()
    assert (staged / "server" / "server.mjs").is_file(), "the command names a staged copy that is not there"
    assert (cache / "0.0.1" / "archflow" / "marker.txt").is_file()


def test_gemini_dry_run_reports_the_reinstall_and_writes_nothing(target, tmp_path):
    home, project = target
    cache, _ = _seed_old_staged(home, tmp_path)
    ext = _seed_installed_extension(home)
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini", extra=("--dry-run",))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = cache / _version() / "archflow"
    assert "move  ~/.gemini/extensions/archflow → ~/.gemini/archflow-extension.previous (already installed; restored if the new install does not land)" in proc.stdout
    assert f"run   gemini extensions install {staged} → ~/.gemini/extensions/archflow (adapter + Studio bundle; interactive)" in proc.stdout
    assert "Gemini asks you to trust the extension folder" in proc.stdout
    assert "uninstall" not in proc.stdout
    assert _calls(bin_dir) == [], "the dry run ran gemini"
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
    assert f"run   gemini extensions install {staged} → ~/.gemini/extensions/archflow (adapter + Studio bundle; interactive)" in proc.stdout
    assert "adapters/gemini" not in proc.stdout, "the dry run names the package copy, not the staged one"
    assert f"remove {cache / '0.0.1'}" in proc.stdout
    assert (cache / "0.0.1" / "archflow" / "marker.txt").is_file(), "the dry run deleted something"
    assert not staged.exists(), "the dry run staged a copy"
    assert not (home / ".gemini").exists()


def test_gemini_dry_run_without_a_terminal_reports_the_skip_and_writes_nothing(target, tmp_path):
    home, project = target
    bin_dir = _fake_gemini(tmp_path / "bin")
    proc = _install_with_path(home, project, bin_dir, "gemini", extra=("--dry-run",), tty=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "skip  gemini extensions install" in proc.stdout and "todo  run in a terminal:" in proc.stdout
    assert _calls(bin_dir) == []
    assert not (home / ".gemini").exists() and not (home / ".cache").exists()


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
