import React, { useEffect, useState } from "react";
import {
  Cpu,
  Bell,
  LogOut,
  Server,
  Sun,
  Moon,
} from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { useTheme } from "../context/useTheme";
import { getHealth } from "../services/api";

function Header({ title, description }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [backendAvailable, setBackendAvailable] = useState(null);

  useEffect(() => {
    let active = true;
    getHealth()
      .then(() => {
        if (active) setBackendAvailable(true);
      })
      .catch(() => {
        if (active) setBackendAvailable(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <header className="header">

      <div className="header-left">

        <div className="header-title">
          {title}
        </div>

        <div className="header-description">
          {description}
        </div>

      </div>


      <div className="header-right">

        <div className="header-status">
          <span className={`header-status-dot ${backendAvailable === false ? "unavailable" : ""}`}></span>
          <Server size={14} />
          {backendAvailable === null
            ? "Checking API"
            : backendAvailable
              ? "Backend online"
              : "Backend unavailable"}
        </div>

        <div className="header-status">
          <Cpu size={14} />
          Model runtime not reported
        </div>

        <button
          type="button"
          className="notification-btn theme-toggle-btn"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        <button className="notification-btn" title="Notifications" aria-label="Notifications">
          <Bell size={18} />
        </button>

        <div className="header-user" title={`${user?.username} (${user?.role})`}>
          <div className="user-avatar">
            {user?.username?.slice(0, 2).toUpperCase() || "--"}
          </div>
          <span>{user?.role}</span>
        </div>

        <button className="notification-btn" onClick={logout} title="Sign out" aria-label="Sign out">
          <LogOut size={18} />
        </button>

      </div>

    </header>
  );
}

export default Header;
