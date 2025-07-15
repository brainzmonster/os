// Import React state hooks
import { useState } from "react";
// Import the LLM training API client from brainz's frontend API layer
import { trainLLM } from "@/api/llm";

// Custom React hook for triggering LLM training and tracking status
export function useTrain() {
  // Status message returned after training (e.g., success or error)
  const [status, setStatus] = useState(null);
  // Boolean to indicate if training is currently in progress
  const [loading, setLoading] = useState(false);

  // Main training function
  // Accepts a list of input texts and sends them to the brainz training endpoint
  const train = async (texts) => {
    setLoading(true); // Begin loading state
    try {
      const res = await trainLLM(texts);  // Call backend training API
      setStatus(res.message);             // Set response status message
    } catch (err) {
      setStatus("Training failed");       // Fallback error status
    } finally {
      setLoading(false); // Reset loading state after completion
    }
  };

  // Expose the train function along with current status and loading state
  return { train, status, loading };
}
