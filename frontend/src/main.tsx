import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import "./styles.css";

// The app's entry point: find the <div id="root"> in index.html
// and render <App> into it. StrictMode adds dev-only checks (it
// intentionally double-invokes some logic in development).
const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root not found.");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
