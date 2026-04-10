import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.models.schemas import MCQResponse
from app.services import ingestion, mcq_parser, ollama_client
from app.utils.file_utils import cleanup_file, save_upload

router = APIRouter()

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "media"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))


@router.post("/extract", response_model=MCQResponse)
async def extract(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    start = time.monotonic()
    upload_path = await save_upload(file, UPLOAD_DIR)

    try:
        pages = ingestion.ingest_file(upload_path, UPLOAD_DIR, MEDIA_DIR)
        all_questions = []

        for page_data in pages:
            raw = None
            questions = []

            for attempt in range(MAX_RETRIES):
                try:
                    raw = await ollama_client.extract_mcqs(page_data)
                    questions = mcq_parser.parse_mcq_response(raw, page_data.page_num)
                    break
                except ValueError:
                    if attempt == MAX_RETRIES - 1:
                        # Exhausted retries — skip this page
                        questions = []

            questions = mcq_parser.attach_images(questions, page_data, MEDIA_DIR)
            all_questions.extend(questions)

            # Clean up full-page PNG (embedded images in media/ are kept)
            if page_data.image_path:
                cleanup_file(page_data.image_path)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        return MCQResponse(
            source_file=file.filename,
            total_pages=len(pages),
            total_questions=len(all_questions),
            processing_time_ms=elapsed_ms,
            questions=all_questions,
        )
    finally:
        cleanup_file(upload_path)


@router.get("/health")
async def health():
    return await ollama_client.health_check()


@router.get("/models")
async def models():
    try:
        return {"models": await ollama_client.list_models()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
