// Import Link component from React Router to enable client-side navigation
import { Link } from "react-router-dom";

// Main landing page for brainzOS
export default function HomePage() {
  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Page title */}
      <h1 className="text-3xl font-bold mb-4">Welcome to brainzOS</h1>

      {/* Short introduction describing the OS */}
      <p className="text-gray-700 mb-6">
        This is a next-gen LLM Operating System focused on crypto, tech, and autonomous learning. Navigate to the train panel to get started.
      </p>

      {/* CTA button linking to the training interface */}
      <Link
        to="/train"
        className="inline-block bg-blue-600 text-white px-4 py-2 rounded shadow"
      >
        Start Training
      </Link>
    </div>
  );
}
