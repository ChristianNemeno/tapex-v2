import shutil
import uuid
from pathlib import Path

from app.models.schemas import PageData


def process_image(image_path: Path, upload_dir: Path) -> PageData:
    """Wrap a standalone image file as a single-page PageData."""
    suffix = image_path.suffix
    dest = upload_dir / f"img_{uuid.uuid4()}{suffix}"
    shutil.copy2(image_path, dest)
    return PageData(
        page_num=1,
        image_path=dest,
        extracted_images=[],
        text="",
    )
