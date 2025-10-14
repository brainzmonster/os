// Import React state management
import { useEffect, useMemo, useRef, useState } from "react";
// Import brainzOS LLM query API function
import { queryLLM /*, streamQueryLLM (optional, if you enabled SSE) */ } from "@/api/llm";
// Import reusable output rendering component
import OutputBox from "@/components/OutputBox";

/**
 * QueryPage — power console for sending prompts to brainzOS.
 *
 * What's new (keeps existing behavior intact):
 * - Advanced controls: system prompt, temperature, max tokens
 * - Latency + token estimates (client-side heuristic)
 * - Draft persistence (localStorage) so your work survives reloads
 * - Keyboard shortcut: Ctrl/Cmd + Enter to send
 * - Copy / Clear / Export helpers
 * - Optional (non-breaking): streaming toggle if your API supports SSE
 *
 * Existing flow still works:
 * - You can just type a prompt and click "Send" to get a response
 * - Response text still renders through <OutputBox output={response} />
 */
export default function QueryPage() {
  // === Core state ===
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // === Advanced controls (all optional, safe defaults) ===
  const [systemPrompt, setSystemPrompt] = useState("");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(200);

  // === Meta / UX ===
  const [latencyMs, setLatencyMs] = useState(null);
  const [meta, setMeta] = useState(null); // store backend meta if provided
  const [stream, setStream] = useState(false); // optional streaming switch (uses non-breaking fallback)

  const inputRef = useRef(null);

  // === Derivations ===
  const charCount = prompt.length;
  const wordCount = useMemo(
    () => (prompt.trim() ? prompt.trim().split(/\s+/).length : 0),
    [prompt]
  );
  // Rough client-side token estimate (no tokenizer in the browser)
  const tokenEstimate = useMemo(() => Math.max(1, Math.ceil(charCount / 4)), [charCount]);

  // === Draft persistence ===
  useEffect(() => {
    const saved = localStorage.getItem("brainz.query.draft");
    const savedSys = localStorage.getItem("brainz.query.sys");
    if (saved) setPrompt(saved);
    if (savedSys) setSystemPrompt(savedSys);
  }, []);
  useEffect(() => {
    localStorage.setItem("brainz.query.draft", prompt);
  }, [prompt]);
  useEffect(() => {
    localStorage.setItem("brainz.query.sys", systemPrompt);
  }, [systemPrompt]);

  // === Keyboard shortcut: Ctrl/Cmd + Enter ===
  useEffect(() => {
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleQuery();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prompt, systemPrompt, temperature, maxTokens, stream]);

  // === Helpers ===
  const clearAll = () => {
    setPrompt("");
    setSystemPrompt("");
    setResponse("");
    setError(null);
    setMeta(null);
    setLatencyMs(null);
    if (inputRef.current) inputRef.current.focus();
  };

  const copyResponse = async () => {
    try {
      await navigator.clipboard.writeText(response || "");
    } catch {
      /* no-op */
    }
  };

  const exportJSON = () => {
    const payload = {
      timestamp: new Date().toISOString(),
      request: {
        prompt,
        system_prompt: systemPrompt || null,
        temperature,
        max_tokens: maxTokens,
      },
      response,
      meta,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.download = `brainz-query-${Date.now()}.json`;
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
  };

  // === Core: send prompt to backend ===
  const handleQuery = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setMeta(null);
    setLatencyMs(null);

    const options = {
      max_tokens: maxTokens,
      temperature,
      system_prompt: systemPrompt || undefined,
    };

    const t0 = performance.now();
    try {
      // If streaming is toggled AND you implemented streamQueryLLM on the client + server,
      // you can switch to that path. Otherwise we fall back to the regular query.
      if (stream && typeof /* streamQueryLLM */ undefined === "function") {
        // Example (commented-out to keep compatibility if you didn't wire SSE yet):
        // let full = "";
        // await streamQueryLLM(prompt, options, (chunk) => {
        //   full += chunk;
        //   setResponse(full);
        // });
        // setMeta({ streamed: true });
        // For now, fallback to plain call:
        const result = await queryLLM(prompt, options);
        setResponse(result.response || "");
        setMeta(result.meta || null);
      } else {
        const result = await queryLLM(prompt, options);
        setResponse(result.response || "");
        setMeta(result.meta || null);
      }

      const t1 = performance.now();
      setLatencyMs(Math.round(t1 - t0));
    } catch (e) {
      setError(e?.message || "Query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold">Query brainzOS</h1>
          <p className="text-gray-500 text-sm">
            Send prompts, inspect meta, and tune generation controls on the fly.
          </p>
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
            onClick={clearAll}
          >
            Clear
          </button>
          <button
            className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-60"
            onClick={copyResponse}
            disabled={!response}
            title={!response ? "Nothing to copy" : "Copy model output"}
          >
            Copy Output
          </button>
          <button
            className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-60"
            onClick={exportJSON}
            disabled={!response}
            title={!response ? "Nothing to export" : "Export as JSON"}
          >
            Export JSON
          </button>
        </div>
      </div>

      {/* System prompt (optional) */}
      <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt (optional)</label>
      <textarea
        value={systemPrompt}
        onChange={(e) => setSystemPrompt(e.target.value)}
        placeholder="You are a terse, technical assistant. Prefer precision over fluff…"
        className="w-full h-20 p-3 border rounded mb-4"
      />

      {/* Prompt input */}
      <label className="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
      <textarea
        ref={inputRef}
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        className="w-full h-32 p-3 border rounded"
        placeholder="Type your question or command..."
      />

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs text-gray-500 mt-1 mb-4">
        <span>
          {wordCount} words • ~{tokenEstimate} tokens • {charCount} chars
        </span>
        <span className="italic">Tip: press ⌘/Ctrl + Enter to send</span>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        {/* Temperature control */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="text-xs text-gray-500">Current: {temperature.toFixed(2)}</div>
        </div>

        {/* Max tokens */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
          <input
            type="number"
            min={1}
            max={1024}
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value || "1", 10))}
            className="w-full border rounded p-2"
          />
        </div>

        {/* Streaming toggle (optional, safe if not wired) */}
        <div className="flex items-center gap-2 pt-6">
          <input
            id="stream-toggle"
            type="checkbox"
            checked={stream}
            onChange={(e) => setStream(e.target.checked)}
          />
          <label htmlFor="stream-toggle" className="text-sm text-gray-700">
            Stream response (if supported)
          </label>
        </div>
      </div>

      {/* Submit button */}
      <button
        onClick={handleQuery}
        className="mt-2 px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-60"
        disabled={loading || !prompt.trim()}
        title="Send to LLM"
      >
        {loading ? "Loading..." : "Send"}
      </button>

      {/* Meta / latency */}
      <div className="mt-3 text-xs text-gray-500">
        {latencyMs !== null && <div>inference: {latencyMs} ms</div>}
        {meta?.total_tokens !== undefined && <div>tokens (in+out): {meta.total_tokens}</div>}
        {meta?.model && <div>model: {meta.model}</div>}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mt-3 p-3 rounded bg-red-50 text-red-700 text-sm border border-red-200">
          {error}
        </div>
      )}

      {/* Component to display the model's response */}
      <div className="mt-6">
        <OutputBox output={response} />
      </div>
    </div>
  );
}
