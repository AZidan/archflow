/**
 * PostHog project API key. This is the *public* write-only key PostHog client
 * libraries embed in browser/CLI code — it is not a secret and is safe to
 * commit (see https://posthog.com/docs/api#public-vs-private-keys). It is
 * kept in its own file so it is the one line to touch after rotating a key.
 *
 * Sourced from docs/internal/ph.env (gitignored); this file is the one place
 * that value is committed. Left empty, telemetry silently no-ops regardless
 * of the on-by-default setting.
 */
export const POSTHOG_API_KEY = "phc_nuuik2SamCaEPcZ8DNF7nfqDZ534zFQ8Ae8cYmEsjMcq";
export const POSTHOG_HOST = "https://us.i.posthog.com";
