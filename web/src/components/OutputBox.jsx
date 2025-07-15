// OutputBox component: displays the LLM response passed via props
export default function OutputBox({ output }) {
  // If there's no output, don't render anything
  if (!output) return null;

  return (
    <div className="mt-4 p-4 bg-gray-100 border rounded shadow-sm">
      {/* Section title */}
      <h2 className="font-semibold mb-2">Model Output</h2>

      {/* Formatted output with preserved whitespace and line breaks */}
      <pre className="whitespace-pre-wrap break-words text-sm text-gray-800">
        {output}
      </pre>
    </div>
  );
}
