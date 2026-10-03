#!/usr/bin/env node
/**
 * Telemetry hook. On by default; see plugin/lib/telemetry.mjs for what is sent.
 *
 *   (no flag)       session start: sends session_start with how the session began
 *   --command-run   Claude Code UserPromptExpansion (matcher ^archflow:.*) and
 *                   OpenCode command.executed: the host names the command, which
 *                   is reported only if it is a shipped one; never reads command_input
 *   --prompt        a host's prompt-submit hook (Codex, Copilot, Cursor, Gemini):
 *                   reads the raw prompt only to match a LEADING /archflow:x,
 *                   /archflow-x or $archflow-x against the shipped command list,
 *                   and sends just that name. Prints nothing, because on some
 *                   hosts prompt-hook stdout becomes model context or must be JSON.
 *   --status | --enable | --disable [--host <name>]   used by /archflow:telemetry (each
 *                   adapter's copy passes its own --host, since no hook sets ARCHFLOW_HOST there)
 *
 * The one-time notice is printed by session start or --command-run, in the
 * format the host surfaces (plain text, or JSON on Copilot and Gemini; see
 * formatNotice), and marked shown only after it was written. Every
 * property is checked against the allow-list in ../lib/telemetry.mjs, which
 * drops unknown keys and turns an unrecognised project_type, phase, mode or
 * session_source into null (or "other").
 *
 * FAIL-OPEN and FAST: no network in this process, exits 0 on every path.
 */

import { existsSync, readFileSync, readdirSync, writeSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isatty } from "node:tty";
import { CONFIG_UNREADABLE_NOTE, NOTICE, OPT_OUT_CONFIRMATION, OPT_OUT_SENT_NOTE, capture, hasSeenNotice, isEnabled, loadConfig, optInConfirmation, optOutLine, recordNoticeShown, setConsent, statusLine } from "../lib/telemetry.mjs";

/**
 * This hook's own install root: plugin/ for the Claude Code plugin, <host>/archflow/
 * (or the Gemini extension root) in an adapter. copyHookRuntime ships
 * .claude-plugin/plugin.json and lib/ next to hooks/ there, so the version and the
 * command list resolve even where no CLAUDE_PLUGIN_ROOT is set (the generic host).
 */
const HOOK_ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

function readInput() {
  // isatty(0), not process.stdin.isTTY: touching process.stdin starts a stream reader
  // that races readFileSync(0) and truncates large payloads such as long prompts.
  if (isatty(0)) return {};
  try {
    return JSON.parse(readFileSync(0, "utf8") || "{}");
  } catch {
    return {};
  }
}

/** The version shipped beside this script, else under CLAUDE_PLUGIN_ROOT. */
function pluginVersion(pluginRoot) {
  for (const root of [HOOK_ROOT, pluginRoot]) {
    try {
      const version = JSON.parse(readFileSync(join(root, ".claude-plugin", "plugin.json"), "utf8")).version;
      if (version) return version;
    } catch {
      // try the next root
    }
  }
  return null;
}

/** Regex, not a YAML parse, like check-upgrade.mjs. */
function projectState(cwd) {
  const file = join(cwd, ".archflow", "current-phase.yaml");
  let phase = null, mode = null;
  try {
    const text = readFileSync(file, "utf8");
    phase = text.match(/^\s*phase:\s*["']?([\w.-]+)/m)?.[1] || null;
    mode = text.match(/^\s*mode:\s*["']?([\w.-]+)/m)?.[1] || null;
  } catch {
    // not an Archflow project yet
  }
  let project_type = null;
  try {
    const settings = readFileSync(join(cwd, ".archflow", "project-settings.yaml"), "utf8");
    project_type = settings.match(/^\s*project_type:\s*["']?([\w.-]+)/m)?.[1] || null;
  } catch {
    // no settings file
  }
  return { has_project: existsSync(file), project_type, phase, mode };
}

/**
 * Shipped command names: the list an adapter build writes, else the plugin's own
 * commands/*.md. The list comes first because some adapters have a commands/ dir
 * in another format (Gemini's is TOML).
 */
function knownCommands(pluginRoot) {
  try {
    return new Set(JSON.parse(readFileSync(join(pluginRoot, "lib", "commands.json"), "utf8")));
  } catch {
    // the Claude Code plugin ships no list; read its command files
  }
  try {
    return new Set(readdirSync(join(pluginRoot, "commands")).filter((f) => f.endsWith(".md")).map((f) => f.slice(0, -3)));
  } catch {
    return null;
  }
}

/**
 * "archflow:status" from a prompt that STARTS with an invocation, or with the
 * marker a Gemini command prompt begins with (Gemini may expand a slash command
 * before its prompt hook runs). null otherwise.
 */
export function commandFromPrompt(prompt, known) {
  if (typeof prompt !== "string") return null;
  const m = prompt.trimStart().match(/^(?:\/archflow[:-]|\$archflow-|<!-- archflow-command: )([a-z][a-z-]*)(?![\w-])/);
  if (!m || !known?.has(m[1])) return null;
  return `archflow:${m[1]}`;
}

/**
 * "archflow:status" from a name a host reports directly ("archflow:status" from
 * Claude Code, "archflow-status" from OpenCode), only when it is a shipped
 * command. A user's own archflow-* command, or a name with anything after it,
 * is not reported.
 */
export function commandFromName(name, known) {
  if (typeof name !== "string") return null;
  const m = name.match(/^\/?archflow[:-]([a-z][a-z-]*)$/);
  if (!m || !known?.has(m[1])) return null;
  return `archflow:${m[1]}`;
}

/**
 * Which host's output rules apply. Every adapter sets ARCHFLOW_HOST. Unset means
 * the Claude Code plugin, but Copilot CLI can load that plugin directly and drops
 * plain-text SessionStart output, so "claude" is claimed only when Claude Code's
 * own markers are present: it writes CLAUDECODE=1 and CLAUDE_CODE_ENTRYPOINT into
 * every subprocess it spawns, hooks included. Either one is enough, so a future
 * Claude Code that drops one still gets the notice. With neither, the host is
 * unknown and the notice stays pending.
 */
function noticeHost() {
  if (process.env.ARCHFLOW_HOST) return process.env.ARCHFLOW_HOST;
  return process.env.CLAUDECODE || process.env.CLAUDE_CODE_ENTRYPOINT ? "claude" : null;
}

/**
 * The notice in the shape each host's hook actually surfaces to the model, or null
 * for a host whose format is unknown. Plain stdout reaches the model on Claude Code
 * and Codex, through the Cursor bridge (which wraps it as additional_context) and
 * the OpenCode plugin (which pushes it into the system prompt), and to the agent
 * that runs the script on generic. Copilot drops non-JSON SessionStart output and
 * reads `additionalContext`; Gemini wants JSON on stdout with
 * `hookSpecificOutput.additionalContext`.
 */
export function formatNotice(text, host = noticeHost(), hookEvent = "SessionStart") {
  if (["claude", "codex", "cursor", "opencode", "generic"].includes(host)) return text;
  if (host === "copilot") return JSON.stringify({ additionalContext: text });
  if (host === "gemini") return JSON.stringify({ hookSpecificOutput: { hookEventName: hookEvent, additionalContext: text } });
  return null;
}

/**
 * Print the one-time notice, and mark it shown only once it has been written in a
 * format this host surfaces. On an unknown host nothing is printed and the notice
 * stays pending, so a later session on a known host still shows it.
 */
function showNoticeOnce() {
  if (hasSeenNotice(loadConfig()) || !isEnabled()) return;
  const host = noticeHost();
  const out = formatNotice(NOTICE + optOutLine(host), host);
  if (out === null) return;
  try {
    writeSync(1, out);
  } catch {
    return; // not emitted, so not shown
  }
  recordNoticeShown();
}

const arg = process.argv[2];

if (arg === "--status") {
  process.stdout.write(`${statusLine()}\n`);
  process.exit(0);
}

if (arg === "--enable" || arg === "--disable") {
  const on = arg === "--enable";
  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || HOOK_ROOT;
  // Each adapter's telemetry command passes `--host <name>`: an agent runs it outside any hook,
  // where ARCHFLOW_HOST is unset. The allow-list in capture() still checks the value.
  const hostAt = process.argv.indexOf("--host");
  const host = hostAt > 2 ? process.argv[hostAt + 1] : undefined;
  const { sentOptOut, unreadable } = setConsent(on, { via: "command", archflow_version: pluginVersion(pluginRoot), host });
  if (unreadable) {
    process.stdout.write(`Nothing was changed. ${CONFIG_UNREADABLE_NOTE}\n`);
    process.exit(0);
  }
  process.stdout.write(on ? `${optInConfirmation()}\n` : `${OPT_OUT_CONFIRMATION}${sentOptOut ? OPT_OUT_SENT_NOTE : ""}\n`);
  process.exit(0);
}

try {
  const input = readInput();
  const cwd = input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || HOOK_ROOT;
  const common = { archflow_version: pluginVersion(pluginRoot), ...projectState(cwd) };

  // The opt-out command itself is never reported: turning telemetry off must not send an event.
  if (arg === "--command-run") {
    const command = commandFromName(input.command_name, knownCommands(pluginRoot));
    if (command && command !== "archflow:telemetry") {
      showNoticeOnce();
      capture("command_run", { ...common, command, detected_by: "command_hook" });
    }
  } else if (arg === "--prompt") {
    const command = commandFromPrompt(input.prompt, knownCommands(pluginRoot));
    // No notice here: on these hosts prompt-hook stdout is model context or must be JSON. If this
    // fires before any session start, capture() still mints the id, and the notice stays pending
    // for the next session start, which prints it through showNoticeOnce like every other surface.
    if (command && command !== "archflow:telemetry") {
      capture("command_run", { ...common, command, detected_by: "prompt_prefix" });
    }
  } else {
    showNoticeOnce();
    capture("session_start", { ...common, session_source: typeof input.source === "string" ? input.source : null });
  }
} catch {
  // fail open
}
process.exit(0);
