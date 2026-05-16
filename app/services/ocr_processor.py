"""Wraps PaddleOCR PP-Structure for scanned pages and standalone images.

The PPStructure engine is initialised once at module import time (slow, ~5–10 s)
so subsequent calls per page are fast (~0.5–3 s on GPU, ~2–8 s on CPU).
"""

import os
from pathlib import Path

import cv2
import numpy as np

from app.models.schemas import FigureRegion, LayoutPage, TextBlock

_USE_GPU = os.getenv("OCR_USE_GPU", "true").lower() in ("true", "1", "yes")
_LANG = os.getenv("OCR_LANG", "en")

# Lazy-load the engine on first call so import doesn't crash when paddleocr
# is absent in test environments that monkeypatch this module.
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        from paddleocr import PPStructure  # noqa: PLC0415
        _engine = PPStructure(
            table=False,
            ocr=True,
            show_log=False,
            lang=_LANG,
            use_gpu=_USE_GPU,
        )
    return _engine


def run(image_path: Path) -> LayoutPage:
    """Run PP-Structure on a page image and return a LayoutPage."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    h, w = img.shape[:2]
    engine = _get_engine()
    result = engine(img)

    text_blocks: list[TextBlock] = []
    figures: list[FigureRegion] = []

    for region in result:
        region_type = region.get("type", "text").lower()
        bbox_raw = region.get("bbox", [0, 0, w, h])
        bbox = (float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3]))

        if region_type == "figure":
            figures.append(FigureRegion(bbox=bbox))
        else:
            # text, title, table, figure_caption → treat as text
            res = region.get("res", [])
            if isinstance(res, list):
                lines = []
                for item in res:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        # PaddleOCR returns [[bbox, (text, confidence)], ...]
                        inner = item[1]
                        text = inner[0] if isinstance(inner, (list, tuple)) else str(inner)
                    else:
                        text = str(item)
                    if text.strip():
                        lines.append(text.strip())
                if lines:
                    text_blocks.append(TextBlock(text="\n".join(lines), bbox=bbox))
            elif isinstance(res, str) and res.strip():
                text_blocks.append(TextBlock(text=res.strip(), bbox=bbox))

    return LayoutPage(
        page_num=1,  # caller overwrites with actual page number
        text_blocks=text_blocks,
        figures=figures,
        page_width=float(w),
        page_height=float(h),
    )
