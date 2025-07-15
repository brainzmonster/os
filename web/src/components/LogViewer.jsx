// React hooks for local state and lifecycle effects
import { useState, useEffect } from "react";

// LogViewer component displays real-time system logs from brainzOS
export default function LogViewer() {
  // State to store the list of logs fetched from the API
  const [logs, setLogs] = useState([]);

  // useEffect runs once on component mount to set up polling
  useEffect(() => {
    // Poll the logs API every 3 seconds
    const interval = setInterval(() => {
      fetch("/api/system/logs")
        .then((res) => res.json())
        .then((data) => {
          // Validate response and update log state
          if (data && Array.isArray(data.logs)) setLogs(data.logs);
        })
        .catch(() => {}); // Silently ignore fetch errors
    }, 3000);

    // Cleanup interval when component unmounts
    return () => clearInterval(interval);
  }, []);

  // Render a styled scrollable log box
  return (
    <div className="mt-6 bg-black text-green-400 p-4 rounded text-sm h-60 overflow-y-scroll">
      <h2 className="font-bold text-white mb-2">brainz Logs</h2>
      <pre className="whitespace-pre-wrap">
        {logs.length > 0 ? logs.join("\n") : "Waiting for logs..."}
      </pre>
    </div>
  );
}
