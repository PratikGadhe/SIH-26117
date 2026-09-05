import React, { useState } from "react";
import {
  Bot,
  Upload,
  FileText,
  Cpu,
  Brain,
  Search,
  Wrench,
  Download,
  FileSpreadsheet,
  Presentation,
  Send,
  CheckCircle2,
  Loader2,
  X,
  ShieldCheck,
} from "lucide-react";

import "./Workbench.css";

function Workbench() {
  const [selectedModel, setSelectedModel] = useState("ASTRA Reasoning");
  const [selectedFile, setSelectedFile] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [taskStarted, setTaskStarted] = useState(false);

  const models = [
    {
      name: "ASTRA Reasoning",
      type: "General Reasoning",
      status: "Ready",
    },
    {
      name: "ASTRA Vision",
      type: "Multimodal / Vision",
      status: "Ready",
    },
    {
      name: "ASTRA Coding",
      type: "Code Generation",
      status: "Ready",
    },
  ];

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (file) {
      setSelectedFile(file);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
  };

  const runTask = () => {
    if (!prompt.trim()) {
      alert("Please enter an AI task first.");
      return;
    }

    setIsRunning(true);
    setTaskStarted(true);

    setTimeout(() => {
      setIsRunning(false);
    }, 3000);
  };

  return (
    <div className="workbench-page">

      {/* PAGE INTRO */}
      <div className="workbench-intro">
        <div>
          <div className="workbench-label">
            <ShieldCheck size={15} />
            SECURE LOCAL AI WORKSPACE
          </div>

          <h1>AI Workbench</h1>

          <p>
            Give ASTRA a task, attach confidential files, select a local model,
            and let the agent plan and execute the workflow securely.
          </p>
        </div>

        <div className="workbench-security">
          <span className="security-dot"></span>
          Offline & Secure
        </div>
      </div>

      {/* MAIN WORKBENCH GRID */}
      <div className="workbench-grid">

        {/* LEFT COLUMN */}
        <div className="workbench-left">

          {/* MODEL SELECTION */}
          <section className="workbench-card">
            <div className="workbench-card-header">
              <div className="workbench-card-title">
                <div className="workbench-icon">
                  <Cpu size={19} />
                </div>

                <div>
                  <h3>Local AI Model</h3>
                  <p>Select an on-premise model</p>
                </div>
              </div>

              <span className="local-badge">
                <span></span>
                LOCAL
              </span>
            </div>

            <div className="model-list">
              {models.map((model) => (
                <button
                  key={model.name}
                  className={`model-option ${
                    selectedModel === model.name ? "selected" : ""
                  }`}
                  onClick={() => setSelectedModel(model.name)}
                >
                  <div className="model-option-icon">
                    <Bot size={18} />
                  </div>

                  <div className="model-info">
                    <strong>{model.name}</strong>
                    <span>{model.type}</span>
                  </div>

                  <div className="model-status">
                    <span className="status-dot"></span>
                    {model.status}
                  </div>
                </button>
              ))}
            </div>
          </section>

          {/* FILE UPLOAD */}
          <section className="workbench-card">
            <div className="workbench-card-header">
              <div className="workbench-card-title">
                <div className="workbench-icon">
                  <FileText size={19} />
                </div>

                <div>
                  <h3>Input Documents</h3>
                  <p>Attach files for ASTRA to analyze</p>
                </div>
              </div>
            </div>

            {!selectedFile ? (
              <label className="upload-zone">
                <input
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.xlsx,.csv"
                />

                <div className="upload-icon">
                  <Upload size={24} />
                </div>

                <strong>Drop your file here</strong>

                <span>
                  or click to browse from your computer
                </span>

                <small>
                  PDF, DOCX, XLSX, CSV, TXT, PNG, JPG
                </small>
              </label>
            ) : (
              <div className="selected-file">
                <div className="selected-file-icon">
                  <FileText size={21} />
                </div>

                <div className="selected-file-info">
                  <strong>{selectedFile.name}</strong>
                  <span>
                    {(selectedFile.size / 1024).toFixed(1)} KB
                  </span>
                </div>

                <button
                  className="remove-file"
                  onClick={removeFile}
                  title="Remove file"
                >
                  <X size={17} />
                </button>
              </div>
            )}
          </section>

          {/* TASK PROMPT */}
          <section className="workbench-card prompt-card">
            <div className="workbench-card-header">
              <div className="workbench-card-title">
                <div className="workbench-icon">
                  <Brain size={19} />
                </div>

                <div>
                  <h3>AI Task</h3>
                  <p>Tell ASTRA what you want to accomplish</p>
                </div>
              </div>
            </div>

            <textarea
              className="task-prompt"
              placeholder="Example: Analyze this inspection report, identify critical findings, compare them with the relevant SOP, and prepare an approval note."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />

            <div className="prompt-footer">
              <span>
                {prompt.length} characters
              </span>

              <button
                className="run-task-btn"
                onClick={runTask}
                disabled={isRunning}
              >
                {isRunning ? (
                  <>
                    <Loader2 size={17} className="spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Send size={17} />
                    Run ASTRA Task
                  </>
                )}
              </button>
            </div>
          </section>

        </div>

        {/* RIGHT COLUMN */}
        <div className="workbench-right">

          {/* AGENT PLANNING */}
          <section className="workbench-card execution-card">
            <div className="workbench-card-header">
              <div className="workbench-card-title">
                <div className="workbench-icon">
                  <Brain size={19} />
                </div>

                <div>
                  <h3>Agent Planning</h3>
                  <p>ASTRA task reasoning pipeline</p>
                </div>
              </div>

              {taskStarted && (
                <span className="running-badge">
                  {isRunning ? "RUNNING" : "COMPLETED"}
                </span>
              )}
            </div>

            <div className="pipeline">

              <div className={`pipeline-step ${taskStarted ? "done" : ""}`}>
                <div className="pipeline-number">
                  {taskStarted ? <CheckCircle2 size={17} /> : "01"}
                </div>

                <div>
                  <strong>Understand Task</strong>
                  <span>Analyze user instructions and inputs</span>
                </div>
              </div>

              <div className="pipeline-line"></div>

              <div className={`pipeline-step ${taskStarted ? "done" : ""}`}>
                <div className="pipeline-number">
                  {taskStarted ? <CheckCircle2 size={17} /> : "02"}
                </div>

                <div>
                  <strong>Create Execution Plan</strong>
                  <span>Break task into actionable steps</span>
                </div>
              </div>

              <div className="pipeline-line"></div>

              <div className={`pipeline-step ${taskStarted ? "active" : ""}`}>
                <div className="pipeline-number">
                  {taskStarted ? "03" : "03"}
                </div>

                <div>
                  <strong>Retrieve Knowledge</strong>
                  <span>Search internal RAG knowledge base</span>
                </div>
              </div>

              <div className="pipeline-line"></div>

              <div className="pipeline-step">
                <div className="pipeline-number">04</div>

                <div>
                  <strong>Execute Tools</strong>
                  <span>Use secure local tools</span>
                </div>
              </div>

            </div>
          </section>

          {/* RAG SEARCH */}
          <section className="workbench-card">
            <div className="workbench-card-header">
              <div className="workbench-card-title">
                <div className="workbench-icon">
                  <Search size={19} />
                </div>

                <div>
                  <h3>Knowledge Base</h3>
                  <p>RAG retrieval status</p>
                </div>
              </div>

              <span className="rag-count">156 sources</span>
            </div>

            <div className="rag-status">
              <div className="rag-status-icon">
                <Search size={18} />
              </div>

              <div>
                <strong>Internal Knowledge Search</strong>
                <span>
                  {taskStarted
                    ? "Searching relevant SOPs and documents..."
                    : "Ready to retrieve internal knowledge"}
                </span>
              </div>

              <span className="status-dot"></span>
            </div>

            <div className="rag-tags">
              <span>SOPs</span>
              <span>Manuals</span>
              <span>Reports</span>
              <span>Regulations</span>
            </div>
          </section>

          {/* TOOL EXECUTION */}
          <section className="workbench-card">
            <div className="workbench-card-header">
              <div className="workbench-card-title">
                <div className="workbench-icon">
                  <Wrench size={19} />
                </div>

                <div>
                  <h3>Tool Execution</h3>
                  <p>Secure local tool environment</p>
                </div>
              </div>
            </div>

            <div className="tool-list">

              <div className="tool-row">
                <div className="tool-row-icon">
                  <FileText size={16} />
                </div>

                <div>
                  <strong>Document Reader</strong>
                  <span>Local file processing</span>
                </div>

                <span className="tool-ready">Ready</span>
              </div>

              <div className="tool-row">
                <div className="tool-row-icon">
                  <Search size={16} />
                </div>

                <div>
                  <strong>RAG Search</strong>
                  <span>ChromaDB knowledge retrieval</span>
                </div>

                <span className="tool-ready">Ready</span>
              </div>

              <div className="tool-row">
                <div className="tool-row-icon">
                  <Wrench size={16} />
                </div>

                <div>
                  <strong>Code Sandbox</strong>
                  <span>Isolated execution environment</span>
                </div>

                <span className="tool-ready">Ready</span>
              </div>

            </div>
          </section>

        </div>
      </div>

      {/* OUTPUT SECTION */}
      <section className="output-section">

        <div className="output-section-header">
          <div>
            <div className="workbench-label">
              <Download size={15} />
              DELIVERABLES
            </div>

            <h2>Generate Output</h2>

            <p>
              Convert ASTRA's results into professional documents.
            </p>
          </div>
        </div>

        <div className="output-grid">

          <button className="output-card">
            <div className="output-icon word">
              <FileText size={24} />
            </div>

            <div>
              <strong>Word Document</strong>
              <span>Generate .docx report</span>
            </div>

            <Download size={17} />
          </button>

          <button className="output-card">
            <div className="output-icon excel">
              <FileSpreadsheet size={24} />
            </div>

            <div>
              <strong>Excel Spreadsheet</strong>
              <span>Generate .xlsx analysis</span>
            </div>

            <Download size={17} />
          </button>

          <button className="output-card">
            <div className="output-icon ppt">
              <Presentation size={24} />
            </div>

            <div>
              <strong>PowerPoint</strong>
              <span>Generate .pptx presentation</span>
            </div>

            <Download size={17} />
          </button>

        </div>

      </section>

    </div>
  );
}

export default Workbench;