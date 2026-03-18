import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from dotenv import load_dotenv
import os
import hashlib

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─────────────────────────────────────────
# Set to True for demo without API key
# Must match MOCK_MODE in main.py
# ─────────────────────────────────────────
MOCK_MODE = True


# ─────────────────────────────────────────
# STEP 1: Convert text to vectors (embeddings)
# ─────────────────────────────────────────

def get_embedding(text: str) -> list:
    """
    Real mode: sends text to OpenAI, gets back a vector of numbers.
    Mock mode: generates a fake but consistent vector using a hash.

    The hash trick:
    - Same text always produces the same vector (deterministic)
    - Different texts produce different vectors
    - Vectors are normalized so cosine similarity still works
    - No API call needed!
    """
    if MOCK_MODE:
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        vector = rng.randn(1536)
        vector = vector / np.linalg.norm(vector)
        return vector.tolist()

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


# ─────────────────────────────────────────
# STEP 2: Build the knowledge base
# ─────────────────────────────────────────

def build_knowledge_base(documents: list) -> list:
    """
    Takes our list of documents and converts each one to a vector.
    We do this ONCE at startup, not on every query.
    Returns the documents with their embeddings attached.
    """
    if MOCK_MODE:
        print("Mock mode: building knowledge base with fake embeddings...")
    else:
        print("Building knowledge base - embedding documents...")

    embedded_docs = []

    for doc in documents:
        embedding = get_embedding(doc["content"])
        embedded_docs.append({
            **doc,              # copy all existing fields (id, title, content)
            "embedding": embedding  # add the vector
        })
        print(f"  Embedded: {doc['title']}")

    print(f"Knowledge base ready with {len(embedded_docs)} documents!")
    return embedded_docs


# ─────────────────────────────────────────
# STEP 3: Find similar documents
# ─────────────────────────────────────────

def retrieve(query: str, knowledge_base: list, top_k: int = 3) -> list:
    """
    Given a user query, find the top_k most similar documents.

    How it works:
    1. Convert the query to a vector
    2. Compare it against every document vector using cosine similarity
    3. Return the top_k most similar ones
    """

    # Convert the user's question to a vector
    query_embedding = get_embedding(query)

    # Get all document vectors as a 2D array
    doc_embeddings = np.array([doc["embedding"] for doc in knowledge_base])

    # Calculate similarity between query and every document
    # 1.0 = identical meaning, 0 = unrelated, -1 = opposite
    similarities = cosine_similarity(
        [query_embedding],  # query vector (1 x embedding_size)
        doc_embeddings      # all doc vectors (num_docs x embedding_size)
    )[0]                    # [0] gets the first (and only) row

    # Get indices of top_k highest similarity scores
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append({
            "id": knowledge_base[idx]["id"],
            "title": knowledge_base[idx]["title"],
            "content": knowledge_base[idx]["content"],
            "similarity": round(float(similarities[idx]), 4)
        })

    return results