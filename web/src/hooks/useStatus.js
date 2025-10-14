// React hooks for state and side effects
import { useEffect, useState, useCallback } from "react";

/**
 * Custom hook to continuously check the status of the brainzOS backend.
 * Keeps original logic but adds:
 * - latency measurement
 * - automatic exponential backoff on repeated failures
 * - timestamp of last successful ping
 * - manual refresh support
 * - color-coded severity levels for UI
 * - optional verbose logging for debugging
 */
export function useStatusPing({ verbose = false } = {}) {
  // Holds the current connection status: "Connecting...", "Online", "Offline", or "Degraded"
  const [status, setStatus] = useState("Connecting...");

  // Measured ping latency (in ms)
  const [latency, setLatency] = useState(null);

  // Timestamp of the last successful ping
  const [lastPing, setLastPing] = useState(null);

  // Counts how many failed attempts occurred in a row
  const [failCount, setFailCount] = useState(0);

  // Dynamically adjusted polling interval (in ms)
  const [intervalMs, setIntervalMs] = useState(3000);

  // === Core ping function ===
  const check = useCallback(async () => {
    const start = performance.now();
    try {
      // Attempt to call the brainzOS root API route
      const res = await fetch("/api");
      const json = await res.json();
      const end = performance.now();

      // Measure latency
      const pingTime = Math.round(end - start);
      setLatency(pingTime);
      setLastPing(new Date().toISOString());

      if (json.message) {
        // Determine if latency is too high (for "Degraded" state)
        if (pingTime > 800) {
          setStatus("Degraded");
          if (verbose) console.warn(`[brainzOS] High latency detected: ${pingTime}ms`);
        } else {
          setStatus("Online");
        }

        // Reset fail count and restore default polling
        setFailCount(0);
        setIntervalMs(3000);
      }
    } catch (error) {
      // Network or server error
      setFailCount((prev) => prev + 1);

      // Switch to "Offline" after 2 consecutive failures
      if (failCount >= 2) {
        setStatus("Offline");
      }

      // Exponential backoff on repeated failures (up to 60s)
      const next = Math.min(3000 * Math.pow(2, failCount), 60000);
      setIntervalMs(next);

      if (verbose)
        console.error(
          `[brainzOS] Ping failed (${failCount}x). Next attempt in ${Math.round(next / 1000)}s.`
        );
    }
  }, [failCount, verbose]);

  // === Manual refresh function ===
  const refresh = useCallback(async () => {
    if (verbose) console.log("[brainzOS] Manual status refresh triggered.");
    await check();
  }, [check, verbose]);

  // === Auto polling effect ===
  useEffect(() => {
    check(); // Run once immediately
    const interval = setInterval(check, intervalMs); // Poll every N milliseconds
    return () => clearInterval(interval);
  }, [check, intervalMs]);

  // === Derived helper: color-coded severity level for UI components ===
  const getSeverityColor = useCallback(() => {
    switch (status) {
      case "Online":
        return "green";
      case "Degraded":
        return "orange";
      case "Offline":
        return "red";
      default:
        return "gray";
    }
  }, [status]);

  // === Derived helper: get human-readable summary string ===
  const summary = useCallback(() => {
    const latencyText = latency ? `${latency}ms` : "n/a";
    const last = lastPing ? new Date(lastPing).toLocaleTimeString() : "never";
    return `[${status}] • latency: ${latencyText} • last ping: ${last}`;
  }, [status, latency, lastPing]);

  // Return full state and helpers for UI or logic layers
  return {
    status,          // "Online" | "Offline" | "Degraded" | "Connecting..."
    latency,         // Latency in ms
    lastPing,        // ISO timestamp of last success
    failCount,       // Number of consecutive failures
    intervalMs,      // Current polling interval
    refresh,         // Manual refresh trigger
    getSeverityColor,// Function returning UI color hint
    summary,         // Text summary
  };
}
