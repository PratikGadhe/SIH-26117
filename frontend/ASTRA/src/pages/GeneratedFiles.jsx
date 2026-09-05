import {
  Archive,
  FileCode2,
  FileSpreadsheet,
  FileText,
  FolderOpen,
  ShieldCheck,
} from "lucide-react";
import "./GeneratedFiles.css";

function GeneratedFiles() {
  return (
    <div className="generated-page">
      <section className="gf-hero">
        <div>
          <span className="gf-eyebrow">FUTURE LOCAL DELIVERABLE MANAGEMENT</span>
          <h1>Generated Files</h1>
          <p>
            This product area will contain real documents, spreadsheets,
            presentations, and code produced by supported Cognivault workflows.
          </p>
        </div>
        <div className="gf-local-badge">
          <ShieldCheck size={17} /><span>Backend support pending</span>
        </div>
      </section>

      <section className="gf-stat-grid">
        <PendingStat icon={<Archive size={19} />} label="Total Files" />
        <PendingStat icon={<FileText size={19} />} label="Documents" />
        <PendingStat icon={<FileSpreadsheet size={19} />} label="Spreadsheets" />
        <PendingStat icon={<FileCode2 size={19} />} label="Code Files" />
      </section>

      <div className="gf-main-grid">
        <section className="gf-files-card">
          <div className="gf-card-header">
            <div>
              <span className="gf-eyebrow light">DELIVERABLES</span>
              <h2>ASTRA Generated Files</h2>
            </div>
            <span className="gf-result-count">0 available</span>
          </div>

          <div className="gf-file-list">
            <div className="gf-empty truthful-file-empty">
              <FolderOpen size={34} />
              <strong>No generated-file backend is available</strong>
              <span>
                No sample records or placeholder downloads are shown. Files will
                appear after generation, storage, listing, and download APIs exist.
              </span>
            </div>
          </div>
        </section>

        <aside className="gf-side">
          <div className="gf-pipeline-card">
            <span className="gf-eyebrow light">REQUIRED BACKEND CONTRACT</span>
            <h2>Future deliverable lifecycle</h2>
            <div className="gf-pipeline">
              <PipelineStep number="1" title="Generate" detail="Create a real artifact from an agent task" />
              <div className="gf-pipe-line" />
              <PipelineStep number="2" title="Store" detail="Persist it under a trusted artifact identifier" />
              <div className="gf-pipe-line" />
              <PipelineStep number="3" title="Retrieve" detail="Authorize listing and controlled download" />
            </div>
          </div>

          <div className="gf-security-card">
            <div className="gf-security-icon"><ShieldCheck size={21} /></div>
            <div>
              <strong>No placeholder files</strong>
              <p>Delete and download actions remain unavailable until the backend can enforce authorization and audit them.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function PendingStat({ icon, label }) {
  return (
    <div className="gf-stat-card">
      <div className="gf-stat-icon">{icon}</div>
      <div><span>{label}</span><strong>—</strong><small>Not yet available</small></div>
    </div>
  );
}

function PipelineStep({ number, title, detail }) {
  return (
    <div className="gf-pipe-step">
      <span>{number}</span>
      <div><strong>{title}</strong><small>{detail}</small></div>
    </div>
  );
}

export default GeneratedFiles;
