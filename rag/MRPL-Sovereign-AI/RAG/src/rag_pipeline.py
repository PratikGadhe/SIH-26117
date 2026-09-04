from search import search_documents
import ollama


def ask_rag(query, top_k=3):
    # Retrieve relevant documents
    results = search_documents(query, top_k=top_k)

    # Build context
    context = ""

    for result in results:
        context += (
            f"Source: {result['source']}\n"
            f"Page: {result['page']}\n"
            f"Content: {result['content']}\n\n"
        )

    # Prompt for the local LLM
    prompt = f"""
You are an AI assistant working with a private knowledge base.

Answer the question using ONLY the provided context.

If the answer is not found in the context, say:
"I could not find this information in the knowledge base."

Mention the source and page when possible.

Context:
{context}

Question:
{query}
"""

    # Generate answer using local LLM
    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = response["message"]["content"]

    # Return structured result
    return {
        "answer": answer,
        "sources": [
            {
                "source": result["source"],
                "page": result["page"]
            }
            for result in results
        ],
        "context": results
    }


if __name__ == "__main__":
    question = input("Enter your question: ")

    result = ask_rag(question)

    print("\nRAG ANSWER\n")
    print(result["answer"])

    print("\nSOURCES\n")

    for source in result["sources"]:
        print(
            f"- {source['source']} | Page {source['page']}"
        )