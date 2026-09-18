import {
  Brain,
  Database,
  FileSearch,
  FileText,
  Image as ImageIcon,
  ScanSearch,
  ShieldCheck,
  Upload,
} from "lucide-react";
import "./DocumentAnalysis.css";

function DocumentAnalysis() {
  return (
    <div className="document-analysis-page">
      <div className="document-hero">
        <div className="document-hero-content">
          <div className="document-label">
            <ShieldCheck size={15} /> SPECIALIZED DOCUMENT WORKSPACE
          </div>
          <h1>Document Analysis</h1>
          <p>
            This workspace is reserved for secure PDF, scanned-document, and
            engineering-image analysis when a trusted browser upload API is available.
          </p>
        </div>
        <div className="document-security">
          <span className="document-security-dot" /> Integration pending
        </div>
      </div>

      <div className="document-main-grid">
        <section className="document-card">
          <div className="document-card-header">
            <div className="document-card-title">
              <div className="document-icon"><Upload size={19} /></div>
              <div>
                <h3>Browser upload</h3>
                <p>Not available in the current backend contract</p>
              </div>
            </div>
            <span className="supported-badge">PENDING</span>
          </div>

          <div className="document-upload-zone pending-upload-zone" aria-disabled="true">
            <div className="document-upload-icon"><Upload size={27} /></div>
            <strong>Upload integration is pending backend support</strong>
            <span>No file is selected, uploaded, or analyzed by this screen.</span>
            <small>Requires a trusted upload/reference API and server-side validation.</small>
          </div>

          <div className="document-types">
            <div className="document-type"><FileText size={16} /><span>PDF</span></div>
            <div className="document-type"><ScanSearch size={16} /><span>Scanned</span></div>
            <div className="document-type"><ImageIcon size={16} /><span>Images</span></div>
            <div className="document-type"><Database size={16} /><span>Tables</span></div>
          </div>

          <button className="analyze-document-button" disabled>
            <ScanSearch size={17} /> Analyze with VYASA
          </button>
        </section>

        <section className="document-card">
          <div className="document-card-header">
            <div className="document-card-title">
              <div className="document-icon"><Brain size={19} /></div>
              <div><h3>Future analysis pipeline</h3><p>No execution is currently performed</p></div>
            </div>
          </div>

          <div className="analysis-pipeline">
            <PendingStep number="01" title="Validated upload" description="Receive a trusted server-owned document reference" />
            <div className="analysis-connector" />
            <PendingStep number="02" title="OCR and vision" description="Invoke the existing local vision boundary" />
            <div className="analysis-connector" />
            <PendingStep number="03" title="Normalized result" description="Return real extracted text and analysis" />
          </div>
        </section>
      </div>

      <section className="document-results-card">
        <div className="results-header">
          <div>
            <div className="document-label results-label"><Brain size={15} /> ANALYSIS RESULTS</div>
            <h2>No document analysis yet</h2>
            <p>Results will appear only after the backend processes a real uploaded document.</p>
          </div>
        </div>
        <div className="results-empty">
          <div className="results-empty-icon"><FileSearch size={27} /></div>
          <strong>Pending backend upload support</strong>
          <span>No analysis findings, entities, page counts, or citations are fabricated.</span>
        </div>
      </section>
    </div>
  );
}

function PendingStep({ number, title, description }) {
  return (
    <div className="analysis-step">
      <div className="analysis-step-number">{number}</div>
      <div className="analysis-step-content"><strong>{title}</strong><span>{description}</span></div>
    </div>
  );
}

export default DocumentAnalysis;
