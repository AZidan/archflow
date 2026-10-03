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
 * WHAT IS SENT: an event name, non-identifying properties (host, entrypoint,
 * archflow version, phase, mode, command name) and a random id generated
 * locally. Never a project name, a file path, file contents, command
 * arguments, or anything from .archflow/project-context.md.
 *
 * FAIL-OPEN: any error here is swallowed. Telemetry must never be the reason
 * a command fails or a hook blocks a session.
 */

import { mkdirSync, readFileSync, realpathSync, renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { POSTHOG_API_KEY, POSTHOG_HOST } from "./telemetry-key.mjs";

export const CONFIG_DIR = process.env.ARCHFLOW_CONFIG_DIR || join(homedir(), ".archflow");
export const CONFIG_PATH = join(CONFIG_DIR, "config.json");

export const NOTICE =
  "Archflow collects anonymous usage telemetry by default: which Archflow commands run, the host,\n" +
  "version, phase and mode. Never project names, file paths, file contents or command arguments.\n";

export function loadConfig() {
  try {
    return JSON.parse(readFileSync(CONFIG_PATH, "utf8"));
  } catch {
    return {};
  }
}

function saveConfig(config) {
  try {
    mkdirSync(CONFIG_DIR, { recursive: true });
    // Atomic: hooks, the CLI and Studio can all write this file at once.
    const tmp = `${CONFIG_PATH}.${process.pid}.tmp`;
    writeFileSync(tmp, JSON.stringify(config, null, 2) + "\n");
    renameSync(tmp, CONFIG_PATH);
  } catch {
    // best-effort: a choice that fails to persist just re-shows the notice next time
  }
}

const set = (v) => Boolean(v) && !/^(0|false|no|off)$/i.test(String(v).trim());

function envDisabled() {
  return set(process.env.ARCHFLOW_TELEMETRY_DISABLED) || set(process.env.DO_NOT_TRACK) || set(process.env.CI);
}

export function hasSeenNotice(config = loadConfig()) {
  return typeof config.noticeShownAt === "string";
}

export function isEnabled(config = loadConfig()) {
  if (envDisabled()) return false;
  return config.telemetryEnabled !== false;
}

/** Call only from code that has just printed NOTICE. */
export function recordNoticeShown() {
  const config = loadConfig();
  if (hasSeenNotice(config)) return config;
  config.noticeShownAt = new Date().toISOString();
  if (!config.distinctId) config.distinctId = randomUUID();
  saveConfig(config);
  return config;
}

/**
 * An explicit on/off choice. A real change sends exactly one event, so opt-outs
 * can be counted: telemetry_opted_out is captured BEFORE the setting is saved
 * (the last event this machine sends), telemetry_opted_in AFTER. Neither is sent
 * when nothing changed, or when DO_NOT_TRACK / CI / ARCHFLOW_TELEMETRY_DISABLED
 * is set, because those mean send nothing at all. `via` says where the change
 * was made (command, cli, studio).
 */
export function setConsent(enabled, { via = null, archflow_version = null, host } = {}) {
  const config = loadConfig();
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
  if (!config.distinctId) {
    config.distinctId = randomUUID();
    saveConfig(config);
  }
  const optedOut = !enabled && wasEnabled && Boolean(POSTHOG_API_KEY);
  if (optedOut) capture("telemetry_opted_out", props);
  config.telemetryEnabled = Boolean(enabled);
  config.noticeShownAt ||= new Date().toISOString();
  saveConfig(config);
  if (enabled && !wasEnabled) capture("telemetry_opted_in", props);
  return { config, sentOptOut: optedOut };
}

export const OPT_OUT_CONFIRMATION = "Anonymous usage telemetry is now OFF.";
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

/** Fire an event without blocking: a detached child does the HTTPS POST. */
export function capture(event, properties = {}) {
  const config = loadConfig();
  if (!isEnabled(config) || !POSTHOG_API_KEY) return;
  const payload = {
    api_key: POSTHOG_API_KEY,
    event,
    properties: {
      ...runtimeContext(),
      ...properties,
      distinct_id: config.distinctId || "anonymous",
      $process_person_profile: false,
    },
    timestamp: new Date().toISOString(),
  };
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
