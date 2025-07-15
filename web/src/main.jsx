// Import React core libraries
import React from "react";
import ReactDOM from "react-dom/client";

// Import main App component that contains global routes/layout
import App from "./App";

// Create the React root using the #root element from index.html
const root = ReactDOM.createRoot(document.getElementById("root"));

// Render the application wrapped in React.StrictMode for development warnings
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
