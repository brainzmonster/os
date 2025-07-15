// Import React hooks for local state management
import { useState } from "react";
// Import the brainz API client for querying the LLM
import { queryLLM } from "@/api/llm";

// Custom React hook for interacting with the brainzOS language model
export function useLLM() {
  // Holds the model's response after a prompt
  const [output, setOutput] = useState("");
  // Tracks the loading state while waiting for the response
  const [loading, setLoading] = useState(false);

  // Sends a prompt to brainz's backend and stores the response
  const ask = async (input, options = {}) => {
    setLoading(true); // Set loading before the request starts
    const res = await queryLLM(input, options); // Query LLM via API
    setOutput(res.response); // Store the generated text in output state
    setLoading(false); // Reset loading state after response
  };

  // Expose model output, loading state, and ask function for components
  return { output, ask, loading };
}
