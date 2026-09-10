import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Bot,
  FileText,
  FolderOpen,
  ShieldCheck,
  History,
  Trash2,
  Image as ImageIcon,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

function getStoredRecentTasks() {
  try {
    const raw = localStorage.getItem("astra_task_history");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.slice(0, 5);
    }
  } catch {
    // Ignore parse errors
  }
  return [];
}

function Sidebar() {
  const navigate = useNavigate();
  const [recentTasks, setRecentTasks] = useState(getStoredRecentTasks);

  useEffect(() => {
    const handleUpdate = () => {
      setRecentTasks(getStoredRecentTasks());
    };

    window.addEventListener("astra_history_updated", handleUpdate);
    window.addEventListener("storage", handleUpdate);

    return () => {
      window.removeEventListener("astra_history_updated", handleUpdate);
      window.removeEventListener("storage", handleUpdate);
    };
  }, []);

  const handleSelectRecent = (task) => {
    try {
      localStorage.setItem("astra_active_task", JSON.stringify(task));
      window.dispatchEvent(new CustomEvent("astra_restore_task", { detail: task }));
    } catch {
      // Ignore storage error
    }
    navigate("/workbench");
  };

  const handleClearHistory = (e) => {
    e.stopPropagation();
    try {
      localStorage.removeItem("astra_task_history");
    } catch {
      // Ignore
    }
    setRecentTasks([]);
  };

  const menuItems = [
    {
      name: "Dashboard",
      path: "/",
      icon: <LayoutDashboard size={18} />,
    },
    {
      name: "AI Workbench",
      path: "/workbench",
      icon: <Bot size={18} />,
    },
    {
      name: "Generated Files",
      path: "/files",
      icon: <FolderOpen size={18} />,
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
          <div className="logo-title">ASTRA</div>
          <div className="logo-subtitle">
            Autonomous Secure Task-Reasoning Agent
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="sidebar-section-title">WORKSPACE</div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink key={item.path} to={item.path}>
            {item.icon}
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* Recent Tasks */}
      {recentTasks.length > 0 && (
        <div className="sidebar-recent-section">
          <div className="sidebar-recent-header">
            <span className="sidebar-section-title recent-title">
              <History size={12} /> RECENT
            </span>
            <button
              type="button"
              className="clear-recent-btn"
              onClick={handleClearHistory}
              title="Clear recent history"
              aria-label="Clear recent history"
            >
              <Trash2 size={12} />
            </button>
          </div>

          <div className="sidebar-recent-list">
            {recentTasks.map((task) => (
              <button
                key={task.id || `${task.timestamp}-${task.query}`}
                type="button"
                className="sidebar-recent-item"
                onClick={() => handleSelectRecent(task)}
                title={task.query}
              >
                {task.hasImage ? <ImageIcon size={13} /> : <FileText size={13} />}
                <span className="recent-item-text">{task.query}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Bottom */}
      <div className="sidebar-bottom">
        <div className="local-mode">
          <span className="local-mode-dot" />
          <span>Local API</span>
        </div>

        <div className="system-secured">Authenticated session</div>
      </div>
    </aside>
  );
}

export default Sidebar;
