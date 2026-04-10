import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.routers.extract import router
from app.utils.file_utils import ensure_dirs

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "media"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs(MEDIA_DIR, UPLOAD_DIR)
    yield


app = FastAPI(
    title="MCQ Extractor",
    description="Extract multiple choice questions from PDF and image files using Gemma 4 via Ollama.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
