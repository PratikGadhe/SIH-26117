import { useState, useRef, useEffect, useCallback } from "react";
import {
  Brain,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock3,
  Copy,
  Database,
  FileText,
  Image as ImageIcon,
  Loader2,
  Paperclip,
  RefreshCw,
  Send,
  ShieldCheck,
  TriangleAlert,
  X,
} from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { ApiError, runAgent } from "../services/api";
import "./Workbench.css";

const ALLOWED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

const ACTIVE_TASK_KEY = "astra_active_task";
const TASK_HISTORY_KEY = "astra_task_history";

// Compact suggestion chips for empty state
const PROMPT_CHIPS = [
  {
    icon: <FileText size={14} />,
    label: "OneDrive Security Rules",
    query:
      "According to the OneDrive manual, what are the security rules and procedures for cloud storage?",
  },
  {
    icon: <ImageIcon size={14} />,
    label: "Inspect P&ID Diagram",
    query:
      "Analyze this diagram. Identify the visible components, labels, and important connections. Only report observations supported by the image.",
  },
  {
    icon: <Database size={14} />,
    label: "Safe Operating Limits",
    query:
      "What are the safe operating procedures and compliance limits documented in the knowledge base?",
  },
  {
    icon: <Brain size={14} />,
    label: "Process Safety Protocol",
    query:
      "Evaluate engineering risks and operational safety protocols for refinery process equipment.",
  },
];

// Lightweight, XSS-safe Markdown Formatter for ASTRA responses
function parseInline(text) {
  const parts = [];
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push({ type: "bold", content: token.slice(2, -2) });
    } else if (token.startsWith("`")) {
      parts.push({ type: "code", content: token.slice(1, -1) });
    } else if (token.startsWith("*")) {
      parts.push({ type: "italic", content: token.slice(1, -1) });
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push({ type: "text", content: text.slice(lastIndex) });
  }

  return parts;
}

function renderInline(text, keyPrefix = "") {
  const parts = parseInline(text);
  return parts.map((part, idx) => {
    const key = `${keyPrefix}-${idx}`;
    if (part.type === "bold") {
      return <strong key={key}>{part.content}</strong>;
    }
    if (part.type === "code") {
      return <code key={key} className="md-inline-code">{part.content}</code>;
    }
    if (part.type === "italic") {
      return <em key={key}>{part.content}</em>;
    }
    return part.content;
  });
}

function MarkdownRenderer({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements = [];
  let currentList = null;
  let inCodeBlock = false;
  let codeLines = [];

  const flushList = (key) => {
    if (!currentList) return;
    if (currentList.type === "bullet") {
      elements.push(
        <ul key={key} className="md-ul">
          {currentList.items.map((it, i) => (
            <li key={`ul-li-${i}`}>{renderInline(it, `ul-${i}`)}</li>
          ))}
        </ul>
      );
    } else if (currentList.type === "numbered") {
      elements.push(
        <ol key={key} className="md-ol">
          {currentList.items.map((it, i) => (
            <li key={`ol-li-${i}`}>{renderInline(it, `ol-${i}`)}</li>
          ))}
        </ol>
      );
    }
    currentList = null;
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // Code block toggle
    if (trimmed.startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${i}`} className="md-code-block">
            <code>{codeLines.join("\n")}</code>
          </pre>
        );
        codeLines = [];
        inCodeBlock = false;
      } else {
        flushList(`list-before-code-${i}`);
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(rawLine);
      continue;
    }

    // Blank line
    if (!trimmed) {
      flushList(`list-before-blank-${i}`);
      continue;
    }

    // Headings
    if (/^#{1,4}\s/.test(trimmed)) {
      flushList(`list-before-h-${i}`);
      const level = trimmed.match(/^#+/)[0].length;
      const headingText = trimmed.replace(/^#+\s*/, "");
      if (level === 1) {
        elements.push(<h2 key={`h1-${i}`} className="md-h1">{renderInline(headingText, `h1-${i}`)}</h2>);
      } else if (level === 2) {
        elements.push(<h3 key={`h2-${i}`} className="md-h2">{renderInline(headingText, `h2-${i}`)}</h3>);
      } else {
        elements.push(<h4 key={`h3-${i}`} className="md-h3">{renderInline(headingText, `h3-${i}`)}</h4>);
      }
      continue;
    }

    // Horizontal Rule
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
      flushList(`list-before-hr-${i}`);
      elements.push(<hr key={`hr-${i}`} className="md-hr" />);
      continue;
    }

    // Bullet List (- or * or •)
    const bulletMatch = trimmed.match(/^[-*•]\s+(.*)$/);
    if (bulletMatch) {
      if (!currentList || currentList.type !== "bullet") {
        flushList(`list-before-ul-${i}`);
        currentList = { type: "bullet", items: [] };
      }
      currentList.items.push(bulletMatch[1]);
      continue;
    }

    // Numbered List (1. 2. etc)
    const numMatch = trimmed.match(/^\d+\.\s+(.*)$/);
    if (numMatch) {
      if (!currentList || currentList.type !== "numbered") {
        flushList(`list-before-ol-${i}`);
        currentList = { type: "numbered", items: [] };
      }
      currentList.items.push(numMatch[1]);
      continue;
    }

    // Regular Paragraph
    flushList(`list-before-p-${i}`);
    elements.push(
      <p key={`p-${i}`} className="md-p">
        {renderInline(trimmed, `p-${i}`)}
      </p>
    );
  }

  flushList("list-final");
  if (inCodeBlock && codeLines.length) {
    elements.push(
      <pre key="code-final" className="md-code-block">
        <code>{codeLines.join("\n")}</code>
      </pre>
    );
  }

  return <div className="md-container">{elements}</div>;
}

function Workbench() {
  const { token, user, logout } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);

  // Active task state with client-side localStorage persistence
  const [submittedQuery, setSubmittedQuery] = useState(() => {
    try {
      const saved = localStorage.getItem(ACTIVE_TASK_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.query || "";
      }
    } catch {
      // Ignore parse error
    }
    return "";
  });

  const [submittedFileName, setSubmittedFileName] = useState(() => {
    try {
      const saved = localStorage.getItem(ACTIVE_TASK_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.fileName || "";
      }
    } catch {
      // Ignore
    }
    return "";
  });

  const [submittedFilePreview, setSubmittedFilePreview] = useState(() => {
    try {
      const saved = localStorage.getItem(ACTIVE_TASK_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.filePreview || null;
      }
    } catch {
      // Ignore
    }
    return null;
  });

  const [result, setResult] = useState(() => {
    try {
      const saved = localStorage.getItem(ACTIVE_TASK_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.result || null;
      }
    } catch {
      // Ignore
    }
    return null;
  });

  const [error, setError] = useState("");

  // Accordion toggles
  const [showSteps, setShowSteps] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const [copied, setCopied] = useState(false);

  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (isRunning || result) {
      scrollToBottom();
    }
  }, [isRunning, result, scrollToBottom]);

  // Listen to external restore events (from Sidebar history clicks)
  useEffect(() => {
    const handleRestore = (event) => {
      const task = event.detail;
      if (!task) return;
      setSubmittedQuery(task.query || "");
      setSubmittedFileName(task.fileName || "");
      setSubmittedFilePreview(task.filePreview || null);
      setResult(task.result || null);
      setError("");
      setPrompt("");
      setSelectedFile(null);
      setFilePreview(null);
    };

    window.addEventListener("astra_restore_task", handleRestore);
    return () => {
      window.removeEventListener("astra_restore_task", handleRestore);
    };
  }, []);

  const handleFileSelect = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const lowerName = file.name.toLowerCase();
    const isValidExtension = ALLOWED_IMAGE_EXTENSIONS.some((ext) =>
      lowerName.endsWith(ext)
    );

    if (!isValidExtension) {
      setError("Unsupported file format. Please attach a PNG, JPG, JPEG, or WEBP image.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setError("File exceeds maximum permitted size of 10 MB.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setError("");
    setSelectedFile(file);

    // Read preview as Data URL so it can be safely persisted across page reloads
    const reader = new FileReader();
    reader.onload = () => {
      setFilePreview(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setFilePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleResetTask = () => {
    try {
      localStorage.removeItem(ACTIVE_TASK_KEY);
    } catch {
      // Ignore
    }
    setSubmittedQuery("");
    setSubmittedFilePreview(null);
    setSubmittedFileName("");
    setResult(null);
    setError("");
    setPrompt("");
    handleRemoveFile();
    if (textareaRef.current) textareaRef.current.focus();
  };

  const persistTask = (query, file, previewData, agentResult) => {
    const sessionData = {
      id: Date.now().toString(),
      query,
      hasImage: Boolean(file),
      fileName: file?.name || "",
      filePreview: previewData || null,
      result: agentResult,
      timestamp: Date.now(),
    };

    try {
      localStorage.setItem(ACTIVE_TASK_KEY, JSON.stringify(sessionData));

      // Append to task history
      const existingRaw = localStorage.getItem(TASK_HISTORY_KEY);
      let history = [];
      if (existingRaw) {
        try {
          const parsed = JSON.parse(existingRaw);
          if (Array.isArray(parsed)) history = parsed;
        } catch {
          // Ignore
        }
      }

      // Filter duplicate query and prepend
      history = [
        sessionData,
        ...history.filter((h) => h.query !== query),
      ].slice(0, 10);

      localStorage.setItem(TASK_HISTORY_KEY, JSON.stringify(history));
      window.dispatchEvent(new CustomEvent("astra_history_updated"));
    } catch {
      // Storage quota or disabled
    }
  };

  const runTask = async () => {
    const userQuery = prompt.trim();
    if (!userQuery || isRunning) return;

    setIsRunning(true);
    setSubmittedQuery(userQuery);
    setSubmittedFilePreview(filePreview);
    setSubmittedFileName(selectedFile?.name || "");
    setResult(null);
    setError("");
    setCopied(false);

    const currentFile = selectedFile;
    const currentPreview = filePreview;

    try {
      const response = await runAgent(token, userQuery, currentFile);
      setResult(response);
      persistTask(userQuery, currentFile, currentPreview, response);
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        if (requestError.status === 401) logout();
        setError(
          requestError.status === 403
            ? "Your authenticated role is not permitted to execute agent tasks. Ask an administrator for an admin, officer, or worker account."
            : requestError.message
        );
      } else {
        setError("The task could not be completed. Please verify the local AI runtime.");
      }
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmit = (event) => {
    if (event) event.preventDefault();
    runTask();
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      runTask();
    }
  };

  const handleCopyResponse = async () => {
    if (!result?.response) return;
    try {
      await navigator.clipboard.writeText(result.response);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const handleSelectChip = (chip) => {
    setPrompt(chip.query);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const hasActiveConversation = Boolean(submittedQuery || isRunning || result);

  return (
    <div className="workbench-workspace">
      {/* Top Workspace Bar */}
      <div className="workspace-header">
        <div className="workspace-header-title">
          <div className="workspace-avatar">
            <ShieldCheck size={18} />
          </div>
          <div>
            <div className="workspace-name">
              ASTRA AI Workbench
              <span className="workspace-badge">SOVEREIGN AIR-GAPPED</span>
            </div>
            <div className="workspace-meta">
              Autonomous Secure Task-Reasoning Agent · Signed in as{" "}
              <strong>{user?.username}</strong> ({user?.role})
            </div>
          </div>
        </div>

        {hasActiveConversation && (
          <button
            type="button"
            className="new-task-btn"
            onClick={handleResetTask}
            disabled={isRunning}
            title="Start a new task (clears active view)"
          >
            <RefreshCw size={13} />
            <span>New Task</span>
          </button>
        )}
      </div>

      {/* Main Content Area: Centered Empty State or Scrollable Conversation */}
      <div className={`workspace-scroll-area ${!hasActiveConversation ? "empty-scroll-area" : ""}`}>
        {!hasActiveConversation ? (
          /* REFINED EMPTY STATE WITH COMPACT CHIPS */
          <div className="workbench-empty-state">
            <div className="empty-hero">
              <div className="empty-hero-icon">
                <ShieldCheck size={32} />
              </div>
              <h1>How can ASTRA help you today?</h1>
              <p>
                Your secure local AI workspace for technical documents, diagrams, and reasoning.
              </p>

              {/* Compact Suggestion Chips */}
              <div className="prompt-chips-row">
                {PROMPT_CHIPS.map((chip, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="prompt-chip"
                    onClick={() => handleSelectChip(chip)}
                    title={chip.query}
                  >
                    <span className="chip-icon">{chip.icon}</span>
                    <span className="chip-label">{chip.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Empty State Centered Composer */}
            <div className="empty-composer-wrapper">
              <form onSubmit={handleSubmit} className="composer-form">
                {selectedFile && (
                  <div className="composer-attachment-chip">
                    {filePreview && (
                      <img
                        src={filePreview}
                        alt="Attachment preview thumbnail"
                        className="chip-thumbnail"
                      />
                    )}
                    <div className="chip-info">
                      <span className="chip-filename" title={selectedFile.name}>
                        {selectedFile.name}
                      </span>
                      <span className="chip-filesize">
                        ({(selectedFile.size / 1024).toFixed(0)} KB)
                      </span>
                    </div>
                    <button
                      type="button"
                      className="chip-remove-btn"
                      onClick={handleRemoveFile}
                      disabled={isRunning}
                      title="Remove attachment"
                      aria-label="Remove attachment"
                    >
                      <X size={13} />
                    </button>
                  </div>
                )}

                <div className="composer-input-row">
                  <textarea
                    ref={textareaRef}
                    className="composer-textarea"
                    maxLength={10000}
                    placeholder="Ask ASTRA anything, or attach an engineering diagram (Enter to send)…"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isRunning}
                    rows={3}
                  />
                </div>

                <div className="composer-actions-row">
                  <div className="composer-left-tools">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                      style={{ display: "none" }}
                      onChange={handleFileSelect}
                      disabled={isRunning}
                      id="workbench-file-input-empty"
                    />
                    <label
                      htmlFor="workbench-file-input-empty"
                      className={`composer-tool-btn ${isRunning ? "disabled" : ""}`}
                      title="Attach engineering diagram (PNG, JPG, WEBP up to 10MB)"
                    >
                      <Paperclip size={15} />
                      <span>Attach file</span>
                    </label>

                    <span className="composer-multimodal-tag">
                      <ImageIcon size={12} /> Vision Active
                    </span>
                  </div>

                  <div className="composer-right-tools">
                    <span className="character-counter">
                      {prompt.length > 0 && `${prompt.length.toLocaleString()} / 10,000`}
                    </span>

                    <button
                      type="submit"
                      className="composer-send-btn"
                      disabled={!prompt.trim() || isRunning}
                      title="Send task to ASTRA (Enter)"
                    >
                      {isRunning ? (
                        <Loader2 size={15} className="spin" />
                      ) : (
                        <Send size={15} />
                      )}
                      <span>{isRunning ? "Reasoning…" : "Send"}</span>
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        ) : (
          /* CONVERSATIONAL THREAD */
          <div className="conversation-thread">
            {/* User Message */}
            <div className="chat-row user-row">
              <div className="chat-bubble user-bubble">
                <div className="chat-bubble-header">
                  <strong>You</strong>
                  <span className="chat-role-tag">{user?.role}</span>
                </div>

                {submittedFilePreview && (
                  <div className="attached-media-card">
                    <img
                      src={submittedFilePreview}
                      alt="Attached schematic"
                      className="attached-media-img"
                    />
                    <div className="attached-media-meta">
                      <ImageIcon size={13} />
                      <span className="attached-media-name">{submittedFileName}</span>
                    </div>
                  </div>
                )}

                <div className="chat-bubble-text">{submittedQuery}</div>
              </div>
            </div>

            {/* Truthful Loading Indicator */}
            {isRunning && (
              <div className="chat-row assistant-row">
                <div className="chat-bubble assistant-bubble loading-bubble">
                  <div className="assistant-badge-row">
                    <div className="assistant-avatar pulse-avatar">
                      <ShieldCheck size={18} />
                    </div>
                    <strong>ASTRA</strong>
                    <span className="running-indicator">
                      <Loader2 size={12} className="spin" /> ASTRA is reasoning…
                    </span>
                  </div>

                  <div className="loading-body">
                    <div className="loading-step-item">
                      <div className="loading-step-pulse" />
                      <div>
                        <strong>Executing multi-agent LangGraph workflow</strong>
                        <p>Orchestrating supervisor, knowledge retrieval, and local inference.</p>
                      </div>
                    </div>
                    <div className="loading-hint">
                      Air-gapped on-device execution (Qwen3-VL &amp; Qwen3 4B) typically completes in 60–120s.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="chat-row error-row">
                <div className="chat-bubble error-bubble">
                  <div className="error-header">
                    <TriangleAlert size={16} />
                    <strong>Task Execution Error</strong>
                  </div>
                  <p>{error}</p>
                  <button
                    type="button"
                    className="error-retry-btn"
                    onClick={runTask}
                    disabled={isRunning}
                  >
                    Retry Request
                  </button>
                </div>
              </div>
            )}

            {/* ASTRA Completed Result Card */}
            {result && (
              <div className="chat-row assistant-row">
                <div className="chat-bubble assistant-bubble result-bubble">
                  {/* Assistant Identity Header */}
                  <div className="assistant-bubble-header">
                    <div className="assistant-id">
                      <div className="assistant-avatar">
                        <ShieldCheck size={18} />
                      </div>
                      <div>
                        <strong>ASTRA</strong>
                        <span className="assistant-model-tag">Local Sovereign AI</span>
                      </div>
                    </div>

                    <div className="result-meta-chips">
                      <span className="meta-chip task-chip" title="Task classification">
                        <Brain size={12} /> {result.task_type}
                      </span>
                      <span className="meta-chip time-chip" title="Total roundtrip execution time">
                        <Clock3 size={12} /> {result.execution_time_seconds}s
                      </span>
                      {result.air_gapped && (
                        <span className="meta-chip airgap-chip" title="Air-gapped local execution">
                          <ShieldCheck size={12} /> Air-Gapped
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Main Formatted Answer (Visually Primary) */}
                  <div className="assistant-response-content">
                    <MarkdownRenderer content={result.response} />
                  </div>

                  {/* Action Bar (Copy + Collapsible Toggles) */}
                  <div className="response-actions-bar">
                    <button
                      type="button"
                      className={`action-btn copy-btn ${copied ? "copied" : ""}`}
                      onClick={handleCopyResponse}
                      title="Copy response text"
                      aria-label="Copy response text"
                    >
                      {copied ? (
                        <>
                          <Check size={13} className="copied-check" />
                          <span>Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy size={13} />
                          <span>Copy</span>
                        </>
                      )}
                    </button>

                    {result.steps?.length > 0 && (
                      <button
                        type="button"
                        className="action-btn toggle-steps-btn"
                        onClick={() => setShowSteps(!showSteps)}
                        title="View agent execution activity"
                      >
                        <CheckCircle2 size={13} />
                        <span>Agent activity ({result.steps.length})</span>
                        {showSteps ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>
                    )}

                    {result.citations?.length > 0 && (
                      <button
                        type="button"
                        className="action-btn toggle-citations-btn"
                        onClick={() => setShowCitations(!showCitations)}
                        title="View cited knowledge sources"
                      >
                        <FileText size={13} />
                        <span>Sources ({result.citations.length})</span>
                        {showCitations ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>
                    )}
                  </div>

                  {/* Collapsible Execution Steps (Secondary) */}
                  {showSteps && result.steps?.length > 0 && (
                    <div className="collapsible-panel steps-panel">
                      <div className="panel-header">
                        <CheckCircle2 size={14} />
                        <strong>Agent Execution Activity</strong>
                      </div>
                      <div className="timeline-steps">
                        {result.steps.map((step) => (
                          <div key={`${step.step}-${step.agent}`} className="timeline-step">
                            <div className="step-badge">
                              <span>{step.step}</span>
                            </div>
                            <div className="step-details">
                              <strong className="step-agent">{step.agent}</strong>
                              <span className="step-action">{step.action}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Collapsible Citations (Secondary) */}
                  {showCitations && result.citations?.length > 0 && (
                    <div className="collapsible-panel citations-panel">
                      <div className="panel-header">
                        <Database size={14} />
                        <strong>Knowledge Sources (ChromaDB RAG)</strong>
                      </div>
                      <div className="citation-cards-grid">
                        {result.citations.map((c, i) => (
                          <div key={`${c.source}-${c.page}-${i}`} className="citation-card">
                            <div className="citation-card-top">
                              <FileText size={13} />
                              <span className="citation-source" title={c.source}>
                                {c.source}
                              </span>
                            </div>
                            <div className="citation-card-bottom">
                              <span className="citation-page">Page {c.page}</span>
                              {c.distance != null && (
                                <span className="citation-distance">
                                  dist: {Number(c.distance).toFixed(3)}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Anchored Bottom Composer (When Conversation is Active) */}
      {hasActiveConversation && (
        <div className="composer-container anchored-composer">
          <form onSubmit={handleSubmit} className="composer-form">
            {selectedFile && (
              <div className="composer-attachment-chip">
                {filePreview && (
                  <img
                    src={filePreview}
                    alt="Attachment preview thumbnail"
                    className="chip-thumbnail"
                  />
                )}
                <div className="chip-info">
                  <span className="chip-filename" title={selectedFile.name}>
                    {selectedFile.name}
                  </span>
                  <span className="chip-filesize">
                    ({(selectedFile.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <button
                  type="button"
                  className="chip-remove-btn"
                  onClick={handleRemoveFile}
                  disabled={isRunning}
                  title="Remove attachment"
                  aria-label="Remove attachment"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            <div className="composer-input-row">
              <textarea
                ref={textareaRef}
                className="composer-textarea"
                maxLength={10000}
                placeholder="Ask a follow-up or attach an engineering diagram (Enter to send)…"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isRunning}
                rows={2}
              />
            </div>

            <div className="composer-actions-row">
              <div className="composer-left-tools">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                  style={{ display: "none" }}
                  onChange={handleFileSelect}
                  disabled={isRunning}
                  id="workbench-file-input-active"
                />
                <label
                  htmlFor="workbench-file-input-active"
                  className={`composer-tool-btn ${isRunning ? "disabled" : ""}`}
                  title="Attach engineering diagram (PNG, JPG, WEBP up to 10MB)"
                >
                  <Paperclip size={15} />
                  <span>Attach file</span>
                </label>

                <span className="composer-multimodal-tag">
                  <ImageIcon size={12} /> Vision Active
                </span>
              </div>

              <div className="composer-right-tools">
                <span className="character-counter">
                  {prompt.length > 0 && `${prompt.length.toLocaleString()} / 10,000`}
                </span>

                <button
                  type="submit"
                  className="composer-send-btn"
                  disabled={!prompt.trim() || isRunning}
                  title="Send task to ASTRA (Enter)"
                >
                  {isRunning ? (
                    <Loader2 size={15} className="spin" />
                  ) : (
                    <Send size={15} />
                  )}
                  <span>{isRunning ? "Reasoning…" : "Send"}</span>
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export default Workbench;
