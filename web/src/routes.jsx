// Import routing components from React Router DOM
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
// Import individual page components used in routing
import TrainPage from "./pages/Train";
import AboutPage from "./pages/About";
import HomePage from "./pages/Home";

// Main routing configuration for brainzOS frontend
export default function AppRoutes() {
  return (
    <Router>
      <Routes>
        {/* Route for landing page */}
        <Route path="/" element={<HomePage />} />
        {/* Route for LLM training interface */}
        <Route path="/train" element={<TrainPage />} />
        {/* Route for project description / about section */}
        <Route path="/about" element={<AboutPage />} />
      </Routes>
    </Router>
  );
}
