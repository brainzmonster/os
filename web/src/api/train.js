// Import Axios for making HTTP requests
import axios from "axios";

/**
 * Lightweight module to interact with the training endpoints.
 * - Keeps the original `trainLLM(texts)` signature 100% intact.
 * - Adds optional helpers for dry-runs, status polling, and basic client-side validation.
 */

let _apiKey = null;

/**
 * Optionally configure a baseURL, timeout, and API key for auth middleware.
 * This is non-breaking: if you never call it, defaults remain unchanged.
 */
export function setTrainApiConfig({ baseURL, timeout, apiKey } = {}) {
  if (typeof baseURL === "string") axios.defaults.baseURL = baseURL;
  if (typeof timeout === "number") axios.defaults.timeout = timeout;
  if (typeof apiKey !== "undefined") _apiKey = apiKey;
}

// Attach API key header if configured
axios.interceptors.request.use((config) => {
  if (_apiKey) {
    config.headers = config.headers || {};
    config.headers["X-API-Key"] = _apiKey;
  }
  return config;
});

/**
 * Internal small helper for exponential backoff retry.
 * Keeps the default behavior as "no retry", opt-in per call.
 */
async function withRetry(fn, { retries = 0, baseDelayMs = 300 } = {}) {
  let attempt = 0;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    try {
      return await fn();
    } catch (err) {
      if (attempt >= retries) throw err;
      const delay = baseDelayMs * Math.pow(2, attempt);
      await new Promise((r) => setTimeout(r, delay));
      attempt += 1;
    }
  }
}

/**
 * Very basic client-side hygiene: trim, drop empties/too short lines.
 * This does not replace server-side validation; it's just a guard.
 * @param {string[]} texts
 * @param {{ minWords?: number }} opts
 * @returns {string[]}
 */
export function sanitizeTrainingTexts(texts = [], { minWords = 1 } = {}) {
  if (!Array.isArray(texts)) return [];
  return texts
    .map((t) => (typeof t === "string" ? t.trim() : ""))
    .filter((t) => t.length > 0 && t.split(/\s+/).length >= minWords);
}

/**
 * === Original function (kept EXACTLY compatible) ===
 * Sends a request to fine-tune the LLM using provided training texts
 * @param {string[]} texts
 * @returns {Promise<object>}
 */
export async function trainLLM(texts = []) {
  // Validate that the input is a non-empty array of strings
  if (!Array.isArray(texts) || texts.length === 0) {
    throw new Error("Training data must be a non-empty array of strings.");
  }

  try {
    // Send POST request to brainzOS training endpoint
    const response = await axios.post("/api/llm/train", { texts });

    // Return the response data from the server
    return response.data;
  } catch (error) {
    // Log error to console and re-throw it for the UI or caller to handle
    console.error("[brainzOS] Training failed:", error);
    throw error;
  }
}

/**
 * NEW: Dry-run training (server simulates training and returns estimates).
 * Accepts optional tags/source to help downstream analytics.
 * Non-breaking addition; does not affect `trainLLM`.
 *
 * @param {string[]} texts
 * @param {{ tags?: string[], source?: string, retries?: number, timeout?: number }} options
 * @returns {Promise<object>}
 */
export async function trainLLMDryRun(texts = [], options = {}) {
  const clean = sanitizeTrainingTexts(texts);
  if (clean.length === 0) {
    throw new Error("Dry-run: no valid texts after sanitation.");
  }

  const payload = {
    texts: clean,
    dry_run: true,
    tags: Array.isArray(options.tags) ? options.tags : [],
    source: options.source || "web",
  };

  const config = {
    timeout: typeof options.timeout === "number" ? options.timeout : axios.defaults.timeout,
  };

  const exec = () => axios.post("/api/llm/train", payload, config);
  const res = await withRetry(exec, { retries: options.retries ?? 0 });
  return res.data;
}

/**
 * NEW: Poll server-side training status (if you wired /api/llm/train/status).
 * Useful for showing progress while long fine-tuning jobs run.
 *
 * @param {string} sessionId - training session ID returned by backend
 * @param {{ retries?: number, timeout?: number }} options
 * @returns {Promise<object>}
 */
export async function getTrainingStatus(sessionId, options = {}) {
  if (!sessionId || typeof sessionId !== "string") {
    throw new Error("A valid sessionId is required to query training status.");
  }

  const config = {
    params: { session_id: sessionId },
    timeout: typeof options.timeout === "number" ? options.timeout : axios.defaults.timeout,
  };

  const exec = () => axios.get("/api/llm/train/status", config);
  const res = await withRetry(exec, { retries: options.retries ?? 0 });
  return res.data;
}

/**
 * NEW: Convenience wrapper — trains with optional dry-run fallback.
 * If the live train fails (e.g., temporary outage), it retries once as dry-run
 * to at least return useful estimates to the UI.
 *
 * @param {string[]} texts
 * @param {{ tags?: string[], source?: string, retries?: number, timeout?: number }} options
 * @returns {Promise<{ mode: "trained" | "simulated", data: object }>}
 */
export async function safeTrainLLM(texts = [], options = {}) {
  try {
    const data = await trainLLM(texts); // uses the original, fully-compatible call
    return { mode: "trained", data };
  } catch (err) {
    console.warn("[brainzOS] live training failed, attempting dry-run fallback…", err?.message || err);
    const data = await trainLLMDryRun(texts, options);
    return { mode: "simulated", data };
  }
}
