import base64
import io
from pathlib import Path

from PIL import Image


def read_image_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def encode_image_base64(path: Path) -> str:
    return base64.b64encode(read_image_bytes(path)).decode("utf-8")


def create_thumbnail(image_path: Path, max_size: tuple[int, int] = (200, 200)) -> str:
    """Return base64-encoded thumbnail of the image."""
    with Image.open(image_path) as img:
        img.thumbnail(max_size, Image.LANCZOS)
        buf = io.BytesIO()
        fmt = img.format or "PNG"
        img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
