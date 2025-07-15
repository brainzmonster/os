// Import Axios for making HTTP requests to the backend API
import axios from "axios";

// Send a prompt to the LLM query endpoint and return the generated response
export async function queryLLM(input, options = {}) {
  const payload = {
    input,                                       // User input / prompt
    max_tokens: options.max_tokens || 100,       // Default to 100 tokens
    temperature: options.temperature || 0.7,     // Default temperature
  };

  // POST the query to the brainz API
  const res = await axios.post("/api/llm/query", payload);

  // Return the API response
  return res.data;
}

// Send training texts to fine-tune the model via the backend API
export async function trainLLM(texts) {
  const res = await axios.post("/api/llm/train", { texts });
  return res.data;
}
