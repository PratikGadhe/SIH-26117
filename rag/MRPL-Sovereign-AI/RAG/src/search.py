import os
import chromadb
from sentence_transformers import SentenceTransformer


# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "chroma_db")


# Connect to ChromaDB
client = chromadb.PersistentClient(path=DB_PATH)

collection = client.get_collection(
    name="mrpl_knowledge"
)


# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


def search_documents(query, top_k=3, max_distance=1.2):

    # Convert the question into an embedding
    query_embedding = model.encode([query])

    # Search ChromaDB
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k * 2,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    clean_results = []
    seen_content = set()

    # Process search results
    for i, document in enumerate(results["documents"][0]):

        # Remove extra spaces
        normalized_content = " ".join(document.split())

        # Remove exact duplicate chunks
        if normalized_content in seen_content:
            continue

        seen_content.add(normalized_content)

        # Get metadata and similarity distance
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        # Ignore results that are too far from the question
        if distance > max_distance:
            continue

        # Store clean result
        clean_results.append({
            "content": document,
            "source": metadata["source"],
            "page": metadata["page"],
            "distance": distance
        })

        # Stop after getting required number of results
        if len(clean_results) >= top_k:
            break

    return clean_results


# Test the search system
if __name__ == "__main__":

    question = input("Enter your question: ")

    results = search_documents(question)

    print("\nRelevant information:\n")

    if not results:
        print("No sufficiently relevant information found.")

    for i, result in enumerate(results):

        print(f"--- Result {i + 1} ---")
        print("Source:", result["source"])
        print("Page:", result["page"])
        print("Distance:", result["distance"])
        print("Content:")
        print(result["content"])
        print()