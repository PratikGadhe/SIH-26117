import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock3,
  Code2,
  Database,
  FileText,
  FileSearch,
  Loader2,
  Play,
  Search,
  ShieldCheck,
  Terminal,
  Wrench,
  Zap,
} from "lucide-react";
import "./AgentExecution.css";

const initialSteps = [
  { id: 1, title: "Read inspection report", tool: "File Reader", status: "completed" },
  { id: 2, title: "Extract findings from document", tool: "OCR + Vision", status: "completed" },
  { id: 3, title: "Search internal safety SOP", tool: "ChromaDB", status: "running" },
  { id: 4, title: "Reason over retrieved context", tool: "Local LLM", status: "pending" },
  { id: 5, title: "Generate approval note", tool: "Document Writer", status: "pending" },
];

const initialLogs = [
  { time: "09:17:02", type: "system", text: "Agent initialized in local mode." },
  { time: "09:17:03", type: "tool", text: "File Reader → Inspection_Report.pdf" },
  { time: "09:17:05", type: "tool", text: "OCR + Vision → extracted 7 visual findings" },
  { time: "09:17:07", type: "agent", text: "Planning next action: search internal safety SOP." },
];

function AgentExecution() {
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(12);
  const [steps, setSteps] = useState(initialSteps);
  const [logs, setLogs] = useState(initialLogs);

  useEffect(() => {
    if (!running) return;

    const timer = setInterval(() => {
      setElapsed((value) => value + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [running]);

  const startAgent = () => {
    setRunning(true);
    setSteps(initialSteps);
    setElapsed(0);
    setLogs([
      {
        time: new Date().toLocaleTimeString([], { hour12: false }),
        type: "system",
        text: "VYASA agent started a new task.",
      },
    ]);

    setTimeout(() => {
      setSteps((current) =>
        current.map((step) =>
          step.id === 3 ? { ...step, status: "completed" } :
          step.id === 4 ? { ...step, status: "running" } : step
        )
      );
      setLogs((current) => [
        ...current,
        {
          time: new Date().toLocaleTimeString([], { hour12: false }),
          type: "tool",
          text: "ChromaDB → retrieved 3 relevant SOP chunks.",
        },
        {
          time: new Date().toLocaleTimeString([], { hour12: false }),
          type: "agent",
          text: "Retrieved context added to agent working memory.",
        },
      ]);
    }, 1800);

    setTimeout(() => {
      setSteps((current) =>
        current.map((step) =>
          step.id === 4 ? { ...step, status: "completed" } :
          step.id === 5 ? { ...step, status: "running" } : step
        )
      );
      setLogs((current) => [
        ...current,
        {
          time: new Date().toLocaleTimeString([], { hour12: false }),
          type: "agent",
          text: "Reasoning completed. Preparing approval note.",
        },
      ]);
    }, 3600);

    setTimeout(() => {
      setSteps((current) =>
        current.map((step) =>
          step.id === 5 ? { ...step, status: "completed" } : step
        )
      );
      setLogs((current) => [
        ...current,
        {
          time: new Date().toLocaleTimeString([], { hour12: false }),
          type: "tool",
          text: "Document Writer → Approval_Note.docx generated.",
        },
        {
          time: new Date().toLocaleTimeString([], { hour12: false }),
          type: "system",
          text: "Task completed successfully.",
        },
      ]);
      setRunning(false);
    }, 5400);
  };

  const completedCount = steps.filter((step) => step.status === "completed").length;
  const currentStep = steps.find((step) => step.status === "running");

  return (
    <div className="agent-page">
      <section className="agent-hero">
        <div>
          <div className="agent-eyebrow">
            <Bot size={15} />
            AGENTIC AI ORCHESTRATION
          </div>
          <h1>Agent Execution</h1>
          <p>
            Watch VYASA plan, reason, call tools, retrieve knowledge and
            complete multi-step tasks locally.
          </p>
        </div>

        <div className="agent-live-badge">
          <span className="live-dot" />
          {running ? "AGENT RUNNING" : "READY TO EXECUTE"}
        </div>
      </section>

      <section className="execution-summary">
        <div className="summary-task">
          <div className="summary-icon"><Zap size={21} /></div>
          <div>
            <span>Current task</span>
            <strong>Analyze inspection report and prepare approval note</strong>
          </div>
        </div>

        <button className="run-agent-btn" onClick={startAgent} disabled={running}>
          {running ? <Loader2 size={17} className="spin" /> : <Play size={17} />}
          {running ? "Agent Running" : "Run Agent"}
        </button>
      </section>

      <div className="agent-stats">
        <Stat icon={<Activity />} label="Agent status" value={running ? "Executing" : "Ready"} live={running} />
        <Stat icon={<Zap />} label="Current step" value={currentStep?.title || "Task completed"} />
        <Stat icon={<Wrench />} label="Tool calls" value="7" />
        <Stat icon={<Clock3 />} label="Execution time" value={`${elapsed}s`} />
        <Stat icon={<CheckCircle2 />} label="Completed steps" value={`${completedCount}/5`} />
      </div>

      <div className="execution-grid">
        <section className="execution-card pipeline-card">
          <div className="card-heading">
            <div>
              <h2>Agent Reasoning Pipeline</h2>
              <p>VYASA autonomously moves from one action to the next.</p>
            </div>
            <span className="local-pill"><ShieldCheck size={14} /> Local execution</span>
          </div>

          <div className="agent-timeline">
            {steps.map((step) => (
              <div className={`agent-step ${step.status}`} key={step.id}>
                <div className="step-rail">
                  <div className="step-marker">
                    {step.status === "completed" ? <CheckCircle2 size={16} /> :
                     step.status === "running" ? <Loader2 size={16} className="spin" /> :
                     <span>{step.id}</span>}
                  </div>
                </div>

                <div className="step-content">
                  <div className="step-title-row">
                    <strong>{step.title}</strong>
                    <span className={`step-status ${step.status}`}>
                      {step.status}
                    </span>
                  </div>
                  <span className="step-tool">
                    <Wrench size={13} />
                    Tool: {step.tool}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="execution-card tool-card">
          <div className="card-heading">
            <div>
              <h2>Tool Calls</h2>
              <p>Actions invoked by the agent.</p>
            </div>
            <span className="tool-count">7 calls</span>
          </div>

          <div className="tool-list">
            <ToolCall icon={<FileText />} name="File Reader" detail="Inspection_Report.pdf" time="1.2s" />
            <ToolCall icon={<FileSearch />} name="OCR + Vision" detail="7 visual findings" time="2.4s" />
            <ToolCall icon={<Database />} name="ChromaDB Search" detail="Top 3 SOP chunks" time="0.8s" />
            <ToolCall icon={<Search />} name="Semantic Retriever" detail="Similarity search" time="0.5s" />
            <ToolCall icon={<Code2 />} name="Local LLM" detail="Reasoning step" time="4.1s" />
            <ToolCall icon={<Terminal />} name="Sandbox" detail="Validation check" time="0.7s" />
            <ToolCall icon={<FileText />} name="Document Writer" detail="Approval_Note.docx" time="1.0s" />
          </div>
        </section>
      </div>

      <section className="execution-card log-card">
        <div className="card-heading">
          <div>
            <h2>Activity Log</h2>
            <p>Live trace of agent decisions, tool calls and execution events.</p>
          </div>
          <span className="log-secure"><ShieldCheck size={14} /> No external calls</span>
        </div>

        <div className="activity-log">
          {logs.map((log, index) => (
            <div className="log-row" key={`${log.time}-${index}`}>
              <span className="log-time">{log.time}</span>
              <span className={`log-type ${log.type}`}>{log.type}</span>
              <span className="log-message">{log.text}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({ icon, label, value, live }) {
  return (
    <div className="agent-stat">
      <div className="stat-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{live && <i className="mini-live" />}{value}</strong>
      </div>
    </div>
  );
}

function ToolCall({ icon, name, detail, time }) {
  return (
    <div className="tool-row">
      <div className="tool-icon">{icon}</div>
      <div className="tool-info">
        <strong>{name}</strong>
        <span>{detail}</span>
      </div>
      <span className="tool-time">{time}</span>
    </div>
  );
}

export default AgentExecution;
