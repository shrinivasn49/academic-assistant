import json
import os
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np

from app.services.embedding_service import generate_embeddings


BACKEND_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BACKEND_DIR / "storage" / "processed"
INDEX_DIR = BACKEND_DIR / "storage" / "indexes"

INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Keep the existing threshold initially.
# We will tune it after evaluating actual retrieval scores.
MIN_SIMILARITY_SCORE = float(os.getenv("RAG_MIN_SIMILARITY_SCORE", "0.30"))


def validate_embeddings(embeddings: list) -> np.ndarray:
    """Validate and normalize embedding vectors."""

    vectors = np.asarray(embeddings, dtype=np.float32)

    if vectors.ndim != 2 or vectors.shape[0] == 0:
        raise ValueError("Invalid or empty embedding vectors.")

    if vectors.shape[1] == 0:
        raise ValueError("Embedding dimension cannot be zero.")

    if not np.isfinite(vectors).all():
        raise ValueError("Embeddings contain invalid numeric values.")

    faiss.normalize_L2(vectors)

    return vectors


def index_document(document_id: str) -> Dict:
    """Generate embeddings and save a FAISS index for a document."""

    metadata_path = PROCESSED_DIR / f"{document_id}.json"

    if not metadata_path.exists():
        raise FileNotFoundError("Document metadata not found.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    chunks = metadata.get("chunks", [])

    if not chunks:
        raise ValueError("No text chunks available for indexing.")

    texts = [chunk["text"] for chunk in chunks]

    embeddings = generate_embeddings(texts)

    vectors = validate_embeddings(embeddings)

    if vectors.shape[0] != len(chunks):
        raise ValueError(
            "Embedding count does not match the number of document chunks."
        )

    dimension = vectors.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    index_path = INDEX_DIR / f"{document_id}.index"
    chunks_path = INDEX_DIR / f"{document_id}.json"

    faiss.write_index(index, str(index_path))

    chunks_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"[VECTOR STORE] Indexed document: {document_id} | "
        f"Chunks: {len(chunks)} | Dimension: {dimension}"
    )

    return {
        "document_id": document_id,
        "total_chunks": len(chunks),
        "embedding_dimension": dimension,
        "index_type": "FAISS IndexFlatIP",
        "status": "indexed",
    }


def search_document(
    document_id: str,
    question: str,
    top_k: int = 5,
) -> List[Dict]:
    """Find relevant document chunks using cosine similarity."""

    if not question or not question.strip():
        raise ValueError("Search question cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    if not 0.0 <= MIN_SIMILARITY_SCORE <= 1.0:
        raise ValueError("RAG_MIN_SIMILARITY_SCORE must be between 0 and 1.")

    index_path = INDEX_DIR / f"{document_id}.index"
    chunks_path = INDEX_DIR / f"{document_id}.json"

    if not index_path.exists() or not chunks_path.exists():
        raise FileNotFoundError("Document index not found.")

    index = faiss.read_index(str(index_path))

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    if index.ntotal == 0 or not chunks:
        return []

    if index.ntotal != len(chunks):
        raise ValueError(
            "FAISS index and stored chunk count do not match. "
            "Please re-index the document."
        )

    query_embedding = generate_embeddings([question.strip()])
    query_vector = validate_embeddings(query_embedding)

    if query_vector.shape[1] != index.d:
        raise ValueError(
            f"Embedding dimension mismatch. "
            f"Query: {query_vector.shape[1]}, "
            f"Index: {index.d}. Please re-index the document."
        )

    # Retrieve additional candidates before applying the threshold.
    candidate_k = min(max(top_k * 3, 10), index.ntotal)

    scores, indices = index.search(query_vector, candidate_k)

    results = []

    for score, position in zip(scores[0], indices[0]):
        if position < 0:
            continue

        similarity = float(score)

        print(
            f"[RAG DEBUG] Chunk: {position} | "
            f"Similarity: {similarity:.4f} | "
            f"Threshold: {MIN_SIMILARITY_SCORE:.4f}"
        )

        if similarity < MIN_SIMILARITY_SCORE:
            continue

        chunk = chunks[int(position)]

        results.append(
            {
                "chunk_id": chunk["chunk_id"],
                "page_number": chunk["page_number"],
                "text": chunk["text"],
                "similarity_score": round(similarity, 4),
            }
        )

        if len(results) >= top_k:
            break

    print(
        f"[RAG DEBUG] Search completed | "
        f"Retrieved: {len(results)} | "
        f"Candidates: {candidate_k} | "
        f"Requested: {top_k}"
    )

    return results
