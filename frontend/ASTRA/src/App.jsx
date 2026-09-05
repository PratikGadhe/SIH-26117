import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";

import MainLayout from "./layout/MainLayout";
import ProtectedRoute from "./components/ProtectedRoute";

import Dashboard from "./pages/Dashboard";
import DocumentAnalysis from "./pages/DocumentAnalysis";
import GeneratedFiles from "./pages/GeneratedFiles";
import Workbench from "./pages/Workbench";
import Login from "./pages/Login";
import UnavailableFeature from "./pages/UnavailableFeature";


function App() {
  return (
    <BrowserRouter>

      <Routes>
        <Route path="/login" element={<Login />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<MainLayout />}>

          <Route
            path="/"
            element={<Dashboard />}
          />

          <Route
            path="/workbench"
            element={<Workbench />}
          />

          <Route
            path="/documents"
            element={<DocumentAnalysis />}
          />

          <Route
            path="/knowledge"
            element={(
              <UnavailableFeature
                title="Knowledge Base Management"
                description="The previous document counts, uploads, and search results were frontend-only sample data."
                requirement="document catalog, controlled ingestion, and authenticated retrieval APIs"
              />
            )}
          />

          <Route
            path="/agent"
            element={(
              <UnavailableFeature
                title="Agent Execution Monitor"
                description="The previous timeline and tool calls were timer-driven and did not represent backend execution."
                requirement="execution event or job-status APIs; text execution is available in the Workbench"
              />
            )}
          />

          <Route
            path="/files"
            element={<GeneratedFiles />}
          />

          <Route
            path="/chatbot"
            element={(
              <UnavailableFeature
                title="Chat Assistant"
                description="The previous chat conversation and tool activity were simulated. Use the connected stateless Workbench instead."
                requirement="conversation/session persistence if a multi-turn chat experience is required"
              />
            )}
          />

          </Route>
        </Route>

      </Routes>

    </BrowserRouter>
  );
}

export default App;
