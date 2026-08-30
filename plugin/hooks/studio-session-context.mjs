#!/usr/bin/env node
/**
 * archflow studio — SessionStart hook: publish the launching session's context.
 *
 * WHAT IT IS FOR
 * --------------
 * Companion mode (S10-01) needs three facts that Claude Code exposes only to a
 * hook: the session id, the transcript path, and the cwd the session started
 * in. This hook receives them on stdin as JSON and writes them to a file that
 * `/archflow:studio` hands to the server via `--session-context`.
 *
 * The written keys are snake_case and copied VERBATIM from stdin, deliberately:
 * the hook is a passthrough and therefore cannot mistranslate. The consumer is
 * `server/mode/sessionContext.ts`, whose header is the contract this satisfies.
 *
 *   {
 *     "session_id":      "b1f0c3d2-…",   // REQUIRED, non-empty
 *     "transcript_path": "/Users/me/.claude/projects/<slug>/<id>.jsonl",
 *     "cwd":             "/Users/me/dev/my-app",
 *     "written_at":      "2026-08-23T09:15:00.000Z"
 *   }
 *
 * PATH — `STUDIO_SESSION_CONTEXT` if set, else
 * `~/.archflow/studio/session-context.json`. Same two rungs, in the same order,
 * as the server's resolver, so producer and consumer cannot disagree.
 *
 * LIFETIME — the file describes ONE session and is rewritten on every
 * SessionStart (startup, resume, clear, compact). Nothing deletes it when a
 * session ends, because no hook reliably fires there; the server expires it by
 * age instead (12 h, SESSION_CONTEXT_MAX_AGE_MS). One file, last session to
 * start wins it — two concurrent sessions need `STUDIO_SESSION_CONTEXT` set
 * per session to get two distinct files.
 *
 * FAILING THE SESSION IS WORSE THAN FAILING THE STUDIO
 * ----------------------------------------------------
 * A hook that errors, hangs, or chatters degrades every Claude Code session in
 * every project the archflow plugin is installed into — including the sessions
 * of users who never open studio. A studio that cannot resolve companion mode
 * merely degrades to full mode with a stated reason. So:
 *
 *   - every failure path exits 0,
 *   - nothing is ever printed (SessionStart stdout is injected into the
 *     session's context; this hook has nothing to say to the model),
 *   - stdin is read under a watchdog so a stdin that never closes cannot hang
 *     session startup,
 *   - the write is temp-file + rename, so a reader never sees a half-written
 *     file and a crashed write leaves the previous context intact.
 */
import { mkdirSync, realpathSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** Give up on stdin after this long and write nothing. */
export const STDIN_TIMEOUT_MS = 3000;

/** Refuse absurd stdin rather than buffering it. */
export const STDIN_MAX_BYTES = 1024 * 1024;

/** Must match `defaultSessionContextPath()` in server/mode/sessionContext.ts. */
export function defaultSessionContextPath(home = homedir()) {
  return join(home, '.archflow', 'studio', 'session-context.json');
}

/** Where to write: `STUDIO_SESSION_CONTEXT`, else the default path. */
export function resolveOutputPath(env = process.env, home = homedir()) {
  const fromEnv = typeof env.STUDIO_SESSION_CONTEXT === 'string' ? env.STUDIO_SESSION_CONTEXT.trim() : '';
  return fromEnv ? resolve(fromEnv) : defaultSessionContextPath(home);
}

/**
 * Turn hook stdin into the context object, or null when there is nothing worth
 * writing. `session_id` is the only required key — the server can `--resume`
 * with nothing else — so a payload without one writes NO file rather than a
 * file the server would reject as `missing-session-id`.
 */
export function buildContext(payload, now = new Date()) {
  if (typeof payload !== 'object' || payload === null || Array.isArray(payload)) return null;

  const sessionId = typeof payload.session_id === 'string' ? payload.session_id.trim() : '';
  if (!sessionId) return null;

  const context = { session_id: sessionId };
  if (typeof payload.transcript_path === 'string' && payload.transcript_path) {
    context.transcript_path = payload.transcript_path;
  }
  if (typeof payload.cwd === 'string' && payload.cwd) {
    context.cwd = payload.cwd;
  }
  // Written last so it is the last key in the file, and so a copied file keeps
  // its own notion of age (the server prefers this over mtime).
  context.written_at = now.toISOString();
  return context;
}

/**
 * Write `text` to `path` such that no reader ever observes a partial file:
 * write a sibling temp file, fsync-free rename over the target (atomic within a
 * filesystem). Creates the directory if it is absent.
 */
export function writeAtomic(path, text) {
  mkdirSync(dirname(path), { recursive: true });
  const tmp = `${path}.${process.pid}.${Date.now()}.tmp`;
  try {
    // 0600: the file names a session id and a transcript path.
    writeFileSync(tmp, text, { encoding: 'utf-8', mode: 0o600 });
    renameSync(tmp, path);
  } catch (err) {
    try {
      unlinkSync(tmp);
    } catch {
      // best effort — a leftover temp file is not worth failing over
    }
    throw err;
  }
}

/**
 * The whole job, given raw stdin.
 *
 * @returns the path written, or null when nothing was written (malformed
 *   stdin, or no `session_id`). Throws only on a filesystem failure, which
 *   `main()` swallows.
 */
export function publish(raw, { env = process.env, home = homedir(), now = new Date() } = {}) {
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  const context = buildContext(payload, now);
  if (!context) return null;

  const path = resolveOutputPath(env, home);
  writeAtomic(path, `${JSON.stringify(context, null, 2)}\n`);
  return path;
}

/** Read all of stdin, or '' if it errors, overflows, or stalls. */
function readStdin() {
  return new Promise((res) => {
    let data = '';
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      res(value);
    };
    const timer = setTimeout(() => finish(''), STDIN_TIMEOUT_MS);
    try {
      process.stdin.setEncoding('utf-8');
      process.stdin.on('data', (chunk) => {
        data += chunk;
        if (data.length > STDIN_MAX_BYTES) finish('');
      });
      process.stdin.on('end', () => finish(data));
      process.stdin.on('error', () => finish(''));
    } catch {
      finish('');
    }
  });
}

async function main() {
  try {
    publish(await readStdin());
  } catch {
    // Deliberately silent. See the header: a broken studio handoff must never
    // become a broken Claude Code session.
  }
  process.exit(0);
}

/**
 * Compare two paths as the filesystem sees them.
 *
 * Symlinks are why this is not `resolve(a) === resolve(b)`: Node hands
 * `import.meta.url` the REAL path of the module while `process.argv[1]` keeps
 * whatever was typed. On macOS a plugin installed under `/tmp` is reached as
 * `/private/tmp`, the two disagree, and the hook silently decides it was
 * imported rather than run — writing nothing, exiting 0, and degrading every
 * studio launch to full mode with no clue why.
 */
function samePath(a, b) {
  const real = (p) => {
    try {
      return realpathSync(p);
    } catch {
      return resolve(p);
    }
  };
  return real(a) === real(b);
}

const invokedDirectly = !!process.argv[1] && samePath(process.argv[1], fileURLToPath(import.meta.url));

if (invokedDirectly) {
  await main();
}
