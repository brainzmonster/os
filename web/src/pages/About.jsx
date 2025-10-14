// Simple React component to display information about brainzOS
// Extended with live system version, team credits, feature list, and backend ping integration.
import { useStatusPing } from "@/hooks/useStatus";
import { useEffect, useState } from "react";

export default function AboutPage() {
  // Hook to get current backend connection status
  const { status, latency, lastPing, summary } = useStatusPing({ verbose: false });

  // Local state for version info fetched from the backend
  const [version, setVersion] = useState("loading...");
  const [features, setFeatures] = useState([]);

  // Fetch version and feature data on mount
  useEffect(() => {
    const fetchInfo = async () => {
      try {
        const res = await fetch("/api/info");
        if (!res.ok) throw new Error("Failed to fetch system info.");
        const data = await res.json();

        setVersion(data.version || "unknown");
        setFeatures(data.features || []);
      } catch (err) {
        console.error("[brainzOS] Failed to fetch info:", err);
        setVersion("unavailable");
      }
    };
    fetchInfo();
  }, []);

  return (
    <div className="p-6 max-w-3xl mx-auto text-gray-800">
      {/* Page title */}
      <h1 className="text-3xl font-bold mb-4 text-black">About brainzOS</h1>

      {/* Description of what brainzOS is and who it's for */}
      <p className="text-gray-700 mb-6">
        brainzOS is an autonomous AI operating system designed to think, learn, and evolve. 
        it’s built for degens, devs, and digital chaos architects who want to push AI into 
        uncharted territory — where data meets instinct and everything trains itself.
      </p>

      {/* System status section */}
      <div className="border-t border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-semibold mb-2">System Status</h2>
        <p>
          <strong>Status:</strong>{" "}
          <span
            className={`${
              status === "Online"
                ? "text-green-600"
                : status === "Degraded"
                ? "text-yellow-600"
                : "text-red-600"
            }`}
          >
            {status}
          </span>
        </p>
        <p>
          <strong>Latency:</strong> {latency ? `${latency} ms` : "N/A"}
        </p>
        <p>
          <strong>Last Ping:</strong> {lastPing ? new Date(lastPing).toLocaleTimeString() : "N/A"}
        </p>
        <p className="text-gray-500 text-sm mt-2">{summary()}</p>
      </div>

      {/* Version and feature list */}
      <div className="border-t border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-semibold mb-2">System Info</h2>
        <p>
          <strong>Version:</strong> {version}
        </p>
        {features.length > 0 ? (
          <ul className="list-disc ml-6 mt-2 text-gray-700">
            {features.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500 italic">No features listed yet.</p>
        )}
      </div>

      {/* Developer / Team credits */}
      <div className="border-t border-gray-300 pt-4 mt-6">
        <h2 className="text-xl font-semibold mb-2">Credits</h2>
        <p className="text-gray-700">
          Developed by the brainz dev collective — the ones who replaced caffeine with compute.
        </p>
        <p className="text-gray-500 mt-1 text-sm">
          Want to contribute? fork it, break it, fix it. <br />
          <a
            href="https://brainz.monster"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            brainz.monster
          </a>
        </p>
      </div>

      {/* Easter egg — small animated detail */}
      <div className="mt-8 text-center text-gray-500 text-xs italic animate-pulse">
        “the machine is still learning... maybe so are you.”
      </div>
    </div>
  );
}
