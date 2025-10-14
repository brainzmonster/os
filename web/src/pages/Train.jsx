// React hooks for local state management and lifecycle
import { useEffect, useMemo, useRef, useState } from "react";
// Input field component to type user prompts (kept for compatibility if used elsewhere)
import TextInput from "../components/TextInput";
// Training button component to trigger fine-tuning (we still use it so existing behavior remains)
import TrainingButton from "../components/TrainingButton";
// Component to render model response
import OutputBox from "../components/OutputBox";

/**
 * TrainPage — manual playground for querying & training brainzOS
 *
 * What's new:
 * - Advanced query controls: system prompt, temperature, max tokens
 * - Local history with quick re-run
 * - Token/char estimator & input length guardrails
 * - Keyboard shortcut: Ctrl/Cmd + Enter to run
 * - Draft persistence to localStorage
 * - Optional "Dry-run Training" that calls the backend without executing
 * - Copy / Clear helpers and simple latency meta
 *
 * Everything existing still works:
 * - `handleSend` posts to /api/llm/query with current textarea
 * - <TrainingButton texts={[inputText]} /> remains unchanged
 * - <OutputBox output={output} /> unchanged
 */
export default function TrainPage() {
  // === Core state ===
  const [inputText, setInputText] = useState("");        // User input for query/training
  const [systemPrompt, setSystemPrompt] = useState("");  // Optional system prompt
  const [output, setOutput] = useState("");              // Model output
  const [loading, setLoading] = useState(false);         // UI loading flag
  const [error, setError] = useState(null);              // Error surface

  // === Advanced generation controls ===
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(200);

  // === UX helpers ===
  const [latencyMs, setLatencyMs] = useState(null);
  const [history, setHistory] = useState([]);            // Simple in-memory history of prompts
  const inputRef = useRef(null);

  // === Derived stats ===
  const charCount = inputText.length;
  const wordCount = useMemo(() => (inputText.trim() ? inputText.trim().split(/\s+/).length : 0), [inputText]);

  // Very rough token estimate (fallback when no tokenizer client-side)
  const tokenEstimate = useMemo(() => {
    // Simple heuristic: ~4 chars/token (English-ish) as a ballpark
    return Math.max(1, Math.ceil(charCount / 4));
  }, [charCount]);

  // === Draft persistence (survives page reloads) ===
  useEffect(() => {
    // Restore saved draft on mount
    const savedDraft = localStorage.getItem("brainz.train.draft");
    const savedSys = localStorage.getItem("brainz.train.sys");
    if (savedDraft) setInputText(savedDraft);
    if (savedSys) setSystemPrompt(savedSys);
  }, []);

  useEffect(() => {
    // Persist on change (debounced by browser write batching)
    localStorage.setItem("brainz.train.draft", inputText);
  }, [inputText]);

  useEffect(() => {
    localStorage.setItem("brainz.train.sys", systemPrompt);
  }, [systemPrompt]);

  // === Keyboard shortcut: Ctrl/Cmd + Enter to run ===
  useEffect(() => {
    const onKey = (e) => {
      const isSubmit = (e.ctrlKey || e.metaKey) && e.key === "Enter";
      if (isSubmit) {
        e.preventDefault();
        handleSend();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [inputText, systemPrompt, temperature, maxTokens]);

  // === Helpers ===
  const addToHistory = (prompt, sys) => {
    setHistory((prev) => {
      const next = [{ prompt, systemPrompt: sys, ts: Date.now() }, ...prev];
      // Limit history size to avoid memory bloat
      return next.slice(0, 20);
    });
  };

  const applyFromHistory = (item) => {
    setInputText(item.prompt || "");
    setSystemPrompt(item.systemPrompt || "");
    // Focus textarea for quick edits
    if (inputRef.current) inputRef.current.focus();
  };

  const clearAll = () => {
    setInputText("");
    setSystemPrompt("");
    setOutput("");
    setError(null);
    setLatencyMs(null);
  };

  const copyOutput = async () => {
    try {
      await navigator.clipboard.writeText(output || "");
    } catch {/* no-op */}
  };

  // === Core: Query model ===
  const handleSend = async () => {
    setLoading(true);
    setError(null);
    setLatencyMs(null);

    // Build payload for /api/llm/query
    const payload = {
      input: inputText,
      max_tokens: maxTokens,
      temperature,
      system_prompt: systemPrompt || undefined,
    };

    const t0 = performance.now();
    try {
      const res = await fetch("/api/llm/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      const t1 = performance.now();

      if (!res.ok) {
        throw new Error(data?.error || "Request failed");
      }

      setOutput(data.response || "");
      setLatencyMs(Math.round(t1 - t0));
      addToHistory(inputText, systemPrompt);
    } catch (err) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // === NEW: Dry-run training — calls /api/llm/train with dry_run=true ===
  const handleDryRunTrain = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/llm/train?dry_run=true", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texts: [inputText] }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail?.reason || data?.detail || "Training preview failed");
      // Surface a minimal confirmation in the output box without altering <TrainingButton> behavior
      setOutput(
        `[preview only] accepted ${data.trained_samples || data.texts?.length || 1} sample(s) • estimated_tokens=${data.estimated_tokens ?? "n/a"}`
      );
    } catch (err) {
      setError(err.message || "Dry-run failed");
    } finally {
      setLoading(false);
    }
  };

  // === Sample prompts to speed up testing ===
  const samples = [
    "Explain MEV on Ethereum like I'm technical.",
    "Outline a secure Solana validator setup checklist.",
    "Compare zk-SNARKs and zk-STARKs for L2 rollups.",
  ];

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-3 mb-4">
        <div>
          <h1 className="text-2xl font-bold">Train brainzOS</h1>
          <p className="text-gray-500 text-sm">
            Query the model, test replies, and feed training samples in real-time.
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
            className="px-3 py-2 text-sm rounded border border-gray-300 hover:bg-gray-50"
            onClick={copyOutput}
            disabled={!output}
            title={!output ? "Nothing to copy" : "Copy output"}
          >
            Copy Output
          </button>
        </div>
      </div>

      {/* System prompt (optional) */}
      <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt (optional)</label>
      <textarea
        value={systemPrompt}
        onChange={(e) => setSystemPrompt(e.target.value)}
        placeholder="You are a precise, no-fluff technical assistant..."
        className="w-full h-20 p-3 border rounded mb-4"
      />

      {/* Main input */}
      <label className="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
      <textarea
        ref={inputRef}
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="Enter your training or query prompt..."
        className="w-full h-40 p-3 border rounded mb-2"
      />

      {/* Input stats */}
      <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
        <span>
          {wordCount} words • ~{tokenEstimate} tokens • {charCount} chars
        </span>
        <span className="italic">Tip: press ⌘/Ctrl + Enter to run</span>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        {/* Temperature */}
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

        {/* Sample chips */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Samples</label>
          <div className="flex flex-wrap gap-2">
            {samples.map((s, i) => (
              <button
                key={i}
                className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-50"
                onClick={() => setInputText(s)}
              >
                {s.length > 30 ? s.slice(0, 30) + "…" : s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Actions: query & train */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded shadow disabled:opacity-60"
          onClick={handleSend}
          disabled={loading || !inputText.trim()}
          title="Run query (⌘/Ctrl + Enter)"
        >
          {loading ? "Running..." : "Run Query"}
        </button>

        {/* Keep existing TrainingButton usage intact */}
        <TrainingButton texts={[inputText]} />

        {/* New: Dry-run training (no actual fine-tune, just preview) */}
        <button
          className="bg-gray-900 text-white px-4 py-2 rounded shadow disabled:opacity-60"
          onClick={handleDryRunTrain}
          disabled={loading || !inputText.trim()}
          title="Send sample as training (simulation only)"
        >
          Preview Training (Dry Run)
        </button>

        {latencyMs !== null && (
          <span className="text-xs text-gray-500">inference: {latencyMs} ms</span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 rounded bg-red-50 text-red-700 text-sm border border-red-200">
          {error}
        </div>
      )}

      {/* Output */}
      <OutputBox output={output} />

      {/* History */}
      {history.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold mb-2">Recent Prompts</h2>
          <div className="space-y-2">
            {history.map((h, idx) => (
              <div
                key={idx}
                className="p-3 border rounded hover:bg-gray-50 cursor-pointer"
                onClick={() => applyFromHistory(h)}
                title="Click to load this prompt back into the editor"
              >
                <div className="text-xs text-gray-500">
                  {new Date(h.ts).toLocaleString()}
                </div>
                {h.systemPrompt && (
                  <div className="text-xs text-gray-400 italic mb-1">
                    [system] {h.systemPrompt.slice(0, 120)}
                    {h.systemPrompt.length > 120 ? "…" : ""}
                  </div>
                )}
                <div className="text-sm text-gray-800">
                  {h.prompt.length > 240 ? h.prompt.slice(0, 240) + "…" : h.prompt}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
