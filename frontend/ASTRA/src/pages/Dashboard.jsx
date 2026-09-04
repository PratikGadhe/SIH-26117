import React from "react";
import {
  FileText,
  Bot,
  FolderOpen,
  Database,
  ArrowRight,
  ShieldCheck,
  Server,
  WifiOff,
  Cpu,
  Activity,
} from "lucide-react";

function Dashboard() {
  const stats = [
    {
      title: "Documents",
      value: "24",
      icon: <FileText size={24} />,
      description: "Processed documents",
    },
    {
      title: "AI Tasks",
      value: "12",
      icon: <Bot size={24} />,
      description: "Completed tasks",
    },
    {
      title: "Generated Files",
      value: "18",
      icon: <FolderOpen size={24} />,
      description: "AI generated files",
    },
    {
      title: "Knowledge Sources",
      value: "156",
      icon: <Database size={24} />,
      description: "Indexed sources",
    },
  ];

  const quickActions = [
    {
      title: "AI Workbench",
      description: "Start a new AI task",
      icon: <Bot size={25} />,
      path: "/workbench",
    },
    {
      title: "Analyze Document",
      description: "Upload and analyze documents",
      icon: <FileText size={25} />,
      path: "/documents",
    },
    {
      title: "Knowledge Base",
      description: "Search internal knowledge",
      icon: <Database size={25} />,
      path: "/knowledge",
    },
  ];

  return (
    <div className="dashboard">

      {/* Welcome Section */}
      <section className="welcome-card">

        <div className="welcome-content">

          <div className="welcome-label">
            <ShieldCheck size={18} />
            <span>SECURE LOCAL AI ENVIRONMENT</span>
          </div>

          <h1>
            Welcome to ASTRA
          </h1>

          <div className="astra-full-name">
            Autonomous Secure Task-Reasoning Agent
          </div>

          <p>
            A secure, on-premise AI agent designed for confidential
            industrial documents, intelligent automation, multimodal
            analysis, and AI-powered decision support.
          </p>

          <button
            className="primary-welcome-btn"
            onClick={() => (window.location.href = "/workbench")}
          >
            Open AI Workbench
            <ArrowRight size={18} />
          </button>

        </div>

        <div className="welcome-visual">

          <div className="visual-circle">
            <Cpu size={60} />
          </div>

          <span>ASTRA AI</span>

        </div>

      </section>


      {/* Statistics */}
      <section className="section">

        <div className="section-header">

          <div>
            <h2>System Overview</h2>

            <p>
              Current activity across your ASTRA environment.
            </p>
          </div>

        </div>


        <div className="stats-grid">

          {stats.map((stat, index) => (

            <div
              className="stat-card"
              key={index}
            >

              <div className="stat-icon">
                {stat.icon}
              </div>

              <div className="stat-info">

                <span>
                  {stat.title}
                </span>

                <strong>
                  {stat.value}
                </strong>

                <small>
                  {stat.description}
                </small>

              </div>

            </div>

          ))}

        </div>

      </section>


      {/* Quick Actions */}
      <section className="section">

        <div className="section-header">

          <div>

            <h2>
              Quick Actions
            </h2>

            <p>
              Access ASTRA's core AI capabilities.
            </p>

          </div>

        </div>


        <div className="quick-actions-grid">

          {quickActions.map((action, index) => (

            <div
              className="quick-action-card"
              key={index}
              onClick={() =>
                (window.location.href = action.path)
              }
            >

              <div className="quick-icon">
                {action.icon}
              </div>

              <div className="quick-content">

                <h3>
                  {action.title}
                </h3>

                <p>
                  {action.description}
                </p>

              </div>

              <ArrowRight
                className="quick-arrow"
                size={20}
              />

            </div>

          ))}

        </div>

      </section>


      {/* Security Status */}
      <section className="security-card">

        <div className="security-header">

          <div className="security-title">

            <div className="security-main-icon">
              <ShieldCheck size={27} />
            </div>

            <div>

              <h2>
                ASTRA Security Status
              </h2>

              <p>
                Your data and AI processing remain inside
                the local infrastructure.
              </p>

            </div>

          </div>


          <div className="secure-badge">

            <span className="status-dot"></span>

            System Secure

          </div>

        </div>


        <div className="security-grid">

          <div className="security-item">

            <div className="security-item-icon">
              <WifiOff size={22} />
            </div>

            <div>

              <span>
                External API Calls
              </span>

              <strong>
                0
              </strong>

            </div>

          </div>


          <div className="security-item">

            <div className="security-item-icon">
              <Server size={22} />
            </div>

            <div>

              <span>
                Cloud Models
              </span>

              <strong>
                0
              </strong>

            </div>

          </div>


          <div className="security-item">

            <div className="security-item-icon">
              <Activity size={22} />
            </div>

            <div>

              <span>
                Network Requests
              </span>

              <strong>
                0
              </strong>

            </div>

          </div>


          <div className="security-item">

            <div className="security-item-icon">
              <Cpu size={22} />
            </div>

            <div>

              <span>
                Local Models
              </span>

              <strong>
                3
              </strong>

            </div>

          </div>

        </div>

      </section>

    </div>
  );
}

export default Dashboard;