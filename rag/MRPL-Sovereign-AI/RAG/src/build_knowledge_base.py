import os

from text_chunker import create_document_chunks
from embedder import create_embeddings
from vector_store import store_chunks


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")


# Find all PDF files in the documents folder
pdf_files = [
    file for file in os.listdir(DOCUMENTS_DIR)
    if file.lower().endswith(".pdf")
]


if not pdf_files:
    print("No PDF files found in documents folder.")
    exit()


print("Found", len(pdf_files), "PDF file(s).")


for filename in pdf_files:

    pdf_path = os.path.join(DOCUMENTS_DIR, filename)

    print("\nProcessing:", filename)

    # Extract text and create page-aware chunks
    chunks = create_document_chunks(pdf_path)

    print("Chunks created:", len(chunks))

    # Create embeddings
    texts = [chunk["text"] for chunk in chunks]

    embeddings = create_embeddings(texts)

    print("Embeddings created.")

    # Store in ChromaDB with source and page metadata
    store_chunks(
        chunks,
        embeddings,
        filename
    )

    print("Stored:", filename)


print("\nKnowledge base created successfully!")