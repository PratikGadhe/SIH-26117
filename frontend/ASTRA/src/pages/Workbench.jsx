import { useState } from "react";
import {
  Bot,
  Brain,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  Loader2,
  Send,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { ApiError, runAgent } from "../services/api";
import "./Workbench.css";

function Workbench() {
  const { token, user, logout } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const runTask = async () => {
    const userQuery = prompt.trim();
    if (!userQuery || isRunning) return;

    setIsRunning(true);
    setSubmittedQuery(userQuery);
    setResult(null);
    setError("");
    try {
      setResult(await runAgent(token, userQuery));
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
            <ShieldCheck size={15} /> AUTHENTICATED TEXT WORKFLOW
          </div>
          <h1>AI Workbench</h1>
          <p>
            Submit a text task to the real Cognivault agent endpoint. Routing,
            model use, and knowledge retrieval are controlled by the backend.
          </p>
        </div>
        <div className="workbench-security">
          Signed in as {user?.username} · {user?.role}
        </div>
      </div>

      <div className="integration-notice">
        <TriangleAlert size={19} />
        <div>
          <strong>Phase 9A capability boundary</strong>
          <span>
            Browser file upload, manual model selection, code tools, and
            deliverable generation are not supported by the current API.
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
            <span className="local-badge"><span /> TEXT ONLY</span>
          </div>

          <form onSubmit={handleSubmit}>
            <textarea
              className="task-prompt"
              maxLength={10000}
              placeholder="Example: Summarize the maintenance safety procedure."
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              disabled={isRunning}
            />
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
                <p>{submittedQuery}</p>
              </div>
              {isRunning && (
                <div className="conversation-message astra-message">
                  <strong>ASTRA</strong><p>Waiting for the local agent…</p>
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
