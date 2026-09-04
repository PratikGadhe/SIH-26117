from search import search_documents
from document_processor import process_document


def search_documents_for_agent(query, top_k=3):
    """
    Search the local knowledge base.

    Returns relevant document content along with
    source and page information.
    """

    results = search_documents(
        query,
        top_k=top_k
    )

    return results


def process_document_for_agent(file_path):
    """
    Process a newly uploaded document and add it
    to the local knowledge base.
    """

    return process_document(file_path)


if __name__ == "__main__":

    print("RAG interface is ready.")

    query = input("Enter your question: ")

    results = search_documents_for_agent(query)

    if not results:

        print("\nNo relevant information found.")

    else:

        print("\nRelevant information:\n")

        for i, result in enumerate(results, start=1):

            print(f"--- Result {i} ---")
            print(f"Source: {result['source']}")
            print(f"Page: {result['page']}")
            print(f"Content: {result['content']}")
            print()