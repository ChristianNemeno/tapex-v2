import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile


def ensure_dirs(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


async def save_upload(file: UploadFile, upload_dir: Path) -> Path:
    suffix = Path(file.filename).suffix.lower()
    dest = upload_dir / f"{uuid.uuid4()}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest


def cleanup_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
