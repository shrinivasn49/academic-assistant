import httpx
from typing import Dict, List

from app.services.vector_store import search_document
import re
from app.services.extraction_service import find_matching_fact

OLLAMA_URL = "http://localhost:11434"
LLM_MODEL = "llama3.2:3b"

NOT_FOUND_MESSAGE = "I could not find relevant information in the uploaded document."


def is_not_found_answer(answer: str) -> bool:
    """Identify NOT_FOUND responses, including punctuation."""

    normalized = answer.strip().lower()

    return bool(re.match(r"^not_found\b|^not found\b", normalized))


def generate_answer(
    document_id: str,
    question: str,
    top_k: int = 5,
) -> Dict:
    """Retrieve relevant PDF chunks and generate a grounded answer."""

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    # 1. Retrieve relevant chunks from FAISS.
    retrieved_chunks = search_document(
        document_id=document_id,
        question=question.strip(),
        top_k=top_k,
    )

    print("\n========== RETRIEVAL DEBUG ==========")
    print("Document ID:", document_id)
    print("Question:", question)
    print("Retrieved chunks:", len(retrieved_chunks))

    for i, chunk in enumerate(retrieved_chunks, start=1):
        print(f"\n--- Chunk {i} ---")
        print("Page:", chunk.get("page_number"))
        print("Similarity:", chunk.get("similarity_score"))
        print("Text:")
        print(chunk.get("text"))

    print("====================================\n")

    if not retrieved_chunks:
        return {
            "answer": NOT_FOUND_MESSAGE,
            "sources": [],
            "model": LLM_MODEL,
        }

    # 2. Build document context and source references.
    context_parts: List[str] = []
    sources: List[Dict] = []

    for chunk in retrieved_chunks:
        page_number = chunk["page_number"]
        chunk_text = chunk["text"]

        context_parts.append(f"[Source: Page {page_number}]\n{chunk_text}")

        sources.append(
            {
                "page_number": page_number,
                "similarity_score": chunk["similarity_score"],
                "text": chunk_text[:300],
            }
        )

    context = "\n\n".join(context_parts)
    # 3. Try deterministic document fact extraction first.
    extracted_fact = find_matching_fact(
        question=question.strip(),
        chunks=retrieved_chunks,
    )

    if extracted_fact:
        page_number = extracted_fact["page_number"]
        fact_value = extracted_fact["value"]
        fact_type = extracted_fact["fact_type"]

        print("\n========== FACT EXTRACTION ==========")
        print("Fact type:", fact_type)
        print("Extracted value:", fact_value)
        print("Page:", page_number)
        print("=====================================\n")

        return {
            "answer": (
                f"The {fact_type} mentioned in the document is "
                f"{fact_value}.\n\n[Page {page_number}]"
            ),
            "sources": [
                source for source in sources if source["page_number"] == page_number
            ],
            "model": "document-extraction",
        }

    # 3. Prepare a strict grounded-answer prompt.

    system_prompt = """
    You are an academic document assistant.

    Answer questions strictly using the supplied document context.

    IMPORTANT RULES:

    1. Identify the exact event, module, session, or topic
    mentioned in the user's question.

    2. Match dates only with the event or topic they belong to.

    3. Never select a date belonging to another event,
    module, or session.

    4. If the user asks about an event date, return the date
    directly associated with that event.

    5. Do not guess or infer dates.

    6. If the requested information is not available,
    respond exactly:
    I could not find relevant information in the uploaded document.

    7. Include the source page number.

    Keep answers concise and factual.
    """

    user_prompt = f"""
    DOCUMENT CONTEXT START

    {context}

    DOCUMENT CONTEXT END

    QUESTION:

    {question}

    Provide a grounded answer with page references.
    If the answer is unavailable in the context, return NOT_FOUND.

    Important:
    If the context contains a date immediately associated
    with the requested event, extract and report that date.
    Do not reject it merely because the text also contains
    the word "Notes".
    """

    # 4. Generate the answer using local Ollama.
    try:
        response = httpx.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "top_p": 0.9,
                },
            },
            timeout=180.0,
        )

        response.raise_for_status()

        result = response.json()
        answer = (result.get("message", {}).get("content", "") or "").strip()
        # Debug information.
        print("\n[RAG DEBUG] Retrieved chunks:", len(retrieved_chunks))
        print("[RAG DEBUG] Context length:", len(context))
        print("[RAG DEBUG] Question:", question)
        print("[RAG DEBUG] Raw Ollama answer:", repr(answer))

        if not answer:
            raise RuntimeError("Ollama returned an empty answer.")

        # 5. Handle unavailable information.
        if is_not_found_answer(answer):
            return {
                "answer": NOT_FOUND_MESSAGE,
                "sources": [],
                "model": LLM_MODEL,
            }

        # 6. Return answer and source references.
        return {
            "answer": answer,
            "sources": sources,
            "model": LLM_MODEL,
        }

    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama request failed: {str(exc)}") from exc
