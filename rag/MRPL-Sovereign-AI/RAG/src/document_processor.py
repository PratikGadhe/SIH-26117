import os
import json

try:
    from src.text_chunker import create_document_chunks
    from src.embedder import create_embeddings
    from src.vector_store import store_chunks,delete_document
except ModuleNotFoundError:
    from text_chunker import create_document_chunks
    from embedder import create_embeddings
    from vector_store import store_chunks,delete_document


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS_DIR = os.path.join(BASE_DIR, "documents")

# File used to remember which documents have already been processed
STATE_FILE = os.path.join(BASE_DIR, "data", "processed_documents.json")


def load_processed_documents():

    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return {}


def save_processed_documents(processed_documents):

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            processed_documents,
            file,
            indent=4
        )


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

    supported_extensions = [".pdf", ".txt", ".docx"]

    processed_documents = load_processed_documents()

    current_documents = {}

    # Find all supported documents
    for filename in os.listdir(DOCUMENTS_DIR):

        extension = os.path.splitext(filename)[1].lower()

        if extension in supported_extensions:

            file_path = os.path.join(
                DOCUMENTS_DIR,
                filename
            )

            # Get the last modified time of the file
            modified_time = os.path.getmtime(file_path)

            current_documents[filename] = modified_time

    if not current_documents:

        print("No supported documents found.")
        return []

    print(
        f"Found {len(current_documents)} document(s)."
    )

    results = []

    # Process only new or modified documents
    for filename, modified_time in current_documents.items():

        old_modified_time = processed_documents.get(filename)

        if old_modified_time == modified_time:

            print(
                f"\nSkipping unchanged document: {filename}"
            )

            continue

        file_path = os.path.join(
            DOCUMENTS_DIR,
            filename
        )

        result = process_document(file_path)

        results.append(result)

        # Remember that this version has been processed
        processed_documents[filename] = modified_time

    # Detect deleted documents
    deleted_documents = set(processed_documents.keys()) - set(
        current_documents.keys()
    )

    for filename in deleted_documents:

        print(
            f"\nDocument deleted from folder: {filename}"
        )

        # We will connect ChromaDB deletion here next.
        delete_document(filename)
        del processed_documents[filename]

    save_processed_documents(processed_documents)

    return results


if __name__ == "__main__":

    results = process_all_documents()

    print("\nDocument processing complete.")

    if results:

        for result in results:

            print(
                f"- {result['source']}: "
                f"{result['chunks']} chunks"
            )

    else:

        print("No new or modified documents to process.")
