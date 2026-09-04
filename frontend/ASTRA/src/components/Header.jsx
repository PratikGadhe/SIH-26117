import React from "react";
import {
  WifiOff,
  Cpu,
  Bell,
} from "lucide-react";

function Header({ title, description }) {
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
          <span className="header-status-dot"></span>
          <WifiOff size={14} />
          Offline
        </div>

        <div className="header-status">
          <span className="header-status-dot"></span>
          <Cpu size={14} />
          GPU Ready
        </div>

        <button className="notification-btn">
          <Bell size={18} />
        </button>

        <div className="user-avatar">
          SA
        </div>

      </div>

    </header>
  );
}

export default Header;