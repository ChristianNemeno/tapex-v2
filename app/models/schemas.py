from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# --- Layout intermediate types ---

class TextBlock(BaseModel):
    text: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1


class FigureRegion(BaseModel):
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    image_path: Optional[Path] = None


class LayoutPage(BaseModel):
    page_num: int
    text_blocks: List[TextBlock]
    figures: List[FigureRegion]
    page_width: float
    page_height: float


# --- Pipeline types ---

class PageData(BaseModel):
    page_num: int
    image_path: Optional[Path] = None  # full-page PNG render
    extracted_images: List[Path] = Field(default_factory=list)
    text: str = ""
    layout: Optional[LayoutPage] = None  # populated for digital PDF pages


class MCQImage(BaseModel):
    filename: str
    description: str = ""
    base64_thumbnail: str


class MCQQuestion(BaseModel):
    question_number: int
    page: int
    question_text: str
    has_image: bool = False
    image: Optional[MCQImage] = None
    options: Dict[str, str]
    answer: Optional[str] = None
    confidence: str = "medium"


class MCQResponse(BaseModel):
    source_file: str
    total_pages: int
    total_questions: int
    processing_time_ms: int
    questions: List[MCQQuestion]
