# SIH 26117 — Cognivault

## Sovereign On-Premise Agentic AI Workbench

This project is developed for Smart India Hackathon 2026, Problem Statement 26117.

### Technology Stack

- Frontend: React + Vite
- Backend: Python + FastAPI
- Agentic AI: LangGraph
- LLM Interface: Ollama
- Text Model: Qwen3 4B Instruct
- Vision Model: Qwen3-VL 4B Instruct
- RAG: ChromaDB
- Embeddings: Sentence Transformers
- PDF Processing: PyMuPDF
- OCR: Tesseract / PaddleOCR
- Database: SQLite
- Authentication: JWT
- Authorization: RBAC
- Deployment: Docker

### Project Structure

```text
frontend/     → React frontend
backend/      → FastAPI backend
agents/       → LangGraph agent workflows
rag/          → Document processing and retrieval
vision/       → Multimodal AI
database/     → Database related code
docs/         → Architecture and project documentation
tests/        → Tests