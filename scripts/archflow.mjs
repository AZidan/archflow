#!/usr/bin/env node
/**
 * archflow — put Archflow into a project, for Claude Code or any other supported host.
 *
 * Does, per host, exactly what adapters/<host>/README.md tells a human to do by hand:
 * copy the adapter tree in, merge the AGENTS.md block, merge Codex's config.toml
 * snippet, install the git pre-push guard. Re-running upgrades in place; it never
 * deletes a file it did not write.
 *
 * Usage (from inside the target project):
 *   npx archflow install                      # detect hosts, install for each
 *   npx archflow install --host codex,cursor  # explicit hosts
 *   npx archflow install --dry-run            # show the plan only
 *   npx archflow                              # same as `install`, the default command
 *   npx archflow telemetry [on|off|status]    # show, or change, anonymous usage telemetry (on by default)
 *   npx archflowai ...                        # alias package, identical
 *
 * Options:
 *   --host <a,b>          claude | codex | copilot | cursor | gemini | opencode | generic
 *   --dir <path>          project directory (default: cwd)
 *   --version <tag>       install the adapters from that GitHub release instead of the latest
 *   --bundled             use the adapters bundled with this package; no network
 *   --marketplace <src>   Claude Code only: marketplace to install the plugin from
 *                         (default AZidan/archflow; a local checkout path works for testing)
 *   --dry-run             print what would happen, change nothing
 *   --no-guard            skip the git pre-push guard
 *   --yes                 do not ask for confirmation
 *
 * The adapters come from the latest GitHub release by default, so the installed copy is
 * never older than what is published, whatever version of this package npx cached. Each
 * release is fetched once into ~/.cache/archflow/<tag>. When the network or the
 * release is unavailable, the copy bundled with this package is used and the run says so.
 *
 * Claude Code is the reference host: `--host claude` installs the marketplace plugin at
 * project scope (`.claude/settings.json`), so the choice is committed with the repo.
 *
 * Archflow Studio's prebuilt bundle (server + web UI, ~6.5 MB) ships ONCE in this package, under
 * plugin/server and plugin/dist, not in every adapter. Each non-Claude host gets its own copy at
 * install time, in the root its studio command launches from (see installStudio).
 *
 * Local testing without publishing:
 *   node /path/to/archflow/scripts/archflow.mjs --host codex
 *   or `npm link` in the archflow checkout, then `archflow install` anywhere.
 */

import {
  chmodSync, cpSync, existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, renameSync,
  rmSync, statSync, symlinkSync, writeFileSync,
} from "node:fs";
import { spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { homedir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { CONFIG_UNREADABLE_NOTE, CONFIG_UNWRITABLE_NOTE, NOTICE, OPT_OUT_CONFIRMATION, OPT_OUT_SENT_NOTE, capture, disabledByEnv, hasSeenNotice, isConfigUnreadable, isEnabled, loadConfig, optInConfirmation, recordNoticeShown, setConsent, statusLine } from "../plugin/lib/telemetry.mjs";

const PKG = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO = "AZidan/archflow";

// Where the adapters come from. Default: the latest GitHub release, cached per tag
// under ~/.cache/archflow. Falls back to the copy bundled with this package.
let SRC, ADAPTERS, PRE_PUSH, VERSION;
/** Archflow Studio's bundle: [path in the package, path under a host's plugin root]. */
const STUDIO_BUNDLE = [["plugin/server/server.mjs", "server/server.mjs"], ["plugin/dist", "dist"]];
function useSource(root, origin) {
  SRC = { root, origin };
  ADAPTERS = join(root, "adapters");
  PRE_PUSH = join(root, "plugin", "scripts", "archflow-pre-push.sh");
  VERSION = JSON.parse(readFileSync(join(root, "plugin", ".claude-plugin", "plugin.json"), "utf8")).version;
}
useSource(PKG, "bundled with this package");

async function latestTag() {
  const res = await fetch(`https://github.com/${REPO}/releases/latest`, { redirect: "follow" });
  const tag = new URL(res.url).pathname.split("/").pop();
  if (!/^\d+\.\d+\.\d+$/.test(tag)) throw new Error(`could not resolve the latest release from ${res.url}`);
  return tag;
}

async function download(url, file) {
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) return false;
  writeFileSync(file, Buffer.from(await res.arrayBuffer()));
  return true;
}

/** Point ADAPTERS at a release (latest unless --version), or stay on the bundled copy. */
async function resolveSource(opts) {
  if (opts.bundled) return;
  let tag;
  try { tag = opts.version || await latestTag(); }
  catch (e) { log(`note  ${e.message}; using the adapters bundled with this package (${VERSION})`); return; }
  const cacheRoot = join(homedir(), ".cache", "archflow");
  const cache = join(cacheRoot, tag);
  if (!opts.version) { // share what we learned with the session-start hook, so it does not nag about this tag
    try { mkdirSync(cacheRoot, { recursive: true }); writeFileSync(join(cacheRoot, "latest.json"), JSON.stringify({ tag, checkedAt: Date.now() }) + "\n"); } catch {}
  }
  if (existsSync(join(cache, "adapters"))) { useSource(cache, `release ${tag}, cached`); return; }
  mkdirSync(cacheRoot, { recursive: true });
  const tmp = mkdtempSync(join(cacheRoot, "tmp-")); // same filesystem as the cache, so the final rename is atomic
  try {
    const tgz = join(tmp, "release.tgz");
    const asset = `https://github.com/${REPO}/releases/download/${tag}/archflow-${tag}.tgz`;
    const source = `https://github.com/${REPO}/archive/refs/tags/${tag}.tar.gz`;
    if (!(await download(asset, tgz)) && !(await download(source, tgz))) throw new Error(`release ${tag} was not found on GitHub`);
    const extracted = join(tmp, "x");
    mkdirSync(extracted);
    const r = spawnSync("tar", ["-xzf", tgz, "-C", extracted, "--strip-components=1"], { encoding: "utf8" });
    if (r.status !== 0) throw new Error(`could not extract release ${tag}: ${(r.stderr || "").trim()}`);
    if (!existsSync(join(extracted, "adapters"))) throw new Error(`release ${tag} ships no host adapters (it predates multi-host support)`);
    rmSync(cache, { recursive: true, force: true });
    renameSync(extracted, cache);
    useSource(cache, `release ${tag}, downloaded`);
  } catch (e) {
    log(`note  ${e.message}; using the adapters bundled with this package (${VERSION})`);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

// ---------------------------------------------------------------------------
// Host table. `copy` are adapter-relative paths copied into the project.
// `hookRoot` is what the hooks see as CLAUDE_PLUGIN_ROOT; it must contain
// skills/archflow, which the adapter provides as a relative symlink. npm drops
// symlinks when packing, so `ensureLink` recreates it after the copy. It is also
// where Studio's bundle goes (installStudio), since each host's studio command
// launches <hookRoot>/server/server.mjs.
// ---------------------------------------------------------------------------
const MARKETPLACE_REPO = "AZidan/archflow";

const HOSTS = {
  claude: {
    label: "Claude Code",
    detect: () => has(homedir(), ".claude") || onPath("claude"),
    plugin: true, // the marketplace plugin, enabled at project scope; no adapter tree
    next: ["Restart Claude Code (or run /reload-plugins).", "Run `/archflow:init` or `/archflow:onboard`."],
  },
  codex: {
    label: "OpenAI Codex",
    detect: (p) => has(p, ".codex") || has(homedir(), ".codex") || onPath("codex"),
    copy: [".agents", ".codex/agents", ".codex/archflow", ".codex/hooks.json"],
    agentsBlock: "AGENTS.archflow.md",
    codexConfig: ".codex/config.archflow.toml",
    hookRoot: ".codex/archflow",
    skillTree: ".agents/skills/archflow",
    next: ["Trust the project in Codex, then restart it.", "Run `$archflow-init` (new project) or `$archflow-onboard` (existing code)."],
  },
  copilot: {
    label: "GitHub Copilot CLI",
    detect: (p) => has(homedir(), ".copilot") || onPath("copilot"),
    copy: [".github/agents", ".github/skills", ".github/hooks", ".github/archflow"],
    agentsBlock: "AGENTS.archflow.md",
    hookRoot: ".github/archflow",
    skillTree: ".github/skills/archflow",
    next: ["Restart Copilot CLI.", "Ask for `/archflow-init` or `/archflow-onboard`."],
  },
  cursor: {
    label: "Cursor",
    detect: (p) => has(p, ".cursor") || has(homedir(), ".cursor"),
    copy: [".cursor"],
    hookRoot: ".cursor/archflow",
    skillTree: ".cursor/skills/archflow",
    next: ["Restart Cursor.", "Run `/archflow-init` or `/archflow-onboard`."],
  },
  gemini: {
    label: "Gemini CLI",
    detect: (p) => has(homedir(), ".gemini") || onPath("gemini"),
    extension: true, // per-user install, not a project overlay
    next: ["Restart Gemini CLI.", "Run `/archflow:init` or `/archflow:onboard`."],
  },
  opencode: {
    label: "OpenCode",
    detect: (p) => has(p, ".opencode") || has(p, "opencode.json") || has(p, "opencode.jsonc") || has(join(homedir(), ".config"), "opencode") || onPath("opencode"),
    copy: [".opencode"],
    agentsBlock: "AGENTS.archflow.md",
    hookRoot: ".opencode/archflow",
    skillTree: ".opencode/skills/archflow",
    next: ["Restart OpenCode.", "Run `/archflow-init` or `/archflow-onboard`."],
  },
  generic: {
    label: "generic AGENTS.md + Agent Skills",
    detect: () => false, // only on request, or when nothing else is found
    copy: [".agents"],
    agentsBlock: "AGENTS.archflow.md",
    hookRoot: ".agents/archflow",
    skillTree: ".agents/skills/archflow",
    next: ["Ask your agent to run `$archflow-init` or `$archflow-onboard`."],
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const has = (dir, name) => existsSync(join(dir, name));
function onPath(bin) {
  const r = spawnSync(process.platform === "win32" ? "where" : "which", [bin], { stdio: "pipe" });
  return r.status === 0;
}
const log = (s) => process.stdout.write(s + "\n");
process.stdout.on("error", (e) => { if (e.code === "EPIPE") process.exit(0); throw e; }); // `| head` is not an error

function parseArgs(argv) {
  const o = { hosts: [], dir: process.cwd(), dryRun: false, guard: true, yes: false, marketplace: MARKETPLACE_REPO, version: null, bundled: false };
  if (argv[0] === "install") argv = argv.slice(1); // the default install command (telemetry is handled before this)
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--host") o.hosts.push(...argv[++i].split(",").map((s) => s.trim()).filter(Boolean));
    else if (a.startsWith("--host=")) o.hosts.push(...a.slice(7).split(","));
    else if (a === "--dir") o.dir = resolve(argv[++i]);
    else if (a === "--marketplace") o.marketplace = argv[++i];
    else if (a === "--version") {
      o.version = argv[++i];
      if (!/^\d+\.\d+\.\d+$/.test(o.version || "")) { console.error(`--version wants a release tag like 2.4.0, got "${o.version}"`); process.exit(2); }
    }
    else if (a === "--bundled") o.bundled = true;
    else if (a === "--dry-run") o.dryRun = true;
    else if (a === "--no-guard") o.guard = false;
    else if (a === "--yes" || a === "-y") o.yes = true;
    else if (a === "--help" || a === "-h") { log(readFileSync(fileURLToPath(import.meta.url), "utf8").match(/\/\*\*([\s\S]*?)\*\//)[1].replace(/^ \* ?/gm, "")); process.exit(0); }
    else if (a.startsWith("-")) { console.error(`Unknown option: ${a}`); process.exit(2); }
    else { console.error(`Unknown command: ${a}. Commands: install (the default). Try --help.`); process.exit(2); }
  }
  return o;
}

async function confirm(question) {
  if (!process.stdin.isTTY) return true;
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await new Promise((res) => rl.question(`${question} [Y/n] `, res));
  rl.close();
  return !/^n/i.test(answer.trim());
}

/**
 * Telemetry is on by default. The first time this installer (or the
 * SessionStart hook, for Claude Code users who never run it directly) sees no
 * ~/.archflow/config.json yet, it prints a one-time notice — not a question —
 * and starts sending. Both write the same config file, so the notice shows
 * once per machine, not once per project.
 */
function maybeNoticeTelemetry(dry) {
  const config = loadConfig();
  if (isConfigUnreadable(config)) { log(`note  ${CONFIG_UNREADABLE_NOTE}\n`); return; }
  if (dry || hasSeenNotice(config) || !isEnabled(config)) return;
  log(NOTICE + "Turn it off any time: npx archflow telemetry off\n");
  recordNoticeShown();
}

/**
 * Copy a file or tree over the destination. Overwrites our files, never deletes theirs.
 * Symlinks are skipped on purpose: Node's cpSync rewrites a relative link to an absolute
 * path into THIS package, which is wrong once the package is gone. ensureLink recreates
 * the one link an adapter needs, relative to the project.
 */
function copyInto(src, dst, dry) {
  if (dry) return;
  mkdirSync(dirname(dst), { recursive: true });
  cpSync(src, dst, {
    recursive: true,
    force: true,
    filter: (s) => !s.endsWith(".DS_Store") && !lstatSync(s).isSymbolicLink(),
  });
}

/**
 * Put Archflow Studio's bundle under a host's plugin root: <root>/server/server.mjs and <root>/dist,
 * where that host's studio command launches it. One copy ships in the package (or the release),
 * so adapters/ never holds six. dist/ is replaced, not merged: its asset names are content hashes,
 * and an upgrade merged over an old copy would pile up every previous build. `label` is the root as
 * the user should read it. `ignore` adds a .gitignore beside it, for project overlays a team
 * commits: the bundle is build output, and a teammate gets it by running this installer.
 */
function installStudio(root, label, dry, { ignore = false } = {}) {
  const missing = STUDIO_BUNDLE.filter(([from]) => !existsSync(join(SRC.root, from)));
  if (missing.length) return [`skip  Archflow Studio bundle (not in ${SRC.origin}; /archflow:studio will say it is missing)`];
  const actions = [`copy  ${label}/server/server.mjs, ${label}/dist/ (Archflow Studio)`];
  if (ignore) actions.push(`${ensureIgnored(root, dry)} ${label}/.gitignore (Studio's bundle is build output)`);
  if (dry) return actions;
  for (const [from, to] of STUDIO_BUNDLE) {
    const dst = join(root, to);
    rmSync(dst, { recursive: true, force: true });
    copyInto(join(SRC.root, from), dst, false);
  }
  return actions;
}

/**
 * Add the bundle's paths to <root>/.gitignore, keeping whatever else is there. Returns the verb the
 * run takes (write, merge or keep). A dry run works out the same verb and writes nothing.
 */
function ensureIgnored(root, dry = false) {
  const file = join(root, ".gitignore");
  const lines = ["/server/", "/dist/"];
  const text = existsSync(file) ? readFileSync(file, "utf8") : "";
  const have = new Set(text.split(/\r?\n/).map((l) => l.trim()));
  const add = lines.filter((l) => !have.has(l));
  if (!add.length) return "keep ";
  if (dry) return text ? "merge" : "write";
  mkdirSync(root, { recursive: true });
  const head = text ? text.replace(/\s*$/, "\n") : "# Archflow Studio's bundle: build output, placed by `npx archflow install`.\n";
  writeFileSync(file, head + add.join("\n") + "\n");
  return text ? "merge" : "write";
}

/** (Re)create hookRoot/skills/archflow → skillTree as a relative link inside the project. */
function ensureLink(project, host, dry) {
  if (!host.hookRoot || !host.skillTree) return null;
  const rel = `${host.hookRoot}/skills/archflow`;
  const linkPath = join(project, rel);
  const target = join(project, host.skillTree);
  if (dry) return `link  ${rel} → ${host.skillTree}`;
  mkdirSync(dirname(linkPath), { recursive: true });
  if (existsSync(linkPath) || isLink(linkPath)) {
    if (!isLink(linkPath)) { // a real directory: the Windows fallback from an earlier run — refresh it
      cpSync(target, linkPath, { recursive: true, force: true });
      return `copy  ${rel} (refreshed; symlinks unavailable)`;
    }
    rmSync(linkPath);
  }
  try {
    symlinkSync(relative(dirname(linkPath), target), linkPath, "dir");
    return `link  ${rel} → ${host.skillTree}`;
  } catch {
    cpSync(target, linkPath, { recursive: true }); // Windows without symlink rights
    return `copy  ${rel} (symlink unavailable)`;
  }
}
function isLink(p) { try { return lstatSync(p).isSymbolicLink(); } catch { return false; } }

/**
 * One AGENTS.md block for every host installed. A project shared between hosts needs
 * every spelling (`$archflow-x` on Codex, `/archflow-x` on Copilot), so the blocks are
 * combined under one marker pair rather than letting the last host win.
 */
function combineBlocks(blocks) {
  if (blocks.length === 1) return blocks[0].text;
  const body = blocks.map(({ label, text }) => {
    const inner = text
      .replace(/^<!-- archflow:start[^>]*-->\n/, "").replace(/<!-- archflow:end -->\n?$/, "")
      .replace(/^# Archflow\n\n/, "").trim();
    return `## When running in ${label}\n\n${inner}`;
  }).join("\n\n");
  return `<!-- archflow:start (managed by Archflow ${VERSION}; merge into AGENTS.md) -->\n# Archflow\n\n` +
    `This project is managed by Archflow, a phase-based development workflow. State lives in \`.archflow/\`. ` +
    `It is set up for more than one coding agent; find your host below.\n\n${body}\n<!-- archflow:end -->\n`;
}

/** Replace or append the <!-- archflow:start --> … <!-- archflow:end --> block in AGENTS.md. */
function mergeAgentsMd(project, block, dry) {
  const file = join(project, "AGENTS.md");
  const region = /<!-- archflow:start[^>]*-->[\s\S]*?<!-- archflow:end -->\n?/;
  let text = existsSync(file) ? readFileSync(file, "utf8") : "";
  let action;
  if (region.test(text)) {
    text = text.replace(region, block);
    action = "update AGENTS.md (archflow block replaced in place)";
  } else if (text.trim()) {
    text = text.replace(/\s*$/, "\n\n") + block;
    action = "append AGENTS.md (archflow block added)";
  } else {
    text = "# AGENTS.md\n\nThis file provides guidance to AI coding agents working with code in this repository.\n\n" + block;
    action = "create AGENTS.md";
  }
  if (!dry) writeFileSync(file, text);
  return action;
}

/**
 * Merge `[table]\nkey = value` lines into a TOML file without a parser.
 * Existing keys are left alone (a human's value wins). Missing tables are appended.
 */
function mergeToml(file, snippet, dry) {
  const wanted = [];
  let table = null;
  for (const raw of snippet.split("\n")) {
    const line = raw.replace(/#.*$/, "").trim();
    if (!line) continue;
    const t = line.match(/^\[([^\]]+)\]$/);
    if (t) { table = t[1]; continue; }
    const kv = line.match(/^([A-Za-z0-9_.-]+)\s*=\s*(.+)$/);
    if (kv && table) wanted.push({ table, key: kv[1], line: `${kv[1]} = ${kv[2]}` });
  }
  if (!existsSync(file)) {
    if (!dry) { mkdirSync(dirname(file), { recursive: true }); writeFileSync(file, snippet); }
    return `create ${relative(dirname(dirname(file)), file)}`;
  }
  const lines = readFileSync(file, "utf8").split("\n");
  const added = [];
  for (const w of wanted) {
    const start = lines.findIndex((l) => l.trim() === `[${w.table}]`);
    if (start === -1) {
      if (lines[lines.length - 1]?.trim() !== "") lines.push("");
      lines.push(`[${w.table}]`, w.line);
      added.push(`${w.table}.${w.key}`);
      continue;
    }
    let end = lines.findIndex((l, i) => i > start && /^\s*\[/.test(l));
    if (end === -1) end = lines.length;
    const present = lines.slice(start + 1, end).some((l) => new RegExp(`^\\s*${w.key.replace(/\./g, "\\.")}\\s*=`).test(l));
    if (!present) { lines.splice(start + 1, 0, w.line); added.push(`${w.table}.${w.key}`); }
  }
  if (!added.length) return `keep  .codex/config.toml (already has hooks, multi_agent, agent threads)`;
  if (lines[lines.length - 1] !== "") lines.push("");
  if (!dry) writeFileSync(file, lines.join("\n"));
  return `merge .codex/config.toml (+ ${added.join(", ")})`;
}

/**
 * Install the pre-push guard. The script itself is copied into .git/hooks so it
 * does not depend on where this package lives. An existing hook is chained; the
 * ref list on stdin is captured to a temp file so BOTH hooks read it.
 */
function installGuard(project, dry) {
  const git = spawnSync("git", ["rev-parse", "--git-path", "hooks"], { cwd: project, encoding: "utf8" });
  if (git.status !== 0) return "skip  git guard (not a git repository)";
  const hooks = resolve(project, git.stdout.trim());
  const script = join(hooks, "archflow-pre-push.sh");
  const hook = join(hooks, "pre-push");
  const existing = existsSync(hook) ? readFileSync(hook, "utf8") : null;
  const chained = existing !== null && !existing.includes("archflow-pre-push");
  const chainedName = "pre-push.pre-archflow";
  if (dry) return existing === null ? "write .git/hooks/pre-push (archflow guard)"
    : chained ? `write .git/hooks/pre-push (archflow guard, chaining your existing hook as ${chainedName})`
    : "keep  .git/hooks/pre-push (archflow guard already installed; script refreshed)";

  mkdirSync(hooks, { recursive: true });
  writeFileSync(script, readFileSync(PRE_PUSH, "utf8"));
  chmodSync(script, 0o755);
  if (existing !== null && !chained) return "keep  .git/hooks/pre-push (archflow guard already installed; script refreshed)";
  if (chained) renameSync(hook, join(hooks, chainedName));
  const body = chained
    ? `#!/bin/sh\n# Installed by archflow ${VERSION}. Runs the Archflow guard, then your previous hook (${chainedName}).\n` +
      `hooks="$(cd "$(dirname "$0")" && pwd)"\ntmp="$(mktemp)"; cat >"$tmp"\n` +
      `"$hooks/archflow-pre-push.sh" "$@" <"$tmp" || { rm -f "$tmp"; exit 1; }\n` +
      `"$hooks/${chainedName}" "$@" <"$tmp"; rc=$?; rm -f "$tmp"; exit $rc\n`
    : `#!/bin/sh\n# Installed by archflow ${VERSION}.\nexec "$(cd "$(dirname "$0")" && pwd)/archflow-pre-push.sh" "$@"\n`;
  writeFileSync(hook, body);
  chmodSync(hook, 0o755);
  return chained ? `write .git/hooks/pre-push (archflow guard, previous hook chained as ${chainedName})` : "write .git/hooks/pre-push (archflow guard)";
}

/**
 * Claude Code: the plugin itself, from the marketplace, enabled at project scope so the
 * choice is committed with the repo and teammates are prompted to install. Prefer the
 * `claude` CLI; without it, write the same two settings keys by hand.
 */
function installClaude(project, source, dry) {
  const rel = ".claude/settings.json";
  if (onPath("claude")) {
    const steps = [
      ["marketplace", ["plugin", "marketplace", "add", source, "--scope", "project"]],
      ["install", ["plugin", "install", "archflow@archflow", "--scope", "project", "-y"]],
    ];
    if (dry) return steps.map(([, a]) => `run   claude ${a.join(" ")}`);
    const out = [];
    const run = (args) => {
      const r = spawnSync("claude", args, { cwd: project, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: 180000 });
      const msg = ((r.stdout || "") + (r.stderr || "")).trim().split("\n").filter(Boolean).pop() || "";
      return { ok: r.status === 0 || /already/i.test(msg), msg: msg || (r.status === 0 ? "ok" : `exit ${r.status}`) };
    };
    let installedBefore = false;
    for (const [, args] of steps) {
      const { ok, msg } = run(args);
      if (!ok) {
        out.push(`fail  claude ${args.join(" ")} → ${msg}`);
        out.push(...writeClaudeSettings(project, source, dry));
        return out;
      }
      out.push(`run   claude ${args.join(" ")} → ${msg}`);
      if (args[1] === "install" && /already installed/i.test(msg)) installedBefore = true;
    }
    // A re-run is an upgrade: refresh the marketplace and move the plugin to its latest version.
    if (installedBefore) {
      for (const args of [["plugin", "marketplace", "update", "archflow"], ["plugin", "update", "archflow@archflow", "--scope", "project"]]) {
        const { msg } = run(args);
        out.push(`run   claude ${args.join(" ")} → ${msg}`);
      }
    }
    return out;
  }
  return [...writeClaudeSettings(project, source, dry), "note  `claude` is not on PATH; the plugin installs when Claude Code next opens this project"];
}

function writeClaudeSettings(project, source, dry) {
  const file = join(project, ".claude", "settings.json");
  let settings = {};
  if (existsSync(file)) {
    try { settings = JSON.parse(readFileSync(file, "utf8")); }
    catch { return [`skip  .claude/settings.json (not valid JSON; add enabledPlugins[\"archflow@archflow\"] = true yourself)`]; }
  }
  const gh = source.match(/^([\w.-]+)\/([\w.-]+)$/);
  const changed = [];
  settings.extraKnownMarketplaces ??= {};
  if (!settings.extraKnownMarketplaces.archflow) {
    settings.extraKnownMarketplaces.archflow = gh
      ? { source: { source: "github", repo: `${gh[1]}/${gh[2]}` } }
      : { source: { source: "directory", path: source } };
    changed.push("extraKnownMarketplaces.archflow");
  }
  settings.enabledPlugins ??= {};
  if (settings.enabledPlugins["archflow@archflow"] !== true) {
    settings.enabledPlugins["archflow@archflow"] = true;
    changed.push("enabledPlugins[archflow@archflow]");
  }
  if (!changed.length) return ["keep  .claude/settings.json (plugin already enabled for this project)"];
  if (!dry) { mkdirSync(dirname(file), { recursive: true }); writeFileSync(file, JSON.stringify(settings, null, 2) + "\n"); }
  return [`${existsSync(file) ? "merge" : "create"} .claude/settings.json (+ ${changed.join(", ")})`];
}

/**
 * Gemini: a per-user extension. Prefer the CLI; with no `gemini` on PATH, copy into ~/.gemini/extensions.
 * The extension is installed from a staged copy of adapters/gemini plus Studio's bundle, kept
 * under ~/.cache/archflow (not a temp dir), because Gemini remembers where an extension came from.
 * Older staged copies are pruned only once the staged copy (bundle included) is confirmed to be the
 * installed extension; an install that did not land leaves everything as it was.
 */
function installGemini(dry) {
  const cache = join(homedir(), ".cache", "archflow", "gemini-extension");
  const staged = join(cache, VERSION, "archflow");
  if (!dry) {
    rmSync(staged, { recursive: true, force: true });
    copyInto(join(ADAPTERS, "gemini"), staged, false);
  }
  const studio = installStudio(staged, staged, dry);
  const bundled = studio.some((a) => a.startsWith("copy"));
  const { actions, via } = installGeminiFrom(staged, dry, bundled);
  const landed = via === "install" || via === "reinstall" || via === "copy";
  return [...studio, ...actions, ...(landed ? pruneStaged(cache, VERSION, dry) : [])];
}

const GEMINI_EXT = () => join(homedir(), ".gemini", "extensions", "archflow");
/** Where an existing extension waits while the new one installs; outside extensions/ so Gemini does not load it. */
const GEMINI_PREV = () => join(homedir(), ".gemini", "archflow-extension.previous");
/** Hosts whose install did not complete; main() reports them instead of "Installed." and exits 1. */
const incomplete = [];

/**
 * Gemini asks its own questions on `extensions install` (trust the source folder? trust this
 * workspace? continue?) and exits 0 when they are declined or unanswered. Those answers are the
 * user's, so the install runs with the terminal passed through, and only when there is a terminal.
 * ARCHFLOW_TEST_STDIN_TTY (1/0) overrides the check, for the test suite only.
 */
function stdinIsTTY() {
  const o = process.env.ARCHFLOW_TEST_STDIN_TTY;
  if (o === "1" || o === "0") return o === "1";
  return Boolean(process.stdin.isTTY);
}

/** True when ~/.gemini/extensions/archflow is the staged copy: same manifest, and the same server bundle when there is one. */
function geminiExtMatches(src) {
  const dst = GEMINI_EXT();
  const same = (rel) => {
    try { return readFileSync(join(src, rel)).equals(readFileSync(join(dst, rel))); } catch { return false; }
  };
  if (!same("gemini-extension.json")) return false;
  return !existsSync(join(src, "server", "server.mjs")) || same(join("server", "server.mjs"));
}

/**
 * Make `src` (the staged adapter + Studio bundle) the installed extension. Returns the actions taken
 * and `via`:
 *   install    first install through `gemini extensions install`, confirmed afterwards
 *   reinstall  it was already installed: the old copy is moved aside, `src` installed, the old copy
 *              removed once the new one is confirmed (or put back when it is not)
 *   copy       no `gemini` CLI on PATH: copied straight into ~/.gemini/extensions/archflow
 *   pending    not installed: no terminal to answer Gemini's prompts, or Gemini's install did not
 *              land (declined, cancelled, failed). The previous extension, if any, is left in place.
 * The exit code of `gemini extensions install` is never trusted: a declined prompt exits 0. Success
 * means `gemini extensions list` names archflow and the extension directory holds the staged copy.
 * `gemini extensions uninstall` and `update` are never used: update re-copies from the source Gemini
 * recorded at the first install (for 2.4.0, adapters/gemini without the bundle), and an uninstall
 * before an install that then stops at a prompt would leave the user with no extension.
 */
function installGeminiFrom(src, dry, bundled) {
  const what = bundled ? "adapter + Studio bundle" : "adapter";
  const label = "~/.gemini/extensions/archflow";
  const cmd = `gemini extensions install ${src}`;
  const ext = GEMINI_EXT();
  const had = existsSync(ext);
  if (onPath("gemini")) {
    const tty = stdinIsTTY();
    const askNote = "note  Gemini asks you to trust the extension folder (and this workspace) and to confirm; answer yes, or Studio's bundle is not installed";
    if (!tty) {
      const why = "no terminal to answer Gemini's trust and consent prompts";
      incomplete.push(`Gemini CLI: extension not installed (${why}). In a terminal, run \`${cmd}\` and accept Gemini's prompts, or re-run \`npx archflow@latest install --host gemini\` there.`);
      return { actions: [
        `skip  ${cmd} (${why}${had ? "; the installed extension is left as it is" : ""})`,
        `todo  run in a terminal: ${cmd}`,
      ], via: "pending" };
    }
    if (dry) {
      return { actions: [
        ...(had ? [`move  ${label} → ~/.gemini/archflow-extension.previous (already installed; restored if the new install does not land)`] : []),
        `run   ${cmd} → ${label} (${what}; interactive)`,
        askNote,
        ...(had ? ["remove ~/.gemini/archflow-extension.previous (once the new install is confirmed)"] : []),
      ], via: had ? "reinstall" : "install" };
    }
    const prev = GEMINI_PREV();
    if (had) {
      rmSync(prev, { recursive: true, force: true });
      renameSync(ext, prev); // same directory tree under ~/.gemini, so a rename, not a copy
    }
    log(`      Running \`${cmd}\`. Gemini asks you to trust the extension folder (and this workspace) and to confirm;`);
    log(`      answer yes, or Studio's bundle is not installed.`);
    const r = spawnSync("gemini", ["extensions", "install", src], { stdio: "inherit" });
    const list = spawnSync("gemini", ["extensions", "list"], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    const listed = /\barchflow\b/.test(`${list.stdout || ""}\n${list.stderr || ""}`);
    if (listed && geminiExtMatches(src)) {
      if (had) rmSync(prev, { recursive: true, force: true });
      return { actions: [
        ...(had ? [`move  ${label} → ~/.gemini/archflow-extension.previous (already installed)`] : []),
        `run   ${cmd} → installed, confirmed in \`gemini extensions list\` and ${label} (${what})`,
        ...(had ? ["remove ~/.gemini/archflow-extension.previous (the new install is confirmed)"] : []),
      ], via: had ? "reinstall" : "install" };
    }
    // Not landed. Put the previous extension back, so a declined upgrade changes nothing.
    let restored = "";
    if (had) {
      if (!existsSync(ext)) { renameSync(prev, ext); restored = "; the previous extension is back in place"; }
      else restored = `; Gemini left a partial ${label}, the previous one is kept at ~/.gemini/archflow-extension.previous`;
    }
    const why = r.error ? `gemini could not run: ${r.error.message}` : r.status === 0 ? "declined or cancelled" : `gemini exited ${r.status}`;
    incomplete.push(`Gemini CLI: install not completed (${why}); Studio bundle not installed. Re-run \`npx archflow@latest install --host gemini\` and accept Gemini's prompts, or run \`${cmd}\` yourself.`);
    return { actions: [`fail  ${cmd} (${why}; not in \`gemini extensions list\` with the staged copy${restored})`], via: "pending" };
  }
  const dst = ext;
  if (!dry) {
    rmSync(join(dst, "dist"), { recursive: true, force: true }); // hashed assets: replace, never merge
    rmSync(join(dst, "server"), { recursive: true, force: true });
    copyInto(src, dst, false);
  }
  return { actions: [`copy  ${src} → ${label} (Gemini extension: ${what}; no gemini CLI on PATH)`], via: "copy" };
}

/**
 * Remove staged Gemini extension copies (~11 MB each) left by earlier versions, keeping `keep`.
 * Only real directories directly under `cache` go; a symlink (the cache dir itself, or an entry in
 * it) is never followed or removed. A dry run lists what it would remove and removes nothing.
 */
function pruneStaged(cache, keep, dry) {
  let entries;
  try {
    if (!lstatSync(cache).isDirectory()) return [];
    entries = readdirSync(cache, { withFileTypes: true });
  } catch { return []; }
  const out = [];
  for (const e of entries) {
    if (e.name === keep || !e.isDirectory() || e.isSymbolicLink()) continue;
    const dir = join(cache, e.name);
    if (!dry) {
      try { rmSync(dir, { recursive: true, force: true }); } catch (err) { out.push(`note  could not remove ${dir} (${err.code || err.message})`); continue; }
    }
    out.push(`remove ${dir} (an older version's staged Gemini extension)`);
  }
  return out;
}

/** `archflow telemetry [on|off|status]` — status with no argument (or `status`), otherwise change it. */
function runTelemetry(arg) {
  if (arg === "on" || arg === "off") {
    const { sentOptOut, unreadable, saved } = setConsent(arg === "on", { via: "cli", host: "cli", archflow_version: VERSION });
    if (unreadable) { log(`Nothing was changed. ${CONFIG_UNREADABLE_NOTE}`); return; }
    if (!saved) { console.error(CONFIG_UNWRITABLE_NOTE); process.exit(1); }
    log(arg === "on" ? optInConfirmation() : `${OPT_OUT_CONFIRMATION}${sentOptOut ? OPT_OUT_SENT_NOTE : ""}`);
    return;
  }
  if (arg && arg !== "status") { console.error(`Unknown telemetry option: ${arg}. Try "on", "off" or "status".`); process.exit(2); }
  const config = loadConfig();
  if (isConfigUnreadable(config)) { log(`Anonymous usage telemetry is OFF for now: ${CONFIG_UNREADABLE_NOTE}`); return; }
  // Same line as /archflow:telemetry's --status: on/off, and since when (or which variable disabled it).
  // While an environment variable disables it, `on` cannot take effect, so suggest nothing.
  const on = isEnabled(config);
  const hint = disabledByEnv() ? "" : ` \`npx archflow telemetry ${on ? "off" : "on"}\` to turn it ${on ? "off" : "on"}.`;
  log(`Anonymous usage telemetry: ${statusLine(config)}.${hint}`);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  if (process.argv[2] === "telemetry") { runTelemetry(process.argv[3]); return; }
  const opts = parseArgs(process.argv.slice(2));
  const project = opts.dir;
  if (!existsSync(project) || !statSync(project).isDirectory()) {
    console.error(`Not a directory: ${project}`); process.exit(2);
  }
  await resolveSource(opts);
  if (!existsSync(ADAPTERS)) {
    console.error(`No adapters/ in ${SRC.root}. Run \`node scripts/build-adapters.mjs\` first.`); process.exit(2);
  }

  let hosts = [...new Set(opts.hosts)];
  for (const h of hosts) if (!HOSTS[h]) { console.error(`Unknown host "${h}". Known: ${Object.keys(HOSTS).join(", ")}`); process.exit(2); }
  if (hosts.includes("generic") && hosts.length > 1) {
    console.error("generic is the fallback for hosts without a native adapter and shares paths with codex; install it on its own.");
    process.exit(2);
  }
  if (!hosts.length) {
    hosts = Object.keys(HOSTS).filter((h) => HOSTS[h].detect(project));
    if (!hosts.length) {
      log("No supported host detected. Pass --host, e.g. --host cursor, or --host generic for any AGENTS.md + Agent Skills tool.");
      process.exit(1);
    }
    log(`Archflow ${VERSION} (${SRC.origin}) — detected: ${hosts.map((h) => HOSTS[h].label).join(", ")}`);
    log(`Project: ${project}\n`);
    if (!opts.yes && !opts.dryRun && !(await confirm(`Install for ${hosts.join(", ")}?`))) process.exit(0);
  } else {
    log(`Archflow ${VERSION} (${SRC.origin}) — hosts: ${hosts.join(", ")}\nProject: ${project}\n`);
  }
  if (opts.dryRun) log("DRY RUN — nothing will be written.\n");
  maybeNoticeTelemetry(opts.dryRun);

  const nextSteps = [];
  const blocks = [];
  for (const name of hosts) {
    const host = HOSTS[name];
    const src = join(ADAPTERS, name);
    if (!host.plugin && !existsSync(src)) { console.error(`adapters/${name} is missing from this package.`); process.exit(2); }
    log(`▸ ${host.label}`);
    const actions = [];

    if (host.plugin) {
      actions.push(...installClaude(project, opts.marketplace, opts.dryRun));
    } else if (host.extension) {
      actions.push(...installGemini(opts.dryRun));
    } else {
      for (const rel of host.copy) {
        const from = join(src, rel);
        if (!existsSync(from)) continue;
        const existed = existsSync(join(project, rel));
        copyInto(from, join(project, rel), opts.dryRun);
        actions.push(`${existed ? "update" : "copy "} ${rel}${lstatSync(from).isDirectory() ? "/" : ""}`);
      }
      const linked = ensureLink(project, host, opts.dryRun);
      if (linked) actions.push(linked);
      actions.push(...installStudio(join(project, host.hookRoot), host.hookRoot, opts.dryRun, { ignore: true }));
      if (host.agentsBlock) blocks.push({ label: host.label, text: readFileSync(join(src, host.agentsBlock), "utf8") });
      if (host.codexConfig) actions.push(mergeToml(join(project, ".codex", "config.toml"), readFileSync(join(src, host.codexConfig), "utf8"), opts.dryRun));
    }
    for (const a of actions) log(`    ${a}`);
    nextSteps.push([host.label, host.next]);
    log("");
  }

  if (blocks.length) {
    log("▸ AGENTS.md");
    log(`    ${mergeAgentsMd(project, combineBlocks(blocks), opts.dryRun)}${blocks.length > 1 ? ` — one section per host: ${blocks.map((b) => b.label).join(", ")}` : ""}\n`);
  }

  if (opts.guard) {
    log("▸ Git guard");
    log(`    ${installGuard(project, opts.dryRun)}\n`);
  }

  if (opts.dryRun) log("Dry run complete.");
  else if (incomplete.length) {
    log("Not fully installed:");
    for (const m of incomplete) log(`  ${m}`);
    process.exitCode = 1;
  } else log("Installed.");
  log("\nNext:");
  for (const [label, steps] of nextSteps) for (const s of steps) log(`  ${label}: ${s}`);
  log("\nRe-run this command after upgrading Archflow; it updates in place and never deletes your files.");

  if (!opts.dryRun) capture("cli_install", { host: "cli", archflow_version: VERSION, installed_hosts: hosts, source: SRC.origin });
}

main().catch((err) => { console.error(`archflow: ${err?.message ?? err}`); process.exit(1); });
