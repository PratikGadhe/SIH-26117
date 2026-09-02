from __future__ import annotations

from typing import Any, Dict, List, Optional


class RAGService:
    """Lightweight retrieval layer for project documents."""

    def __init__(self, documents: Optional[List[str]] = None):
        self.documents: List[str] = documents or []
        self.metadata: List[Dict[str, Any]] = [{"source": "memory"} for _ in self.documents]

    def add_documents(self, documents: List[str], metadata: Optional[List[Dict[str, Any]]] = None) -> None:
        self.documents.extend(documents)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend({"source": "memory"} for _ in documents)

    def query(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        if not self.documents:
            return {
                "status": "empty",
                "query": query_text,
                "results": [],
                "answer": "No documents loaded yet. Add documents before querying.",
            }

        ranked = []
        query_tokens = {token.lower() for token in query_text.split() if token.strip()}

        for index, document in enumerate(self.documents):
            doc_tokens = {token.lower() for token in document.split() if token.strip()}
            score = len(query_tokens & doc_tokens)
            ranked.append({
                "score": score,
                "text": document,
                "metadata": self.metadata[index],
            })

        ranked.sort(key=lambda item: item["score"], reverse=True)
        top_results = ranked[:top_k]
        answer = "\n\n".join(item["text"] for item in top_results if item["score"] > 0)

        if not answer:
            answer = top_results[0]["text"] if top_results else "No relevant match found."

        return {
            "status": "success",
            "query": query_text,
            "results": top_results,
            "answer": answer,
        }
