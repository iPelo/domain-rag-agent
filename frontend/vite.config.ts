import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The browser calls the app under the `/api` prefix; Vite proxies those calls
// to the FastAPI backend in development so no CORS configuration is required.
// Override the backend target with VITE_BACKEND_URL when needed.
// Dev server config. The key part is the proxy: browser calls to /api are forwarded
// to the FastAPI backend (default :8000) and the /api prefix is stripped, so
// there's no CORS setup and the frontend never needs to know the backend's real
// port.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
