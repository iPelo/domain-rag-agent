import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The browser calls the app under the `/api` prefix; Vite proxies those calls
// to the FastAPI backend in development so no CORS configuration is required.
// Override the backend target with VITE_BACKEND_URL when needed.
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
