#!/usr/bin/env node
/**
 * PreToolUse guard for Bash.
 *
 * Archflow's safety envelope is written in prompts: "never merge to main",
 * "merging stays the user's". Prompt rules hold most of the time, and "most of
 * the time" is the wrong reliability for an irreversible operation on a shared
 * branch — especially during /archflow:autopilot, which runs unattended for
 * hours by design.
 *
 * This turns the one rule that cannot be undone into a mechanical block.
 *
 * WHAT IT BLOCKS
 *   During an ACTIVE autopilot run only:
 *     - git push  targeting main/master
 *     - git merge while main/master is checked out
 *     - git checkout/switch to main/master (the setup move for both)
 *   Always:
 *     - git push --force / --force-with-lease targeting main/master
 *
 * WHAT IT DOES NOT DO
 *   Outside an autopilot run it blocks nothing except a force-push to main. The
 *   framework's approval gates are the control there, and a hook that fought
 *   every ordinary merge would be turned off within a day.
 *
 * FAIL-OPEN
 *   Any internal error allows the command and prints a warning to stderr. A
 *   guard that breaks the session when its own parsing is wrong is worse than
 *   the risk it removes. It reads at most a small directory listing and exits
 *   well inside the 2s budget.
 *
 * Exit codes: 0 allow · 2 block (stderr goes back to the model)
 */

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const PROTECTED = /^(?:main|master|origin\/main|origin\/master)$/;

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

/** Is an autopilot run live in this project? Cheap: one directory read. */
function activeAutopilotRun(cwd) {
  let entries;
  try {
    entries = readdirSync(join(cwd, ".archflow", "autopilot"));
  } catch {
    return null; // no directory, no run
  }
  for (const name of entries) {
    if (!name.endsWith(".yaml") && !name.endsWith(".yml")) continue;
    let text;
    try {
      text = readFileSync(join(cwd, ".archflow", "autopilot", name), "utf8");
    } catch {
      continue;
    }
    // Deliberately not a YAML parse: one regex on a small file keeps this fast
    // and dependency-free. The field is written by the framework itself.
    const m = text.match(/^\s*status:\s*["']?([a-z_]+)["']?\s*$/m);
    if (m && (m[1] === "running" || m[1] === "preflight")) {
      const id = text.match(/^\s*run_id:\s*["']?([^"'\s]+)/m);
      return { file: name, runId: id ? id[1] : name.replace(/\.ya?ml$/, "") };
    }
  }
  return null;
}

/** Split a compound command into its individual invocations. */
function segments(command) {
  return command
    .split(/\s*(?:&&|\|\||;|\n)\s*/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function analyse(segment) {
  const words = segment.split(/\s+/).filter(Boolean);
  const gi = words.findIndex((w) => w === "git" || w.endsWith("/git"));
  if (gi === -1) return null;

  // Skip git's own global options to find the subcommand.
  let i = gi + 1;
  while (i < words.length && words[i].startsWith("-")) {
    if (words[i] === "-c" || words[i] === "-C") i++; // these take a value
    i++;
  }
  const sub = words[i];
  if (!sub) return null;
  const rest = words.slice(i + 1);
  const targets = rest.filter((w) => !w.startsWith("-"));
  const forced = rest.some((w) => w === "-f" || w === "--force" || w.startsWith("--force-with-lease"));

  if (sub === "push") {
    const hitsProtected = targets.some((t) => PROTECTED.test(t.replace(/^\+/, "").split(":").pop()));
    if (hitsProtected) return { kind: "push", forced, segment };
    return null;
  }
  if (sub === "merge") return { kind: "merge", forced, segment };
  if (sub === "checkout" || sub === "switch") {
    if (targets.some((t) => PROTECTED.test(t))) return { kind: "checkout", forced, segment };
    return null;
  }
  return null;
}

function currentBranch(cwd) {
  try {
    const head = readFileSync(join(cwd, ".git", "HEAD"), "utf8").trim();
    const m = head.match(/^ref:\s*refs\/heads\/(.+)$/);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function block(reason, detail) {
  process.stderr.write(`${reason}\n\n${detail}\n`);
  process.exit(2);
}

function main() {
  const raw = readStdin();
  if (!raw.trim()) process.exit(0);

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    process.exit(0); // not our shape; never get in the way
  }

  if (input.tool_name !== "Bash") process.exit(0);
  const command = input?.tool_input?.command;
  if (typeof command !== "string" || !command.includes("git")) process.exit(0);

  const cwd = input.cwd || process.cwd();
  const findings = segments(command).map(analyse).filter(Boolean);
  if (findings.length === 0) process.exit(0);

  // Always: a force-push to a protected branch rewrites shared history.
  const forcePush = findings.find((f) => f.kind === "push" && f.forced);
  if (forcePush) {
    block(
      "Blocked: force-push to a protected branch.",
      `Archflow never rewrites history on main or master. If this is genuinely intended, run it\n` +
        `yourself outside the agent session.\n\n  ${forcePush.segment}`
    );
  }

  const run = activeAutopilotRun(cwd);
  if (!run) process.exit(0); // outside a run, the approval gates are the control

  const branch = currentBranch(cwd);

  for (const f of findings) {
    if (f.kind === "push") {
      block(
        "Blocked: pushing to a protected branch during an autopilot run.",
        `Autopilot pre-authorizes review gates, never the merge to main. Everything lands on the\n` +
          `run branch and the user merges when they are ready.\n\n` +
          `  run: ${run.runId} (.archflow/autopilot/${run.file})\n  ${f.segment}\n\n` +
          `Finish the run and report. If the run is actually over, set its status to finished or\n` +
          `aborted in the ledger.`
      );
    }
    if (f.kind === "checkout") {
      block(
        "Blocked: checking out a protected branch during an autopilot run.",
        `An autopilot run works on its run branch. Switching to main is the setup move for a merge\n` +
          `the user has not approved.\n\n` +
          `  run: ${run.runId} (.archflow/autopilot/${run.file})\n  ${f.segment}`
      );
    }
    if (f.kind === "merge" && branch && PROTECTED.test(branch)) {
      block(
        "Blocked: merging into a protected branch during an autopilot run.",
        `HEAD is on ${branch}. Merging here is the one thing autopilot may never do — the schema\n` +
          `pins merge_to_main to false and the user owns that decision.\n\n` +
          `  run: ${run.runId} (.archflow/autopilot/${run.file})\n  ${f.segment}`
      );
    }
  }
  process.exit(0);
}

try {
  main();
} catch (err) {
  // Fail open, loudly. Never break a session because the guard misparsed.
  process.stderr.write(`archflow guard-git: allowing command (guard error: ${err?.message ?? err})\n`);
  process.exit(0);
}
