#!/usr/bin/env node
/**
 * build-adapters.mjs — emit per-host packages from the Claude Code plugin.
 *
 * The plugin under ./plugin stays the single source of truth. This script
 * reads it and writes ./adapters/<host>/, a directory a user copies (or
 * `npx archflow install` copies) into their project root.
 *
 * Usage:
 *   node scripts/build-adapters.mjs            # all hosts
 *   node scripts/build-adapters.mjs codex      # one host
 *   node scripts/build-adapters.mjs --check    # exit 1 if adapters/ is stale
 *   node scripts/build-adapters.mjs --list-hooks  # print hook lists + host names as JSON (tests)
 *
 * Adding a host = adding an entry to HOSTS below. Each host declares:
 *   - vocab: phrase substitutions applied to every markdown/yaml file
 *   - emit(ctx): writes the host-specific layout
 */

import {
  cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync,
  statSync, writeFileSync,
} from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { symlinkSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const PLUGIN = join(ROOT, "plugin");
const OUT = join(ROOT, "adapters");

const manifest = JSON.parse(
  readFileSync(join(PLUGIN, ".claude-plugin", "plugin.json"), "utf8"),
);

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/** Parse `---\nkey: value\n---\nbody` frontmatter. Values may be quoted. */
function parseFrontmatter(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!m) return { meta: {}, body: text };
  const meta = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_-]+):\s*(.*)$/);
    if (!kv) continue;
    let v = kv[2].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    meta[kv[1]] = v;
  }
  return { meta, body: m[2] };
}

const TEXT_EXT = new Set([".md", ".yaml", ".yml", ".json", ".txt"]);

/** Substitutions every non-Claude host needs, applied before the host's own. */
const COMMON_VOCAB = [
  [/`CLAUDE\.md` \(Claude Code only\)/g, "`CLAUDE.md` (skip: Claude Code only)"],
  [/CLAUDE\.md \(Claude Code only\)/g, "CLAUDE.md (skip: Claude Code only)"],
  [/\(\+ CLAUDE\.md on Claude Code\)/g, ""],
];

/** Apply a host's vocab substitutions to a string. */
function applyVocab(text, vocab) {
  let out = text;
  for (const [from, to] of COMMON_VOCAB) out = out.replace(from, to);
  out = out.replace(/skip: Claude Code only/g, "skip: \u0000HOST0\u0000 only");
  for (const [from, to] of vocab) out = out.replace(from, to);
  return out.replace(/\u0000HOST0\u0000/g, "Claude Code");
}

/** Recursively copy a tree, rewriting text files through the host vocab. */
function copyTree(src, dst, vocab, { skip = () => false } = {}) {
  mkdirSync(dst, { recursive: true });
  for (const name of readdirSync(src)) {
    const s = join(src, name);
    const d = join(dst, name);
    if (skip(s)) continue;
    if (statSync(s).isDirectory()) {
      copyTree(s, d, vocab, { skip });
    } else if (TEXT_EXT.has(extname(name))) {
      writeFileSync(d, applyVocab(readFileSync(s, "utf8"), vocab));
    } else {
      cpSync(s, d);
    }
  }
}

/** TOML literal multi-line string. No escapes are processed inside ''' ''' . */
function tomlLiteral(s) {
  if (s.includes("'''")) throw new Error("body contains ''' — cannot emit as TOML literal");
  return `'''\n${s.replace(/\r\n/g, "\n")}\n'''`;
}

function tomlString(s) {
  return JSON.stringify(s); // TOML basic strings share JSON escaping rules
}

/**
 * Relative symlink, used only INSIDE an adapter (hook root → the adapter's own skill tree).
 * Never link out to ../plugin: users copy the adapter into their project, and a link that
 * escapes the adapter dangles there. Everything an adapter needs is physically inside it.
 */
function link(target, linkPath) {
  mkdirSync(dirname(linkPath), { recursive: true });
  rmSync(linkPath, { recursive: true, force: true });
  symlinkSync(relative(dirname(linkPath), target), linkPath);
}

function write(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

/**
 * Everything an adapter's hooks need at <rootDir>: the hook scripts, the telemetry
 * library they import from ../lib, the command list telemetry matches prompts
 * against, plugin.json (version) and scripts/ (doctor, upgrade). One place, so a
 * new hook is one entry in HOOK_SCRIPTS instead of an edit per host.
 *
 * Every plugin/hooks/*.mjs must be in exactly one of these two lists; tests/test_build_adapters.py
 * fails otherwise, so a new hook cannot be silently left out of the adapters.
 *
 * One HOOK_SCRIPTS entry copies the hook into every adapter. Wiring it to an event is a
 * per-host edit, because each host's event model differs (Codex/Gemini/Copilot hooks files,
 * the Cursor bridge, the OpenCode plugin, the generic AGENTS.md). test_build_adapters.py
 * fails and lists each host that still needs that edit, and the file to change.
 */
const HOOK_SCRIPTS = ["check-upgrade.mjs", "check-state.mjs", "guard-git.mjs", "telemetry.mjs"];
/** Hooks that only make sense on Claude Code and ship in no adapter. */
const CLAUDE_ONLY_HOOKS = [
  "studio-session-context.mjs", // Studio drives the `claude` binary; no other host has it
];

function copyHookRuntime(rootDir, commandNames) {
  for (const f of HOOK_SCRIPTS) cpSync(join(PLUGIN, "hooks", f), join(rootDir, "hooks", f));
  cpSync(join(PLUGIN, "lib"), join(rootDir, "lib"), { recursive: true });
  write(join(rootDir, "lib", "commands.json"), JSON.stringify(commandNames) + "\n");
  cpSync(join(PLUGIN, ".claude-plugin", "plugin.json"), join(rootDir, ".claude-plugin", "plugin.json"));
  cpSync(join(PLUGIN, "scripts"), join(rootDir, "scripts"), { recursive: true });
}

function readCommands() {
  return readdirSync(join(PLUGIN, "commands"))
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const name = f.replace(/\.md$/, "");
      const { meta, body } = parseFrontmatter(readFileSync(join(PLUGIN, "commands", f), "utf8"));
      return { name, meta, body };
    });
}

/**
 * A command's body as one host ships it. help.md lists every plugin command, but a host that
 * skips one (a host's `skip` set; empty on every host today) must not advertise it: drop that command's line
 * from help's command block, with the usage note continuing beneath it. Throws if a skipped
 * command has no line there, so a reshaped help.md cannot silently leak it back in.
 */
function hostBody(c, skip) {
  if (c.name !== "help" || !skip.size) return c.body;
  const start = c.body.indexOf("## Commands");
  const end = c.body.indexOf("## How Archflow works");
  if (start < 0 || end < start) throw new Error("help.md: cannot find its ## Commands section");
  const kept = [];
  const dropped = new Set();
  let dropIndent = -1; // indent of the skipped command line being dropped, or -1
  for (const line of c.body.slice(start, end).split("\n")) {
    const cmd = line.match(/^(\s+)\/archflow:([a-z][a-z-]*)\s/);
    const indent = line.length - line.trimStart().length;
    if (cmd) {
      dropIndent = skip.has(cmd[2]) ? cmd[1].length : -1;
      if (dropIndent >= 0) { dropped.add(cmd[2]); continue; }
    } else if (dropIndent >= 0 && line.trim() && indent > dropIndent) {
      continue; // the skipped command's usage note, wrapped onto the next line(s)
    } else {
      dropIndent = -1;
    }
    kept.push(line);
  }
  const missing = [...skip].filter((n) => !dropped.has(n));
  if (missing.length) throw new Error(`help.md: no command line for skipped command(s) ${missing.join(", ")}`);
  return c.body.slice(0, start) + kept.join("\n") + c.body.slice(end);
}

/**
 * Where `${CLAUDE_PLUGIN_ROOT}/commands/<name>.md` lands on a host. Commands are not copied
 * under the host's plugin root; each host emits them in its own layout, so a pointer to a command
 * file must be rewritten to that layout, before the generic root rewrite would turn it into a
 * path that is never generated. `<name>` (a placeholder in prose) is kept as is.
 */
const commandPathRule = (to) => [/\$\{CLAUDE_PLUGIN_ROOT\}\/commands\/([a-z-]+|<name>)\.md/g, to];

/**
 * Archflow Studio's server (plugin/server/server.mjs) and web UI (plugin/dist/) are ~6.5 MB of
 * prebuilt output from the archflow-studio repo. They are deliberately NOT copied into adapters/:
 * six copies would put ~39 MB in git and in the npm package. The package ships the plugin's one
 * copy, and `npx archflow install` (scripts/archflow.mjs, installStudio) places it at
 * <plugin root>/server/server.mjs and <plugin root>/dist for every host it installs, which is where
 * each host's studio command (its ${CLAUDE_PLUGIN_ROOT}/server/server.mjs, rewritten) looks.
 */

/** The host README's row for Studio: what it does there, and where its bundle comes from. */
function studioRow(spelling, root) {
  return `| \`/archflow:studio\` | \`${spelling}\` in forward mode: Studio runs no agent, its chat composes the command and you paste it into this host's session. Its server bundle goes in \`${root}/server\` and \`${root}/dist\`: \`npx archflow@latest install\` puts it there, or by hand copy the Archflow package's \`plugin/server/\` and \`plugin/dist/\` |\n`;
}

function readAgents() {
  return readdirSync(join(PLUGIN, "agents"))
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const name = f.replace(/\.md$/, "");
      const { meta, body } = parseFrontmatter(readFileSync(join(PLUGIN, "agents", f), "utf8"));
      return { name, meta, body };
    });
}


const OPENCODE_PLUGIN = `// Generated by scripts/build-adapters.mjs — do not edit.
// Bridges Archflow's Claude-Code-shaped hook scripts to OpenCode's plugin API.
import type { Plugin } from "@opencode-ai/plugin"
import { spawnSync } from "node:child_process"
import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"

const ROOT = ".opencode/archflow"

function runHook(cwd: string, script: string, payload: object): { code: number; stdout: string; stderr: string } {
  const r = spawnSync("node", [join(cwd, ROOT, "hooks", script)], {
    cwd,
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 6000,
    env: { ...process.env, CLAUDE_PLUGIN_ROOT: join(cwd, ROOT), CLAUDE_PROJECT_DIR: cwd, ARCHFLOW_HOST: "opencode" },
  })
  return { code: r.status ?? 0, stdout: r.stdout ?? "", stderr: r.stderr ?? "" }
}

function runTelemetry(cwd: string, args: string[], payload: object): string {
  const r = spawnSync("node", [join(cwd, ROOT, "hooks", "telemetry.mjs"), ...args], {
    cwd,
    input: JSON.stringify(payload),
    encoding: "utf8",
    timeout: 3000,
    env: { ...process.env, CLAUDE_PLUGIN_ROOT: join(cwd, ROOT), CLAUDE_PROJECT_DIR: cwd, ARCHFLOW_HOST: "opencode" },
  })
  return r.stdout ?? ""
}

export const ArchflowPlugin: Plugin = async ({ directory }) => {
  const cwd = directory
  const isArchflow = () => existsSync(join(cwd, ".archflow"))
  // The telemetry notice can only be printed from an event; it reaches the model on the next system transform.
  let pendingNotice = ""

  return {
    // SessionStart equivalent: inject instructions.md + upgrade notice into the system prompt.
    // Note: this runs on every model request, so nothing here may count sessions.
    "experimental.chat.system.transform": async (_input, output) => {
      if (pendingNotice) { output.system.push(pendingNotice); pendingNotice = "" }
      if (!isArchflow()) return
      const parts: string[] = []
      try { parts.push(readFileSync(join(cwd, ".archflow", "instructions.md"), "utf8")) } catch {}
      const up = runHook(cwd, "check-upgrade.mjs", { hook_event_name: "SessionStart", cwd })
      if (up.stdout.trim()) parts.push(up.stdout)
      if (parts.length) output.system.push(parts.join("\\n\\n"))
    },
    // Keep instructions after compaction, mirroring the Claude Code \`compact\` matcher.
    "experimental.session.compacting": async (_input, output) => {
      if (!isArchflow()) return
      try { output.context.push(readFileSync(join(cwd, ".archflow", "instructions.md"), "utf8")) } catch {}
    },
    // PreToolUse[Bash] equivalent: git guard. Exit 2 from the script = block.
    "tool.execute.before": async (input, output) => {
      if (input.tool !== "bash" || !isArchflow()) return
      const r = runHook(cwd, "guard-git.mjs", {
        hook_event_name: "PreToolUse",
        tool_name: "Bash",
        tool_input: { command: output.args?.command },
        cwd,
      })
      if (r.code === 2) throw new Error(r.stderr.trim() || "Blocked by Archflow git guard")
    },
    // Stop equivalent: schema drift warning when the session goes idle.
    // (session.idle is a bus event, not a named hook.)
    event: async ({ event }) => {
      // Telemetry: one session_start per top-level session (subagent sessions have a parentID),
      // and command_run with the command name only, never its arguments. telemetry.mjs reports the
      // name only if lib/commands.json lists it, so a user's own archflow-* command is not counted.
      if (event.type === "session.created" && !event.properties?.info?.parentID) {
        pendingNotice += runTelemetry(cwd, [], { hook_event_name: "SessionStart", cwd })
        return
      }
      if (event.type === "command.executed") {
        const name = String(event.properties?.name ?? "").replace(/^\\//, "")
        if (name.startsWith("archflow-")) {
          pendingNotice += runTelemetry(cwd, ["--command-run"], { command_name: "archflow:" + name.slice("archflow-".length), cwd })
        }
        return
      }
      if (event.type !== "session.idle" || !isArchflow()) return
      const r = runHook(cwd, "check-state.mjs", { hook_event_name: "Stop", cwd })
      if (r.stdout.trim()) console.warn(r.stdout.trim())
    },
  }
}

export default ArchflowPlugin
`


const CURSOR_BRIDGE = `#!/usr/bin/env node
// Generated by scripts/build-adapters.mjs — do not edit.
// Translates Cursor hook JSON <-> the Claude-Code-shaped payloads Archflow's hook scripts expect.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const event = process.argv[2];
const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
let input = {};
try { input = JSON.parse(readFileSync(0, "utf8") || "{}"); } catch {}
if (!input || typeof input !== "object") input = {};

// Which project the event is about. Every Cursor payload carries workspace_roots; only some events
// (beforeShellExecution among them) carry cwd, the shell's working directory, which may be a
// subdirectory of the project. ~/.archflow is the telemetry config dir, never a project.
const isProject = (d) => d !== homedir() && existsSync(join(d, ".archflow"));
const inside = (d, r) => { const rel = relative(r, d); return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel)); };
const roots = Array.isArray(input.workspace_roots)
  ? input.workspace_roots.filter((r) => typeof r === "string" && r).map((r) => resolve(r))
  : [];
function projectDir() {
  const at = typeof input.cwd === "string" && input.cwd ? resolve(input.cwd) : null;
  if (at) {
    // The workspace root cwd is in (the innermost, if roots nest). The walk stops there: a repo
    // opened as the workspace is judged on its own, even when it sits inside an Archflow project.
    const bound = roots.filter((r) => inside(at, r)).sort((a, b) => b.length - a.length)[0];
    // 1. The nearest directory from cwd up to that root (or, outside every root, up to the
    //    filesystem root) that is an Archflow project.
    for (let d = at; ; d = dirname(d)) {
      if (isProject(d)) return d;
      if (d === bound || dirname(d) === d) break;
    }
    // 2. cwd inside a workspace root that is not an Archflow project: the command is about that
    //    repo, which never opted in, so it is treated as a plain workspace.
    if (bound) return bound;
  }
  // 3. No cwd, or cwd outside every root: the first Archflow root, else the first root.
  return roots.find(isProject) || roots[0] || at || process.cwd();
}
const cwd = projectDir();
const isArchflow = isProject(cwd);
const env = { ...process.env, CLAUDE_PLUGIN_ROOT: root, CLAUDE_PROJECT_DIR: cwd, ARCHFLOW_HOST: "cursor" };
const run = (script, payload, args = []) =>
  spawnSync("node", [join(here, script), ...args], { cwd, env, input: JSON.stringify(payload), encoding: "utf8", timeout: 6000 });
const out = (o) => { process.stdout.write(JSON.stringify(o)); process.exit(0); };

// Telemetry runs in every workspace, like the Claude Code plugin; the rest only in Archflow projects.
if (event === "beforeSubmitPrompt") {
  // Observation only: always continue, whatever the telemetry script does.
  run("telemetry.mjs", { prompt: input.prompt, cwd }, ["--prompt"]);
  out({ continue: true });
}
if (event === "sessionStart") {
  const parts = [];
  const t = run("telemetry.mjs", { hook_event_name: "SessionStart", cwd });
  if (t.stdout?.trim()) parts.push(t.stdout.trim());
  if (isArchflow) {
    try { parts.push(readFileSync(join(cwd, ".archflow", "instructions.md"), "utf8")); } catch {}
    const r = run("check-upgrade.mjs", { hook_event_name: "SessionStart", cwd });
    if (r.stdout?.trim()) parts.push(r.stdout.trim());
  }
  out(parts.length ? { additional_context: parts.join("\\n\\n") } : {});
}
if (!isArchflow) out({});

if (event === "beforeShellExecution") {
  const r = run("guard-git.mjs", { hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command: input.command }, cwd });
  if (r.status === 2) {
    const msg = (r.stderr || "Blocked by Archflow git guard").trim();
    out({ permission: "deny", user_message: msg.split("\\n")[0], agent_message: msg });
  }
  out({ permission: "allow" });
}
if (event === "stop") {
  const r = run("check-state.mjs", { hook_event_name: "Stop", cwd });
  // Advisory: check-state reports drift on stderr, and anything it prints goes to our stderr too,
  // because Cursor reads the stop hook's stdout as JSON for follow-ups.
  const msg = [r.stderr, r.stdout].map((x) => (x || "").trim()).filter(Boolean).join("\\n");
  if (msg) console.error(msg);
  out({});
}
out({});
`

// ---------------------------------------------------------------------------
// Host definitions
// ---------------------------------------------------------------------------

const HOSTS = {
  /**
   * OpenAI Codex CLI / IDE / app.
   *
   * Mapping:
   *   commands/<n>.md        → .agents/skills/archflow-<n>/SKILL.md   ($archflow-<n>)
   *   skills/archflow/       → .agents/skills/archflow/               (core, vocab-rewritten)
   *   agents/<n>.md          → .codex/agents/<n>.toml                 (spawn_agent targets)
   *   hooks/hooks.json       → .codex/hooks.json                      (same schema, minus Studio's session hook)
   *   hooks/*.mjs, plugin.json → .codex/archflow/…                    (so CLAUDE_PLUGIN_ROOT resolves)
   *   —                      → AGENTS.md block, config.toml snippet, README
   *
   * Not ported: the Studio session hook (companion mode needs Claude Code),
   * `memory: user` agent frontmatter, `color`. $archflow-studio ships like every
   * command; its server bundle is placed by the installer (see studioRow).
   */
  codex: {
    label: "OpenAI Codex",
    skip: new Set(),
    vocab: [
      // Command invocation: /archflow:feature → $archflow-feature
      [/\/archflow:([a-z-]+)/g, "$$archflow-$1"],
      [/\/archflow:<name>/g, "$$archflow-<name>"],
      [/\/archflow:\*/g, "$$archflow-*"],
      [/\/archflow:\{/g, "$$archflow-{"],
      // Sub-agent dispatch
      [/Task tool with `subagent_type:\s*"([^"]+)"`/g, "`spawn_agent` targeting the `$1` agent"],
      [/`subagent_type:\s*"([^"]+)"`/g, "agent `$1`"],
      [/\bTask tool\b/g, "`spawn_agent`"],
      [/`run_in_background:\s*true`/g, "(do not wait; collect results when all have returned)"],
      // Built-in Claude Code agent types that Codex has no equivalent for
      [/`spawn_agent` targeting the `general-purpose` agent/g, "`spawn_agent` with no custom agent (a plain worker)"],
      [/`spawn_agent` targeting the `Explore` agent/g, "`spawn_agent` with a read-only worker (`sandbox_mode = \"read-only\"`)"],
      // User interaction
      [/\bAskUserQuestion\b/g, "a direct question to the user (wait for the reply before continuing)"],
      // Host naming
      [/Claude Code CLI/g, "Codex CLI"],
      [/\bClaude Code\b/g, "Codex"],
      [/\$ARGUMENTS/g, "the text the user wrote after the skill mention"],
      commandPathRule(".agents/skills/archflow-$1/SKILL.md"),
      [/\$\{CLAUDE_PLUGIN_ROOT\}/g, ".codex/archflow"],
      // Session-start injection is an AGENTS.md instruction on Codex
      [/reloaded via hook/g, "read at the start of every session (see AGENTS.md)"],
    ],
    emit(ctx) {
      const { out, vocab, commands, agents } = ctx;

      // 1. Core skill (progressive-disclosure entry point)
      copyTree(join(PLUGIN, "skills", "archflow"), join(out, ".agents", "skills", "archflow"), vocab);

      // 2. One skill per command. Codex deprecated custom prompts in favour of skills,
      //    so /archflow:feature becomes $archflow-feature.
      for (const c of commands) {
        if (this.skip.has(c.name)) continue;
        const skillName = `archflow-${c.name}`;
        const desc = applyVocab(c.meta.description || `Archflow ${c.name}`, vocab);
        const hint = c.meta["argument-hint"] ? `\n\nArguments: \`${c.meta["argument-hint"]}\`` : "";
        const body =
          `---\nname: ${skillName}\ndescription: ${JSON.stringify(desc)}\n---\n\n` +
          `> Invoke with \`$${skillName}\`. Arguments are the text after the mention.${hint}\n\n` +
          applyVocab(hostBody(c, this.skip), vocab);
        write(join(out, ".agents", "skills", skillName, "SKILL.md"), body);
        // Commands are explicit actions; don't let Codex fire them implicitly.
        write(
          join(out, ".agents", "skills", skillName, "agents", "openai.yaml"),
          `interface:\n  display_name: "Archflow: ${c.name}"\n  short_description: ${JSON.stringify(desc.slice(0, 120))}\npolicy:\n  allow_implicit_invocation: false\n`,
        );
      }

      // 3. Agents → Codex custom sub-agents (TOML)
      for (const a of agents) {
        const desc = applyVocab(a.meta.description || "", vocab);
        const lines = [
          `# Generated from plugin/agents/${a.name}.md by scripts/build-adapters.mjs — do not edit.`,
          `name = ${tomlString(a.name)}`,
          `description = ${tomlString(desc)}`,
        ];
        if (a.meta.model) lines.push(`# Claude model hint (${a.meta.model}) has no Codex mapping; set model/model_reasoning_effort here if you want one.`);
        if (["code-reviewer", "pm-reviewer", "a11y-expert"].includes(a.name)) {
          lines.push(`sandbox_mode = "read-only"`);
        }
        lines.push(`developer_instructions = ${tomlLiteral(applyVocab(a.body, vocab).trim())}`);
        write(join(out, ".codex", "agents", `${a.name}.toml`), lines.join("\n") + "\n");
      }

      // 4. Hooks. Codex's hooks.json uses the same event → matcher → handlers
      //    shape as Claude Code (SessionStart, PreToolUse[Bash], Stop), timeout in
      //    seconds. Studio's session hook is dropped. CLAUDE_PLUGIN_ROOT is set
      //    inline so the unmodified scripts find plugin.json.
      const hookRoot = ".codex/archflow";
      copyHookRuntime(join(out, hookRoot), commands.map((c) => c.name));
      // upgrade_archflow.py / doctor read framework files from <root>/skills/archflow
      link(join(out, ".agents", "skills", "archflow"), join(out, hookRoot, "skills", "archflow"));
      const env = `CLAUDE_PLUGIN_ROOT="$PWD/${hookRoot}" CLAUDE_PROJECT_DIR="$PWD" ARCHFLOW_HOST=codex`;
      const hooks = {
        hooks: {
          SessionStart: [
            { matcher: "startup|resume", hooks: [{ type: "command", command: "cat .archflow/instructions.md 2>/dev/null || true", statusMessage: "Loading Archflow instructions" }] },
            { matcher: "startup|resume|clear", hooks: [{ type: "command", command: `${env} node ${hookRoot}/hooks/check-upgrade.mjs`, timeout: 6 }] },
            { matcher: "startup|resume|clear", hooks: [{ type: "command", command: `${env} node ${hookRoot}/hooks/telemetry.mjs`, timeout: 3 }] },
          ],
          // Observation only: prints nothing, so it adds no context and never blocks.
          UserPromptSubmit: [
            { hooks: [{ type: "command", command: `${env} node ${hookRoot}/hooks/telemetry.mjs --prompt`, timeout: 3 }] },
          ],
          PreToolUse: [
            { matcher: "Bash", hooks: [{ type: "command", command: `${env} node ${hookRoot}/hooks/guard-git.mjs`, timeout: 5 }] },
          ],
          Stop: [
            { hooks: [{ type: "command", command: `${env} node ${hookRoot}/hooks/check-state.mjs`, timeout: 5 }] },
          ],
        },
      };
      write(join(out, ".codex", "hooks.json"), JSON.stringify(hooks, null, 2) + "\n");

      // 5. config.toml snippet (hooks are opt-in on Codex; sub-agents need multi-agent on)
      write(
        join(out, ".codex", "config.archflow.toml"),
        `# Merge into .codex/config.toml (project) or ~/.codex/config.toml (user).\n` +
          `# Both features are on by default in current Codex; listed so they survive a user config that turned them off.\n[features]\nhooks = true        # legacy alias: codex_hooks\nmulti_agent = true\n\n[agents]\nmax_concurrent_threads_per_session = 9  # $archflow-onboard dispatches up to 9\n`,
      );

      // 6. AGENTS.md block — the Codex equivalent of the SessionStart injection
      //    and of the CLAUDE.md section onboarding writes.
      const cmdList = commands
        .filter((c) => !this.skip.has(c.name))
        .map((c) => `- \`$archflow-${c.name}\` — ${applyVocab(c.meta.description || "", vocab)}`)
        .join("\n");
      write(
        join(out, "AGENTS.archflow.md"),
        `<!-- archflow:start (managed by Archflow ${manifest.version}; merge into AGENTS.md) -->\n` +
          `# Archflow\n\n` +
          `This project is managed by Archflow, a phase-based development workflow. State lives in \`.archflow/\`.\n\n` +
          `**At the start of every session, read \`.archflow/instructions.md\` before doing anything else.** ` +
          `It is the always-loaded core; \`.archflow/reference.md\` holds detail to read on demand.\n\n` +
          `Archflow actions are skills. Invoke them explicitly with \`$\`:\n\n${cmdList}\n\n` +
          `Specialised agents live in \`.codex/agents/\` and are dispatched with \`spawn_agent\`. ` +
          `Phase 3 runs \`ui-engineer\` and \`api-engineer\` in parallel against the same API contract; ` +
          `if multi-agent is unavailable, run them serially in that order — the contract is what keeps them consistent, not the concurrency.\n\n` +
          `Nothing advances a phase or merges to \`main\` without explicit user approval.\n` +
          `<!-- archflow:end -->\n`,
      );

      // 7. Host README
      write(
        join(out, "README.md"),
        `# Archflow for ${this.label}\n\n` +
          `Generated from Archflow ${manifest.version} by \`scripts/build-adapters.mjs\`. Do not edit here; edit \`plugin/\` and rebuild.\n\n` +
          `## Install\n\n**One command:** \`npx archflow install --host ${ctx.host}\` from your project root does every step below, and re-running it upgrades in place. By hand:\n\n` +
          `1. Copy \`.agents/\` and \`.codex/\` into your project root.\n` +
          `2. Merge \`AGENTS.archflow.md\` into your \`AGENTS.md\` (create it if absent).\n` +
          `3. Merge \`.codex/config.archflow.toml\` into \`.codex/config.toml\`.\n` +
          `4. Trust the project in Codex (project-scoped agents and hooks only load in trusted projects), then restart Codex.\n` +
          `5. Run \`$archflow-init\` (new project) or \`$archflow-onboard\` (existing codebase).\n\n` +
          `Node.js 18+ is required for the hooks.\n\n` +
          `## What is different on Codex\n\n` +
          `| Claude Code | Codex |\n|---|---|\n` +
          `| \`/archflow:<cmd>\` slash commands | \`$archflow-<cmd>\` skills (explicit invocation only) |\n` +
          `| \`agents/*.md\` sub-agents | \`.codex/agents/*.toml\` custom agents via \`spawn_agent\` |\n` +
          `| Plugin hooks (\`hooks.json\`) | \`.codex/hooks.json\` — same events; needs the \`hooks\` feature (default on) |\n` +
          `| \`SessionStart\` injects \`instructions.md\` | Same hook, plus an AGENTS.md instruction as a fallback |\n` +
          studioRow("$archflow-studio", ".codex/archflow") +
          `| Telemetry: \`UserPromptExpansion\` names the command | \`UserPromptSubmit\` counts a prompt that starts with \`$archflow-<cmd>\` |\n` +
          `| \`memory: user\` agent memory | Not available |\n\n` +
          `The \`.archflow/\` state files, schemas, phases, design systems and stack profiles are identical across hosts, ` +
          `so a project can be worked on from both Claude Code and Codex.\n`,
      );
    },
  },

  /**
   * Google Gemini CLI — packaged as an extension (install with
   * `gemini extensions install <path|repo>` or `gemini extensions link`).
   *
   * Mapping:
   *   commands/<n>.md   → commands/archflow/<n>.toml      (/archflow:<n> — same spelling as Claude Code)
   *   agents/<n>.md     → agents/<n>.md                   (kind: local sub-agents, preview feature)
   *   skills/archflow/  → skills/archflow/
   *   hooks/hooks.json  → hooks/hooks.json                (SessionStart / BeforeTool / AfterAgent; timeout in ms)
   *   —                 → gemini-extension.json, GEMINI.md, README
   */
  gemini: {
    label: "Gemini CLI",
    skip: new Set(),
    vocab: [
      // /archflow:<n> is already the Gemini namespaced form — no rewrite needed.
      [/Task tool with `subagent_type:\s*"([^"]+)"`/g, "delegating to the `$1` sub-agent"],
      [/`subagent_type:\s*"([^"]+)"`/g, "sub-agent `$1`"],
      [/\bTask tool\b/g, "sub-agent delegation"],
      [/`run_in_background:\s*true`/g, "(delegate all, then collect results)"],
      [/delegating to the `general-purpose` sub-agent/g, "delegating to a plain sub-agent"],
      [/delegating to the `Explore` sub-agent/g, "delegating to a read-only sub-agent (built-in `codebase_investigator`)"],
      [/\bAskUserQuestion\b/g, "a direct question to the user (wait for the reply before continuing)"],
      [/Claude Code CLI/g, "Gemini CLI"],
      [/\bClaude Code\b/g, "Gemini CLI"],
      [/\$ARGUMENTS/g, "{{args}}"],
      // Gemini only substitutes ${extensionPath} in the manifest and hooks, not in prompts.
      // $HOME, not ~: prompts quote the path ("…/scripts/x.py"), and ~ does not expand inside quotes.
      // Command bodies ship as commands/archflow/<n>.toml here, not commands/<n>.md; the prompt is inside.
      commandPathRule("$HOME/.gemini/extensions/archflow/commands/archflow/$1.toml"),
      [/\$\{CLAUDE_PLUGIN_ROOT\}/g, "$HOME/.gemini/extensions/archflow"],
      [/reloaded via hook/g, "injected by the extension's SessionStart hook"],
    ],
    emit(ctx) {
      const { out, vocab, commands, agents } = ctx;

      copyTree(join(PLUGIN, "skills", "archflow"), join(out, "skills", "archflow"), vocab);

      // Commands: TOML with a `prompt` field. {{args}} substitution mirrors $ARGUMENTS.
      for (const c of commands) {
        if (this.skip.has(c.name)) continue;
        const desc = applyVocab(c.meta.description || `Archflow ${c.name}`, vocab);
        const body = applyVocab(hostBody(c, this.skip), vocab);
        // The leading marker lets the BeforeAgent telemetry hook name the command even if
        // Gemini hands it the expanded prompt rather than the literal /archflow:<name>.
        write(
          join(out, "commands", "archflow", `${c.name}.toml`),
          `# Generated from plugin/commands/${c.name}.md — do not edit.\n` +
            `description = ${tomlString(desc)}\n` +
            `prompt = ${tomlLiteral(`<!-- archflow-command: ${c.name} -->\n` + body.trim())}\n`,
        );
      }

      // Sub-agents: markdown with YAML frontmatter; body is the system prompt.
      for (const a of agents) {
        const desc = applyVocab(a.meta.description || "", vocab);
        const readOnly = ["code-reviewer", "pm-reviewer", "a11y-expert"].includes(a.name);
        const fm = [
          "---",
          `name: ${a.name}`,
          `description: ${JSON.stringify(desc)}`,
          "kind: local",
          ...(readOnly ? ["tools:", "  - read_file", "  - grep_search", "  - glob", "  - list_directory", "  - run_shell_command"] : []),
          "---",
          "",
        ];
        write(join(out, "agents", `${a.name}.md`), fm.join("\n") + applyVocab(a.body, vocab).trim() + "\n");
      }

      // Hooks. Gemini's schema is Claude-shaped but events are renamed and timeout is ms.
      // ${extensionPath} makes CLAUDE_PLUGIN_ROOT resolve; plugin.json is mirrored there.
      copyHookRuntime(out, commands.map((c) => c.name));
      const env = `CLAUDE_PLUGIN_ROOT="\${extensionPath}" CLAUDE_PROJECT_DIR="\${workspacePath}" ARCHFLOW_HOST=gemini`;
      const hooks = {
        hooks: {
          SessionStart: [
            { matcher: "startup|resume", hooks: [{ name: "archflow-instructions", type: "command", command: `cat "\${workspacePath}/.archflow/instructions.md" 2>/dev/null || true`, timeout: 3000 }] },
            { matcher: "startup|resume|clear", hooks: [{ name: "archflow-check-upgrade", type: "command", command: `${env} node "\${extensionPath}/hooks/check-upgrade.mjs"`, timeout: 6000 }] },
            { matcher: "startup|resume|clear", hooks: [{ name: "archflow-telemetry", type: "command", command: `${env} node "\${extensionPath}/hooks/telemetry.mjs"`, timeout: 3000 }] },
          ],
          // Gemini parses prompt-hook stdout as JSON; the script prints nothing, so answer {} (allow).
          BeforeAgent: [
            { hooks: [{ name: "archflow-telemetry-command", type: "command", command: `${env} node "\${extensionPath}/hooks/telemetry.mjs" --prompt; printf '{}'`, timeout: 3000 }] },
          ],
          BeforeTool: [
            { matcher: "run_shell_command", hooks: [{ name: "archflow-git-guard", type: "command", command: `${env} node "\${extensionPath}/hooks/guard-git.mjs"`, timeout: 5000 }] },
          ],
          AfterAgent: [
            { hooks: [{ name: "archflow-check-state", type: "command", command: `${env} node "\${extensionPath}/hooks/check-state.mjs"`, timeout: 5000 }] },
          ],
        },
      };
      write(join(out, "hooks", "hooks.json"), JSON.stringify(hooks, null, 2) + "\n");

      write(
        join(out, "gemini-extension.json"),
        JSON.stringify(
          {
            name: "archflow",
            version: manifest.version,
            description: "Phase-based AI development framework: 17 specialized agents, structured phases, file-based handoffs.",
            contextFileName: "GEMINI.md",
          },
          null,
          2,
        ) + "\n",
      );

      const cmdList = commands
        .filter((c) => !this.skip.has(c.name))
        .map((c) => `- \`/archflow:${c.name}\` — ${applyVocab(c.meta.description || "", vocab)}`)
        .join("\n");
      write(
        join(out, "GEMINI.md"),
        `# Archflow\n\nThis extension manages projects with Archflow, a phase-based development workflow. Project state lives in \`.archflow/\`.\n\n` +
          `**If \`.archflow/\` exists, read \`.archflow/instructions.md\` before doing anything else.** The SessionStart hook injects it; this line is the fallback if hooks are disabled.\n\n` +
          `Commands:\n\n${cmdList}\n\n` +
          `Specialised sub-agents ship with the extension (\`agents/\`). Phase 3 delegates to \`ui-engineer\` and \`api-engineer\` against the same API contract; if sub-agents are unavailable, run them serially in that order.\n\n` +
          `Nothing advances a phase or merges to \`main\` without explicit user approval.\n`,
      );

      write(
        join(out, "README.md"),
        `# Archflow for ${this.label}\n\nGenerated from Archflow ${manifest.version} by \`scripts/build-adapters.mjs\`. Do not edit here.\n\n` +
          `## Install\n\n**One command:** \`npx archflow install --host ${ctx.host}\` from your project root does every step below, and re-running it upgrades in place. By hand:\n\n\`\`\`\ngemini extensions install https://github.com/AZidan/archflow --ref main   # once published under adapters/gemini\ngemini extensions link ./adapters/gemini                                # local development\n\`\`\`\n\n` +
          `Gemini asks you to trust the extension folder (and the workspace) and to confirm the install. Answer yes: if you decline, nothing is installed, Studio's bundle included. The one-command install runs Gemini's install in your terminal so you can answer; with no terminal (CI, piped) it prints the command to run instead.\n\n` +
          `Restart Gemini CLI, then run \`/archflow:init\` or \`/archflow:onboard\`. Node.js 18+ is required for the hooks.\n\n` +
          `## What is different on Gemini CLI\n\n| Claude Code | Gemini CLI |\n|---|---|\n` +
          `| \`/archflow:<cmd>\` | \`/archflow:<cmd>\` (identical; TOML commands under \`commands/archflow/\`) |\n` +
          `| \`agents/*.md\` sub-agents | \`agents/*.md\` (\`kind: local\`) — sub-agents are a preview feature |\n` +
          `| \`PreToolUse\` / \`Stop\` hooks | \`BeforeTool\` / \`AfterAgent\` hooks (timeouts in ms) |\n` +
          `| Telemetry: \`UserPromptExpansion\` names the command | \`BeforeAgent\` counts a prompt that starts with \`/archflow:<cmd>\` or the command's marker line |\n` +
          studioRow("/archflow:studio", "~/.gemini/extensions/archflow") +
          `| \`memory: user\` | Not available |\n\n` +
          `Note: Gemini CLI's extension install location is per-user (\`~/.gemini/extensions\`), not per-project. Use \`gemini extensions disable archflow --scope workspace\` in repos that don't use it.\n`,
      );
    },
  },

  /**
   * OpenCode — a project overlay under .opencode/.
   *
   * Mapping:
   *   commands/<n>.md   → .opencode/commands/archflow-<n>.md   (/archflow-<n>, $ARGUMENTS supported natively)
   *   agents/<n>.md     → .opencode/agents/<n>.md             (mode: subagent; @mention or task tool)
   *   skills/archflow/  → .opencode/skills/archflow/
   *   hooks             → .opencode/plugins/archflow.ts        (tool.execute.before / system.transform / session.idle)
   *   —                 → AGENTS.archflow.md, README
   */
  opencode: {
    label: "OpenCode",
    skip: new Set(),
    vocab: [
      [/\/archflow:([a-z-]+)/g, "/archflow-$1"],
      [/\/archflow:<name>/g, "/archflow-<name>"],
      [/\/archflow:\*/g, "/archflow-*"],
      [/\/archflow:\{/g, "/archflow-{"],
      [/Task tool with `subagent_type:\s*"([^"]+)"`/g, "the `task` tool targeting the `$1` subagent"],
      [/`subagent_type:\s*"([^"]+)"`/g, "subagent `$1`"],
      [/\bTask tool\b/g, "`task` tool"],
      [/`run_in_background:\s*true`/g, "(launch all, then collect results)"],
      [/targeting the `general-purpose` subagent/g, "targeting the built-in `general` subagent"],
      [/targeting the `Explore` subagent/g, "targeting the built-in `explore` subagent (read-only)"],
      [/\bAskUserQuestion\b/g, "the `question` tool"],
      [/Claude Code CLI/g, "OpenCode"],
      [/\bClaude Code\b/g, "OpenCode"],
      // $ARGUMENTS is native to OpenCode commands — keep it.
      commandPathRule(".opencode/commands/archflow-$1.md"),
      [/\$\{CLAUDE_PLUGIN_ROOT\}/g, ".opencode/archflow"],
      [/reloaded via hook/g, "injected by the Archflow plugin at session start"],
    ],
    emit(ctx) {
      const { out, vocab, commands, agents } = ctx;

      copyTree(join(PLUGIN, "skills", "archflow"), join(out, ".opencode", "skills", "archflow"), vocab);

      for (const c of commands) {
        if (this.skip.has(c.name)) continue;
        const desc = applyVocab(c.meta.description || `Archflow ${c.name}`, vocab);
        write(
          join(out, ".opencode", "commands", `archflow-${c.name}.md`),
          `---\ndescription: ${JSON.stringify(desc)}\n---\n\n` + applyVocab(hostBody(c, this.skip), vocab),
        );
      }

      for (const a of agents) {
        const desc = applyVocab(a.meta.description || "", vocab);
        const readOnly = ["code-reviewer", "pm-reviewer", "a11y-expert"].includes(a.name);
        const fm = [
          "---",
          `description: ${JSON.stringify(desc)}`,
          "mode: subagent",
          ...(readOnly ? ["permission:", "  edit: deny", "  write: deny", "  patch: deny"] : []),
          "---",
          "",
        ];
        write(join(out, ".opencode", "agents", `${a.name}.md`), fm.join("\n") + applyVocab(a.body, vocab).trim() + "\n");
      }

      // Hooks become a plugin. It shells out to the unmodified hook scripts with a
      // Claude-shaped stdin payload so they need no host branching.
      copyHookRuntime(join(out, ".opencode", "archflow"), commands.map((c) => c.name));
      link(join(out, ".opencode", "skills", "archflow"), join(out, ".opencode", "archflow", "skills", "archflow"));
      write(join(out, ".opencode", "plugins", "archflow.ts"), OPENCODE_PLUGIN);

      const cmdList = commands
        .filter((c) => !this.skip.has(c.name))
        .map((c) => `- \`/archflow-${c.name}\` — ${applyVocab(c.meta.description || "", vocab)}`)
        .join("\n");
      write(
        join(out, "AGENTS.archflow.md"),
        `<!-- archflow:start (managed by Archflow ${manifest.version}; merge into AGENTS.md) -->\n# Archflow\n\n` +
          `This project is managed by Archflow, a phase-based development workflow. State lives in \`.archflow/\`.\n\n` +
          `**At the start of every session, read \`.archflow/instructions.md\` before doing anything else.** The Archflow plugin injects it; this line is the fallback.\n\n` +
          `Commands:\n\n${cmdList}\n\n` +
          `Specialised subagents live in \`.opencode/agents/\`; invoke with \`@name\` or the \`task\` tool. Phase 3 runs \`ui-engineer\` and \`api-engineer\` in parallel against the same API contract.\n\n` +
          `Nothing advances a phase or merges to \`main\` without explicit user approval.\n<!-- archflow:end -->\n`,
      );

      write(
        join(out, "README.md"),
        `# Archflow for ${this.label}\n\nGenerated from Archflow ${manifest.version} by \`scripts/build-adapters.mjs\`. Do not edit here.\n\n` +
          `## Install\n\n**One command:** \`npx archflow install --host ${ctx.host}\` from your project root does every step below, and re-running it upgrades in place. By hand:\n\n1. Copy \`.opencode/\` into your project root.\n2. Merge \`AGENTS.archflow.md\` into \`AGENTS.md\`.\n3. Restart OpenCode; run \`/archflow-init\` or \`/archflow-onboard\`.\n\nNode.js 18+ (or Bun) is required for the plugin hooks.\n\n` +
          `## What is different on OpenCode\n\n| Claude Code | OpenCode |\n|---|---|\n` +
          `| \`/archflow:<cmd>\` | \`/archflow-<cmd>\` (OpenCode has no colon namespaces) |\n` +
          `| \`agents/*.md\` sub-agents | \`.opencode/agents/*.md\` with \`mode: subagent\` |\n` +
          `| Telemetry: \`UserPromptExpansion\` names the command | \`command.executed\` names the command |\n` +
          `| Plugin hooks | \`.opencode/plugins/archflow.ts\` (\`tool.execute.before\`, system-prompt transform, \`session.created\`, \`command.executed\`, \`session.idle\`) |\n` +
          studioRow("/archflow-studio", ".opencode/archflow") +
          `| \`memory: user\` | Not available |\n\n` +
          `Known limitation: OpenCode plugin hooks do not currently fire for tool calls made *inside* subagents (anomalyco/opencode#5894), so the git guard only covers the primary agent. The approval gates remain the real control.\n`,
      );
    },
  },

  /**
   * Generic — the Agent Skills open standard. AGENTS.md + .agents/skills/ is read
   * by Codex, Copilot, OpenCode, Cursor, Cline, Windsurf and anything implementing
   * agentskills.io. No hooks, no sub-agents: the git pre-push guard is the safety net
   * and Phase 3 runs serially. Agents become skills so the orchestrator can load
   * "role" instructions on demand.
   */
  generic: {
    label: "any Agent-Skills host",
    skip: new Set(),
    vocab: [
      [/\/archflow:([a-z-]+)/g, "$$archflow-$1"],
      [/\/archflow:<name>/g, "$$archflow-<name>"],
      [/\/archflow:\*/g, "$$archflow-*"],
      [/\/archflow:\{/g, "$$archflow-{"],
      [/Task tool with `subagent_type:\s*"([^"]+)"`/g, "loading the `archflow-agent-$1` skill and performing that role yourself (no sub-agent runtime)"],
      [/`subagent_type:\s*"([^"]+)"`/g, "the `archflow-agent-$1` role"],
      [/\bTask tool\b/g, "role delegation (load the role's skill; work serially)"],
      [/`run_in_background:\s*true`/g, "(serially, one role at a time)"],
      [/loading the `archflow-agent-general-purpose` skill and performing that role yourself \(no sub-agent runtime\)/g, "doing the work directly"],
      [/loading the `archflow-agent-Explore` skill and performing that role yourself \(no sub-agent runtime\)/g, "exploring the codebase read-only yourself"],
      [/\bAskUserQuestion\b/g, "a direct question to the user (wait for the reply before continuing)"],
      [/Claude Code CLI/g, "your coding agent"],
      [/\bClaude Code\b/g, "your coding agent"],
      [/\$ARGUMENTS/g, "the text the user wrote after the skill name"],
      commandPathRule(".agents/skills/archflow-$1/SKILL.md"),
      [/\$\{CLAUDE_PLUGIN_ROOT\}/g, ".agents/archflow"],
      [/reloaded via hook/g, "read at the start of every session (see AGENTS.md)"],
    ],
    emit(ctx) {
      const { out, vocab, commands, agents } = ctx;
      copyTree(join(PLUGIN, "skills", "archflow"), join(out, ".agents", "skills", "archflow"), vocab);
      for (const c of commands) {
        if (this.skip.has(c.name)) continue;
        const desc = applyVocab(c.meta.description || `Archflow ${c.name}`, vocab);
        write(
          join(out, ".agents", "skills", `archflow-${c.name}`, "SKILL.md"),
          `---\nname: archflow-${c.name}\ndescription: ${JSON.stringify(`Use ONLY when the user asks for $archflow-${c.name} or "archflow ${c.name}". ${desc}`)}\n---\n\n` +
            `> Arguments are the text after the skill name.\n\n` + applyVocab(hostBody(c, this.skip), vocab),
        );
      }
      for (const a of agents) {
        const desc = applyVocab(a.meta.description || "", vocab);
        write(
          join(out, ".agents", "skills", `archflow-agent-${a.name}`, "SKILL.md"),
          `---\nname: archflow-agent-${a.name}\ndescription: ${JSON.stringify(`Archflow role: ${a.name}. Load when an Archflow phase or skill delegates to this role. ${desc}`)}\n---\n\n` +
            applyVocab(a.body, vocab).trim() + "\n",
        );
      }
      // Scripts + a mirrored root so ${CLAUDE_PLUGIN_ROOT} paths resolve
      const root = ".agents/archflow";
      // No session hooks here, so AGENTS.md asks the agent to run the session-start scripts itself.
      copyHookRuntime(join(out, root), commands.map((c) => c.name));
      link(join(out, ".agents", "skills", "archflow"), join(out, root, "skills", "archflow"));

      const cmdList = commands.filter((c) => !this.skip.has(c.name))
        .map((c) => `- \`$archflow-${c.name}\` — ${applyVocab(c.meta.description || "", vocab)}`).join("\n");
      write(
        join(out, "AGENTS.archflow.md"),
        `<!-- archflow:start (managed by Archflow ${manifest.version}; merge into AGENTS.md) -->\n# Archflow\n\n` +
          `This project is managed by Archflow, a phase-based development workflow. State lives in \`.archflow/\`.\n\n` +
          `**At the start of every session, read \`.archflow/instructions.md\` before doing anything else.** ` +
          `Then run \`ARCHFLOW_HOST=generic node .agents/archflow/hooks/check-upgrade.mjs\` and ` +
          `\`ARCHFLOW_HOST=generic node .agents/archflow/hooks/telemetry.mjs </dev/null\`, and relay anything either prints: ` +
          `they are the upgrade check and usage telemetry other hosts run automatically at session start.\n\n` +
          `Archflow actions are skills under \`.agents/skills/\`. Run one when the user asks for it by name:\n\n${cmdList}\n\n` +
          `Specialised roles are skills named \`archflow-agent-<role>\`. When a phase delegates to a role, load that skill and perform the role yourself, one role at a time. ` +
          `Phase 3 runs \`ui-engineer\` then \`api-engineer\` serially against the same API contract.\n\n` +
          `Never push to or merge into \`main\` yourself; a git pre-push guard enforces this. Nothing advances a phase without explicit user approval.\n<!-- archflow:end -->\n`,
      );
      write(
        join(out, "README.md"),
        `# Archflow for ${this.label}\n\nGenerated from Archflow ${manifest.version} by \`scripts/build-adapters.mjs\`. Do not edit here.\n\n` +
          `This is the lowest-common-denominator package: \`AGENTS.md\` + Agent Skills (agentskills.io). It works in any host that reads those, ` +
          `including Cline, Roo, Kilo, Windsurf, Zed, Amp and Copilot/Codex/OpenCode/Cursor without their native adapters.\n\n` +
          `## Install\n\n**One command:** \`npx archflow install --host ${ctx.host}\` from your project root does every step below, and re-running it upgrades in place. By hand:\n\n1. Copy \`.agents/\` into your project root.\n2. Merge \`AGENTS.archflow.md\` into \`AGENTS.md\`.\n3. Install the git guard: \`sh .agents/archflow/scripts/archflow-install-git-guard.sh\`\n4. Ask your agent to run \`$archflow-init\` or \`$archflow-onboard\`.\n\n` +
          `## What you give up\n\n- No sub-agents: roles run serially inside the main context (bigger context use, slower Phase 3).\n- No lifecycle hooks: instructions load via AGENTS.md, and the upgrade check and session telemetry run because AGENTS.md asks the agent to run them, not because the host does. Per-command telemetry is not available.\n- The git guard is a real \`pre-push\` hook, so it also protects you from your own terminal.\n\n` +
          `## Archflow Studio\n\n| Claude Code | Here |\n|---|---|\n` + studioRow("$archflow-studio", ".agents/archflow"),
      );
    },
  },

  /**
   * Cursor — packaged as a Cursor Plugin (.cursor-plugin/plugin.json) that also
   * works dropped into a project's .cursor/. Cursor has sub-agents, commands,
   * skills and hooks (camelCase events, JSON permission decisions).
   */
  cursor: {
    label: "Cursor",
    skip: new Set(),
    vocab: [
      [/\/archflow:([a-z-]+)/g, "/archflow-$1"],
      [/\/archflow:<name>/g, "/archflow-<name>"],
      [/\/archflow:\*/g, "/archflow-*"],
      [/\/archflow:\{/g, "/archflow-{"],
      [/Task tool with `subagent_type:\s*"([^"]+)"`/g, "delegating to the `$1` subagent"],
      [/`subagent_type:\s*"([^"]+)"`/g, "subagent `$1`"],
      [/\bTask tool\b/g, "subagent delegation"],
      [/`run_in_background:\s*true`/g, "(background subagents; collect results when all return)"],
      [/delegating to the `general-purpose` subagent/g, "delegating to a plain subagent"],
      [/delegating to the `Explore` subagent/g, "delegating to the built-in `Explore` subagent"],
      [/\bAskUserQuestion\b/g, "a direct question to the user (wait for the reply before continuing)"],
      [/Claude Code CLI/g, "Cursor"],
      [/\bClaude Code\b/g, "Cursor"],
      [/\$ARGUMENTS/g, "the text the user wrote after the command"],
      commandPathRule(".cursor/commands/archflow-$1.md"),
      [/\$\{CLAUDE_PLUGIN_ROOT\}/g, ".cursor/archflow"],
      [/reloaded via hook/g, "injected by the sessionStart hook"],
    ],
    emit(ctx) {
      const { out, vocab, commands, agents } = ctx;
      // Everything lives under .cursor/ so the same tree is both a project overlay
      // and (with .cursor-plugin/plugin.json at the top) an installable plugin.
      const C = join(out, ".cursor");
      copyTree(join(PLUGIN, "skills", "archflow"), join(C, "skills", "archflow"), vocab);
      for (const c of commands) {
        if (this.skip.has(c.name)) continue;
        const desc = applyVocab(c.meta.description || `Archflow ${c.name}`, vocab);
        write(join(C, "commands", `archflow-${c.name}.md`),
          `---\nname: archflow-${c.name}\ndescription: ${JSON.stringify(desc)}\n---\n\n` + applyVocab(hostBody(c, this.skip), vocab));
      }
      for (const a of agents) {
        const desc = applyVocab(a.meta.description || "", vocab);
        const readOnly = ["code-reviewer", "pm-reviewer", "a11y-expert"].includes(a.name);
        write(join(C, "agents", `${a.name}.md`),
          `---\nname: ${a.name}\ndescription: ${JSON.stringify(desc)}\nmodel: inherit\n${readOnly ? "readonly: true\n" : ""}---\n\n` +
            applyVocab(a.body, vocab).trim() + "\n");
      }
      // Hooks: Cursor speaks its own JSON on stdin/stdout, so a thin bridge
      // translates to the Claude-shaped payload the core scripts expect.
      const root = ".cursor/archflow";
      copyHookRuntime(join(out, root), commands.map((c) => c.name));
      link(join(C, "skills", "archflow"), join(out, root, "skills", "archflow"));
      write(join(out, root, "hooks", "cursor-bridge.mjs"), CURSOR_BRIDGE);
      write(join(C, "hooks.json"), JSON.stringify({
        version: 1,
        hooks: {
          sessionStart: [{ command: `node ${root}/hooks/cursor-bridge.mjs sessionStart`, timeout: 8 }],
          beforeSubmitPrompt: [{ command: `node ${root}/hooks/cursor-bridge.mjs beforeSubmitPrompt`, timeout: 5 }],
          beforeShellExecution: [{ command: `node ${root}/hooks/cursor-bridge.mjs beforeShellExecution`, timeout: 5 }],
          stop: [{ command: `node ${root}/hooks/cursor-bridge.mjs stop`, timeout: 5 }],
        },
      }, null, 2) + "\n");
      // Plugin manifest (Cursor Plugin format) pointing at the .cursor/ tree
      write(join(out, ".cursor-plugin", "plugin.json"), JSON.stringify({
        name: "archflow", displayName: "Archflow", version: manifest.version,
        description: "Phase-based AI development framework: 17 specialized agents, structured phases, file-based handoffs.",
        author: { name: "AZidan" }, license: "MIT", repository: "https://github.com/AZidan/archflow", category: "productivity",
        keywords: ["workflow", "agents", "phases", "architecture"],
        rules: ".cursor/rules", skills: ".cursor/skills", agents: ".cursor/agents", commands: ".cursor/commands", hooks: ".cursor/hooks.json",
      }, null, 2) + "\n");
      // An always-on rule = the AGENTS.md equivalent
      const cmdList = commands.filter((c) => !this.skip.has(c.name))
        .map((c) => `- \`/archflow-${c.name}\` — ${applyVocab(c.meta.description || "", vocab)}`).join("\n");
      write(join(C, "rules", "archflow.mdc"),
        `---\ndescription: Archflow phase-based workflow — always on in Archflow projects\nalwaysApply: true\n---\n\n# Archflow\n\n` +
          `If \`.archflow/\` exists, this project is managed by Archflow. **Read \`.archflow/instructions.md\` before doing anything else** (the sessionStart hook injects it; this is the fallback).\n\n` +
          `Commands:\n\n${cmdList}\n\n` +
          `Specialised subagents live in \`.cursor/agents/\`. Phase 3 delegates to \`ui-engineer\` and \`api-engineer\` against the same API contract.\n\n` +
          `Nothing advances a phase or merges to \`main\` without explicit user approval.\n`);
      write(join(out, "README.md"),
        `# Archflow for ${this.label}\n\nGenerated from Archflow ${manifest.version} by \`scripts/build-adapters.mjs\`. Do not edit here.\n\n` +
          `## Install\n\n**One command:** \`npx archflow install --host ${ctx.host}\` from your project root does every step below, and re-running it upgrades in place. By hand:\n\n**As a project overlay:** copy \`.cursor/\` into your project root and restart Cursor.\n\n**As a plugin:** the directory is a Cursor Plugin (\`.cursor-plugin/plugin.json\`); install it from Customize → Plugins, or publish it to a marketplace.\n\nNode.js 18+ is required for the hooks.\n\n` +
          `## What is different on Cursor\n\n| Claude Code | Cursor |\n|---|---|\n` +
          `| \`/archflow:<cmd>\` | \`/archflow-<cmd>\` (\`.cursor/commands/\`) |\n` +
          `| \`agents/*.md\` sub-agents | \`.cursor/agents/*.md\` (\`model: inherit\`; reviewers \`readonly: true\`) |\n` +
          `| Plugin hooks | \`.cursor/hooks.json\` (\`sessionStart\` / \`beforeSubmitPrompt\` / \`beforeShellExecution\` / \`stop\`) via a small bridge script |\n` +
          `| \`CLAUDE.md\` section | \`.cursor/rules/archflow.mdc\` (\`alwaysApply\`) |\n` +
          `| Telemetry: \`UserPromptExpansion\` names the command | \`beforeSubmitPrompt\` counts a prompt that starts with \`/archflow-<cmd>\` |\n` +
          studioRow("/archflow-studio", ".cursor/archflow") +
          `| \`memory: user\` | Not available |\n\nProject hooks also run in Cursor cloud agents.\n`);
    },
  },

  /**
   * GitHub Copilot CLI (and VS Code agent mode, which shares the .github/ paths).
   * Copilot accepts PascalCase hook names with Claude/VS-Code-shaped snake_case
   * payloads, so the core hook scripts run unmodified.
   */
  copilot: {
    label: "GitHub Copilot CLI",
    skip: new Set(),
    vocab: [
      [/\/archflow:([a-z-]+)/g, "/archflow-$1"],
      [/\/archflow:<name>/g, "/archflow-<name>"],
      [/\/archflow:\*/g, "/archflow-*"],
      [/\/archflow:\{/g, "/archflow-{"],
      [/Task tool with `subagent_type:\s*"([^"]+)"`/g, "delegating to the `$1` custom agent"],
      [/`subagent_type:\s*"([^"]+)"`/g, "custom agent `$1`"],
      [/\bTask tool\b/g, "custom-agent delegation"],
      [/`run_in_background:\s*true`/g, "(delegate all, then collect results)"],
      [/delegating to the `general-purpose` custom agent/g, "delegating to a plain subagent"],
      [/delegating to the `Explore` custom agent/g, "delegating to a read-only subagent"],
      [/\bAskUserQuestion\b/g, "a direct question to the user (wait for the reply before continuing)"],
      [/Claude Code CLI/g, "Copilot CLI"],
      [/\bClaude Code\b/g, "Copilot"],
      [/\$ARGUMENTS/g, "the text the user wrote after the skill name"],
      commandPathRule(".github/skills/archflow-$1/SKILL.md"),
      [/\$\{CLAUDE_PLUGIN_ROOT\}/g, ".github/archflow"],
      [/reloaded via hook/g, "injected by the SessionStart hook"],
    ],
    emit(ctx) {
      const { out, vocab, commands, agents } = ctx;
      const G = join(out, ".github");
      copyTree(join(PLUGIN, "skills", "archflow"), join(G, "skills", "archflow"), vocab);
      for (const c of commands) {
        if (this.skip.has(c.name)) continue;
        const desc = applyVocab(c.meta.description || `Archflow ${c.name}`, vocab);
        write(join(G, "skills", `archflow-${c.name}`, "SKILL.md"),
          `---\nname: archflow-${c.name}\ndescription: ${JSON.stringify(`Use ONLY when the user asks for /archflow-${c.name} or "archflow ${c.name}". ${desc}`)}\n---\n\n` +
            `> Arguments are the text after the skill name.\n\n` + applyVocab(hostBody(c, this.skip), vocab));
      }
      for (const a of agents) {
        const desc = applyVocab(a.meta.description || "", vocab);
        const readOnly = ["code-reviewer", "pm-reviewer", "a11y-expert"].includes(a.name);
        const body = applyVocab(a.body, vocab).trim();
        if (body.length > 30000) throw new Error(`${a.name} prompt exceeds Copilot's 30,000-char limit`);
        write(join(G, "agents", `${a.name}.agent.md`),
          `---\nname: ${a.name}\ndescription: ${JSON.stringify(desc)}\n${readOnly ? 'tools: ["read", "search", "shell"]\n' : ""}disable-model-invocation: true\n---\n\n` + body + "\n");
      }
      const root = ".github/archflow";
      copyHookRuntime(join(out, root), commands.map((c) => c.name));
      link(join(G, "skills", "archflow"), join(out, root, "skills", "archflow"));
      const env = { CLAUDE_PLUGIN_ROOT: root, CLAUDE_PROJECT_DIR: ".", ARCHFLOW_HOST: "copilot" };
      // PascalCase event names => VS-Code/Claude-compatible snake_case payloads.
      write(join(G, "hooks", "archflow.json"), JSON.stringify({
        version: 1,
        hooks: {
          SessionStart: [
            { type: "command", bash: "cat .archflow/instructions.md 2>/dev/null || true", cwd: ".", timeoutSec: 3 },
            { type: "command", bash: `node ${root}/hooks/check-upgrade.mjs`, cwd: ".", env, timeoutSec: 6 },
            { type: "command", bash: `node ${root}/hooks/telemetry.mjs`, cwd: ".", env, timeoutSec: 3 },
          ],
          // Output of a command-type prompt hook is dropped by Copilot: observation only.
          UserPromptSubmit: [
            { type: "command", bash: `node ${root}/hooks/telemetry.mjs --prompt`, cwd: ".", env, timeoutSec: 3 },
          ],
          PreToolUse: [
            { type: "command", bash: `node ${root}/hooks/guard-git.mjs`, cwd: ".", env, timeoutSec: 5 },
          ],
          Stop: [
            { type: "command", bash: `node ${root}/hooks/check-state.mjs`, cwd: ".", env, timeoutSec: 5 },
          ],
        },
      }, null, 2) + "\n");
      const cmdList = commands.filter((c) => !this.skip.has(c.name))
        .map((c) => `- \`/archflow-${c.name}\` — ${applyVocab(c.meta.description || "", vocab)}`).join("\n");
      write(join(out, "AGENTS.archflow.md"),
        `<!-- archflow:start (managed by Archflow ${manifest.version}; merge into AGENTS.md) -->\n# Archflow\n\n` +
          `This project is managed by Archflow, a phase-based development workflow. State lives in \`.archflow/\`.\n\n` +
          `**At the start of every session, read \`.archflow/instructions.md\` before doing anything else.** The SessionStart hook injects it; this line is the fallback.\n\n` +
          `Archflow actions are skills. Run one when the user asks for it by name:\n\n${cmdList}\n\n` +
          `Specialised custom agents live in \`.github/agents/\` and are dispatched as subagents. Phase 3 runs \`ui-engineer\` and \`api-engineer\` in parallel against the same API contract.\n\n` +
          `Nothing advances a phase or merges to \`main\` without explicit user approval.\n<!-- archflow:end -->\n`);
      write(join(out, "README.md"),
        `# Archflow for ${this.label}\n\nGenerated from Archflow ${manifest.version} by \`scripts/build-adapters.mjs\`. Do not edit here.\n\n` +
          `## Install\n\n**One command:** \`npx archflow install --host ${ctx.host}\` from your project root does every step below, and re-running it upgrades in place. By hand:\n\n**Fastest: load the Claude Code plugin directly.** Copilot CLI reads \`.claude-plugin/plugin.json\` and Claude-shaped \`hooks.json\`, and sets \`CLAUDE_PLUGIN_ROOT\` / \`CLAUDE_PROJECT_DIR\` for plugin hooks:\n\n\`\`\`\ncopilot --plugin-dir /path/to/archflow/plugin      # local checkout\ncopilot plugin install AZidan/archflow:plugin      # from GitHub (subdirectory form)\n\`\`\`\n\n**Repo-scoped (this adapter), for teams that want it committed under .github/:**\n\n1. Copy \`.github/agents\`, \`.github/skills\`, \`.github/hooks\` and \`.github/archflow\` into your repo (they merge alongside your workflows).\n2. Merge \`AGENTS.archflow.md\` into \`AGENTS.md\`.\n3. Restart Copilot CLI; ask for \`/archflow-init\` or \`/archflow-onboard\`.\n\nNode.js 18+ is required for the hooks. The same \`.github/\` tree is read by VS Code agent mode and by Copilot cloud agent (hooks must be on the default branch for cloud agent).\n\n` +
          `## What is different on Copilot\n\n| Claude Code | Copilot |\n|---|---|\n` +
          `| \`/archflow:<cmd>\` | \`archflow-<cmd>\` skills (\`.github/skills/\`), invoked by name |\n` +
          `| \`agents/*.md\` sub-agents | \`.github/agents/*.agent.md\` custom agents (\`disable-model-invocation: true\`, so only Archflow dispatches them) |\n` +
          `| Plugin hooks | \`.github/hooks/archflow.json\` using PascalCase events, which give Claude-compatible payloads |\n` +
          `| Telemetry: \`UserPromptExpansion\` names the command | \`UserPromptSubmit\` counts a prompt that starts with \`/archflow-<cmd>\`. Loading the Claude plugin directly should report session starts only, as \`host: claude\` (Copilot lists no \`UserPromptExpansion\` event) |\n` +
          studioRow("/archflow-studio", ".github/archflow") +
          `| \`memory: user\` | Not available |\n`);
    },
  },
};

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);

// Introspection for tests: print the hook lists and build nothing.
if (args.includes("--list-hooks")) {
  console.log(JSON.stringify({
    hook_scripts: HOOK_SCRIPTS, claude_only_hooks: CLAUDE_ONLY_HOOKS, hosts: Object.keys(HOSTS),
  }));
  process.exit(0);
}

const check = args.includes("--check");
const wanted = args.filter((a) => !a.startsWith("--"));
const targets = wanted.length ? wanted : Object.keys(HOSTS);

const commands = readCommands();
const agents = readAgents();

for (const host of targets) {
  const def = HOSTS[host];
  if (!def) {
    console.error(`Unknown host "${host}". Known: ${Object.keys(HOSTS).join(", ")}`);
    process.exit(2);
  }
  const out = check ? join(OUT, `.${host}.check`) : join(OUT, host);
  rmSync(out, { recursive: true, force: true });
  // The telemetry command runs its script outside any hook, so ARCHFLOW_HOST is unset there; pass
  // the host on the command line instead, so an opt-out or opt-in is attributed to this host.
  const vocab = [
    ...def.vocab,
    [/(\/hooks\/telemetry\.mjs") --(enable|disable)\b/g, `$1 --$2 --host ${host}`],
    // studio.md names the host it runs in by Studio's id for it, to compare with what Studio resolved.
    [/This host's id, `claude`/g, `This host's id, \`${host}\``],
  ];
  def.emit({ out, vocab, commands, agents, host });

  if (check) {
    const live = join(OUT, host);
    let dirty = false;
    try {
      execSync(`diff -rq --no-dereference "${live}" "${out}"`, { stdio: "pipe" });
    } catch (e) {
      dirty = true;
      process.stdout.write(e.stdout.toString());
    }
    rmSync(out, { recursive: true, force: true });
    if (dirty) {
      console.error(`adapters/${host} is stale — run: node scripts/build-adapters.mjs ${host}`);
      process.exit(1);
    }
    console.log(`adapters/${host} is up to date`);
  } else {
    console.log(`built adapters/${host} (${relative(ROOT, out)})`);
  }
}
