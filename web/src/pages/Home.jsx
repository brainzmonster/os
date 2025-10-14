// Import React hooks for dynamic updates
import { useEffect, useState } from "react";
// Import Link for client-side routing
import { Link } from "react-router-dom";
// Import the custom hook for backend status
import { useStatusPing } from "@/hooks/useStatus";

/**
 * Main landing page for brainzOS
 * Extended to include:
 * - Live backend status
 * - Animated hero banner with gradient text
 * - Quick access cards for key areas (Train, Query, Logs, Docs)
 * - System version fetched from API
 * - Subtle real-time ping updates
 */
export default function HomePage() {
  // Hook to monitor backend status and latency
  const { status, latency, getSeverityColor } = useStatusPing();

  // Local state for system info fetched from backend
  const [version, setVersion] = useState("loading...");
  const [uptime, setUptime] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(true);

  // Fetch additional system information on mount
  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        const res = await fetch("/api/info");
        const data = await res.json();
        setVersion(data.version || "unavailable");
        setUptime(data.uptime || "N/A");
      } catch (err) {
        console.error("[brainzOS] Failed to fetch system info:", err);
        setVersion("error");
      } finally {
        setLoadingInfo(false);
      }
    };
    fetchSystemInfo();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto text-gray-800">
      {/* Hero section */}
      <div className="text-center mb-10">
        <h1 className="text-5xl font-extrabold bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 bg-clip-text text-transparent mb-4">
          Welcome to brainzOS
        </h1>
        <p className="text-gray-600 text-lg">
          the autonomous ai operating system built for devs, researchers, and degen innovators.
        </p>
      </div>

      {/* System status display */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 rounded-full shadow-sm">
          <span className="font-semibold">Status:</span>
          <span
            className={`font-semibold capitalize`}
            style={{ color: getSeverityColor() }}
          >
            {status}
          </span>
          {latency && (
            <span className="text-sm text-gray-500">
              ({latency} ms)
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-2">
          {loadingInfo
            ? "Loading system details..."
            : `Version ${version} • Uptime: ${uptime}`}
        </p>
      </div>

      {/* Short intro */}
      <p className="text-gray-700 text-center mb-8 leading-relaxed">
        brainzOS combines real-time fine-tuning, semantic memory, and self-learning agents — 
        all packed into one modular LLM infrastructure. connect your brain to the machine and start training your own.
      </p>

      {/* Quick navigation cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        {/* Train card */}
        <Link
          to="/train"
          className="block bg-blue-600 hover:bg-blue-700 text-white p-5 rounded-xl shadow transition"
        >
          <h2 className="text-xl font-semibold mb-2">Train the Model</h2>
          <p className="text-sm text-blue-100">
            Feed prompts and datasets to evolve the core model in real-time.
          </p>
        </Link>

        {/* Query card */}
        <Link
          to="/query"
          className="block bg-gray-900 hover:bg-black text-white p-5 rounded-xl shadow transition"
        >
          <h2 className="text-xl font-semibold mb-2">Query brainzOS</h2>
          <p className="text-sm text-gray-300">
            Interact directly with the model and test how it responds to prompts.
          </p>
        </Link>

        {/* Logs card */}
        <Link
          to="/logs"
          className="block bg-green-600 hover:bg-green-700 text-white p-5 rounded-xl shadow transition"
        >
          <h2 className="text-xl font-semibold mb-2">System Logs</h2>
          <p className="text-sm text-green-100">
            View detailed backend logs, prompt histories, and system activity.
          </p>
        </Link>

        {/* Docs card */}
        <a
          href="https://brainz.gitbook.io/os"
          target="_blank"
          rel="noopener noreferrer"
          className="block bg-purple-600 hover:bg-purple-700 text-white p-5 rounded-xl shadow transition"
        >
          <h2 className="text-xl font-semibold mb-2">Read the Docs</h2>
          <p className="text-sm text-purple-100">
            Dive into the architecture, API reference, and integration guides.
          </p>
        </a>
      </div>

      {/* Call to action footer */}
      <div className="text-center mt-12">
        <Link
          to="/train"
          className="inline-block bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-3 rounded-lg shadow-lg font-semibold hover:opacity-90 transition"
        >
          Start Training Now
        </Link>

        <p className="mt-4 text-sm text-gray-500 italic">
          “every prompt teaches the machine something new.”
        </p>
      </div>
    </div>
  );
}
