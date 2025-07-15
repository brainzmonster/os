// Import React's useState hook to manage local state
import { useState } from "react";
// Import the training API function from brainzOS client
import { trainLLM } from "../api/train";

// Button component to trigger fine-tuning of the model using provided texts
export default function TrainingButton({ texts }) {
  // State to track current status message
  const [status, setStatus] = useState(null);
  // State to manage loading indicator
  const [loading, setLoading] = useState(false);

  // Handle the training request on button click
  const handleTrain = async () => {
    // Validate input: at least one training sample must be provided
    if (!Array.isArray(texts) || texts.length === 0) {
      alert("Please provide at least one training text.");
      return;
    }

    setLoading(true);    // Show loading spinner
    setStatus(null);     // Reset status

    try {
      // Call brainzOS backend API to fine-tune the model
      const res = await trainLLM(texts);
      // Display success message from API response
      setStatus(res.message);
    } catch (err) {
      // Handle error (log can be checked in browser dev tools)
      setStatus("Training failed. Check console.");
    } finally {
      // Reset loading state after API completes
      setLoading(false);
    }
  };

  // Render training button and optional status message
  return (
    <div className="mt-4">
      <button
        onClick={handleTrain}
        disabled={loading}
        className="px-4 py-2 bg-green-600 text-white rounded"
      >
        {loading ? "Training..." : "Train brainzOS"}
      </button>
      {status && <p className="mt-2 text-sm text-gray-700">{status}</p>}
    </div>
  );
}
