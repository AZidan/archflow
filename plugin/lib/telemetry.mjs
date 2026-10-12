/**
 * Anonymous usage telemetry, shared by the CLI (scripts/archflow.mjs) and the
 * Claude Code plugin hooks (plugin/hooks/telemetry.mjs).
 *
 * ON BY DEFAULT, OPT-OUT. The first surface to run on a machine prints a
 * one-time notice (never a yes/no prompt) saying telemetry is on and how to
 * turn it off. The notice is only marked shown by code that actually prints
 * it. `/archflow:telemetry off` or `archflow telemetry off` opts out, and the
 * choice lives in ~/.archflow/config.json, shared by every project on the
 * machine.
 *
 * WHAT IS SENT: exactly EVENT_PROPERTIES below, enforced in capture(): an event
 * name, non-identifying properties (host, entrypoint, Studio flags, archflow
 * version, project type, phase, mode, command name) and a random id generated
 * locally. Never a project name, a file path, file contents, a prompt, command
 * arguments, or anything from .archflow/project-context.md.
 *
 * FAIL-OPEN: any error here is swallowed. Telemetry must never be the reason
 * a command fails or a hook blocks a session.
 */

import { appendFileSync, mkdirSync, readFileSync, realpathSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { POSTHOG_API_KEY, POSTHOG_HOST } from "./telemetry-key.mjs";

export const CONFIG_DIR = process.env.ARCHFLOW_CONFIG_DIR || join(homedir(), ".archflow");
export const CONFIG_PATH = join(CONFIG_DIR, "config.json");

export const NOTICE =
  "Archflow sends anonymous usage telemetry by default: which Archflow commands run, the host and its\n" +
  "entrypoint, whether Studio launched it, the Archflow version, the project type, phase and mode, and\n" +
  "for an install, the hosts installed and where from. Never project names, file paths, file contents,\n" +
  "prompts or command arguments.\n";

/**
 * How the user turns telemetry off on each host, as that host invokes the command
 * (adapters/<host>: Codex and generic run skills as $archflow-<cmd>; Copilot, Cursor
 * and OpenCode use /archflow-<cmd>; Gemini nests commands as /archflow:<cmd>). Any
 * other host gets the CLI, which works everywhere.
 */
export const OPT_OUT_COMMANDS = {
  claude: "/archflow:telemetry off",
  gemini: "/archflow:telemetry off",
  codex: "$archflow-telemetry off",
  generic: "$archflow-telemetry off",
  copilot: "/archflow-telemetry off",
  cursor: "/archflow-telemetry off",
  opencode: "/archflow-telemetry off",
};

export function optOutLine(host) {
  const command = Object.prototype.hasOwnProperty.call(OPT_OUT_COMMANDS, host) ? OPT_OUT_COMMANDS[host] : "npx archflow telemetry off";
  return `Tell the user this once, and that ${command} turns it off.\n`;
}

/*
 * THE ALLOW-LIST. capture() sends only the events named here, only the properties
 * listed for each, and only values that pass the property's check. Anything else
 * is dropped before the payload is built, so a caller cannot leak a field by
 * passing it, and a hand-edited YAML value (a project name typed as `mode:`)
 * cannot ride along. Keep this identical to SECURITY.md "## Telemetry".
 */
export const HOSTS = ["claude", "codex", "copilot", "cursor", "gemini", "opencode", "generic", "cli", "studio"];
export const PROJECT_TYPES = ["fullstack", "frontend_only", "backend_only", "mobile"];
export const MODES = ["quick", "full"];
/** .archflow/schemas/current-phase-schema.yaml `phase` enum, as strings. */
export const PHASES = ["1", "2", "2.25", "2.5", "3", "4", "5", "6"];
/** SessionStart `source` values the hosts send (Copilot says "new" for a fresh session). */
export const SESSION_SOURCES = ["startup", "resume", "clear", "compact", "new"];

const oneOf = (list, fallback = null) => (v) => {
  const s = typeof v === "number" ? String(v) : v;
  return typeof s === "string" && list.includes(s) ? s : (v == null ? null : fallback);
};
const matching = (re, fallback = null) => (v) => (typeof v === "string" && re.test(v) ? v : (v == null ? null : fallback));
const bool = (v) => v === true;
const isUuid = (v) => typeof v === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);

const COMMON = {
  distinct_id: (v) => (isUuid(v) ? v : null),
  archflow_version: matching(/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/),
  host: oneOf(HOSTS, "other"),
  entrypoint: matching(/^[a-z0-9][a-z0-9_.-]{0,39}$/i, "other"),
  via_studio: bool,
  studio_capture: bool,
};
const PROJECT = {
  has_project: bool,
  project_type: oneOf(PROJECT_TYPES),
  phase: oneOf(PHASES),
  mode: oneOf(MODES),
};
const CONSENT = {
  via: oneOf(["command", "cli", "studio"], "other"),
  days_since_notice: (v) => (Number.isInteger(v) && v >= 0 ? v : null),
};

export const EVENT_PROPERTIES = {
  session_start: { ...COMMON, ...PROJECT, session_source: oneOf(SESSION_SOURCES, "other") },
  command_run: {
    ...COMMON,
    ...PROJECT,
    command: matching(/^archflow:[a-z][a-z-]{0,40}$/),
    detected_by: oneOf(["command_hook", "prompt_prefix"], "other"),
  },
  cli_install: {
    ...COMMON,
    installed_hosts: (v) => (Array.isArray(v) ? v.filter((h) => HOSTS.includes(h)) : []),
    source: matching(/^(?:bundled with this package|release \d+\.\d+\.\d+, (?:cached|downloaded))$/, "other"),
  },
  telemetry_opted_out: { ...COMMON, ...CONSENT },
  telemetry_opted_in: { ...COMMON, ...CONSENT },
};

/** The properties an event may carry, each checked; null for an event not on the list. */
export function allowedProperties(event, properties) {
  const checks = Object.prototype.hasOwnProperty.call(EVENT_PROPERTIES, event) ? EVENT_PROPERTIES[event] : null;
  if (!checks) return null;
  const out = {};
  for (const [key, check] of Object.entries(checks)) out[key] = check(properties[key]);
  if (out.command === null && event === "command_run") return null; // a command event with no valid name says nothing
  return out;
}

/**
 * Marks a config.json that exists but is not a JSON object (corrupt, truncated,
 * `null`, an array). Such a file may hold an opt-out we cannot read, so for that
 * run telemetry is OFF and the file is never overwritten; the user fixes or
 * deletes it. A missing file is simply the defaults.
 */
const UNREADABLE = Symbol("unreadable config");

export function loadConfig() {
  let text;
  try {
    text = readFileSync(CONFIG_PATH, "utf8");
  } catch (e) {
    if (e?.code === "ENOENT") return {};
    return { [UNREADABLE]: true };
  }
  try {
    const config = JSON.parse(text);
    if (config && typeof config === "object" && !Array.isArray(config)) return config;
  } catch {
    // fall through
  }
  return { [UNREADABLE]: true };
}

export function isConfigUnreadable(config = loadConfig()) {
  return Boolean(config?.[UNREADABLE]);
}

export const CONFIG_UNREADABLE_NOTE =
  `${CONFIG_PATH} could not be read, so anonymous usage telemetry is off and that file was left as is. ` +
  "Fix or delete it to choose again.";

/** true once the file is written; false if it was left alone (unreadable) or the write failed. */
function saveConfig(config) {
  // Never replace a file we could not read: it may hold the user's opt-out.
  if (isConfigUnreadable(config) || isConfigUnreadable(loadConfig())) return false;
  const tmp = `${CONFIG_PATH}.${process.pid}.tmp`;
  try {
    mkdirSync(CONFIG_DIR, { recursive: true });
    // Atomic: hooks, the CLI and Studio can all write this file at once.
    writeFileSync(tmp, JSON.stringify(config, null, 2) + "\n");
    renameSync(tmp, CONFIG_PATH);
    return true;
  } catch {
    // Callers that only record the notice or the id treat this as best-effort (the notice is
    // re-shown next time). setConsent does not: an unsaved choice must not be reported as made.
    try { rmSync(tmp, { force: true }); } catch { /* nothing to clean up */ }
    return false;
  }
}

export const CONFIG_UNWRITABLE_NOTE = `Nothing was changed: could not write ${CONFIG_PATH}.`;

const set = (v) => Boolean(v) && !/^(0|false|no|off)$/i.test(String(v).trim());

/** The environment variable that turns telemetry off for this process, or null. */
export function disabledByEnv() {
  return ["ARCHFLOW_TELEMETRY_DISABLED", "DO_NOT_TRACK", "CI"].find((k) => set(process.env[k])) || null;
}

function envDisabled() {
  return disabledByEnv() !== null;
}

export function hasSeenNotice(config = loadConfig()) {
  return typeof config?.noticeShownAt === "string";
}

export function isEnabled(config = loadConfig()) {
  if (envDisabled() || !config || isConfigUnreadable(config)) return false;
  return config.telemetryEnabled !== false;
}

/** Call only from code that has just printed NOTICE. */
export function recordNoticeShown() {
  const config = loadConfig();
  if (hasSeenNotice(config) || isConfigUnreadable(config)) return config;
  config.noticeShownAt = new Date().toISOString();
  if (!isUuid(config.distinctId)) config.distinctId = randomUUID();
  saveConfig(config);
  return config;
}

/**
 * An explicit on/off choice. A real change sends exactly one event, so opt-outs
 * can be counted. The choice is saved FIRST and an event goes out only once it
 * has persisted: telemetry_opted_out (the last event this machine sends) is sent
 * despite the stored "off" it follows, telemetry_opted_in once "on" is stored.
 * If the save fails nothing is sent and `saved: false` tells the caller to say so. Neither is sent
 * when nothing changed, or when DO_NOT_TRACK / CI / ARCHFLOW_TELEMETRY_DISABLED
 * is set, because those mean send nothing at all. `via` says where the change
 * was made (command, cli, studio).
 */
export function setConsent(enabled, { via = null, archflow_version = null, host } = {}) {
  const config = loadConfig();
  // Unreadable config: change nothing and send nothing; the caller tells the user.
  if (isConfigUnreadable(config)) return { config, sentOptOut: false, unreadable: true };
  const wasEnabled = isEnabled(config);
  const props = {
    ...(host ? { host } : {}),
    via,
    archflow_version,
    days_since_notice: config.noticeShownAt
      ? Math.floor((Date.now() - Date.parse(config.noticeShownAt)) / 86400000)
      : null,
  };
  // Mint the id first, so an opt-out that is someone's very first action is still one distinct person.
  if (!isUuid(config.distinctId)) config.distinctId = randomUUID();
  const now = new Date().toISOString();
  // When the stored choice last changed, so status can say "off since" the opt-out rather than
  // since the notice. Repeating the current choice leaves it alone; noticeShownAt keeps its meaning.
  if ((config.telemetryEnabled !== false) !== Boolean(enabled)) config.consentChangedAt = now;
  config.telemetryEnabled = Boolean(enabled);
  config.noticeShownAt ||= now;
  if (!saveConfig(config)) return { config: loadConfig(), sentOptOut: false, saved: false };
  // wasEnabled already folds in the env variables and an unreadable file, so this is the
  // stored-choice check capture() would make, taken before "off" was written.
  const sentOptOut = !enabled && wasEnabled && Boolean(POSTHOG_API_KEY);
  if (sentOptOut) emit("telemetry_opted_out", props, config);
  if (enabled && !wasEnabled) capture("telemetry_opted_in", props);
  return { config, sentOptOut, saved: true };
}

/**
 * One line for `--status` and `archflow telemetry`: "on" or "off", and why or since when.
 * An environment variable wins over the stored choice, so it is named rather than a date.
 */
export function statusLine(config = loadConfig()) {
  if (isConfigUnreadable(config)) return `off (${CONFIG_UNREADABLE_NOTE})`;
  const byEnv = disabledByEnv();
  if (byEnv) return `off (${byEnv} is set in the environment; nothing is sent while it is)`;
  const state = isEnabled(config) ? "on" : "off";
  const since = typeof config.consentChangedAt === "string" ? config.consentChangedAt : config.noticeShownAt;
  return `${state}${typeof since === "string" ? ` (since ${since})` : " (default)"}`;
}

export const OPT_OUT_CONFIRMATION = "Anonymous usage telemetry is now OFF.";

/**
 * What `on` prints, from the CLI and every host's command. While an environment variable
 * disables telemetry the choice is still saved, but nothing is sent, so say so and name it.
 */
export function optInConfirmation() {
  const byEnv = disabledByEnv();
  return byEnv
    ? `Your choice (on) is saved, but anonymous usage telemetry stays OFF while ${byEnv} is set; nothing is sent.`
    : "Anonymous usage telemetry is now ON.";
}
export const OPT_OUT_SENT_NOTE = " One final event recorded the opt-out; nothing else will be sent.";

/**
 * Where an event came from. `host` is set by each adapter's hook wiring;
 * unset means the Claude Code plugin, which Copilot CLI can also load
 * directly, so `entrypoint` (Claude Code's own CLAUDE_CODE_ENTRYPOINT) is sent
 * raw alongside it: a null there on host=claude marks a session that was not
 * Claude Code. Studio launches `claude` with its environment passed through,
 * so STUDIO_PROJECT_PATH marks Studio-driven sessions and STUDIO_CAPTURE marks
 * demo recordings, which should be filtered out of usage numbers.
 */
export function runtimeContext() {
  return {
    host: process.env.ARCHFLOW_HOST || "claude",
    entrypoint: process.env.CLAUDE_CODE_ENTRYPOINT || null,
    via_studio: Boolean(process.env.STUDIO_PROJECT_PATH),
    studio_capture: Boolean(process.env.STUDIO_CAPTURE),
  };
}

/**
 * The random id, minted on first use by whichever surface runs first (a prompt
 * hook can fire before any session-start hook), so no event is ever sent
 * without one.
 */
/** A missing or malformed stored id is replaced, so no event goes out with distinct_id null. */
function ensureDistinctId(config) {
  if (!isUuid(config.distinctId)) {
    config.distinctId = randomUUID();
    saveConfig(config);
  }
  return config.distinctId;
}

/** Fire an event without blocking: a detached child does the HTTPS POST. */
export function capture(event, properties = {}) {
  const config = loadConfig();
  if (!isEnabled(config) || !POSTHOG_API_KEY) return;
  emit(event, properties, config);
}

/** Build and send one event. Only capture() and setConsent's opt-out call this, after their checks. */
function emit(event, properties, config) {
  if (!POSTHOG_API_KEY) return;
  const props = allowedProperties(event, {
    ...runtimeContext(),
    ...properties,
    distinct_id: ensureDistinctId(config),
  });
  if (!props) return;
  const payload = {
    api_key: POSTHOG_API_KEY,
    event,
    properties: { ...props, $process_person_profile: false },
    timestamp: new Date().toISOString(),
  };
  // Test seam: write the payload to a local file instead of sending it. tests/test_telemetry.py
  // sets this so no test ever reaches PostHog.
  if (process.env.ARCHFLOW_TELEMETRY_SINK) {
    try {
      appendFileSync(process.env.ARCHFLOW_TELEMETRY_SINK, JSON.stringify(payload) + "\n");
    } catch {
      // best-effort
    }
    return;
  }
  try {
    const child = spawn(
      process.execPath,
      [fileURLToPath(import.meta.url), "--send", JSON.stringify(payload)],
      { detached: true, stdio: "ignore", windowsHide: true }
    );
    child.unref();
  } catch {
    // cannot spawn: skip this event
  }
}

// Detached sender, only when this file is the entry point (never in an importer).
function isEntryPoint() {
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (process.argv[2] === "--send" && isEntryPoint()) {
  try {
    await fetch(`${POSTHOG_HOST}/capture/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: process.argv[3],
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    // offline, or PostHog is unreachable: drop the event
  }
  process.exit(0);
}
