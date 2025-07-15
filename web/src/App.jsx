// Import application route configuration
import AppRoutes from "./routes";

// Import global top navigation bar component
import Header from "./components/Header";

// Import global styles (Tailwind-based)
import "./styles/globals.css";

// Main application wrapper for brainzOS
export default function App() {
  return (
    <div className="min-h-screen bg-white text-black">
      {/* Persistent header across all pages */}
      <Header />

      {/* Dynamic content rendered based on current route */}
      <main>
        <AppRoutes />
      </main>
    </div>
  );
}
