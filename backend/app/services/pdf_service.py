import json
import re
import uuid

from io import BytesIO
from pathlib import Path
from typing import Dict, List

import fitz
import pytesseract

from PIL import Image
from pypdf import PdfReader


BACKEND_DIR = Path(__file__).resolve().parents[2]

DOCUMENT_DIR = BACKEND_DIR / "storage" / "documents"
PROCESSED_DIR = BACKEND_DIR / "storage" / "processed"

DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
OCR_MIN_CHARACTERS = 40


def split_text(text: str) -> List[str]:
    """
    Split extracted text into overlapping chunks.
    Prefer paragraph boundaries to avoid separating related content.
    """

    if not text or not text.strip():
        return []

    # Normalize each paragraph while preserving paragraph boundaries.
    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    if not paragraphs:
        return []

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        # Keep a long paragraph intact by splitting it into smaller pieces.
        if len(paragraph) > CHUNK_SIZE:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            start = 0

            while start < len(paragraph):
                end = min(start + CHUNK_SIZE, len(paragraph))

                if end < len(paragraph):
                    boundary = paragraph.rfind(" ", start, end)
                    if boundary > start:
                        end = boundary

                piece = paragraph[start:end].strip()

                if piece:
                    chunks.append(piece)

                if end >= len(paragraph):
                    break

                start = max(start + 1, end - CHUNK_OVERLAP)

            continue

        candidate = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph

        if len(candidate) <= CHUNK_SIZE:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())

            current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def extract_page_text(page) -> str:
    """
    Extract normal PDF text.
    Run OCR only when extracted text is insufficient
    and the page contains visible content.
    """

    text = page.get_text("text") or ""

    # Normal text-based PDF page
    if len(text.strip()) >= OCR_MIN_CHARACTERS:
        return normalize_schedule_dates(text)

    # Render page to grayscale to detect visible content
    pix = page.get_pixmap(
        matrix=fitz.Matrix(1.5, 1.5), colorspace=fitz.csGRAY, alpha=False
    )

    image = Image.open(BytesIO(pix.tobytes("png")))

    # Count pixels darker than near-white
    histogram = image.histogram()
    dark_pixels = sum(histogram[:245])

    total_pixels = image.width * image.height
    content_ratio = dark_pixels / total_pixels if total_pixels else 0

    # Skip OCR for genuinely blank pages
    if content_ratio < 0.0005:
        print("Blank page detected. Skipping OCR.")
        return ""

    print("Low-text page detected. Running OCR...")

    ocr_text = pytesseract.image_to_string(image, lang="eng")

    extracted_text = ocr_text or text

    return normalize_schedule_dates(extracted_text)


def process_pdf(file_content: bytes, filename: str) -> Dict:
    """Extract PDF text page by page, using OCR when needed."""

    document_id = str(uuid.uuid4())

    reader = PdfReader(BytesIO(file_content))

    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported.")

    pdf_document = fitz.open(stream=file_content, filetype="pdf")

    all_chunks = []
    page_results = []

    try:
        for page_index, page in enumerate(pdf_document):
            page_number = page_index + 1

            page_text = extract_page_text(page)
            page_chunks = split_text(page_text)
            print("\n========== GENERATED CHUNKS ==========")

            for index, chunk in enumerate(page_chunks, start=1):
                print(f"\nCHUNK {index}")
                print(chunk)

            print("======================================\n")
            for chunk_number, chunk in enumerate(page_chunks, start=1):
                all_chunks.append(
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "page_number": page_number,
                        "chunk_number": chunk_number,
                        "text": chunk,
                    }
                )

            print(
                f"Page {page_number}: "
                f"{len(page_text)} characters extracted, "
                f"{len(page_chunks)} chunks"
            )

            page_results.append(
                {
                    "page_number": page_number,
                    "character_count": len(page_text),
                    "chunk_count": len(page_chunks),
                }
            )

    finally:
        pdf_document.close()

    original_pdf_path = DOCUMENT_DIR / f"{document_id}.pdf"
    metadata_path = PROCESSED_DIR / f"{document_id}.json"

    original_pdf_path.write_bytes(file_content)

    metadata = {
        "document_id": document_id,
        "filename": filename,
        "page_count": len(reader.pages),
        "chunk_count": len(all_chunks),
        "pages": page_results,
        "chunks": all_chunks,
    }

    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "document_id": document_id,
        "filename": filename,
        "page_count": len(reader.pages),
        "chunk_count": len(all_chunks),
        "pages": page_results,
        "preview": [
            {"page_number": chunk["page_number"], "text": chunk["text"][:250]}
            for chunk in all_chunks[:3]
        ],
    }


def normalize_schedule_dates(text: str) -> str:
    """
    Repair OCR dates where the day is split into two digits.

    Example:
    AM 4 1 8-Jul-2026 -> AM 4 18-Jul-2026
    AM 6 0 1-Aug-2026 -> AM 6 01-Aug-2026
    """

    months = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"

    pattern = re.compile(
        rf"(\b(?:AM|PM)\s+\d{{1,2}}\s+)"
        rf"(\d)\s+(\d)-({months})-(\d{{4}})",
        re.IGNORECASE,
    )

    return pattern.sub(
        lambda match: (
            f"{match.group(1)}"
            f"{match.group(2)}{match.group(3)}-"
            f"{match.group(4)}-{match.group(5)}"
        ),
        text,
    )
