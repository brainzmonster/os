// React hook for local state management
import { useState } from "react";
// Input field component to type user prompts
import TextInput from "../components/TextInput";
// Training button component to trigger fine-tuning
import TrainingButton from "../components/TrainingButton";
// Component to render model response
import OutputBox from "../components/OutputBox";

// Page for training or querying the brainzOS LLM manually
export default function TrainPage() {
  // Store user input for training or querying
  const [inputText, setInputText] = useState("");
  // Store output result from the model
  const [output, setOutput] = useState("");

  // Sends a POST request to the LLM API with the user-provided inputText
  const handleSend = async () => {
    const res = await fetch("/api/llm/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: inputText }),
    });
    const data = await res.json(); // Parse response from backend
    setOutput(data.response);      // Update output state
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      {/* Page title */}
      <h1 className="text-2xl font-bold mb-4">Train brainzOS</h1>

      {/* Input field for typing prompts or training data */}
      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="Enter your training or query prompt..."
        className="w-full h-40 p-3 border rounded mb-4"
      />

      {/* Action buttons: query model + train model */}
      <div className="flex gap-4">
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded"
          onClick={handleSend}
        >
          Run Query
        </button>
        {/* Pass current inputText as training data */}
        <TrainingButton texts={[inputText]} />
      </div>

      {/* Render model output below the buttons */}
      <OutputBox output={output} />
    </div>
  );
}
