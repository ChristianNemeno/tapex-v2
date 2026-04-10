import json
import re
from pathlib import Path
from typing import List

from pydantic import ValidationError

from app.models.schemas import MCQImage, MCQQuestion, PageData
from app.utils.image_utils import create_thumbnail

# Strip markdown code fences if the model wraps output in ```json ... ```
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def _strip_fences(text: str) -> str:
    match = _CODE_FENCE_RE.search(text)
    return match.group(1) if match else text.strip()


def parse_mcq_response(raw: str, page_num: int) -> List[MCQQuestion]:
    """
    Parse raw model output into a list of MCQQuestion objects.
    Raises ValueError on unrecoverable parse failure (caller should retry).
    """
    cleaned = _strip_fences(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON decode error on page {page_num}: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__} on page {page_num}")

    questions: List[MCQQuestion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        # Ensure page number is set correctly
        item.setdefault("page", page_num)
        try:
            questions.append(MCQQuestion.model_validate(item))
        except ValidationError:
            # Skip individual malformed questions rather than failing the whole page
            continue

    return questions


def attach_images(
    questions: List[MCQQuestion],
    page_data: PageData,
    media_dir: Path,
) -> List[MCQQuestion]:
    """
    For questions flagged has_image=True, attempt to attach an extracted image
    as a base64 thumbnail. Images are matched positionally by question order.
    """
    image_queue = list(page_data.extracted_images)
    img_idx = 0

    for q in questions:
        if not q.has_image:
            continue
        if img_idx >= len(image_queue):
            break
        img_path = image_queue[img_idx]
        img_idx += 1
        if not img_path.exists():
            continue
        try:
            thumbnail_b64 = create_thumbnail(img_path)
            q.image = MCQImage(
                filename=img_path.name,
                description="",
                base64_thumbnail=thumbnail_b64,
            )
        except Exception:
            pass

    return questions
