// React hooks for state and side effects
import { useEffect, useState } from "react";

// Custom hook to check brainzOS backend status
export function useStatusPing() {
  // Holds the current connection status: "Connecting...", "Online", or "Offline"
  const [status, setStatus] = useState("Connecting...");

  // useEffect runs once on mount to start polling
  useEffect(() => {
    // Function to ping the backend API and check connectivity
    const check = async () => {
      try {
        // Attempt to call the brainzOS root API route
        const res = await fetch("/api");
        const json = await res.json();
        // If API responds with a valid message, set status to Online
        if (json.message) setStatus("Online");
      } catch {
        // If request fails, mark as Offline
        setStatus("Offline");
      }
    };

    check(); // Run once immediately
    const interval = setInterval(check, 3000); // Poll every 3 seconds

    // Clear polling interval when component unmounts
    return () => clearInterval(interval);
  }, []);

  // Return current backend status to consuming component
  return status;
}
