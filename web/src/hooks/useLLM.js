// Import React hooks for local state and effects
import { useState, useCallback, useEffect } from "react";
// Import the brainz API client for querying the LLM
import { queryLLM } from "@/api/llm";

/**
 * Custom React hook for interacting with the brainzOS language model.
 * Keeps the original structure but adds:
 * - Streaming response support
 * - Token usage tracking
 * - Error handling and retries
 * - Auto-scroll-ready updates for chat UIs
 * - Session and metadata logging
 */
export function useLLM() {
  // Holds the model's response after a prompt
  const [output, setOutput] = useState("");

  // Tracks the loading state while waiting for the response
  const [loading, setLoading] = useState(false);

  // Tracks any error message from the API
  const [error, setError] = useState(null);

  // Holds model metadata (token counts, inference time, etc.)
  const [meta, setMeta] = useState(null);

  // Tracks ongoing response streaming (if enabled)
  const [isStreaming, setIsStreaming] = useState(false);

  // Logs multiple queries/responses for chat-like interfaces
  const [history, setHistory] = useState([]);

  // Optional retry counter for failed queries
  const [retries, setRetries] = useState(0);

  // === Core ask() function ===
  // Sends a prompt to brainzOS and stores the response
  const ask = useCallback(
    async (input, options = {}) => {
      if (!input || typeof input !== "string" || input.trim().length === 0) {
        setError("Prompt cannot be empty.");
        return;
      }

      setLoading(true);
      setError(null);
      setIsStreaming(false);
      setMeta(null);

      try {
        // Query the LLM via backend API
        const res = await queryLLM(input, options);

        // Store response and metadata
        setOutput(res.response || "");
        setMeta(res.meta || null);

        // Add this interaction to the history
        setHistory((prev) => [
          ...prev,
          {
            id: res.session_id || crypto.randomUUID(),
            input,
            output: res.response,
            timestamp: res.meta?.timestamp || new Date().toISOString(),
            tokens: res.meta?.total_tokens || null,
            model: res.meta?.model || "unknown",
          },
        ]);
      } catch (err) {
        console.error("[brainzOS] Query failed:", err);
        setError(err.message || "An unexpected error occurred.");
        setRetries((r) => r + 1);
      } finally {
        setLoading(false);
        setIsStreaming(false);
      }
    },
    []
  );

  // === New: streamAsk() ===
  // Optional streaming response handler (if backend supports SSE or WebSocket)
  const streamAsk = useCallback(
    async (input, { onChunk, onComplete, temperature = 0.7 } = {}) => {
      if (!input) return;
      setLoading(true);
      setIsStreaming(true);
      setError(null);

      try {
        const res = await fetch("/api/llm/query-stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input, temperature }),
        });

        if (!res.ok || !res.body) throw new Error("Streaming not supported.");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullText = "";

        // Read the response stream in chunks
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          fullText += chunk;
          setOutput((prev) => prev + chunk);
          onChunk?.(chunk);
        }

        setIsStreaming(false);
        onComplete?.(fullText);
      } catch (err) {
        console.error("[brainzOS] Stream failed:", err);
        setError(err.message);
      } finally {
        setLoading(false);
        setIsStreaming(false);
      }
    },
    []
  );

  // === New: reset state ===
  const reset = useCallback(() => {
    setOutput("");
    setError(null);
    setMeta(null);
    setHistory([]);
    setRetries(0);
    setIsStreaming(false);
  }, []);

  // === Auto-log if output updates ===
  useEffect(() => {
    if (output && !loading) {
      console.debug("[brainzOS] Output updated:", output.slice(0, 80));
    }
  }, [output, loading]);

  // === New: Re-run last query (if failed) ===
  const retryLast = useCallback(() => {
    const last = history[history.length - 1];
    if (last) ask(last.input);
  }, [history, ask]);

  // Expose everything for the consuming component
  return {
    output,           // Latest LLM output
    meta,             // Token + performance info
    error,            // Last error message
    loading,          // Request in progress
    isStreaming,      // Whether currently streaming
    history,          // All past prompts/responses
    retries,          // How many times retried
    ask,              // Main LLM query method
    streamAsk,        // Streaming version of ask()
    retryLast,        // Retry last failed query
    reset,            // Reset all local state
  };
}
