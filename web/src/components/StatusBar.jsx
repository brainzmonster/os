// Import React hooks for state and lifecycle handling
import { useState, useEffect } from "react";

// StatusBar component for brainzOS
// It pings the backend API periodically and displays the connection status
export default function StatusBar() {
  // Initialize connection status with default value
  const [status, setStatus] = useState("Connecting...");

  // useEffect runs once on component mount
  useEffect(() => {
    // Check connectivity with the brainzOS backend
    const check = async () => {
      try {
        // Send a GET request to the root API endpoint
        const res = await fetch("/api");
        const json = await res.json();
        // If response is valid and includes message, mark as Online
        if (json.message) setStatus("Online");
      } catch {
        // If request fails, mark as Offline
        setStatus("Offline");
      }
    };

    check(); // Initial status check

    // Set up polling every 3 seconds
    const interval = setInterval(check, 3000);

    // Clear interval when component unmounts
    return () => clearInterval(interval);
  }, []);

  // Render the floating status bar in bottom-right corner
  return (
    <div className="fixed bottom-4 right-4 px-3 py-1 rounded bg-black text-white text-xs shadow">
      brainzOS: {status}
    </div>
  );
}
