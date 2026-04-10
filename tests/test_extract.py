import io
import json
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("MODEL_NAME", "gemma4:e4b")

from app.main import app
from app.services.mcq_parser import parse_mcq_response

client = TestClient(app)


# --- Parser unit tests ---

VALID_MCQ_JSON = json.dumps([
    {
        "question_number": 1,
        "page": 1,
        "question_text": "What is 2 + 2?",
        "has_image": False,
        "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
        "answer": "B",
        "confidence": "high",
    }
])


def test_parse_valid_json():
    questions = parse_mcq_response(VALID_MCQ_JSON, page_num=1)
    assert len(questions) == 1
    assert questions[0].question_number == 1
    assert questions[0].answer == "B"
    assert questions[0].options["B"] == "4"


def test_parse_with_code_fences():
    fenced = f"```json\n{VALID_MCQ_JSON}\n```"
    questions = parse_mcq_response(fenced, page_num=1)
    assert len(questions) == 1


def test_parse_empty_array():
    questions = parse_mcq_response("[]", page_num=1)
    assert questions == []


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_mcq_response("not valid json", page_num=1)


def test_parse_non_array_raises():
    with pytest.raises(ValueError):
        parse_mcq_response('{"key": "value"}', page_num=1)


# --- API endpoint tests ---

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "ollama" in data


def test_models_endpoint_returns_structure():
    response = client.get("/models")
    # May return 503 if Ollama not running — just check it responds
    assert response.status_code in (200, 503)


def test_extract_unsupported_file_type():
    response = client.post(
        "/extract",
        files={"file": ("test.txt", b"some text content", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_extract_with_image(monkeypatch):
    """Test /extract with a synthetic PNG. Mocks Ollama call."""
    async def mock_extract_mcqs(page_data):
        return json.dumps([{
            "question_number": 1,
            "page": 1,
            "question_text": "Mock question?",
            "has_image": False,
            "options": {"A": "Yes", "B": "No", "C": "Maybe", "D": "Always"},
            "answer": "A",
            "confidence": "high",
        }])

    monkeypatch.setattr("app.routers.extract.ollama_client.extract_mcqs", mock_extract_mcqs)

    # Create a minimal white PNG in memory
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.post(
        "/extract",
        files={"file": ("test_page.png", buf, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_file"] == "test_page.png"
    assert data["total_questions"] == 1
    assert data["questions"][0]["answer"] == "A"
