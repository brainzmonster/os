// Import Vite configuration utilities
import { defineConfig } from "vite";

// Enable React support (JSX, fast refresh, etc.)
import react from "@vitejs/plugin-react";

// Node.js path module for resolving file paths
import path from "path";

// Export Vite config
export default defineConfig({
  // Register Vite plugins (React in this case)
  plugins: [react()],

  // Define custom path aliases (e.g. @ -> /src)
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },

  // Dev server configuration
  server: {
    port: 3000, // Run dev server on localhost:3000

    // Proxy API requests to the backend server (FastAPI on port 8000)
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
 