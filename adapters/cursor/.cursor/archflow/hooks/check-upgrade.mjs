#!/usr/bin/env node
/**
 * SessionStart hook: tell the user, once per session, when their project has
 * fallen behind the installed plugin.
 *
 * A project's .archflow/ is a COPY of framework files made at setup. When the
 * plugin updates, that copy does not. The result is a project running against
 * files the current agents no longer match, and the symptom arrives later as an
 * agent doing something inexplicable — a design system it cannot read, an agent
 * name that no longer resolves.
 *
 * Nothing surfaced that, so it surfaces here, before the first command rather
 * than in the middle of a story.
 *
 * WHY A VERSION COMPARE FIRST
 *   This runs on every session start. The common case is "up to date", and that
 *   path must cost nothing: two small file reads and a string compare. The
 *   detector only runs when the versions actually differ.
 *
 * WHY IT STOPS NAGGING
 *   /archflow:doctor --fix stamps plugin_version. The same field that detects
 *   the drift is the one that silences the notice, so a user who repairs is not
 *   told again, and a user who ignores it is — which is the correct asymmetry
 *   for something that will otherwise bite them later.
 *
 * FAIL-OPEN and FAST: any error, missing file or slow detector exits silently.
 *
 * NEWER RELEASE
 *   The hook also says when a newer Archflow release exists than what is installed.
 *   On Claude Code that means the marketplace plugin fell behind (auto-update off, or
 *   a plugin loaded from a path); on every other host it means the copied adapter,
 *   which nothing refreshes. The check is the npm/brew kind: it reads a cache
 *   (~/.cache/archflow-install/latest.json), and when that is older than a day it
 *   spawns a detached child to refresh it. The hook itself never waits on the
 *   network. Off with `update_check: false` in project-settings.yaml, or the
 *   ARCHFLOW_NO_UPDATE_CHECK env var. The host is named by ARCHFLOW_HOST, which
 *   each adapter's hook wiring sets; unset means Claude Code, and the notice then
 *   names the plugin update command instead of the installer.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const RELEASES_URL = process.env.ARCHFLOW_RELEASES_URL || "https://github.com/AZidan/archflow/releases/latest";
const CACHE_DIR = process.env.ARCHFLOW_CACHE_DIR || join(homedir(), ".cache", "archflow-install");
const LATEST = join(CACHE_DIR, "latest.json");
const DAY = 24 * 60 * 60 * 1000;

// Detached refresher: resolve the latest tag through the releases-page redirect
// (no API, no rate limit), write the cache, exit. Only ever run in the background.
if (process.argv.includes("--refresh-latest")) {
  try {
    const res = await fetch(RELEASES_URL, { redirect: "follow", signal: AbortSignal.timeout(8000) });
    const tag = new URL(res.url).pathname.split("/").pop();
    if (/^\d+\.\d+\.\d+$/.test(tag)) {
      mkdirSync(CACHE_DIR, { recursive: true });
      writeFileSync(LATEST, JSON.stringify({ tag, checkedAt: Date.now() }) + "\n");
    }
  } catch {
    // offline, or GitHub is not answering: try again next time
  }
  process.exit(0);
}

const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || join(cwd, "plugin");

// Set once the installed version is known; printed on every exit path.
let releaseNotice = null;

function quit() {
  if (releaseNotice) process.stdout.write(releaseNotice);
  process.exit(0);
}

function isNewer(a, b) {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) > (pb[i] || 0);
  }
  return false;
}

function checkRelease(installed) {
  const host = process.env.ARCHFLOW_HOST || "claude";
  if (process.env.ARCHFLOW_NO_UPDATE_CHECK) return null;
  try {
    const settings = readFileSync(join(cwd, ".archflow", "project-settings.yaml"), "utf8");
    if (/^\s*update_check:\s*false\b/m.test(settings)) return null;
  } catch {
    // no settings file: the check is on by default
  }
  let cache = null;
  try {
    cache = JSON.parse(readFileSync(LATEST, "utf8"));
  } catch {
    // no cache yet
  }
  const fresh = cache && typeof cache.checkedAt === "number" && Date.now() - cache.checkedAt < DAY;
  if (!fresh) {
    try {
      const child = spawn(process.execPath, [fileURLToPath(import.meta.url), "--refresh-latest"], {
        detached: true, stdio: "ignore", env: process.env,
      });
      child.unref();
    } catch {
      // cannot spawn: no check this time
    }
  }
  if (!cache?.tag || typeof cache.tag !== "string" || !isNewer(cache.tag, installed)) return null;
  const how = host === "claude"
    ? [`⬆️  Archflow ${cache.tag} is available. The installed plugin is ${installed}.`,
       `    Update it:  claude plugin marketplace update archflow && claude plugin update archflow@archflow`,
       `    (add --scope project if it was installed for this project only; /plugin in Claude Code does the same).`,
       `    Then run /archflow:doctor --fix so .archflow/ catches up.`]
    : [`⬆️  Archflow ${cache.tag} is available. This project's ${host} adapter is ${installed}.`,
       `    Upgrade from the project root:  npx archflow-install --host ${host}`,
       `    Then run the Archflow doctor with --fix so .archflow/ catches up.`];
  return [...how, `    Tell the user. Do not run either unless they ask.`, ""].join("\n");
}

// Not an Archflow project.
const currentPhase = join(cwd, ".archflow", "current-phase.yaml");
if (!existsSync(currentPhase)) quit();

let installed = null;
try {
  installed = JSON.parse(
    readFileSync(join(pluginRoot, ".claude-plugin", "plugin.json"), "utf8")
  ).version;
} catch {
  quit(); // cannot tell what is installed; say nothing
}
if (!installed) quit();

releaseNotice = checkRelease(installed);

let stamped = null;
try {
  const text = readFileSync(currentPhase, "utf8");
  const m = text.match(/^\s*plugin_version:\s*["']?([^"'\s#]+)/m);
  stamped = m ? m[1] : null;
} catch {
  quit();
}

// The fast path: up to date, nothing to say.
if (stamped === installed) quit();

// Versions differ or the stamp is absent. Now it is worth looking properly.
const detector = join(pluginRoot, "scripts", "upgrade_archflow.py");
if (!existsSync(detector)) quit();

let result;
try {
  result = spawnSync(
    "python3",
    [detector, cwd, "--plugin-root", pluginRoot, "--version", installed, "--json"],
    { encoding: "utf8", timeout: 3000, killSignal: "SIGKILL" }
  );
} catch {
  quit();
}
if (!result || result.error || result.status === null || result.status === 2) quit();

let report;
try {
  report = JSON.parse(result.stdout);
} catch {
  quit();
}
if (!report.drift || !report.findings?.length) quit();

const repairable = report.findings.filter((f) => f.fix_by !== "user");
const manual = report.findings.filter((f) => f.fix_by === "user");

const lines = [];
lines.push("⬆️  This project is behind the installed Archflow plugin.");
lines.push("");
lines.push(
  `    Project was last set up on ${stamped ? `plugin ${stamped}` : "a plugin that predates version stamping"}.`
);
lines.push(`    Installed plugin is ${installed}.`);
lines.push("");
lines.push("    .archflow/ is a copy of framework files made at setup and is not refreshed");
lines.push("    automatically, so some of it no longer matches the agents that read it:");
lines.push("");
for (const f of report.findings) {
  lines.push(`      - ${f.summary}`);
}
lines.push("");
if (repairable.length) {
  lines.push(`    Run /archflow:doctor --fix to repair ${repairable.length} of these. It backs up`);
  lines.push("    everything it touches and never writes project content.");
}
if (manual.length) {
  lines.push(`    ${manual.length} item(s) need a decision only the user can make — /archflow:doctor explains them.`);
}
lines.push("");
lines.push("    Tell the user this before running their command. Do not repair anything unless");
lines.push("    they ask. If they would rather continue, that is fine — say what may misbehave.");

process.stdout.write((releaseNotice || "") + lines.join("\n") + "\n");
process.exit(0);
