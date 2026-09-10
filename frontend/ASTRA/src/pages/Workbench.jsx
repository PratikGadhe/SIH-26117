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
const ALLOWED_DOCUMENT_EXTENSIONS = [".pdf"];
const ALLOWED_EXTENSIONS = [...ALLOWED_IMAGE_EXTENSIONS, ...ALLOWED_DOCUMENT_EXTENSIONS];
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

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

// Safe storage hydration supporting both new conversation format and legacy single tasks
function getStoredActiveConversation() {
  try {
    const saved = localStorage.getItem(ACTIVE_TASK_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved);
    if (!parsed) return null;

    // Already in multi-turn conversation model
    if (Array.isArray(parsed.messages) && parsed.messages.length > 0) {
      return {
        conversationId: parsed.conversationId || `conv-${parsed.createdAt || Date.now()}`,
        messages: parsed.messages,
        createdAt: parsed.createdAt || Date.now(),
        updatedAt: parsed.updatedAt || Date.now(),
      };
    }

    // Convert legacy single-task format { query, result, ... } into conversation
    if (parsed.query && parsed.result) {
      const isPdf = parsed.fileType === "pdf" || parsed.fileName?.toLowerCase().endsWith(".pdf");
      const userMsg = {
        id: `msg-${parsed.id || Date.now()}-u`,
        role: "user",
        content: parsed.query,
        timestamp: parsed.timestamp || Date.now(),
        fileMeta: parsed.fileName
          ? {
              name: parsed.fileName,
              size: 0,
              type: isPdf ? "pdf" : "image",
            }
          : null,
      };
      const assistantMsg = {
        id: `msg-${parsed.id || Date.now()}-a`,
        role: "assistant",
        content: parsed.result.response || "",
        taskType: parsed.result.task_type || "UNKNOWN",
        executionTimeSeconds: parsed.result.execution_time_seconds || 0,
        airGapped: Boolean(parsed.result.air_gapped),
        steps: parsed.result.steps || [],
        citations: parsed.result.citations || [],
        timestamp: parsed.timestamp || Date.now(),
      };
      return {
        conversationId: parsed.id || `conv-${Date.now()}`,
        messages: [userMsg, assistantMsg],
        createdAt: parsed.timestamp || Date.now(),
        updatedAt: parsed.timestamp || Date.now(),
      };
    }
  } catch {
    // Ignore parse errors
  }
  return null;
}

// Strip data URLs / base64 and sensitive tokens before writing to localStorage (ensures <10KB)
function sanitizeConversationForStorage(conversation) {
  if (!conversation) return null;
  return {
    conversationId: conversation.conversationId,
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
    messages: (conversation.messages || []).map((msg) => {
      if (msg.role === "user") {
        return {
          id: msg.id,
          role: "user",
          content: msg.content,
          timestamp: msg.timestamp,
          fileMeta: msg.fileMeta
            ? {
                name: msg.fileMeta.name,
                size: msg.fileMeta.size,
                type: msg.fileMeta.type,
              }
            : null,
          // Note: filePreview data URL is intentionally excluded to prevent browser quota exhaustion
        };
      }
      return {
        id: msg.id,
        role: "assistant",
        content: msg.content,
        taskType: msg.taskType,
        executionTimeSeconds: msg.executionTimeSeconds,
        airGapped: msg.airGapped,
        steps: msg.steps || [],
        citations: msg.citations || [],
        timestamp: msg.timestamp,
      };
    }),
  };
}

// Self-contained assistant card with individual copy feedback and collapsible panels
function AssistantMessageCard({ message }) {
  const [showSteps, setShowSteps] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!message.content) return;
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
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
              <Brain size={12} /> {message.taskType}
            </span>
            <span className="meta-chip time-chip" title="Total roundtrip execution time">
              <Clock3 size={12} /> {message.executionTimeSeconds}s
            </span>
            {message.airGapped && (
              <span className="meta-chip airgap-chip" title="Air-gapped local execution">
                <ShieldCheck size={12} /> Air-Gapped
              </span>
            )}
          </div>
        </div>

        {/* Main Formatted Answer (Visually Primary) */}
        <div className="assistant-response-content">
          <MarkdownRenderer content={message.content} />
        </div>

        {/* Action Bar (Copy + Collapsible Toggles) */}
        <div className="response-actions-bar">
          <button
            type="button"
            className={`action-btn copy-btn ${copied ? "copied" : ""}`}
            onClick={handleCopy}
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

          {message.steps?.length > 0 && (
            <button
              type="button"
              className="action-btn toggle-steps-btn"
              onClick={() => setShowSteps(!showSteps)}
              title="View agent execution activity"
            >
              <CheckCircle2 size={13} />
              <span>Agent activity ({message.steps.length})</span>
              {showSteps ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}

          {message.citations?.length > 0 && (
            <button
              type="button"
              className="action-btn toggle-citations-btn"
              onClick={() => setShowCitations(!showCitations)}
              title="View cited knowledge sources"
            >
              <FileText size={13} />
              <span>Sources ({message.citations.length})</span>
              {showCitations ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </div>

        {/* Collapsible Execution Steps (Secondary) */}
        {showSteps && message.steps?.length > 0 && (
          <div className="collapsible-panel steps-panel">
            <div className="panel-header">
              <CheckCircle2 size={14} />
              <strong>Agent Execution Activity</strong>
            </div>
            <div className="timeline-steps">
              {message.steps.map((step) => (
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
        {showCitations && message.citations?.length > 0 && (
          <div className="collapsible-panel citations-panel">
            <div className="panel-header">
              <Database size={14} />
              <strong>Knowledge Sources (ChromaDB RAG)</strong>
            </div>
            <div className="citation-cards-grid">
              {message.citations.map((c, i) => (
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
  );
}

function Workbench() {
  const { token, user, logout } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);

  // Unified conversation state containing multi-turn messages
  const [conversation, setConversation] = useState(() => {
    const stored = getStoredActiveConversation();
    if (stored) return stored;
    return {
      conversationId: `conv-${Date.now()}`,
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
  });

  const [error, setError] = useState("");

  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (isRunning || conversation.messages.length > 0) {
      scrollToBottom();
    }
  }, [isRunning, conversation.messages.length, scrollToBottom]);

  // Listen to external restore events (from Sidebar history clicks)
  useEffect(() => {
    const handleRestore = (event) => {
      const task = event.detail;
      if (!task) return;

      if (Array.isArray(task.messages) && task.messages.length > 0) {
        setConversation({
          conversationId: task.id || `conv-${Date.now()}`,
          messages: task.messages,
          createdAt: task.timestamp || Date.now(),
          updatedAt: task.timestamp || Date.now(),
        });
      } else if (task.query && task.result) {
        const isPdf = task.fileType === "pdf" || task.fileName?.toLowerCase().endsWith(".pdf");
        setConversation({
          conversationId: task.id || `conv-${Date.now()}`,
          messages: [
            {
              id: `msg-${task.id || Date.now()}-u`,
              role: "user",
              content: task.query,
              timestamp: task.timestamp || Date.now(),
              fileMeta: task.fileName
                ? {
                    name: task.fileName,
                    size: 0,
                    type: isPdf ? "pdf" : "image",
                  }
                : null,
            },
            {
              id: `msg-${task.id || Date.now()}-a`,
              role: "assistant",
              content: task.result.response || "",
              taskType: task.result.task_type || "UNKNOWN",
              executionTimeSeconds: task.result.execution_time_seconds || 0,
              airGapped: Boolean(task.result.air_gapped),
              steps: task.result.steps || [],
              citations: task.result.citations || [],
              timestamp: task.timestamp || Date.now(),
            },
          ],
          createdAt: task.timestamp || Date.now(),
          updatedAt: task.timestamp || Date.now(),
        });
      }
      setError("");
      setPrompt("");
      setSelectedFile(null);
      setFilePreview(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
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
    const isValidExtension = ALLOWED_EXTENSIONS.some((ext) =>
      lowerName.endsWith(ext)
    );

    if (!isValidExtension) {
      setError("Unsupported file format. Please attach a PNG, JPG, JPEG, WEBP image, or PDF document.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError("File exceeds maximum permitted size of 10 MB.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setError("");
    setSelectedFile(file);

    const isPdf = lowerName.endsWith(".pdf");
    if (isPdf) {
      // PDF documents don't use image Data URLs
      setFilePreview(null);
    } else {
      // Read preview as Data URL for in-memory display during current turn
      const reader = new FileReader();
      reader.onload = () => {
        setFilePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
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
    setConversation({
      conversationId: `conv-${Date.now()}`,
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    });
    setError("");
    setPrompt("");
    handleRemoveFile();
    if (textareaRef.current) textareaRef.current.focus();
  };

  const persistConversation = (conv, lastQuery, lastFile, lastResult) => {
    try {
      // 1. Save active conversation (safely sanitized, without heavy base64 strings)
      const sanitized = sanitizeConversationForStorage(conv);
      localStorage.setItem(ACTIVE_TASK_KEY, JSON.stringify(sanitized));

      // 2. Append/update in Recent History (TASK_HISTORY_KEY)
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

      const firstUserMsg = conv.messages.find((m) => m.role === "user");
      const firstQuery = firstUserMsg?.content || lastQuery || "Conversation";
      const hasImage = Boolean(
        conv.messages.some((m) => m.fileMeta?.type === "image")
      );
      const isPdf = Boolean(
        conv.messages.some((m) => m.fileMeta?.type === "pdf")
      );
      const fileName =
        conv.messages.find((m) => m.fileMeta)?.fileMeta?.name || lastFile?.name || "";

      const historyItem = {
        id: conv.conversationId,
        query: firstQuery,
        hasImage,
        hasFile: hasImage || isPdf,
        fileType: isPdf ? "pdf" : (hasImage ? "image" : null),
        fileName,
        result: lastResult || null,
        messages: sanitized.messages,
        timestamp: conv.updatedAt || Date.now(),
      };

      // Filter out same conversationId or duplicate query and prepend
      history = [
        historyItem,
        ...history.filter(
          (h) => h.id !== conv.conversationId && h.query !== firstQuery
        ),
      ].slice(0, 10);

      localStorage.setItem(TASK_HISTORY_KEY, JSON.stringify(history));
      window.dispatchEvent(new CustomEvent("astra_history_updated"));
    } catch {
      // Storage quota or disabled
    }
  };

  const runTask = async (overrideQuery, overrideFile) => {
    const userQuery = (overrideQuery || prompt).trim();
    if (!userQuery || isRunning) return;

    const currentFile = overrideFile !== undefined ? overrideFile : selectedFile;
    const currentPreview = overrideFile !== undefined ? null : filePreview;
    const isPdf = currentFile?.name?.toLowerCase().endsWith(".pdf");

    const userMessage = {
      id: `msg-${Date.now()}-u`,
      role: "user",
      content: userQuery,
      timestamp: Date.now(),
      fileMeta: currentFile
        ? {
            name: currentFile.name,
            size: currentFile.size,
            type: isPdf ? "pdf" : "image",
          }
        : null,
      filePreview: isPdf ? null : currentPreview,
    };

    // Append user message to conversation
    const updatedMessages = overrideQuery
      ? conversation.messages
      : [...conversation.messages, userMessage];

    const updatedConversation = {
      ...conversation,
      messages: updatedMessages,
      updatedAt: Date.now(),
    };

    if (!overrideQuery) {
      setConversation(updatedConversation);
      setPrompt("");
      setSelectedFile(null);
      setFilePreview(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
    setIsRunning(true);
    setError("");

    try {
      const response = await runAgent(token, userQuery, currentFile);
      const assistantMessage = {
        id: `msg-${Date.now()}-a`,
        role: "assistant",
        content: response.response,
        taskType: response.task_type,
        executionTimeSeconds: response.execution_time_seconds,
        airGapped: response.air_gapped,
        steps: response.steps || [],
        citations: response.citations || [],
        timestamp: Date.now(),
      };

      const finalConversation = {
        ...updatedConversation,
        messages: [...updatedMessages, assistantMessage],
        updatedAt: Date.now(),
      };

      setConversation(finalConversation);
      persistConversation(finalConversation, userQuery, currentFile, response);
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
      persistConversation(updatedConversation, userQuery, currentFile, null);
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

  const handleSelectChip = (chip) => {
    setPrompt(chip.query);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const hasActiveConversation = Boolean(
    conversation.messages.length > 0 || isRunning
  );

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
                    {selectedFile.name.toLowerCase().endsWith(".pdf") ? (
                      <div className="chip-pdf-preview" title="PDF Document">
                        <FileText size={16} className="chip-pdf-icon" />
                      </div>
                    ) : (
                      filePreview && (
                        <img
                          src={filePreview}
                          alt="Attachment preview thumbnail"
                          className="chip-thumbnail"
                        />
                      )
                    )}
                    <div className="chip-info">
                      <span className="chip-filename" title={selectedFile.name}>
                        {selectedFile.name}
                      </span>
                      <span className="chip-filesize">
                        ({(selectedFile.size / 1024).toFixed(0)} KB{selectedFile.name.toLowerCase().endsWith(".pdf") ? " • PDF" : ""})
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
                    placeholder="Ask ASTRA anything, or attach a diagram/PDF (Enter to send)…"
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
                      accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp,.pdf,application/pdf"
                      style={{ display: "none" }}
                      onChange={handleFileSelect}
                      disabled={isRunning}
                      id="workbench-file-input-empty"
                    />
                    <label
                      htmlFor="workbench-file-input-empty"
                      className={`composer-tool-btn ${isRunning ? "disabled" : ""}`}
                      title="Attach engineering diagram or PDF document (PNG, JPG, WEBP, PDF up to 10MB)"
                    >
                      <Paperclip size={15} />
                      <span>Attach file</span>
                    </label>

                    <span className="composer-multimodal-tag">
                      <FileText size={12} /> Multimodal Active
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
            {conversation.messages.map((message) => {
              if (message.role === "user") {
                return (
                  <div key={message.id} className="chat-row user-row">
                    <div className="chat-bubble user-bubble">
                      <div className="chat-bubble-header">
                        <strong>You</strong>
                        <span className="chat-role-tag">{user?.role}</span>
                      </div>

                      {message.fileMeta && (
                        message.fileMeta.type === "pdf" ? (
                          <div className="attached-media-card attached-document-card">
                            <div className="attached-media-meta">
                              <FileText size={15} className="attached-document-icon" />
                              <span className="attached-media-name">{message.fileMeta.name}</span>
                              <span className="attached-file-badge">PDF</span>
                            </div>
                          </div>
                        ) : (
                          <div className="attached-media-card">
                            {message.filePreview && (
                              <img
                                src={message.filePreview}
                                alt="Attached schematic"
                                className="attached-media-img"
                              />
                            )}
                            <div className="attached-media-meta">
                              <ImageIcon size={13} />
                              <span className="attached-media-name">{message.fileMeta.name}</span>
                              <span className="attached-file-badge">IMAGE</span>
                            </div>
                          </div>
                        )
                      )}

                      <div className="chat-bubble-text">{message.content}</div>
                    </div>
                  </div>
                );
              }

              if (message.role === "assistant") {
                return <AssistantMessageCard key={message.id} message={message} />;
              }

              return null;
            })}

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
                {selectedFile.name.toLowerCase().endsWith(".pdf") ? (
                  <div className="chip-pdf-preview" title="PDF Document">
                    <FileText size={16} className="chip-pdf-icon" />
                  </div>
                ) : (
                  filePreview && (
                    <img
                      src={filePreview}
                      alt="Attachment preview thumbnail"
                      className="chip-thumbnail"
                    />
                  )
                )}
                <div className="chip-info">
                  <span className="chip-filename" title={selectedFile.name}>
                    {selectedFile.name}
                  </span>
                  <span className="chip-filesize">
                    ({(selectedFile.size / 1024).toFixed(0)} KB{selectedFile.name.toLowerCase().endsWith(".pdf") ? " • PDF" : ""})
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
                placeholder="Ask a follow-up or attach a diagram/PDF (Enter to send)…"
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
                  accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp,.pdf,application/pdf"
                  style={{ display: "none" }}
                  onChange={handleFileSelect}
                  disabled={isRunning}
                  id="workbench-file-input-active"
                />
                <label
                  htmlFor="workbench-file-input-active"
                  className={`composer-tool-btn ${isRunning ? "disabled" : ""}`}
                  title="Attach engineering diagram or PDF document (PNG, JPG, WEBP, PDF up to 10MB)"
                >
                  <Paperclip size={15} />
                  <span>Attach file</span>
                </label>

                <span className="composer-multimodal-tag">
                  <FileText size={12} /> Multimodal Active
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
