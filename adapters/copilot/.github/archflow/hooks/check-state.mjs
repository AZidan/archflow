#!/usr/bin/env node
/**
 * Stop hook: warn when a session leaves .archflow/ state files invalid.
 *
 * Agents write these files by hand from prose instructions. A field that drifts
 * from its schema is not noticed at the moment it is written; it surfaces later
 * as an agent doing the wrong thing somewhere unrelated. This closes the loop at
 * the end of the turn that caused it, while the change is still in view.
 *
 * ADVISORY ONLY. It prints and exits 0. Blocking a session over state that is
 * mid-edit would punish the normal case, and a story is frequently half-written
 * when a turn ends.
 *
 * FAIL-OPEN and FAST: skips silently when there is no project, no validator, or
 * no python3, and gives the validator a hard 2s ceiling.
 */

import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const cwd = process.env.CLAUDE_PROJECT_DIR || process.cwd();

// Nothing to check.
if (!existsSync(join(cwd, ".archflow", "schemas"))) process.exit(0);

const validator = join(
  process.env.CLAUDE_PLUGIN_ROOT || join(cwd, "plugin"),
  "scripts",
  "validate_archflow.py"
);
if (!existsSync(validator)) process.exit(0);

let result;
try {
  result = spawnSync("python3", [validator, cwd, "--quiet"], {
    encoding: "utf8",
    timeout: 2000,
    killSignal: "SIGKILL",
  });
} catch {
  process.exit(0);
}

// python3 absent, timed out, or could not run (exit 2): stay quiet. PyYAML is a
// recommended dependency, not a required one, and this is advisory.
if (!result || result.error || result.status === null || result.status === 2) process.exit(0);

if (result.status === 1) {
  const detail = (result.stdout || "").trim();
  process.stderr.write(
    "archflow: .archflow/ state files have drifted from their schemas.\n\n" +
      detail +
      "\n  Run /archflow:doctor --validate for the full report.\n"
  );
}
process.exit(0);
