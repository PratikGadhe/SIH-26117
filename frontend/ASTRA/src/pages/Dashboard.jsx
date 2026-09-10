import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  Brain,
  CheckCircle2,
  Clock3,
  Cpu,
  FileText,
  FolderOpen,
  History,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { getSystemStatus } from "../services/api";

const TASK_HISTORY_KEY = "astra_task_history";
const ACTIVE_TASK_KEY = "astra_active_task";

function getStoredRecentTasks() {
  try {
    const raw = localStorage.getItem(TASK_HISTORY_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed.slice(0, 5);
    }
  } catch {
    // Ignore storage parse errors
  }
  return [];
}

function formatRelativeTime(timestamp) {
  if (!timestamp) return "";
  const diffMs = Date.now() - timestamp;
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return new Date(timestamp).toLocaleDateString();
}

function Dashboard() {
  const navigate = useNavigate();
  const { user, token } = useAuth();

  // System status state: 'checking' | 'loaded' | 'error'
  const [statusState, setStatusState] = useState("checking");
  const [systemStatus, setSystemStatus] = useState(null);
  const [recentTasks, setRecentTasks] = useState(getStoredRecentTasks);

  const fetchStatus = useCallback(async () => {
    if (!token) return;
    setStatusState("checking");
    try {
      const data = await getSystemStatus(token);
      setSystemStatus(data);
      setStatusState("loaded");
    } catch {
      setStatusState("error");
      setSystemStatus(null);
    }
  }, [token]);

  useEffect(() => {
    let ignore = false;
    async function loadInitialStatus() {
      if (!token) return;
      try {
        const data = await getSystemStatus(token);
        if (!ignore) {
          setSystemStatus(data);
          setStatusState("loaded");
        }
      } catch {
        if (!ignore) {
          setStatusState("error");
          setSystemStatus(null);
        }
      }
    }
    loadInitialStatus();
    return () => {
      ignore = true;
    };
  }, [token]);

  // Keep recent tasks synced with localStorage
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
      localStorage.setItem(ACTIVE_TASK_KEY, JSON.stringify(task));
      window.dispatchEvent(new CustomEvent("astra_restore_task", { detail: task }));
    } catch {
      // Ignore
    }
    navigate("/workbench");
  };

  const handleStartNewTask = () => {
    try {
      localStorage.removeItem(ACTIVE_TASK_KEY);
    } catch {
      // Ignore
    }
    navigate("/workbench");
  };

  // Status helper badges
  const renderStatusBadge = (isOk, label) => {
    if (statusState === "checking") {
      return (
        <span className="status-pill status-checking">
          <Loader2 size={11} className="spin" /> Checking…
        </span>
      );
    }
    if (isOk) {
      return <span className="status-pill status-online">{label || "Available"}</span>;
    }
    return <span className="status-pill status-offline">{label || "Unavailable"}</span>;
  };

  const isBackendOnline = statusState === "loaded" && systemStatus?.backend?.status === "online";
  const isOllamaAvailable = statusState === "loaded" && systemStatus?.ollama?.status === "available";
  const isQwen3Available = Boolean(systemStatus?.models?.qwen3_4b?.available);
  const isQwen3VlAvailable = Boolean(systemStatus?.models?.qwen3_vl_4b?.available);

  return (
    <div className="dashboard">
      {/* Welcome Hero Section */}
      <section className="welcome-card">
        <div className="welcome-content">
          <div className="welcome-label">
            <ShieldCheck size={18} />
            <span>SOVEREIGN LOCAL AI ENVIRONMENT</span>
          </div>

          <h1>Welcome to ASTRA</h1>

          <div className="astra-full-name">
            Autonomous Secure Task-Reasoning Agent
          </div>

          <p>
            An air-gapped sovereign AI workbench designed for confidential industrial documents,
            schematic inspections, local RAG synthesis, and verifiable reasoning on on-premise hardware.
          </p>

          <div className="welcome-meta-user">
            Signed in as <strong>{user?.username || "authenticated user"}</strong> ({user?.role || "worker"})
          </div>

          <div className="welcome-actions">
            <button
              type="button"
              className="primary-welcome-btn"
              onClick={() => navigate("/workbench")}
            >
              Open AI Workbench
              <ArrowRight size={18} />
            </button>
            <button
              type="button"
              className="secondary-welcome-btn"
              onClick={handleStartNewTask}
            >
              <RefreshCw size={15} />
              Start New Task
            </button>
          </div>
        </div>

        <div className="welcome-visual">
          <div className="visual-circle">
            <Cpu size={54} />
          </div>
          <span>LOCAL RUNTIME</span>
        </div>
      </section>

      {/* SECTION 1 — REAL SYSTEM STATUS */}
      <section className="section">
        <div className="section-header">
          <div>
            <h2>System Status</h2>
            <p>Real-time availability of backend services and local on-device AI runtime.</p>
          </div>
          <button
            type="button"
            className="refresh-status-btn"
            onClick={fetchStatus}
            disabled={statusState === "checking"}
            title="Refresh system status check"
          >
            <RefreshCw size={13} className={statusState === "checking" ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>

        <div className="system-status-grid">
          {/* Backend API */}
          <div className="system-status-card">
            <div className="status-card-top">
              <div className="status-card-icon">
                <Server size={20} />
              </div>
              {renderStatusBadge(isBackendOnline, "Online")}
            </div>
            <div className="status-card-body">
              <strong>Backend Service</strong>
              <span>FastAPI gateway (port 8000)</span>
            </div>
          </div>

          {/* Ollama Daemon */}
          <div className="system-status-card">
            <div className="status-card-top">
              <div className="status-card-icon">
                <Cpu size={20} />
              </div>
              {renderStatusBadge(isOllamaAvailable, "Available")}
            </div>
            <div className="status-card-body">
              <strong>Local AI Runtime</strong>
              <span>Ollama Metal inference engine</span>
            </div>
          </div>

          {/* Qwen3 4B Model */}
          <div className="system-status-card">
            <div className="status-card-top">
              <div className="status-card-icon">
                <Brain size={20} />
              </div>
              {renderStatusBadge(isQwen3Available, isQwen3Available ? "Available" : "Not detected")}
            </div>
            <div className="status-card-body">
              <strong>Qwen3 4B Model</strong>
              <span>Text reasoning &amp; synthesis</span>
            </div>
          </div>

          {/* Qwen3-VL 4B Vision Model */}
          <div className="system-status-card">
            <div className="status-card-top">
              <div className="status-card-icon">
                <ImageIcon size={20} />
              </div>
              {renderStatusBadge(isQwen3VlAvailable, isQwen3VlAvailable ? "Available" : "Not detected")}
            </div>
            <div className="status-card-body">
              <strong>Qwen3-VL Vision</strong>
              <span>Multimodal visual inspection</span>
            </div>
          </div>

          {/* Local Processing Guarantee */}
          <div className="system-status-card">
            <div className="status-card-top">
              <div className="status-card-icon">
                <ShieldCheck size={20} />
              </div>
              <span className="status-pill status-airgap">Active</span>
            </div>
            <div className="status-card-body">
              <strong>Local Processing</strong>
              <span>Air-gapped execution reported</span>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2 — QUICK ACTIONS */}
      <section className="section">
        <div className="section-header">
          <div>
            <h2>Quick Actions</h2>
            <p>Direct entry points to sovereign ASTRA workspaces.</p>
          </div>
        </div>

        <div className="quick-actions-grid">
          <div
            className="quick-action-card"
            onClick={() => navigate("/workbench")}
            role="button"
            tabIndex={0}
          >
            <div className="quick-icon">
              <Bot size={24} />
            </div>
            <div className="quick-content">
              <h3>AI Workbench</h3>
              <p>Open the conversational workspace for text, image, and PDF queries.</p>
            </div>
            <ArrowRight className="quick-arrow" size={18} />
          </div>

          <div
            className="quick-action-card"
            onClick={handleStartNewTask}
            role="button"
            tabIndex={0}
          >
            <div className="quick-icon">
              <RefreshCw size={24} />
            </div>
            <div className="quick-content">
              <h3>Start New Task</h3>
              <p>Reset active session and start a fresh question or schematic analysis.</p>
            </div>
            <ArrowRight className="quick-arrow" size={18} />
          </div>

          <div
            className="quick-action-card"
            onClick={() => navigate("/files")}
            role="button"
            tabIndex={0}
          >
            <div className="quick-icon">
              <FolderOpen size={24} />
            </div>
            <div className="quick-content">
              <h3>Generated Files</h3>
              <p>View and download deliverables produced by ASTRA agents.</p>
            </div>
            <ArrowRight className="quick-arrow" size={18} />
          </div>
        </div>
      </section>

      {/* SECTION 3 — RECENT ACTIVITY */}
      <section className="section">
        <div className="section-header">
          <div>
            <h2>Recent Activity</h2>
            <p>Tasks executed in your local workbench session.</p>
          </div>
        </div>

        {recentTasks.length > 0 ? (
          <div className="recent-activity-grid">
            {recentTasks.map((task) => {
              const isPdf = task.fileType === "pdf" || task.fileName?.toLowerCase().endsWith(".pdf");
              const isImage = task.hasImage || task.fileType === "image";

              return (
                <div
                  key={task.id || `${task.timestamp}-${task.query}`}
                  className="recent-activity-card"
                  onClick={() => handleSelectRecent(task)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="recent-card-header">
                    <div className="recent-card-type">
                      {isPdf ? (
                        <span className="recent-badge badge-pdf">
                          <FileText size={12} /> PDF
                        </span>
                      ) : isImage ? (
                        <span className="recent-badge badge-image">
                          <ImageIcon size={12} /> IMAGE
                        </span>
                      ) : (
                        <span className="recent-badge badge-chat">
                          <Bot size={12} /> CHAT
                        </span>
                      )}
                      {task.result?.task_type && (
                        <span className="recent-task-tag">{task.result.task_type}</span>
                      )}
                    </div>
                    <span className="recent-card-time">
                      <Clock3 size={11} /> {formatRelativeTime(task.timestamp)}
                    </span>
                  </div>

                  <div className="recent-card-query" title={task.query}>
                    {task.query}
                  </div>

                  {task.fileName && (
                    <div className="recent-card-file">
                      <FileText size={12} />
                      <span>{task.fileName}</span>
                    </div>
                  )}

                  <div className="recent-card-footer">
                    <span>Resume task</span>
                    <ArrowRight size={13} />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="recent-activity-empty">
            <div className="empty-icon-wrap">
              <History size={26} />
            </div>
            <div className="empty-text">
              <strong>No recent activity yet</strong>
              <p>Execute your first task or attach an engineering document in the AI Workbench.</p>
            </div>
            <button
              type="button"
              className="empty-action-btn"
              onClick={() => navigate("/workbench")}
            >
              Open AI Workbench
            </button>
          </div>
        )}
      </section>

      {/* SECTION 4 — VERIFIED CAPABILITIES */}
      <section className="section">
        <div className="section-header">
          <div>
            <h2>Verified Capabilities</h2>
            <p>Features implemented, tested, and actively supported in this deployment.</p>
          </div>
        </div>

        <div className="capabilities-grid">
          <div className="capability-card">
            <div className="capability-header">
              <CheckCircle2 size={16} className="capability-check" />
              <strong>Text Reasoning &amp; QA</strong>
            </div>
            <p>Direct chat and multi-agent reasoning powered by local Qwen3 4B on Apple Silicon Metal.</p>
          </div>

          <div className="capability-card">
            <div className="capability-header">
              <CheckCircle2 size={16} className="capability-check" />
              <strong>Schematic Vision Inspection</strong>
            </div>
            <p>Visual component identification in P&amp;ID engineering diagrams powered by local Qwen3-VL.</p>
          </div>

          <div className="capability-card">
            <div className="capability-header">
              <CheckCircle2 size={16} className="capability-check" />
              <strong>Multimodal PDF Analysis</strong>
            </div>
            <p>Native text, structure, and table extraction from uploaded PDF documents via PyMuPDF.</p>
          </div>

          <div className="capability-card">
            <div className="capability-header">
              <CheckCircle2 size={16} className="capability-check" />
              <strong>ChromaDB Vector RAG</strong>
            </div>
            <p>Local knowledge base retrieval with verified source document citations and distances.</p>
          </div>

          <div className="capability-card">
            <div className="capability-header">
              <CheckCircle2 size={16} className="capability-check" />
              <strong>Air-Gapped Sovereign Design</strong>
            </div>
            <p>Zero external API calls or telemetry. Complete isolation on on-premise hardware.</p>
          </div>

          <div className="capability-card">
            <div className="capability-header">
              <CheckCircle2 size={16} className="capability-check" />
              <strong>Multi-Agent LangGraph</strong>
            </div>
            <p>Deterministic supervisor routing with transparent execution activity traces and audit trails.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
