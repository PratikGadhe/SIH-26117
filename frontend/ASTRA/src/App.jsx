import React from "react";
import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";

import MainLayout from "./layout/MainLayout";

import Dashboard from "./pages/Dashboard";
import Workbench from "./pages/Workbench";
import DocumentAnalysis from "./pages/DocumentAnalysis";
import KnowledgeBase from "./pages/KnowledgeBase";
import AgentExecution from "./pages/AgentExecution";
import GeneratedFiles from "./pages/GeneratedFiles";
import Chatbot from "./pages/Chatbot";


function App() {
  return (
    <BrowserRouter>

      <Routes>

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
            element={<KnowledgeBase />}
          />

          <Route
            path="/agent"
            element={<AgentExecution />}
          />

          <Route
            path="/files"
            element={<GeneratedFiles />}
          />

          <Route
            path="/chatbot"
            element={<Chatbot />}
          />

        </Route>

      </Routes>

    </BrowserRouter>
  );
}

export default App;