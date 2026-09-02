import os

try:
    from src.text_chunker import create_document_chunks
    from src.embedder import create_embeddings
    from src.vector_store import store_chunks
except ModuleNotFoundError:
    from text_chunker import create_document_chunks
    from embedder import create_embeddings
    from vector_store import store_chunks


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")


def process_document(file_path):

    source = os.path.basename(file_path)

    print(f"\nProcessing: {source}")

    chunks = create_document_chunks(file_path)

    print(f"Chunks created: {len(chunks)}")

    if not chunks:
        print("No text found in document.")
        return {
            "source": source,
            "chunks": 0
        }

    texts = [chunk["text"] for chunk in chunks]

    embeddings = create_embeddings(texts)

    print("Embeddings created.")

    store_chunks(
        chunks,
        embeddings,
        source
    )

    print(f"Successfully added: {source}")

    return {
        "source": source,
        "chunks": len(chunks)
    }


def process_all_documents():

    supported_files = []

    for filename in os.listdir(DOCUMENTS_DIR):

        extension = os.path.splitext(filename)[1].lower()

        if extension in [".pdf", ".txt", ".docx"]:
            supported_files.append(filename)

    if not supported_files:
        print("No supported documents found.")
        return []

    print(
        f"Found {len(supported_files)} document(s)."
    )

    results = []

    for filename in supported_files:

        file_path = os.path.join(
            DOCUMENTS_DIR,
            filename
        )

        result = process_document(file_path)

        results.append(result)

    return results


if __name__ == "__main__":

    results = process_all_documents()

    print("\nDocument processing complete.")

    for result in results:

        print(
            f"- {result['source']}: "
            f"{result['chunks']} chunks"
        )