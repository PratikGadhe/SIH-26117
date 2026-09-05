import React, { useState } from "react";
import {
  FileText,
  Upload,
  ScanSearch,
  Eye,
  Brain,
  CheckCircle2,
  Clock3,
  AlertTriangle,
  X,
  Image as ImageIcon,
  FileSearch,
  Database,
  ShieldCheck,
} from "lucide-react";

import "./DocumentAnalysis.css";

function DocumentAnalysis() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (file) {
      setSelectedFile(file);
      setAnalysisComplete(false);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    setAnalysisComplete(false);
  };

  const analyzeDocument = () => {
    if (!selectedFile) {
      alert("Please upload a document first.");
      return;
    }

    setIsAnalyzing(true);

    setTimeout(() => {
      setIsAnalyzing(false);
      setAnalysisComplete(true);
    }, 3000);
  };

  return (
    <div className="document-analysis-page">

      {/* PAGE INTRO */}
      <div className="document-hero">

        <div className="document-hero-content">

          <div className="document-label">
            <ShieldCheck size={15} />
            MULTIMODAL DOCUMENT INTELLIGENCE
          </div>

          <h1>Document Analysis</h1>

          <p>
            Upload confidential industrial documents and let ASTRA
            understand text, scanned pages, images, and structured
            information using local AI.
          </p>

        </div>

        <div className="document-security">
          <span className="document-security-dot"></span>
          Processed Locally
        </div>

      </div>


      {/* UPLOAD + ANALYSIS */}
      <div className="document-main-grid">

        {/* LEFT: UPLOAD */}
        <section className="document-card">

          <div className="document-card-header">

            <div className="document-card-title">

              <div className="document-icon">
                <Upload size={19} />
              </div>

              <div>
                <h3>Upload Document</h3>
                <p>
                  Add a document for multimodal analysis
                </p>
              </div>

            </div>

            <span className="supported-badge">
              MULTIMODAL
            </span>

          </div>


          {!selectedFile ? (

            <label className="document-upload-zone">

              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.xlsx,.csv"
                onChange={handleFileChange}
              />

              <div className="document-upload-icon">
                <Upload size={27} />
              </div>

              <strong>
                Drop your document here
              </strong>

              <span>
                or click to browse from your computer
              </span>

              <small>
                PDF · DOCX · TXT · PNG · JPG · XLSX · CSV
              </small>

            </label>

          ) : (

            <div className="document-selected-file">

              <div className="selected-document-icon">
                <FileText size={23} />
              </div>

              <div className="selected-document-info">

                <strong>
                  {selectedFile.name}
                </strong>

                <span>
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </span>

              </div>

              <button
                className="document-remove-button"
                onClick={removeFile}
              >
                <X size={17} />
              </button>

            </div>

          )}


          <div className="document-types">

            <div className="document-type">
              <FileText size={16} />
              <span>Text</span>
            </div>

            <div className="document-type">
              <ScanSearch size={16} />
              <span>Scanned</span>
            </div>

            <div className="document-type">
              <ImageIcon size={16} />
              <span>Images</span>
            </div>

            <div className="document-type">
              <Database size={16} />
              <span>Tables</span>
            </div>

          </div>


          <button
            className="analyze-document-button"
            onClick={analyzeDocument}
            disabled={isAnalyzing}
          >

            {isAnalyzing ? (
              <>
                <Clock3 size={17} />
                Analyzing Locally...
              </>
            ) : (
              <>
                <ScanSearch size={17} />
                Analyze with ASTRA
              </>
            )}

          </button>

        </section>


        {/* RIGHT: ANALYSIS PIPELINE */}
        <section className="document-card">

          <div className="document-card-header">

            <div className="document-card-title">

              <div className="document-icon">
                <Brain size={19} />
              </div>

              <div>
                <h3>Analysis Pipeline</h3>
                <p>
                  ASTRA multimodal processing
                </p>
              </div>

            </div>

            {analysisComplete && (
              <span className="analysis-complete-badge">
                COMPLETE
              </span>
            )}

          </div>


          <div className="analysis-pipeline">

            <PipelineStep
              number="01"
              icon={<FileSearch size={17} />}
              title="Document Detection"
              description="Identify format and document structure"
              active={isAnalyzing || analysisComplete}
              complete={analysisComplete}
            />

            <PipelineConnector />

            <PipelineStep
              number="02"
              icon={<ScanSearch size={17} />}
              title="OCR & Text Extraction"
              description="Extract text from digital and scanned pages"
              active={isAnalyzing || analysisComplete}
              complete={analysisComplete}
            />

            <PipelineConnector />

            <PipelineStep
              number="03"
              icon={<Eye size={17} />}
              title="Vision Understanding"
              description="Understand images, diagrams and visual content"
              active={isAnalyzing || analysisComplete}
              complete={analysisComplete}
            />

            <PipelineConnector />

            <PipelineStep
              number="04"
              icon={<Brain size={17} />}
              title="Semantic Analysis"
              description="Identify entities, findings and key information"
              active={analysisComplete}
              complete={analysisComplete}
            />

            <PipelineConnector />

            <PipelineStep
              number="05"
              icon={<Database size={17} />}
              title="Knowledge Preparation"
              description="Prepare extracted information for RAG"
              active={analysisComplete}
              complete={analysisComplete}
            />

          </div>

        </section>

      </div>


      {/* ANALYSIS RESULTS */}
      <section className="document-results-card">

        <div className="results-header">

          <div>

            <div className="document-label results-label">
              <Brain size={15} />
              AI ANALYSIS RESULTS
            </div>

            <h2>
              Extracted Information
            </h2>

            <p>
              Structured information identified from the document.
            </p>

          </div>

          {analysisComplete && (
            <div className="result-status">
              <CheckCircle2 size={16} />
              Analysis Complete
            </div>
          )}

        </div>


        {!analysisComplete ? (

          <div className="results-empty">

            <div className="results-empty-icon">
              <FileSearch size={27} />
            </div>

            <strong>
              No analysis available yet
            </strong>

            <span>
              Upload a document and click
              <b> Analyze with ASTRA </b>
              to view extracted information.
            </span>

          </div>

        ) : (

          <div className="analysis-results-grid">

            {/* DOCUMENT SUMMARY */}

            <div className="result-panel">

              <div className="result-panel-title">
                <FileText size={17} />
                Document Summary
              </div>

              <div className="result-content">

                <div className="result-row">
                  <span>Document Type</span>
                  <strong>Inspection Report</strong>
                </div>

                <div className="result-row">
                  <span>Pages</span>
                  <strong>12</strong>
                </div>

                <div className="result-row">
                  <span>Text Extracted</span>
                  <strong>8,426 characters</strong>
                </div>

                <div className="result-row">
                  <span>Images Detected</span>
                  <strong>7</strong>
                </div>

              </div>

            </div>


            {/* KEY FINDINGS */}

            <div className="result-panel">

              <div className="result-panel-title">
                <AlertTriangle size={17} />
                Key Findings
              </div>

              <div className="finding-list">

                <div className="finding-item high">
                  <span className="finding-indicator"></span>

                  <div>
                    <strong>
                      Equipment maintenance overdue
                    </strong>

                    <p>
                      Maintenance interval exceeds recommended schedule.
                    </p>
                  </div>
                </div>

                <div className="finding-item medium">
                  <span className="finding-indicator"></span>

                  <div>
                    <strong>
                      Safety inspection required
                    </strong>

                    <p>
                      Additional inspection is recommended.
                    </p>
                  </div>
                </div>

                <div className="finding-item normal">
                  <span className="finding-indicator"></span>

                  <div>
                    <strong>
                      Operating parameters within range
                    </strong>

                    <p>
                      Recorded values match expected operating limits.
                    </p>
                  </div>
                </div>

              </div>

            </div>


            {/* ENTITIES */}

            <div className="result-panel">

              <div className="result-panel-title">
                <Brain size={17} />
                Detected Entities
              </div>

              <div className="entity-list">

                <span>Equipment</span>
                <span>Inspection Date</span>
                <span>Maintenance</span>
                <span>Safety</span>
                <span>Operating Parameters</span>
                <span>SOP-102</span>

              </div>

            </div>


            {/* RAG STATUS */}

            <div className="result-panel">

              <div className="result-panel-title">
                <Database size={17} />
                RAG Preparation
              </div>

              <div className="rag-ready-box">

                <CheckCircle2 size={19} />

                <div>
                  <strong>
                    Ready for Knowledge Retrieval
                  </strong>

                  <p>
                    Extracted content can now be indexed
                    and searched by ASTRA.
                  </p>
                </div>

              </div>

            </div>

          </div>

        )}

      </section>

    </div>
  );
}


/* PIPELINE STEP */

function PipelineStep({
  number,
  icon,
  title,
  description,
  active,
  complete,
}) {
  return (
    <div
      className={`analysis-step ${
        active ? "active" : ""
      } ${complete ? "complete" : ""}`}
    >

      <div className="analysis-step-number">

        {complete ? (
          <CheckCircle2 size={17} />
        ) : (
          number
        )}

      </div>

      <div className="analysis-step-icon">
        {icon}
      </div>

      <div className="analysis-step-content">

        <strong>
          {title}
        </strong>

        <span>
          {description}
        </span>

      </div>

      {complete && (
        <span className="step-done">
          Done
        </span>
      )}

    </div>
  );
}


/* PIPELINE CONNECTOR */

function PipelineConnector() {
  return (
    <div className="analysis-connector"></div>
  );
}


export default DocumentAnalysis;