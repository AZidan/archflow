#!/usr/bin/env node
/**
 * askUserServer — the stdio MCP server behind `mcp__archflow-studio__ask_user`
 * (S3-28, docs/api-contract.md § S3-28).
 *
 * The CLI spawns this as its own child, so it lives as long as the CLI and not
 * as long as the studio. A call REGISTERS a question with the studio over
 * loopback REST, then POLLS until it has an outcome, and returns that outcome
 * as the tool result. Nothing goes near the CLI's stdin.
 *
 * PLAIN .mjs WITH NO DEPENDENCIES, AND THAT IS LOAD-BEARING. This file runs under
 * a bare `node` from wherever the studio was installed: beside the TypeScript
 * sources in dev (where the studio itself runs under tsx, but this child would
 * not), and beside the esbuild bundle in `plugin/server/`, where there is no
 * node_modules at all. Importing anything but node builtins breaks one of them.
 *
 * IT READS, NEVER CACHES, ITS INPUTS. The config's env carries only
 * ARCHFLOW_RUN_DIR. Every request re-reads `ask-credential.json` for the token
 * and `studio.json` for the API URL, so a studio restart on another port is
 * picked up on the next attempt with no signalling (S3-14 rewrites studio.json).
 */
import { randomBytes } from 'node:crypto';
import { readFileSync, realpathSync } from 'node:fs';
import http from 'node:http';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

export const SERVER_NAME = 'archflow-studio';
export const TOOL_NAME = 'ask_user';

const QUESTIONS_PATH = '/api/chat/ask/questions';
const REQUEST_ID = /^[A-Za-z0-9_-]{1,128}$/;
const TOKEN_HEADER = 'X-Archflow-Ask-Token';

/** The contract's bounds (§ Bounds). Fixed: the tests pin them. */
export const POLL_WAIT_MS = 20_000;
export const UNREACHABLE_BOUND_MS = 120_000;
export const MAX_WAIT_MS = 4 * 60 * 60 * 1000;
export const BACKOFF_START_MS = 1_000;
export const BACKOFF_MAX_MS = 5_000;
export const PROGRESS_EVERY_MS = 30_000;
/** Added to a request's own wait, so a slow answer is not mistaken for a dead studio. */
const REQUEST_GRACE_MS = 10_000;
/** How long a best-effort withdrawal gets. */
const WITHDRAW_TIMEOUT_MS = 1_500;

/** The contract's error results. Wording is fixed: the tests pin it. */
export const TEXT = {
  sessionEnded:
    'The Archflow Studio session that hosted this question has ended, so it was not asked. Ask the user in plain text instead.',
  mismatch:
    'This question belongs to a different session and was not asked. Ask the user in plain text instead.',
  unreachable:
    'Archflow Studio could not be reached for 2 minutes, so the question was not asked. Ask the user in plain text instead.',
  maxWait:
    'No answer was given within 4 hours, so the question was withdrawn. Continue with your best judgment, or ask in plain text.',
  invalid: (error) =>
    `The question input was not valid (${error}). Ask the user in plain text instead.`,
};

/** The `AskUserQuestion` input shape, exactly (contract § mcp-tool-ask-user). */
export const TOOL_DEFINITION = {
  name: TOOL_NAME,
  description:
    'Ask the user one or more questions in the Archflow Studio chat panel and wait for the answer, ' +
    'which comes back as this tool result. Use it wherever you would use AskUserQuestion: to gather ' +
    'preferences, clarify a request, or get a decision only the user can make. Each question can ' +
    'offer options to choose from; give no options for a free-text answer.',
  inputSchema: {
    type: 'object',
    properties: {
      questions: {
        type: 'array',
        description: 'The questions to ask, in order.',
        minItems: 1,
        maxItems: 8,
        items: {
          type: 'object',
          properties: {
            question: { type: 'string', description: 'The complete question to ask.' },
            header: { type: 'string', description: 'A very short label for the question.' },
            multiSelect: {
              type: 'boolean',
              description: 'Whether the user may choose more than one option.',
            },
            options: {
              type: 'array',
              maxItems: 12,
              items: {
                type: 'object',
                properties: {
                  label: { type: 'string', description: 'The text of this choice.' },
                  description: { type: 'string', description: 'What choosing it means.' },
                  preview: {
                    type: 'string',
                    description: 'Pre-formatted material this choice would produce.',
                  },
                },
                required: ['label'],
              },
            },
          },
          required: ['question'],
        },
      },
    },
    required: ['questions'],
  },
};

// ---------------------------------------------------------------------------
// One HTTP attempt
// ---------------------------------------------------------------------------

/** Read both input files. Null when either is missing or unreadable. */
export function readInputs(runDir) {
  try {
    const credential = JSON.parse(readFileSync(join(runDir, 'ask-credential.json'), 'utf-8'));
    const studio = JSON.parse(readFileSync(join(runDir, 'studio.json'), 'utf-8'));
    if (typeof credential.token !== 'string' || typeof studio.api_url !== 'string') return null;
    return { token: credential.token, apiUrl: studio.api_url };
  } catch {
    return null;
  }
}

/**
 * One request against whichever studio `studio.json` names right now. Resolves
 * `{ status, json }`, or null for anything that produced no HTTP response.
 *
 * `localhost` is dialled as 127.0.0.1. The studio binds only that, and a node
 * that resolves `localhost` to ::1 first would otherwise see a refused
 * connection from a healthy studio. 127.0.0.1 is an allowed Host (security/trust).
 */
export function createTransport(runDir) {
  return (method, path, body, timeoutMs, signal) =>
    new Promise((resolve) => {
      const inputs = readInputs(runDir);
      if (!inputs || signal?.aborted) {
        resolve(null);
        return;
      }
      let url;
      try {
        url = new URL(path, inputs.apiUrl);
      } catch {
        resolve(null);
        return;
      }
      if (url.hostname === 'localhost') url.hostname = '127.0.0.1';
      const payload = body === undefined ? null : JSON.stringify(body);
      const req = http.request(
        url,
        {
          method,
          signal,
          headers: {
            [TOKEN_HEADER]: inputs.token,
            ...(payload === null
              ? {}
              : {
                  'Content-Type': 'application/json',
                  'Content-Length': Buffer.byteLength(payload),
                }),
          },
        },
        (res) => {
          const chunks = [];
          res.on('data', (chunk) => chunks.push(chunk));
          res.on('error', () => resolve(null));
          res.on('end', () => {
            let json = null;
            try {
              json = JSON.parse(Buffer.concat(chunks).toString('utf-8'));
            } catch {
              /* A body we cannot read still has a status. */
            }
            resolve({ status: res.statusCode ?? 0, json });
          });
        }
      );
      req.setTimeout(timeoutMs, () => req.destroy());
      req.on('error', () => resolve(null));
      req.end(payload ?? undefined);
    });
}

// ---------------------------------------------------------------------------
// One tool call
// ---------------------------------------------------------------------------

/** `requestId` is the tool call id when it can be one, else minted ONCE per call. */
export function chooseRequestId(toolUseId) {
  if (typeof toolUseId === 'string' && REQUEST_ID.test(toolUseId)) return toolUseId;
  return `ask_${randomBytes(8).toString('hex')}`;
}

/** The model sometimes sends `questions` as a JSON-encoded string, as for AskUserQuestion. */
export function decodeQuestions(questions) {
  if (typeof questions !== 'string') return questions;
  try {
    return JSON.parse(questions);
  } catch {
    return questions;
  }
}

function abortableSleep(ms, signal) {
  return new Promise((resolve) => {
    if (signal?.aborted) {
      resolve();
      return;
    }
    const done = () => {
      clearTimeout(timer);
      signal?.removeEventListener('abort', done);
      resolve();
    };
    const timer = setTimeout(done, ms);
    signal?.addEventListener('abort', done, { once: true });
  });
}

const failure = (text) => ({ text, isError: true });

/**
 * Run one `ask_user` call to its end. It always ends: an answer, a terminal
 * studio response, or one of the two bounds. Resolves null only when `signal`
 * aborted, which means the CLI no longer wants an answer.
 *
 * `transport` and `clock` are parameters so the bounds can be tested without
 * waiting two minutes.
 */
export async function runAskCall({
  input,
  toolUseId,
  requestId = chooseRequestId(toolUseId),
  transport,
  clock = { now: () => Date.now(), sleep: abortableSleep },
  signal,
}) {
  const askedAtMs = clock.now();
  const body = {
    requestId,
    toolUseId: typeof toolUseId === 'string' ? toolUseId : null,
    // Set once. Re-registering with the same value is what fixes queue order
    // across a studio restart.
    askedAt: new Date(askedAtMs).toISOString(),
    questions: decodeQuestions(input?.questions),
  };
  const questionPath = `${QUESTIONS_PATH}/${encodeURIComponent(requestId)}`;

  let lastSuccess = clock.now();
  let backoff = BACKOFF_START_MS;
  let registered = false;

  for (;;) {
    if (signal?.aborted) return null;

    const remaining = MAX_WAIT_MS - (clock.now() - askedAtMs);
    if (remaining <= 0) {
      await transport('DELETE', questionPath, undefined, REQUEST_GRACE_MS);
      return failure(TEXT.maxWait);
    }

    const waitMs = Math.min(POLL_WAIT_MS, remaining);
    const res = registered
      ? await transport('GET', `${questionPath}?waitMs=${waitMs}`, undefined, waitMs + REQUEST_GRACE_MS, signal)
      : await transport('POST', QUESTIONS_PATH, body, REQUEST_GRACE_MS, signal);
    if (signal?.aborted) return null;

    const status = res?.status ?? 0;
    const code = res?.json?.code;

    if (status === 410) return failure(TEXT.sessionEnded);
    if (status === 403) return failure(TEXT.mismatch);
    if (status === 400) return failure(TEXT.invalid(res?.json?.error ?? 'invalid input'));

    if (status === 404 && code === 'QUESTION_NOT_FOUND') {
      // The studio does not know this question: it restarted. Ask again, with
      // the same id and the same askedAt, and the card comes back.
      lastSuccess = clock.now();
      backoff = BACKOFF_START_MS;
      registered = false;
      continue;
    }

    // `state` is what makes it this API. A studio without these routes answers
    // 200 with its SPA, and that must not read as "still pending" for 4 hours.
    if ((status === 200 || status === 201) && typeof res?.json?.state === 'string') {
      lastSuccess = clock.now();
      backoff = BACKOFF_START_MS;
      if (!registered) {
        // The next pass polls, whatever state this said: only a poll carries
        // `resultText`, and a repeat of a finished question gets it there.
        registered = true;
        continue;
      }
      const state = res?.json?.state;
      if (state === 'answered' || state === 'cancelled') {
        return { text: String(res?.json?.resultText ?? ''), isError: state !== 'answered' };
      }
      continue;
    }

    // No response, 401 (a studio that has not adopted this run yet), or a 5xx.
    if (clock.now() - lastSuccess >= UNREACHABLE_BOUND_MS) return failure(TEXT.unreachable);
    await clock.sleep(backoff, signal);
    backoff = Math.min(backoff * 2, BACKOFF_MAX_MS);
  }
}

// ---------------------------------------------------------------------------
// JSON-RPC over stdio
// ---------------------------------------------------------------------------

export function serve({
  runDir,
  input = process.stdin,
  output = process.stdout,
  exit = process.exit,
  progressEveryMs = PROGRESS_EVERY_MS,
}) {
  const transport = createTransport(runDir);
  /** rpc id -> the running call, so `notifications/cancelled` can find it. */
  const calls = new Map();
  let closing = false;

  const send = (message) => output.write(`${JSON.stringify({ jsonrpc: '2.0', ...message })}\n`);

  const startCall = (id, params) => {
    const meta = params?._meta ?? {};
    const controller = new AbortController();
    const progressToken = meta.progressToken;
    let progress = 0;
    const heartbeat =
      progressToken === undefined
        ? null
        : setInterval(() => {
            progress += 1;
            send({
              method: 'notifications/progress',
              params: { progressToken, progress, message: 'Waiting for the user to answer.' },
            });
          }, progressEveryMs);

    const toolUseId = meta['claudecode/toolUseId'];
    // Decided here as well as used inside the call: a cancelled call withdraws by it.
    const call = { controller, requestId: chooseRequestId(toolUseId) };
    calls.set(id, call);

    runAskCall({
      input: params?.arguments,
      toolUseId,
      requestId: call.requestId,
      transport,
      signal: controller.signal,
    })
      .then((outcome) => {
        if (outcome === null) return; // cancelled: the CLI wants no response
        send({
          id,
          result: { content: [{ type: 'text', text: outcome.text }], isError: outcome.isError },
        });
      })
      .catch((err) => {
        send({
          id,
          result: {
            content: [{ type: 'text', text: TEXT.invalid(err?.message ?? 'unknown error') }],
            isError: true,
          },
        });
      })
      .finally(() => {
        if (heartbeat) clearInterval(heartbeat);
        calls.delete(id);
      });
  };

  const withdraw = (call) =>
    transport(
      'DELETE',
      `${QUESTIONS_PATH}/${encodeURIComponent(call.requestId)}`,
      undefined,
      WITHDRAW_TIMEOUT_MS
    );

  /**
   * Leaves without withdrawing, because every way here means the process is
   * ending, and the contract's amendment makes that `tool-ended`. A DELETE would
   * reach the studio first and say `withdrawn`: a CLI on SIGTERM sends this server
   * SIGINT about a second before it exits itself. The studio ends the pending
   * question when it sees the CLI exit, or the stream show the call ended if only
   * this server died.
   */
  const shutdown = () => {
    if (closing) return;
    closing = true;
    for (const call of calls.values()) call.controller.abort();
    exit(0);
  };

  const handle = (message) => {
    const { id, method, params } = message;
    switch (method) {
      case 'initialize':
        send({
          id,
          result: {
            protocolVersion: params?.protocolVersion ?? '2025-06-18',
            capabilities: { tools: {} },
            serverInfo: { name: SERVER_NAME, version: '1.0.0' },
          },
        });
        return;
      case 'ping':
        send({ id, result: {} });
        return;
      case 'tools/list':
        send({ id, result: { tools: [TOOL_DEFINITION] } });
        return;
      case 'tools/call':
        if (params?.name !== TOOL_NAME) {
          send({ id, error: { code: -32602, message: `Unknown tool: ${params?.name}` } });
          return;
        }
        startCall(id, params);
        return;
      case 'notifications/cancelled': {
        const call = calls.get(params?.requestId);
        if (call) {
          call.controller.abort();
          void withdraw(call);
        }
        return;
      }
      default:
        if (id !== undefined && id !== null) {
          send({ id, error: { code: -32601, message: `Method not found: ${method}` } });
        }
    }
  };

  const lines = createInterface({ input });
  lines.on('line', (line) => {
    if (!line.trim()) return;
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      send({ id: null, error: { code: -32700, message: 'Parse error' } });
      return;
    }
    handle(message);
  });
  // The CLI is gone or going. Nobody can read an answer, so leave.
  lines.on('close', shutdown);
  process.once('SIGTERM', shutdown);
  process.once('SIGINT', shutdown);
}

function isMain() {
  if (!process.argv[1]) return false;
  try {
    return realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

if (isMain()) {
  serve({ runDir: process.env.ARCHFLOW_RUN_DIR ?? '' });
}
