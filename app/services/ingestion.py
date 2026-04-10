from pathlib import Path
from typing import List

from fastapi import HTTPException

from app.models.schemas import PageData
from app.services import image_processor, pdf_processor

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}


def ingest_file(file_path: Path, upload_dir: Path, media_dir: Path) -> List[PageData]:
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return pdf_processor.extract_pages(file_path, upload_dir, media_dir)
    elif ext in SUPPORTED_IMAGE_EXTS:
        return [image_processor.process_image(file_path, upload_dir)]
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: .pdf, .png, .jpg, .jpeg",
        )
