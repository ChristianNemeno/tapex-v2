from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PageData(BaseModel):
    page_num: int
    image_path: Optional[Path] = None  # full-page PNG render
    extracted_images: List[Path] = Field(default_factory=list)
    text: str = ""


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
