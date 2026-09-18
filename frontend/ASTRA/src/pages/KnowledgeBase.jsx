import { useState } from "react";
import {
  FileText,
  Scissors,
  Brain,
  Database,
  Search,
  BookOpen,
  Upload,
  CheckCircle2,
  Server,
  Layers3,
  ArrowDown
} from "lucide-react";

import "./KnowledgeBase.css";

function KnowledgeBase() {
  const [documents, setDocuments] = useState([
    {
      name: "Safety_SOP.pdf",
      type: "PDF",
      chunks: 42,
      status: "Embedded"
    },
    {
      name: "Equipment_Manual.pdf",
      type: "PDF",
      chunks: 68,
      status: "Embedded"
    },
    {
      name: "Maintenance_Guide.pdf",
      type: "PDF",
      chunks: 51,
      status: "Embedded"
    },
    {
      name: "Inspection_Report.pdf",
      type: "PDF",
      chunks: 34,
      status: "Embedded"
    }
  ]);

  const [query, setQuery] = useState("");

  const [searched, setSearched] = useState(false);

  const handleUpload = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    setDocuments((prev) => [
      ...prev,
      {
        name: file.name,
        type: file.name.split(".").pop().toUpperCase(),
        chunks: "--",
        status: "Processing"
      }
    ]);
  };

  const handleSearch = () => {
    if (!query.trim()) return;

    setSearched(true);
  };

  return (
    <div className="knowledge-page">

      {/* HERO */}
      <section className="knowledge-hero">

        <div>
          <div className="knowledge-eyebrow">
            <Database size={15} />
            LOCAL KNOWLEDGE INTELLIGENCE
          </div>

          <h1>Knowledge Base</h1>

          <p>
            Secure document storage, local embeddings and semantic retrieval
            powered by ChromaDB.
          </p>
        </div>

        <div className="local-status">
          <CheckCircle2 size={17} />
          <div>
            <strong>Local Mode</strong>
            <span>No external API calls</span>
          </div>
        </div>

      </section>


      {/* PIPELINE */}
      <section className="pipeline-card">

        <div className="section-heading">
          <div>
            <h2>Knowledge Retrieval Pipeline</h2>
            <p>
              How VYASA converts documents into searchable knowledge.
            </p>
          </div>

          <span className="pipeline-status">
            <span className="status-dot"></span>
            SYSTEM READY
          </span>
        </div>


        <div className="pipeline">

          <PipelineStep
            icon={<FileText />}
            number="01"
            title="Documents"
            description="PDF, DOCX, TXT & images"
          />

          <Arrow />

          <PipelineStep
            icon={<Scissors />}
            number="02"
            title="Chunking"
            description="Split into meaningful sections"
          />

          <Arrow />

          <PipelineStep
            icon={<Brain />}
            number="03"
            title="Embeddings"
            description="Convert text into vectors"
          />

          <Arrow />

          <PipelineStep
            icon={<Database />}
            number="04"
            title="ChromaDB"
            description="Store vectors locally"
          />

          <Arrow />

          <PipelineStep
            icon={<Search />}
            number="05"
            title="Semantic Search"
            description="Find relevant meaning"
          />

          <Arrow />

          <PipelineStep
            icon={<BookOpen />}
            number="06"
            title="Context"
            description="Return relevant knowledge"
          />

        </div>

      </section>


      {/* TWO COLUMN AREA */}
      <div className="knowledge-grid">

        {/* DOCUMENTS */}
        <section className="kb-card">

          <div className="card-header">

            <div>
              <h2>Knowledge Documents</h2>
              <p>Documents indexed into the local knowledge base.</p>
            </div>

            <label className="upload-button">
              <Upload size={16} />
              Add Document

              <input
                type="file"
                accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
                onChange={handleUpload}
              />
            </label>

          </div>


          <div className="document-list">

            {documents.map((doc, index) => (

              <div className="document-row" key={index}>

                <div className="document-icon">
                  <FileText size={20} />
                </div>

                <div className="document-info">

                  <strong>{doc.name}</strong>

                  <span>
                    {doc.type} • {doc.chunks} chunks
                  </span>

                </div>

                <div className="document-status">

                  {doc.status === "Embedded" ? (
                    <>
                      <CheckCircle2 size={15} />
                      Embedded
                    </>
                  ) : (
                    <>
                      <span className="processing-dot"></span>
                      Processing
                    </>
                  )}

                </div>

              </div>

            ))}

          </div>

        </section>


        {/* CHROMADB */}
        <section className="kb-card chroma-card">

          <div className="chroma-top">

            <div className="chroma-icon">
              <Database size={24} />
            </div>

            <div>
              <h2>ChromaDB</h2>
              <p>Local vector database</p>
            </div>

          </div>


          <div className="db-status">
            <span className="status-dot"></span>
            Connected & Ready
          </div>


          <div className="db-stats">

            <div>
              <strong>156</strong>
              <span>Documents</span>
            </div>

            <div>
              <strong>1,284</strong>
              <span>Chunks</span>
            </div>

            <div>
              <strong>384</strong>
              <span>Vector Size</span>
            </div>

          </div>


          <div className="storage-bar">

            <div className="storage-label">
              <span>Vector Storage</span>
              <span>68%</span>
            </div>

            <div className="storage-track">
              <div className="storage-fill"></div>
            </div>

          </div>


          <div className="database-location">
            <Server size={16} />
            <span>./chroma_db/</span>
          </div>

        </section>

      </div>


      {/* SEARCH */}
      <section className="search-card">

        <div className="search-heading">

          <div className="search-title-icon">
            <Search size={21} />
          </div>

          <div>
            <h2>Semantic Search</h2>
            <p>
              Search by meaning instead of exact keywords.
            </p>
          </div>

        </div>


        <div className="search-box">

          <Search size={19} />

          <input
            type="text"
            placeholder="Ask something about your internal documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSearch();
              }
            }}
          />

          <button onClick={handleSearch}>
            Search Knowledge
          </button>

        </div>

      </section>


      {/* RETRIEVED CONTEXT */}
      <section className="retrieval-card">

        <div className="retrieval-header">

          <div>
            <h2>
              <BookOpen size={20} />
              Retrieved Context
            </h2>

            <p>
              Most relevant knowledge retrieved from ChromaDB.
            </p>
          </div>

          {searched && (
            <span className="results-count">
              3 relevant chunks
            </span>
          )}

        </div>


        {!searched ? (

          <div className="empty-retrieval">

            <Search size={32} />

            <h3>No search performed yet</h3>

            <p>
              Enter a question above to see retrieved document context.
            </p>

          </div>

        ) : (

          <div className="retrieved-results">

            <RetrievedResult
              rank="01"
              file="Safety_SOP.pdf"
              section="Section 4.2 — Safety Inspection"
              score="94%"
              text="Safety inspection must be completed before operating equipment. All critical components should be verified according to the approved inspection procedure."
            />

            <RetrievedResult
              rank="02"
              file="Maintenance_Guide.pdf"
              section="Section 7 — Inspection Schedule"
              score="87%"
              text="Equipment maintenance and periodic inspection must follow the maintenance schedule defined for the specific equipment category."
            />

            <RetrievedResult
              rank="03"
              file="Equipment_Manual.pdf"
              section="Section 3 — Operating Safety"
              score="81%"
              text="Operators must verify safety conditions and operating parameters before starting the equipment."
            />

          </div>

        )}

      </section>


      {/* FOOTER PIPELINE */}
      <div className="knowledge-footer">

        <div>
          <Layers3 size={17} />
          <span>Documents</span>
        </div>

        <span>→</span>

        <div>
          <Brain size={17} />
          <span>Embeddings</span>
        </div>

        <span>→</span>

        <div>
          <Database size={17} />
          <span>ChromaDB</span>
        </div>

        <span>→</span>

        <div>
          <Search size={17} />
          <span>Semantic Search</span>
        </div>

        <span>→</span>

        <div>
          <BookOpen size={17} />
          <span>Retrieved Context</span>
        </div>

      </div>

    </div>
  );
}


/* PIPELINE STEP */

function PipelineStep({ icon, number, title, description }) {
  return (
    <div className="pipeline-step">

      <div className="pipeline-number">{number}</div>

      <div className="pipeline-icon">
        {icon}
      </div>

      <strong>{title}</strong>

      <span>{description}</span>

    </div>
  );
}


/* ARROW */

function Arrow() {
  return (
    <div className="pipeline-arrow">
      <ArrowDown size={18} />
    </div>
  );
}


/* RETRIEVED RESULT */

function RetrievedResult({
  rank,
  file,
  section,
  score,
  text
}) {
  return (
    <div className="retrieved-result">

      <div className="result-rank">
        {rank}
      </div>

      <div className="result-main">

        <div className="result-top">

          <div>

            <strong>{file}</strong>

            <span>{section}</span>

          </div>

          <div className="similarity">

            <span>Similarity</span>
            <strong>{score}</strong>

          </div>

        </div>

        <p>
          {text}
        </p>

      </div>

    </div>
  );
}

export default KnowledgeBase;
