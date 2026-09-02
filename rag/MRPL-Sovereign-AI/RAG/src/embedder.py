from sentence_transformers import SentenceTransformer


# Load the embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(chunks):
    embeddings = model.encode(chunks)

    return embeddings


if __name__ == "__main__":

    test_chunks = [
        "Safety inspection is required before starting maintenance.",
        "Equipment must be checked regularly.",
        "The weather today is sunny."
    ]

    embeddings = create_embeddings(test_chunks)

    print("Number of chunks:", len(embeddings))
    print("Embedding size:", len(embeddings[0]))