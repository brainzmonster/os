// Import React state and effect hooks
import { useState, useEffect, useCallback } from "react";
// Import the LLM training API client from brainz's frontend API layer
import { trainLLM, trainLLMDryRun, getTrainingStatus, safeTrainLLM } from "@/api/llm";

/**
 * Custom React hook for triggering LLM training and tracking status in real time.
 * Keeps backward compatibility with the original version but adds:
 * - dry-run mode
 * - live progress polling (if backend exposes a status endpoint)
 * - error logs
 * - event timestamp
 * - automatic retries (safeTrainLLM)
 */
export function useTrain() {
  // Status message returned after training (e.g., success, simulated, error)
  const [status, setStatus] = useState(null);

  // Boolean to indicate if training is currently in progress
  const [loading, setLoading] = useState(false);

  // Last training session metadata (session_id, timestamp, etc.)
  const [sessionInfo, setSessionInfo] = useState(null);

  // List of logs or backend responses for debug
  const [logs, setLogs] = useState([]);

  // Progress tracking (if supported)
  const [progress, setProgress] = useState(0);

  // Boolean to indicate dry-run mode
  const [dryRun, setDryRun] = useState(false);

  // Helper: append to local logs
  const appendLog = useCallback((msg) => {
    setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }, []);

  // === Main training function ===
  // Accepts a list of input texts and sends them to the brainz training endpoint
  const train = async (texts, options = {}) => {
    setLoading(true);
    setStatus(null);
    setProgress(0);

    const isDryRun = options?.dryRun || dryRun;
    appendLog(`Starting ${isDryRun ? "dry-run" : "live"} training on ${texts.length} samples...`);

    try {
      // Choose between real or simulated training
      const res = isDryRun
        ? await trainLLMDryRun(texts, options)
        : await safeTrainLLM(texts, options);

      // Extract details
      const meta = res?.data?.meta || res?.meta || {};
      const mode = res?.mode || (isDryRun ? "simulated" : "trained");
      const message =
        res?.data?.status ||
        res?.status ||
        (isDryRun ? "Dry-run completed" : "Training completed");

      setSessionInfo(meta);
      setStatus(`${message} (${mode})`);
      appendLog(`${message} (${mode})`);

      // Optionally begin polling for status if session ID is available
      if (meta.session_id) {
        appendLog(`Session ID: ${meta.session_id}`);
        pollTrainingStatus(meta.session_id);
      }
    } catch (err) {
      console.error("[brainzOS] Training failed:", err);
      setStatus("Training failed");
      appendLog(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // === Poll backend for live training progress (if supported) ===
  const pollTrainingStatus = useCallback(async (sessionId) => {
    try {
      appendLog("Polling training status...");
      const res = await getTrainingStatus(sessionId);
      if (res?.progress) {
        setProgress(res.progress);
        appendLog(`Progress: ${Math.round(res.progress * 100)}%`);
      }
      if (res?.status) {
        setStatus(res.status);
      }
    } catch (err) {
      appendLog(`Polling failed: ${err.message}`);
    }
  }, [appendLog]);

  // === Cancel any running training (client-side only) ===
  const cancelTraining = useCallback(() => {
    setLoading(false);
    setStatus("Training cancelled");
    appendLog("Training cancelled by user.");
  }, [appendLog]);

  // === Auto-log when training finishes ===
  useEffect(() => {
    if (!loading && status) {
      appendLog(`Training finished: ${status}`);
    }
  }, [loading, status, appendLog]);

  // === Reset all local states ===
  const resetTrainingState = useCallback(() => {
    setStatus(null);
    setSessionInfo(null);
    setLogs([]);
    setProgress(0);
    setDryRun(false);
    appendLog("Training state reset.");
  }, [appendLog]);

  // === Toggle dry-run mode ===
  const toggleDryRun = useCallback(() => {
    setDryRun((prev) => !prev);
    appendLog(`Dry-run mode ${!dryRun ? "enabled" : "disabled"}.`);
  }, [dryRun, appendLog]);

  // Expose the full API
  return {
    train,               // Trigger training
    cancelTraining,      // Cancel training manually
    resetTrainingState,  // Reset all local state
    toggleDryRun,        // Toggle dry-run mode
    status,              // Latest status message
    loading,             // Is training running
    dryRun,              // Current dry-run mode
    progress,            // Progress (0-1)
    sessionInfo,         // Metadata from backend
    logs,                // Internal logs for UI
  };
}
