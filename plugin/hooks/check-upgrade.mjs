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
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();
const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || join(cwd, "plugin");

function quit() {
  process.exit(0);
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

const fixable = report.findings.filter((f) => f.fixable);
const manual = report.findings.filter((f) => !f.fixable);

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
if (fixable.length) {
  lines.push(`    Run /archflow:doctor --fix to repair ${fixable.length} of these. It backs up`);
  lines.push("    everything it touches and never writes project content.");
}
if (manual.length) {
  lines.push(`    ${manual.length} item(s) need a decision from the user — /archflow:doctor explains them.`);
}
lines.push("");
lines.push("    Tell the user this before running their command. Do not repair anything unless");
lines.push("    they ask. If they would rather continue, that is fine — say what may misbehave.");

process.stdout.write(lines.join("\n") + "\n");
process.exit(0);
