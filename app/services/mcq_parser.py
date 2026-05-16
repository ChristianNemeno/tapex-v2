from pathlib import Path
from typing import List

from app.models.schemas import MCQImage, MCQQuestion, PageData
from app.utils.image_utils import create_thumbnail


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
