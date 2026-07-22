import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { applyTheme } from "./store/store";
import "./styles/tokens.css";
import "./styles/app.css";

applyTheme(localStorage.getItem("pitchsmith.theme") || "apricot");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
