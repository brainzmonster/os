// Import Axios for making HTTP requests
import axios from "axios";

// Sends a request to fine-tune the LLM using provided training texts
export async function trainLLM(texts = []) {
  // Validate that the input is a non-empty array of strings
  if (!Array.isArray(texts) || texts.length === 0) {
    throw new Error("Training data must be a non-empty array of strings.");
  }

  try {
    // Send POST request to brainzOS training endpoint
    const response = await axios.post("/api/llm/train", { texts });

    // Return the response data from the server
    return response.data;

  } catch (error) {
    // Log error to console and re-throw it for the UI or caller to handle
    console.error("[brainzOS] Training failed:", error);
    throw error;
  }
}
