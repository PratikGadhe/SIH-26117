from search import search_documents


query = "What security features does OneDrive provide?"

results = search_documents(query, top_k=3)


print("\nRAG RESULTS\n")

for result in results:

    print("Source:", result["source"])
    print("Page:", result["page"])
    print("Content:")
    print(result["content"])
    print("-" * 50)