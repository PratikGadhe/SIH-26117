import React from "react";
import {
  LayoutDashboard,
  Bot,
  FileText,
  Database,
  Cpu,
  FolderOpen,
  ShieldCheck,
} from "lucide-react";

import { NavLink } from "react-router-dom";

function Sidebar() {
  const menuItems = [
    {
      name: "Dashboard",
      path: "/",
      icon: <LayoutDashboard size={20} />,
    },
    {
      name: "AI Workbench",
      path: "/workbench",
      icon: <Bot size={20} />,
    },
    {
      name: "Document Analysis",
      path: "/documents",
      icon: <FileText size={20} />,
    },
    {
      name: "Knowledge Base",
      path: "/knowledge",
      icon: <Database size={20} />,
    },
    {
      name: "Agent Execution",
      path: "/agent",
      icon: <Cpu size={20} />,
    },
    {
      name: "Generated Files",
      path: "/files",
      icon: <FolderOpen size={20} />,
    },
  ];

  return (
    <aside className="sidebar">

      {/* Logo */}
      <div className="sidebar-logo">

        <div className="logo-icon">
          <ShieldCheck size={22} />
        </div>

        <div className="logo-text">
          <div className="logo-title">
            ASTRA
          </div>

          <div className="logo-subtitle">
            Autonomous Secure Task-Reasoning Agent
          </div>
        </div>

      </div>

      {/* Navigation */}
      <div className="sidebar-section-title">
        WORKSPACE
      </div>

      <nav className="sidebar-nav">

        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
          >
            {item.icon}
            <span>{item.name}</span>
          </NavLink>
        ))}

      </nav>

      {/* Bottom */}
      <div className="sidebar-bottom">

        <div className="local-mode">
          <span className="local-mode-dot"></span>
          <span>Local Mode</span>
        </div>

        <div className="system-secured">
          System secured
        </div>

      </div>

    </aside>
  );
}

export default Sidebar;