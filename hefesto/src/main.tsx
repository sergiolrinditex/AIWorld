import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { initTeams } from "./lib/teams";

// Initialize Teams SDK (no-op if not running inside Teams)
initTeams().then((inTeams) => {
  if (inTeams) {
    console.log("[Hefesto] Running inside Microsoft Teams");
  }
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
