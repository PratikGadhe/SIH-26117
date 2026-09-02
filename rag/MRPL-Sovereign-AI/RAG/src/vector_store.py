import os
import chromadb


# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "chroma_db")


# Connect to ChromaDB
client = chromadb.PersistentClient(path=DB_PATH)


# Create or connect to the knowledge collection
collection = client.get_or_create_collection(
    name="mrpl_knowledge"
)


def store_chunks(chunks, embeddings, source):

    documents = []
    ids = []
    metadatas = []

    for i, chunk in enumerate(chunks):

        documents.append(chunk["text"])

        ids.append(f"{source}_chunk_{i}")

        metadatas.append({
            "source": source,
            "page": chunk["page"]
        })

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )

    print(f"Stored {len(chunks)} chunks in ChromaDB.")


# Test ChromaDB
if __name__ == "__main__":

    print("ChromaDB is ready!")
    print("Collection name:", collection.name)
    print("Number of stored chunks:", collection.count())