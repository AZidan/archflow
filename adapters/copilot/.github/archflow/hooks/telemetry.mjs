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
 *   --status | --enable | --disable   used by /archflow:telemetry
 *
 * The one-time notice is printed by session start or --command-run, whose
 * plain stdout reaches the model, and marked shown only after printing. Every
 * property is checked against the allow-list in ../lib/telemetry.mjs, which
 * drops unknown keys and turns an unrecognised project_type, phase, mode or
 * session_source into null (or "other").
 *
 * FAIL-OPEN and FAST: no network in this process, exits 0 on every path.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { isatty } from "node:tty";
import { NOTICE, OPT_OUT_CONFIRMATION, OPT_OUT_SENT_NOTE, capture, hasSeenNotice, isEnabled, loadConfig, recordNoticeShown, setConsent } from "../lib/telemetry.mjs";

const OPT_OUT_LINE = "Tell the user this once, and that /archflow:telemetry off turns it off.\n";

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

function pluginVersion(pluginRoot) {
  try {
    return JSON.parse(readFileSync(join(pluginRoot, ".claude-plugin", "plugin.json"), "utf8")).version || null;
  } catch {
    return null;
  }
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

function showNoticeOnce() {
  if (hasSeenNotice(loadConfig()) || !isEnabled()) return;
  process.stdout.write(NOTICE + OPT_OUT_LINE);
  recordNoticeShown();
}

const arg = process.argv[2];

if (arg === "--status") {
  const config = loadConfig();
  process.stdout.write(`${isEnabled(config) ? "on" : "off"}${config.noticeShownAt ? ` (since ${config.noticeShownAt})` : " (default)"}\n`);
  process.exit(0);
}

if (arg === "--enable" || arg === "--disable") {
  const on = arg === "--enable";
  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || join(process.env.CLAUDE_PROJECT_DIR || process.cwd(), "plugin");
  const { sentOptOut } = setConsent(on, { via: "command", archflow_version: pluginVersion(pluginRoot) });
  process.stdout.write(on ? "Anonymous usage telemetry is now ON.\n" : `${OPT_OUT_CONFIRMATION}${sentOptOut ? OPT_OUT_SENT_NOTE : ""}\n`);
  process.exit(0);
}

try {
  const input = readInput();
  const cwd = input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();
  const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || join(cwd, "plugin");
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
