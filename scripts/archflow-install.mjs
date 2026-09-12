#!/usr/bin/env node
/**
 * archflow-install — put Archflow into a project for hosts other than Claude Code.
 *
 * Does, per host, exactly what adapters/<host>/README.md tells a human to do by hand:
 * copy the adapter tree in, merge the AGENTS.md block, merge Codex's config.toml
 * snippet, install the git pre-push guard. Re-running upgrades in place; it never
 * deletes a file it did not write.
 *
 * Usage (from inside the target project):
 *   npx archflow-install                      # detect hosts, install for each
 *   npx archflow-install --host codex,cursor  # explicit hosts
 *   npx archflow-install --dry-run            # show the plan only
 *
 * Options:
 *   --host <a,b>   codex | copilot | cursor | gemini | opencode | generic
 *   --dir <path>   project directory (default: cwd)
 *   --dry-run      print what would happen, change nothing
 *   --no-guard     skip the git pre-push guard
 *   --yes          do not ask for confirmation
 *
 * Local testing without publishing:
 *   node /path/to/archflow/scripts/archflow-install.mjs --host codex
 *   or `npm link` in the archflow checkout, then `archflow-install` anywhere.
 */

import {
  chmodSync, cpSync, existsSync, lstatSync, mkdirSync, readFileSync, renameSync, rmSync,
  symlinkSync, writeFileSync,
} from "node:fs";
import { spawnSync } from "node:child_process";
import { createInterface } from "node:readline";
import { homedir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PKG = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ADAPTERS = join(PKG, "adapters");
const PRE_PUSH = join(PKG, "plugin", "scripts", "archflow-pre-push.sh");
const VERSION = JSON.parse(readFileSync(join(PKG, "plugin", ".claude-plugin", "plugin.json"), "utf8")).version;

// ---------------------------------------------------------------------------
// Host table. `copy` are adapter-relative paths copied into the project.
// `hookRoot` is what the hooks see as CLAUDE_PLUGIN_ROOT; it must contain
// skills/archflow, which the adapter provides as a relative symlink. npm drops
// symlinks when packing, so `ensureLink` recreates it after the copy.
// ---------------------------------------------------------------------------
const HOSTS = {
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

function parseArgs(argv) {
  const o = { hosts: [], dir: process.cwd(), dryRun: false, guard: true, yes: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--host") o.hosts.push(...argv[++i].split(",").map((s) => s.trim()).filter(Boolean));
    else if (a.startsWith("--host=")) o.hosts.push(...a.slice(7).split(","));
    else if (a === "--dir") o.dir = resolve(argv[++i]);
    else if (a === "--dry-run") o.dryRun = true;
    else if (a === "--no-guard") o.guard = false;
    else if (a === "--yes" || a === "-y") o.yes = true;
    else if (a === "--help" || a === "-h") { log(readFileSync(fileURLToPath(import.meta.url), "utf8").match(/\/\*\*([\s\S]*?)\*\//)[1].replace(/^ \* ?/gm, "")); process.exit(0); }
    else { console.error(`Unknown option: ${a}`); process.exit(2); }
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
    ? `#!/bin/sh\n# Installed by archflow-install ${VERSION}. Runs the Archflow guard, then your previous hook (${chainedName}).\n` +
      `hooks="$(cd "$(dirname "$0")" && pwd)"\ntmp="$(mktemp)"; cat >"$tmp"\n` +
      `"$hooks/archflow-pre-push.sh" "$@" <"$tmp" || { rm -f "$tmp"; exit 1; }\n` +
      `"$hooks/${chainedName}" "$@" <"$tmp"; rc=$?; rm -f "$tmp"; exit $rc\n`
    : `#!/bin/sh\n# Installed by archflow-install ${VERSION}.\nexec "$(cd "$(dirname "$0")" && pwd)/archflow-pre-push.sh" "$@"\n`;
  writeFileSync(hook, body);
  chmodSync(hook, 0o755);
  return chained ? `write .git/hooks/pre-push (archflow guard, previous hook chained as ${chainedName})` : "write .git/hooks/pre-push (archflow guard)";
}

/** Gemini: a per-user extension. Prefer the CLI; fall back to copying into ~/.gemini/extensions. */
function installGemini(dry) {
  const src = join(ADAPTERS, "gemini");
  if (onPath("gemini")) {
    if (dry) return [`run   gemini extensions install ${src}`];
    const r = spawnSync("gemini", ["extensions", "install", src], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
    if (r.status === 0) return [`run   gemini extensions install → ${(r.stdout || "").trim().split("\n").pop() || "ok"}`];
    const msg = (r.stderr || r.stdout || "").trim().split("\n").pop();
    if (/already/i.test(msg)) {
      const u = spawnSync("gemini", ["extensions", "update", "archflow"], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
      if (u.status === 0) return [`run   gemini extensions update archflow → ${(u.stdout || "").trim().split("\n").pop() || "ok"}`];
    }
    log(`      gemini CLI install failed (${msg}); copying the extension directly`);
  }
  const dst = join(homedir(), ".gemini", "extensions", "archflow");
  if (!dry) copyInto(src, dst, false);
  return [`copy  ${dst} (Gemini extension)`];
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const project = opts.dir;
  if (!existsSync(project) || !lstatSync(project).isDirectory()) {
    console.error(`Not a directory: ${project}`); process.exit(2);
  }
  if (!existsSync(ADAPTERS)) {
    console.error(`No adapters/ next to this script (${ADAPTERS}). Run \`node scripts/build-adapters.mjs\` first.`); process.exit(2);
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
    log(`Archflow ${VERSION} — detected: ${hosts.map((h) => HOSTS[h].label).join(", ")}`);
    log(`Project: ${project}\n`);
    if (!opts.yes && !opts.dryRun && !(await confirm(`Install for ${hosts.join(", ")}?`))) process.exit(0);
  } else {
    log(`Archflow ${VERSION} — hosts: ${hosts.join(", ")}\nProject: ${project}\n`);
  }
  if (opts.dryRun) log("DRY RUN — nothing will be written.\n");

  const nextSteps = [];
  const blocks = [];
  for (const name of hosts) {
    const host = HOSTS[name];
    const src = join(ADAPTERS, name);
    if (!existsSync(src)) { console.error(`adapters/${name} is missing from this package.`); process.exit(2); }
    log(`▸ ${host.label}`);
    const actions = [];

    if (host.extension) {
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

  log(opts.dryRun ? "Dry run complete." : "Installed.");
  log("\nNext:");
  for (const [label, steps] of nextSteps) for (const s of steps) log(`  ${label}: ${s}`);
  log("\nRe-run this command after upgrading Archflow; it updates in place and never deletes your files.");
}

main().catch((err) => { console.error(`archflow-install: ${err?.message ?? err}`); process.exit(1); });
