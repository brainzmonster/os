// Import Axios for making HTTP requests to the backend API
import axios from "axios";

/**
 * ----------------------------------------
 * Axios instance & runtime configuration
 * ----------------------------------------
 * We keep defaults compatible with the existing code (same-origin, no headers),
 * but expose setters so the app can:
 *  - point to a custom baseURL (e.g., http://localhost:8000)
 *  - attach an API key header (X-API-Key) when auth middleware is enabled
 *  - tweak timeouts without touching each call
 */
let _apiKey = null;

export const http = axios.create({
  baseURL: "",            // same-origin by default (works behind a reverse proxy)
  timeout: 15000,         // sensible default; adjustable via setApiConfig
});

// Attach API key automatically if provided via setApiKey/setApiConfig
http.interceptors.request.use((config) => {
  if (_apiKey) {
    config.headers = config.headers || {};
    config.headers["X-API-Key"] = _apiKey;
  }
  return config;
});

/**
 * Update baseURL/timeout/API key at runtime.
 * @param {{ baseURL?: string, timeout?: number, apiKey?: string | null }} cfg
 */
export function setApiConfig(cfg = {}) {
  if (typeof cfg.baseURL === "string") http.defaults.baseURL = cfg.baseURL;
  if (typeof cfg.timeout === "number") http.defaults.timeout = cfg.timeout;
  if (typeof cfg.apiKey !== "undefined") _apiKey = cfg.apiKey;
}

/**
 * Shorthand to only set the API key.
 * @param {string|null} apiKey
 */
export function setApiKey(apiKey) {
  _apiKey = apiKey;
}

/**
 * Internal helper: retry wrapper with exponential backoff.
 * Keeps things lightweight and opt-in per request.
 * @param {Function} fn async function to invoke
 * @param {{retries?: number, baseDelayMs?: number}} options
 */
async function withRetry(fn, { retries = 0, baseDelayMs = 300 } = {}) {
  let attempt = 0;
  while (true) {
    try {
      return await fn();
    } catch (err) {
      if (attempt >= retries) throw err;
      const delay = baseDelayMs * Math.pow(2, attempt); // 300, 600, 1200, ...
      await new Promise((r) => setTimeout(r, delay));
      attempt += 1;
    }
  }
}

/**
 * ----------------------------------------
 * LLM: Query endpoint
 * ----------------------------------------
 * Send a prompt to the LLM query endpoint and return the generated response.
 * Signature stays backward compatible.
 *
 * @param {string} input - User prompt
 * @param {{
 *   max_tokens?: number,
 *   temperature?: number,
 *   system_prompt?: string,
 *   signal?: AbortSignal,           // optional AbortController signal
 *   retries?: number,               // optional retry attempts
 *   timeout?: number                // per-request timeout override
 * }} options
 * @returns {Promise<object>} JSON response from API
 */
export async function queryLLM(input, options = {}) {
  const payload = {
    input,                                        // Required by backend
    max_tokens: options.max_tokens ?? 100,        // Default to 100 tokens
    temperature: options.temperature ?? 0.7,      // Default temperature
    system_prompt: options.system_prompt ?? null, // Optional system prompt
  };

  const config = {
    signal: options.signal,
    timeout: options.timeout ?? http.defaults.timeout,
  };

  const exec = () => http.post("/api/llm/query", payload, config);
  try {
    const res = await withRetry(exec, { retries: options.retries ?? 0 });
    return res.data;
  } catch (err) {
    // Normalize error to keep the callsite simple
    const status = err.response?.status;
    const detail = err.response?.data || err.message;
    throw new Error(
      `[queryLLM] request failed${status ? ` (${status})` : ""}: ${JSON.stringify(
        detail
      )}`
    );
  }
}

/**
 * ----------------------------------------
 * LLM: Train endpoint
 * ----------------------------------------
 * Send training texts to fine-tune the model via the backend API.
 * Signature remains compatible (trainLLM(texts)), but you can pass extras.
 *
 * @param {string[]} texts
 * @param {{
 *   dry_run?: boolean,
 *   tags?: string[],
 *   source?: string,
 *   retries?: number,
 *   timeout?: number
 * }} options
 * @returns {Promise<object>}
 */
export async function trainLLM(texts, options = {}) {
  const payload = {
    texts,
    // Optional extended fields supported by the backend
    dry_run: options.dry_run ?? false,
    tags: options.tags ?? [],
    source: options.source ?? "web",
  };

  const config = {
    timeout: options.timeout ?? http.defaults.timeout,
  };

  const exec = () => http.post("/api/llm/train", payload, config);
  try {
    const res = await withRetry(exec, { retries: options.retries ?? 0 });
    return res.data;
  } catch (err) {
    const status = err.response?.status;
    const detail = err.response?.data || err.message;
    throw new Error(
      `[trainLLM] request failed${status ? ` (${status})` : ""}: ${JSON.stringify(
        detail
      )}`
    );
  }
}

/**
 * ----------------------------------------
 * System: Fetch logs
 * ----------------------------------------
 * Paginated + filterable log retrieval from /api/system/logs.
 *
 * @param {{
 *   limit?: number,
 *   offset?: number,
 *   level?: string,
 *   source?: string,
 *   start_time?: string, // ISO8601
 *   end_time?: string,   // ISO8601
 *   retries?: number,
 *   timeout?: number
 * }} params
 * @returns {Promise<{ logs: any[], count: number, meta: object }>}
 */
export async function getSystemLogs(params = {}) {
  const query = {
    limit: params.limit ?? 50,
    offset: params.offset ?? 0,
    level: params.level ?? undefined,
    source: params.source ?? undefined,
    start_time: params.start_time ?? undefined,
    end_time: params.end_time ?? undefined,
  };

  const config = {
    params: query,
    timeout: params.timeout ?? http.defaults.timeout,
  };

  const exec = () => http.get("/api/system/logs", config);
  try {
    const res = await withRetry(exec, { retries: params.retries ?? 0 });
    return res.data;
  } catch (err) {
    const status = err.response?.status;
    const detail = err.response?.data || err.message;
    throw new Error(
      `[getSystemLogs] request failed${status ? ` (${status})` : ""}: ${JSON.stringify(
        detail
      )}`
    );
  }
}

/**
 * ----------------------------------------
 * Health: Basic ping
 * ----------------------------------------
 * Simple health check against the root endpoint.
 * Useful for readiness checks in the frontend before enabling UI controls.
 *
 * @returns {Promise<{ ok: boolean, message?: string }>}
 */
export async function healthCheck() {
  try {
    const res = await http.get("/");
    return { ok: res.status === 200, message: res.data?.message };
  } catch (err) {
    return { ok: false, message: err.message };
  }
}

/**
 * ----------------------------------------
 * Utility: Abortable controller factory
 * ----------------------------------------
 * Helper to create an AbortController for cancellable queries (e.g. live typing).
 * Example:
 *   const { controller, signal } = createAbort();
 *   queryLLM("...", { signal });
 *   controller.abort(); // cancel inflight request
 */
export function createAbort() {
  const controller = new AbortController();
  return { controller, signal: controller.signal };
}
