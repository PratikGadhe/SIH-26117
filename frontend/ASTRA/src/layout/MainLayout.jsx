import React from "react";
import { Outlet, useLocation } from "react-router-dom";

import Sidebar from "../components/Sidebar";
import Header from "../components/Header";

function MainLayout() {
  const location = useLocation();

  const pageInfo = {

    "/": {
      title: "ASTRA Dashboard",
      description:
        "Autonomous Secure Task-Reasoning Agent",
    },

    "/workbench": {
      title: "ASTRA AI Workbench",
      description:
        "Run intelligent tasks using secure local AI models",
    },

    "/documents": {
      title: "Document Analysis",
      description:
        "Analyze confidential documents using ASTRA",
    },

    "/knowledge": {
      title: "Knowledge Base",
      description:
        "Search your internal knowledge securely",
    },

    "/agent": {
      title: "Agent Execution",
      description:
        "Monitor ASTRA agents and tool execution",
    },

    "/files": {
      title: "Generated Files",
      description:
        "View and manage ASTRA-generated deliverables",
    },

    "/chatbot": {
      title: "ASTRA Assistant",
      description:
        "Conversation mode is not connected in Phase 9A",
    },

  };

  const currentPage =
    pageInfo[location.pathname] || pageInfo["/"];

  return (
    <div className="app-layout">

      <Sidebar />

      <div className="main-area">

        <Header
          title={currentPage.title}
          description={currentPage.description}
        />

        <main className="page-content">

          <Outlet />

        </main>

      </div>

    </div>
  );
}

export default MainLayout;
