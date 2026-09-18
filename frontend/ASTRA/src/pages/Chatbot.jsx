import React, { useEffect, useRef, useState } from "react";
import {
  Bot,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Database,
  FileSearch,
  Paperclip,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Wrench,
  X,
} from "lucide-react";
import "./Chatbot.css";

const initialMessages = [
  {
    id: 1,
    role: "assistant",
    text:
      "Hello! I am VYASA, your secure local AI assistant. I can analyze documents, search your internal knowledge base, and execute multi-step tasks without sending your data to external services.",
    time: "Now",
  },
];

const suggestions = [
  {
    title: "Search an SOP",
    text: "Find the safety procedure for equipment inspection.",
    icon: Search,
  },
  {
    title: "Analyze a document",
    text: "Analyze the inspection report and list the key findings.",
    icon: FileSearch,
  },
  {
    title: "Draft a report",
    text: "Prepare an approval note from the latest inspection findings.",
    icon: Wrench,
  },
];

const defaultActivity = [
  { label: "Understanding request", status: "pending", icon: Sparkles },
  { label: "Searching ChromaDB", status: "pending", icon: Database },
  { label: "Retrieved relevant context", status: "pending", icon: Search },
  { label: "Reasoning with local LLM", status: "pending", icon: Bot },
  { label: "Preparing response", status: "pending", icon: Wrench },
];

function Chatbot() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [activity, setActivity] = useState(defaultActivity);
  const [toolCalls, setToolCalls] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [showSources, setShowSources] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!running) return;

    timerRef.current = setInterval(() => {
      setElapsed((value) => value + 0.1);
    }, 100);

    return () => clearInterval(timerRef.current);
  }, [running]);

  useEffect(() => {
    return () => clearInterval(timerRef.current);
  }, []);

  const updateActivity = (index, status) => {
    setActivity((items) =>
      items.map((item, i) => (i === index ? { ...item, status } : item))
    );
  };

  const runAssistant = (userText) => {
    const cleanText = userText.trim();
    if (!cleanText || running) return;

    setMessages((items) => [
      ...items,
      {
        id: Date.now(),
        role: "user",
        text: cleanText,
        attachment: attachedFile?.name || null,
        time: "Now",
      },
    ]);

    setInput("");
    setAttachedFile(null);
    setRunning(true);
    setElapsed(0);
    setToolCalls(0);
    setShowSources(false);
    setActivity(defaultActivity.map((item) => ({ ...item, status: "pending" })));

    const steps = [
      { index: 0, delay: 350, calls: 0 },
      { index: 1, delay: 900, calls: 1 },
      { index: 2, delay: 1500, calls: 2 },
      { index: 3, delay: 2200, calls: 3 },
      { index: 4, delay: 2900, calls: 4 },
    ];

    steps.forEach(({ index, delay, calls }) => {
      setTimeout(() => {
        updateActivity(index, "running");
        setToolCalls(calls);
      }, delay);

      setTimeout(() => {
        updateActivity(index, "done");
      }, delay + 420);
    });

    setTimeout(() => {
      clearInterval(timerRef.current);
      setRunning(false);
      setToolCalls(4);
      setShowSources(true);

      setMessages((items) => [
        ...items,
        {
          id: Date.now() + 1,
          role: "assistant",
          text:
            "I processed your request using VYASA's local agent workflow. The relevant internal knowledge was retrieved and used as context for the response. This demo is currently running with simulated local-agent behavior; the FastAPI + ChromaDB + local LLM backend can be connected next.",
          sources: [
            "Safety_SOP.pdf",
            "Equipment_Manual.pdf",
            "Maintenance_Guide.pdf",
          ],
          time: `${elapsed.toFixed(1)}s`,
        },
      ]);
    }, 3450);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    runAssistant(input);
  };

  const handleNewChat = () => {
    clearInterval(timerRef.current);
    setMessages(initialMessages);
    setInput("");
    setRunning(false);
    setElapsed(0);
    setToolCalls(0);
    setShowSources(false);
    setAttachedFile(null);
    setActivity(defaultActivity);
  };

  return (
    <div className="chatbot-page">
      <section className="chat-hero">
        <div>
          <span className="eyebrow">SECURE AGENTIC AI ASSISTANT</span>
          <h1>VYASA Assistant</h1>
          <p>
            Ask VYASA to search internal knowledge, analyze documents, and
            execute multi-step tasks using local AI tools.
          </p>
        </div>
        <div className="local-badge">
          <ShieldCheck size={17} />
          <span>Local Mode</span>
          <span className="status-dot" />
        </div>
      </section>

      <div className="chat-workspace">
        <section className="chat-panel">
          <div className="chat-panel-header">
            <div className="assistant-identity">
              <div className="assistant-avatar">
                <Bot size={21} />
              </div>
              <div>
                <h2>VYASA</h2>
                <span>Vision-augmented Yield & Agentic Synthesis Architecture</span>
              </div>
            </div>

            <button className="new-chat-btn" onClick={handleNewChat}>
              <Plus size={16} />
              New Chat
            </button>
          </div>

          <div className="messages">
            {messages.map((message) => (
              <div key={message.id} className={`message-row ${message.role}`}>
                <div className="message-avatar">
                  {message.role === "assistant" ? <Bot size={17} /> : "SA"}
                </div>

                <div className="message-content">
                  <div className="message-meta">
                    <strong>{message.role === "assistant" ? "VYASA" : "You"}</strong>
                    <span>{message.time}</span>
                  </div>

                  <div className="message-bubble">
                    <p>{message.text}</p>

                    {message.attachment && (
                      <div className="message-attachment">
                        <Paperclip size={14} />
                        {message.attachment}
                      </div>
                    )}

                    {message.sources && (
                      <div className="source-box">
                        <button
                          className="source-toggle"
                          onClick={() => setShowSources((value) => !value)}
                        >
                          <Database size={15} />
                          Retrieved 3 internal sources
                          <ChevronRight
                            size={15}
                            className={showSources ? "rotate" : ""}
                          />
                        </button>

                        {showSources && (
                          <div className="source-list">
                            {message.sources.map((source) => (
                              <div className="source-item" key={source}>
                                <CheckCircle2 size={14} />
                                <span>{source}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {running && (
              <div className="message-row assistant">
                <div className="message-avatar">
                  <Bot size={17} />
                </div>
                <div className="message-content">
                  <div className="message-meta">
                    <strong>VYASA</strong>
                    <span>Working...</span>
                  </div>
                  <div className="thinking-bubble">
                    <span />
                    <span />
                    <span />
                    VYASA is processing your request locally
                  </div>
                </div>
              </div>
            )}
          </div>

          {messages.length === 1 && (
            <div className="suggestion-area">
              <div className="suggestion-title">Try asking VYASA</div>
              <div className="suggestion-grid">
                {suggestions.map(({ title, text, icon: Icon }) => (
                  <button
                    className="suggestion-card"
                    key={title}
                    onClick={() => runAssistant(text)}
                  >
                    <span className="suggestion-icon">
                      <Icon size={17} />
                    </span>
                    <span>
                      <strong>{title}</strong>
                      <small>{text}</small>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <form className="composer" onSubmit={handleSubmit}>
            {attachedFile && (
              <div className="attachment-chip">
                <Paperclip size={14} />
                {attachedFile.name}
                <button
                  type="button"
                  onClick={() => setAttachedFile(null)}
                  aria-label="Remove attachment"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            <div className="composer-row">
              <label className="attach-btn" title="Attach document">
                <Paperclip size={19} />
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.xlsx,.csv"
                  onChange={(event) =>
                    setAttachedFile(event.target.files?.[0] || null)
                  }
                />
              </label>

              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask VYASA to analyze, search, reason, or create..."
                disabled={running}
              />

              <button
                className="send-btn"
                type="submit"
                disabled={!input.trim() || running}
                title="Send"
              >
                <Send size={18} />
              </button>
            </div>

            <div className="composer-note">
              <ShieldCheck size={13} />
              Your data stays inside the local VYASA environment.
            </div>
          </form>
        </section>

        <aside className="activity-panel">
          <div className="activity-header">
            <div>
              <span className="eyebrow">LIVE MONITOR</span>
              <h2>Agent Activity</h2>
            </div>
            <span className={`activity-status ${running ? "active" : ""}`}>
              <span />
              {running ? "Running" : "Idle"}
            </span>
          </div>

          <div className="activity-card">
            {activity.map(({ label, status, icon: Icon }, index) => (
              <div className={`activity-step ${status}`} key={label}>
                <div className="activity-line">
                  {status === "done" ? (
                    <CheckCircle2 size={17} />
                  ) : status === "running" ? (
                    <span className="spinner" />
                  ) : (
                    <span className="step-number">{index + 1}</span>
                  )}
                </div>
                <div className="activity-step-text">
                  <span>{label}</span>
                  {status === "done" && <small>Completed</small>}
                  {status === "running" && <small>In progress...</small>}
                </div>
                <Icon size={16} />
              </div>
            ))}
          </div>

          <div className="metrics-card">
            <div className="metric">
              <span>Tool calls</span>
              <strong>{toolCalls}</strong>
            </div>
            <div className="metric">
              <span>Execution</span>
              <strong>{elapsed.toFixed(1)}s</strong>
            </div>
            <div className="metric">
              <span>External calls</span>
              <strong>0</strong>
            </div>
            <div className="metric">
              <span>Cloud models</span>
              <strong>0</strong>
            </div>
          </div>

          <div className="security-card">
            <div className="security-icon">
              <ShieldCheck size={20} />
            </div>
            <div>
              <strong>Sovereign execution</strong>
              <p>Requests are designed to stay within your organization's local environment.</p>
            </div>
          </div>

          <div className="architecture-mini">
            <div className="mini-title">AGENT PIPELINE</div>
            <span>User Request</span>
            <ChevronRight size={14} />
            <span>RAG</span>
            <ChevronRight size={14} />
            <span>Tools</span>
            <ChevronRight size={14} />
            <span>Local LLM</span>
          </div>

          <div className="last-run">
            <Clock3 size={15} />
            <span>Ready for next task</span>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default Chatbot;
