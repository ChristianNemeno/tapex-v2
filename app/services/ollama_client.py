import asyncio
import os
from functools import partial
from typing import Any

import ollama

from app.models.schemas import PageData
from app.prompts.extraction import SYSTEM_PROMPT, build_user_prompt
from app.utils.image_utils import read_image_bytes

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma4:e4b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "1.0"))
TOP_P = float(os.getenv("TOP_P", "0.95"))
TOP_K = int(os.getenv("TOP_K", "64"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "1120"))

_client = ollama.Client(host=OLLAMA_HOST)


def _chat_sync(messages: list[dict], options: dict) -> str:
    response = _client.chat(
        model=MODEL_NAME,
        messages=messages,
        options=options,
    )
    return response["message"]["content"]


async def extract_mcqs(page_data: PageData) -> str:
    """Send page data to Gemma 4 and return raw response text."""
    image_bytes_list: list[bytes] = []

    # Full-page render is the primary visual input
    if page_data.image_path and page_data.image_path.exists():
        image_bytes_list.append(read_image_bytes(page_data.image_path))

    # Append any extracted embedded images
    for img_path in page_data.extracted_images:
        if img_path.exists():
            image_bytes_list.append(read_image_bytes(img_path))

    has_images = bool(image_bytes_list)
    user_content = build_user_prompt(page_data.page_num, has_images)

    # Images placed BEFORE text per Gemma 4 best practice
    user_message: dict[str, Any] = {
        "role": "user",
        "content": user_content,
    }
    if image_bytes_list:
        user_message["images"] = image_bytes_list

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        user_message,
    ]

    options = {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "num_ctx": TOKEN_BUDGET,
    }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_chat_sync, messages, options))


def health_check_sync() -> dict:
    try:
        models = _client.list()
        model_names = [m["model"] for m in models.get("models", [])]
        model_available = MODEL_NAME in model_names
        return {
            "ollama": "ok",
            "model": MODEL_NAME,
            "model_available": model_available,
            "available_models": model_names,
        }
    except Exception as exc:
        return {"ollama": "error", "detail": str(exc)}


async def health_check() -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, health_check_sync)


def list_models_sync() -> list:
    models = _client.list()
    return [m["model"] for m in models.get("models", [])]


async def list_models() -> list:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, list_models_sync)
