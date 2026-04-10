import uuid
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from app.models.schemas import PageData

# Pages with fewer characters than this are treated as scanned (image-only)
SCANNED_TEXT_THRESHOLD = 50
# DPI for full-page PNG renders
RENDER_DPI = 200


def extract_pages(pdf_path: Path, upload_dir: Path, media_dir: Path) -> List[PageData]:
    pages: List[PageData] = []
    doc = fitz.open(str(pdf_path))

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1

        text = page.get_text()
        is_scanned = len(text.strip()) < SCANNED_TEXT_THRESHOLD

        # Render full page as PNG (used as primary input to Gemma 4)
        matrix = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        page_png = upload_dir / f"page_{uuid.uuid4()}.png"
        pix.save(str(page_png))

        # Extract embedded images (only for non-scanned PDFs)
        extracted_images: List[Path] = []
        if not is_scanned:
            for img_index, img_info in enumerate(page.get_images(full=True)):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    img_path = media_dir / f"img_{uuid.uuid4()}.{img_ext}"
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    extracted_images.append(img_path)
                except Exception:
                    continue

        pages.append(PageData(
            page_num=page_num,
            image_path=page_png,
            extracted_images=extracted_images,
            text=text if not is_scanned else "",
        ))

    doc.close()
    return pages
