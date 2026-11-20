import httpx
from typing import List

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using the local Ollama model."""

    if not texts:
        return []

    response = httpx.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120.0,
    )

    response.raise_for_status()

    result = response.json()
    embeddings = result.get("embeddings", [])

    if len(embeddings) != len(texts):
        raise ValueError("Embedding count does not match input count.")

    if not embeddings or any(not embedding for embedding in embeddings):
        raise ValueError("Ollama returned empty embeddings.")

    dimensions = len(embeddings[0])

    if any(len(embedding) != dimensions for embedding in embeddings):
        raise ValueError("Inconsistent embedding dimensions.")

    return embeddings
