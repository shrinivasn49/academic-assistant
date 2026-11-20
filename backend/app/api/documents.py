import os

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.pdf_service import process_pdf
from pydantic import BaseModel, Field

from app.services.vector_store import index_document, search_document
from app.services.rag_service import generate_answer

router = APIRouter(prefix="/api/documents", tags=["Documents"])

MAX_FILE_SIZE_MB = int(os.getenv("ACADEMIC_MAX_FILE_SIZE_MB", "10"))

MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


class DocumentSearchRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=10)


class DocumentQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail=f"Maximum file size is {MAX_FILE_SIZE_MB} MB."
        )

    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file.")

    try:
        # 1. Extract PDF text and create chunks
        result = process_pdf(file_content=content, filename=file.filename)

        # 2. Automatically generate embeddings and FAISS index
        index_result = index_document(result["document_id"])

        return {
            "success": True,
            "message": "PDF uploaded, processed and indexed successfully.",
            "data": {**result, "index": index_result},
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"PDF processing or indexing failed: {str(error)}"
        )


@router.post("/{document_id}/index")
def create_document_index(document_id: str):

    try:
        result = index_document(document_id)

        return {
            "success": True,
            "message": "Document indexed successfully.",
            "data": result,
        }

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/{document_id}/search")
def search_document_chunks(document_id: str, request: DocumentSearchRequest):

    try:
        results = search_document(
            document_id=document_id, question=request.question, top_k=request.top_k
        )

        return {"success": True, "question": request.question, "results": results}

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@router.post("/{document_id}/ask")
def ask_document_question(document_id: str, request: DocumentQuestionRequest):

    try:
        result = generate_answer(
            document_id=document_id, question=request.question, top_k=request.top_k
        )

        return {
            "success": True,
            "document_id": document_id,
            "question": request.question,
            "answer": result["answer"],
            "sources": result["sources"],
            "model": result["model"],
        }

    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500, detail=f"Question answering failed: {str(error)}"
        )
