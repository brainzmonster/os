// Import Axios for making HTTP requests to the backend API
import axios from "axios";

/**
 * Global API key and baseURL config for authenticated user operations.
 * This setup keeps the original functionality but allows flexible expansion.
 */
let _apiKey = null;

/**
 * Configure runtime connection options for user API calls.
 * @param {{ baseURL?: string, timeout?: number, apiKey?: string }} cfg
 */
export function setUserApiConfig(cfg = {}) {
  if (typeof cfg.baseURL === "string") axios.defaults.baseURL = cfg.baseURL;
  if (typeof cfg.timeout === "number") axios.defaults.timeout = cfg.timeout;
  if (typeof cfg.apiKey !== "undefined") _apiKey = cfg.apiKey;
}

// Interceptor: attach API key if configured
axios.interceptors.request.use((config) => {
  if (_apiKey) {
    config.headers = config.headers || {};
    config.headers["X-API-Key"] = _apiKey;
  }
  return config;
});

/**
 * Send a request to create a new user with the given username.
 * This is the original function — unchanged in behavior.
 * @param {string} username
 * @returns {Promise<object>} e.g., { username, api_key, timestamp, ... }
 */
export async function createUser(username) {
  if (!username || typeof username !== "string" || username.trim().length < 3) {
    throw new Error("Invalid username. Must be a non-empty string of at least 3 characters.");
  }

  // POST to the brainzOS /api/user/create endpoint with username payload
  const res = await axios.post("/api/user/create", { username });

  // Return the response data (e.g., { username, api_key })
  return res.data;
}

/**
 * NEW: Create a user with extended fields (email + role).
 * Fully backward-compatible with `createUser`, but uses the full payload
 * supported by the backend’s Pydantic model.
 *
 * @param {{
 *   username: string,
 *   email?: string,
 *   role?: string
 * }} data
 * @returns {Promise<object>}
 */
export async function createUserExtended(data = {}) {
  const { username, email, role } = data;
  if (!username || typeof username !== "string" || username.trim().length < 3) {
    throw new Error("Invalid username. Must be a non-empty string of at least 3 characters.");
  }

  const payload = {
    username,
    ...(email ? { email } : {}),
    ...(role ? { role } : {}),
  };

  try {
    const res = await axios.post("/api/user/create", payload);
    return res.data;
  } catch (error) {
    console.error("[brainzOS] Failed to create user:", error);
    throw error;
  }
}

/**
 * NEW: Fetch user info by username.
 * Useful for UI displays or checking duplicates before creating a user.
 *
 * @param {string} username
 * @returns {Promise<object|null>}
 */
export async function getUserByName(username) {
  if (!username) throw new Error("Username is required.");
  try {
    const res = await axios.get(`/api/user/info?username=${encodeURIComponent(username)}`);
    return res.data || null;
  } catch (error) {
    if (error.response && error.response.status === 404) return null;
    console.error("[brainzOS] Failed to fetch user:", error);
    throw error;
  }
}

/**
 * NEW: Delete user by API key (soft delete if supported by backend).
 * Keeps the system consistent with backend soft_delete_user logic.
 *
 * @param {string} apiKey
 * @returns {Promise<{ status: string, deleted: boolean }>}
 */
export async function deleteUser(apiKey) {
  if (!apiKey) throw new Error("API key is required for user deletion.");
  try {
    const res = await axios.delete("/api/user/delete", {
      headers: { "X-API-Key": apiKey },
    });
    return res.data;
  } catch (error) {
    console.error("[brainzOS] User deletion failed:", error);
    throw error;
  }
}

/**
 * NEW: Regenerate API key for an existing user.
 * Matches backend route for regenerating API keys (e.g. /api/user/regenerate).
 *
 * @param {string} username
 * @returns {Promise<{ username: string, api_key: string }>}
 */
export async function regenerateApiKey(username) {
  if (!username) throw new Error("Username is required.");
  try {
    const res = await axios.post("/api/user/regenerate", { username });
    return res.data;
  } catch (error) {
    console.error("[brainzOS] Failed to regenerate API key:", error);
    throw error;
  }
}

/**
 * NEW: Health check for user API availability.
 * Simple ping endpoint (if defined) to verify backend connection.
 *
 * @returns {Promise<{ ok: boolean, timestamp?: string }>}
 */
export async function userApiHealthCheck() {
  try {
    const res = await axios.get("/api/user/health");
    return { ok: true, timestamp: res.data?.timestamp || new Date().toISOString() };
  } catch (error) {
    console.warn("[brainzOS] User API health check failed:", error.message);
    return { ok: false, timestamp: new Date().toISOString() };
  }
}
