import { useState, useRef } from "react";
import {
  Bot,
  Brain,
  CheckCircle2,
  Clock3,
  Database,
  Eye,
  FileText,
  Image as ImageIcon,
  Loader2,
  Paperclip,
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

function Workbench() {
  const { token, user, logout } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [submittedFilePreview, setSubmittedFilePreview] = useState(null);
  const [submittedFileName, setSubmittedFileName] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);

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
    if (filePreview) URL.revokeObjectURL(filePreview);
    setFilePreview(URL.createObjectURL(file));
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (filePreview) {
      URL.revokeObjectURL(filePreview);
      setFilePreview(null);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
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

    const currentFile = selectedFile;

    try {
      setResult(await runAgent(token, userQuery, currentFile));
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        if (requestError.status === 401) logout();
        setError(
          requestError.status === 403
            ? "Your authenticated role is not permitted to execute agent tasks. Ask an administrator for an admin, officer, or worker account."
            : requestError.message,
        );
      } else {
        setError("The task could not be completed.");
      }
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    runTask();
  };

  return (
    <div className="workbench-page">
      <div className="workbench-intro">
        <div>
          <div className="workbench-label">
            <ShieldCheck size={15} /> AUTHENTICATED MULTIMODAL WORKFLOW
          </div>
          <h1>AI Workbench</h1>
          <p>
            Submit technical questions or attach engineering schematics to the real Cognivault agent endpoint.
            Routing, visual analysis (Qwen3-VL), and knowledge retrieval are orchestrated by LangGraph.
          </p>
        </div>
        <div className="workbench-security">
          Signed in as {user?.username} · {user?.role}
        </div>
      </div>

      <div className="integration-notice active-multimodal-notice">
        <ShieldCheck size={19} />
        <div>
          <strong>Multimodal Vision &amp; Reasoning Active</strong>
          <span>
            Attach P&amp;ID schematics, equipment photos, or engineering diagrams (PNG, JPG, WEBP up to 10MB) for inspection via local Qwen3-VL.
          </span>
        </div>
      </div>

      <div className="workbench-grid connected-workbench-grid">
        <section className="workbench-card prompt-card">
          <div className="workbench-card-header">
            <div className="workbench-card-title">
              <div className="workbench-icon"><Brain size={19} /></div>
              <div>
                <h3>Agent task</h3>
                <p>POST /api/v1/agent/run</p>
              </div>
            </div>
            <span className="local-badge"><span /> TEXT &amp; VISION</span>
          </div>

          <form onSubmit={handleSubmit}>
            <textarea
              className="task-prompt"
              maxLength={10000}
              placeholder="Example: Analyze this diagram and identify the visible components, labels, and safety connections."
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              disabled={isRunning}
            />

            <div className="attachment-bar">
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                style={{ display: "none" }}
                onChange={handleFileSelect}
                disabled={isRunning}
                id="workbench-file-input"
              />
              <label
                htmlFor="workbench-file-input"
                className={`attach-file-btn ${isRunning ? "disabled" : ""}`}
                title="Attach an engineering diagram or image"
              >
                <Paperclip size={15} />
                <span>Attach Image</span>
              </label>

              {selectedFile && (
                <div className="file-chip">
                  <ImageIcon size={14} className="file-chip-icon" />
                  <span className="file-chip-name" title={selectedFile.name}>
                    {selectedFile.name}
                  </span>
                  <span className="file-chip-size">
                    ({(selectedFile.size / 1024).toFixed(0)} KB)
                  </span>
                  <button
                    type="button"
                    className="file-chip-remove"
                    onClick={handleRemoveFile}
                    disabled={isRunning}
                    aria-label="Remove attached image"
                  >
                    <X size={13} />
                  </button>
                </div>
              )}
            </div>

            {filePreview && (
              <div className="attachment-preview-container">
                <div className="preview-header">
                  <span><Eye size={13} /> Attached Preview</span>
                </div>
                <img
                  src={filePreview}
                  alt="Attachment preview"
                  className="attachment-preview-thumbnail"
                />
              </div>
            )}

            <div className="prompt-footer">
              <span>{prompt.length} / 10,000 characters</span>
              <button
                className="run-task-btn"
                disabled={!prompt.trim() || isRunning}
                type="submit"
              >
                {isRunning ? (
                  <><Loader2 size={17} className="spin" /> Running…</>
                ) : (
                  <><Send size={17} /> Run ASTRA Task</>
                )}
              </button>
            </div>
          </form>

          {error && (
            <div className="workbench-error" role="alert">
              <TriangleAlert size={18} /> <span>{error}</span>
            </div>
          )}
        </section>

        <section className="workbench-card execution-card live-result-card">
          <div className="workbench-card-header">
            <div className="workbench-card-title">
              <div className="workbench-icon"><Bot size={19} /></div>
              <div>
                <h3>Conversation</h3>
                <p>Real request and normalized LangGraph result</p>
              </div>
            </div>
            {result && <span className="running-badge">COMPLETED</span>}
          </div>

          {!submittedQuery ? (
            <div className="result-placeholder">
              <Bot size={32} />
              <strong>No task executed</strong>
              <span>Actual backend output will appear here.</span>
            </div>
          ) : (
            <div className="conversation-result">
              <div className="conversation-message user-message">
                <strong>You</strong>
                {submittedFilePreview && (
                  <div className="submitted-attachment">
                    <img
                      src={submittedFilePreview}
                      alt="Submitted diagram"
                      className="submitted-thumbnail"
                    />
                    <span className="submitted-file-tag">
                      <ImageIcon size={12} /> {submittedFileName}
                    </span>
                  </div>
                )}
                <p>{submittedQuery}</p>
              </div>
              {isRunning && (
                <div className="conversation-message astra-message">
                  <strong>ASTRA</strong><p>Waiting for the local agent (executing LangGraph workflow)…</p>
                </div>
              )}
              {result && (
                <div className="conversation-message astra-message agent-result">
                  <strong>ASTRA</strong>
                  <p className="agent-answer">{result.response}</p>
                  <div className="agent-result-meta">
                    <span><Brain size={14} /> {result.task_type}</span>
                    <span><Clock3 size={14} /> {result.execution_time_seconds}s</span>
                    <span><ShieldCheck size={14} /> Air-gapped: {result.air_gapped ? "reported" : "not reported"}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {result && (
        <div className="workbench-grid result-detail-grid">
          <section className="workbench-card">
            <div className="workbench-card-title">
              <div className="workbench-icon"><CheckCircle2 size={19} /></div>
              <div><h3>Execution steps</h3><p>Returned by the backend</p></div>
            </div>
            <div className="connected-list">
              {result.steps.length ? result.steps.map((step) => (
                <div key={`${step.step}-${step.agent}`}>
                  <strong>{step.step}. {step.agent}</strong>
                  <span>{step.action}</span>
                </div>
              )) : <span>No execution steps were returned.</span>}
            </div>
          </section>

          <section className="workbench-card">
            <div className="workbench-card-title">
              <div className="workbench-icon"><Database size={19} /></div>
              <div><h3>Citations</h3><p>Sources returned by RAG</p></div>
            </div>
            <div className="connected-list">
              {result.citations.length ? result.citations.map((citation, index) => (
                <div key={`${citation.source}-${citation.page}-${index}`}>
                  <strong><FileText size={14} /> {citation.source}</strong>
                  <span>Page {citation.page}{citation.distance == null ? "" : ` · distance ${citation.distance}`}</span>
                </div>
              )) : <span>No citations were returned for this task.</span>}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

export default Workbench;
