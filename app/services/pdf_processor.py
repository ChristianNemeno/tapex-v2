import uuid
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from app.models.schemas import FigureRegion, LayoutPage, PageData, TextBlock

SCANNED_TEXT_THRESHOLD = 50
RENDER_DPI = 200


def _build_layout_page(page: fitz.Page, page_num: int) -> LayoutPage:
    """Build a LayoutPage from a digital PDF page using PyMuPDF's block extraction."""
    page_rect = page.rect
    raw = page.get_text("dict")

    text_blocks: List[TextBlock] = []
    figure_regions: List[FigureRegion] = []

    for block in raw.get("blocks", []):
        bbox = tuple(block["bbox"])  # (x0, y0, x1, y1)
        if block["type"] == 0:  # text block
            lines = []
            for line in block.get("lines", []):
                line_text = "".join(span["text"] for span in line.get("spans", []))
                if line_text.strip():
                    lines.append(line_text)
            if lines:
                text_blocks.append(TextBlock(text="\n".join(lines), bbox=bbox))
        elif block["type"] == 1:  # image block embedded in PDF
            figure_regions.append(FigureRegion(bbox=bbox))

    return LayoutPage(
        page_num=page_num,
        text_blocks=text_blocks,
        figures=figure_regions,
        page_width=page_rect.width,
        page_height=page_rect.height,
    )


def extract_pages(pdf_path: Path, upload_dir: Path, media_dir: Path) -> List[PageData]:
    pages: List[PageData] = []
    doc = fitz.open(str(pdf_path))

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1

        text = page.get_text()
        is_scanned = len(text.strip()) < SCANNED_TEXT_THRESHOLD

        # Render full page as PNG (used for scanned pages and as input to OCR)
        matrix = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        page_png = upload_dir / f"page_{uuid.uuid4()}.png"
        pix.save(str(page_png))

        extracted_images: List[Path] = []
        layout: LayoutPage | None = None

        if not is_scanned:
            # Digital page: extract layout from text layer
            layout = _build_layout_page(page, page_num)

            # Also pull out embedded image files for attach_images
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    img_path = media_dir / f"img_{uuid.uuid4()}.{img_ext}"
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    extracted_images.append(img_path)
                    # Annotate matching FigureRegion with the saved path
                    if layout.figures:
                        for fig in layout.figures:
                            if fig.image_path is None:
                                fig.image_path = img_path
                                break
                except Exception:
                    continue

        pages.append(PageData(
            page_num=page_num,
            image_path=page_png,
            extracted_images=extracted_images,
            text=text if not is_scanned else "",
            layout=layout,
        ))

    doc.close()
    return pages
