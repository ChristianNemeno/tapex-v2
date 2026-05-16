import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.models.schemas import MCQResponse
from app.services import ingestion, mcq_parser, mcq_structurer, ocr_processor
from app.utils.file_utils import cleanup_file, save_upload

router = APIRouter()

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "media"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))


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
            layout = page_data.layout

            if layout is None:
                # Scanned page or standalone image — run OCR
                layout = ocr_processor.run(page_data.image_path)
                layout.page_num = page_data.page_num

            questions = mcq_structurer.structure(layout)
            questions = mcq_parser.attach_images(questions, page_data, MEDIA_DIR)
            all_questions.extend(questions)

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
    """Check that the OCR engine can be loaded and required libs are present."""
    try:
        import cv2  # noqa: F401
        from paddleocr import PPStructure  # noqa: F401
        return {"status": "ok", "ocr_backend": "paddleocr"}
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"OCR backend unavailable: {exc}")


@router.get("/models")
async def models():
    """Return info about the active OCR configuration."""
    lang = os.getenv("OCR_LANG", "en")
    use_gpu = os.getenv("OCR_USE_GPU", "true").lower() in ("true", "1", "yes")
    return {"ocr_backend": "paddleocr", "lang": lang, "use_gpu": use_gpu}
