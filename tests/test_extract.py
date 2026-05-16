import io
import os

from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("OCR_USE_GPU", "false")
os.environ.setdefault("OCR_LANG", "en")

from app.main import app
from app.models.schemas import FigureRegion, LayoutPage, TextBlock
from app.services.mcq_structurer import structure

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_layout(*lines: str, figures: list | None = None) -> LayoutPage:
    """Build a LayoutPage from plain text lines, each as a separate TextBlock."""
    blocks = [
        TextBlock(text=line, bbox=(0.0, float(i * 20), 500.0, float(i * 20 + 18)))
        for i, line in enumerate(lines)
    ]
    return LayoutPage(
        page_num=1,
        text_blocks=blocks,
        figures=figures or [],
        page_width=600.0,
        page_height=800.0,
    )


# ---------------------------------------------------------------------------
# MCQ structurer unit tests
# ---------------------------------------------------------------------------

def test_structure_basic_mcq():
    layout = _make_layout(
        "1. What is 2 + 2?",
        "A. 3",
        "B. 4",
        "C. 5",
        "D. 6",
    )
    questions = structure(layout)
    assert len(questions) == 1
    q = questions[0]
    assert q.question_number == 1
    assert q.question_text == "What is 2 + 2?"
    assert q.options == {"A": "3", "B": "4", "C": "5", "D": "6"}
    assert q.answer is None
    assert q.confidence == "high"


def test_structure_answer_line_detected():
    layout = _make_layout(
        "1. Which is primary?",
        "A. Green",
        "B. Blue",
        "C. Orange",
        "D. Purple",
        "Answer: B",
    )
    questions = structure(layout)
    assert len(questions) == 1
    assert questions[0].answer == "B"


def test_structure_multiple_questions():
    layout = _make_layout(
        "1. First question?",
        "A. Alpha",
        "B. Beta",
        "C. Gamma",
        "D. Delta",
        "2. Second question?",
        "A. Yes",
        "B. No",
        "C. Maybe",
        "D. Always",
    )
    questions = structure(layout)
    assert len(questions) == 2
    assert questions[0].question_number == 1
    assert questions[1].question_number == 2


def test_structure_no_mcq_returns_empty():
    layout = _make_layout(
        "This is just a paragraph of text.",
        "It contains no multiple choice questions.",
    )
    questions = structure(layout)
    assert questions == []


def test_structure_noise_dropped():
    """A block with only 1 option should be dropped as noise."""
    layout = _make_layout(
        "1. Is this a question?",
        "A. Yes",
    )
    questions = structure(layout)
    assert questions == []


def test_structure_figure_association():
    fig = FigureRegion(bbox=(0.0, 60.0, 500.0, 120.0))
    layout = LayoutPage(
        page_num=1,
        text_blocks=[
            TextBlock(text="1. Refer to the figure below.", bbox=(0.0, 20.0, 500.0, 38.0)),
            TextBlock(text="A. Option one", bbox=(0.0, 40.0, 500.0, 58.0)),
            TextBlock(text="B. Option two", bbox=(0.0, 60.0, 500.0, 78.0)),
            TextBlock(text="C. Option three", bbox=(0.0, 80.0, 500.0, 98.0)),
            TextBlock(text="D. Option four", bbox=(0.0, 100.0, 500.0, 118.0)),
        ],
        figures=[fig],
        page_width=600.0,
        page_height=800.0,
    )
    questions = structure(layout)
    assert len(questions) == 1
    assert questions[0].has_image is True


def test_structure_confidence_medium():
    layout = _make_layout(
        "1. Incomplete question?",
        "A. First",
        "B. Second",
    )
    questions = structure(layout)
    assert len(questions) == 1
    assert questions[0].confidence == "medium"


def test_structure_option_variants():
    """Accept (A), A), A. as option markers."""
    layout = _make_layout(
        "1) What color is the sky?",
        "(A) Red",
        "(B) Blue",
        "(C) Green",
        "(D) Yellow",
    )
    questions = structure(layout)
    assert len(questions) == 1
    assert "A" in questions[0].options


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def test_health_endpoint():
    # Health just checks if paddleocr can be imported; may return 503 if absent
    response = client.get("/health")
    assert response.status_code in (200, 503)


def test_models_endpoint():
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert data["ocr_backend"] == "paddleocr"


def test_extract_unsupported_file_type():
    response = client.post(
        "/extract",
        files={"file": ("test.txt", b"some text content", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]


def test_extract_with_image(monkeypatch):
    """Test /extract with a synthetic PNG. Mocks the OCR processor."""
    mock_layout = _make_layout(
        "1. Mock question?",
        "A. Yes",
        "B. No",
        "C. Maybe",
        "D. Always",
    )

    monkeypatch.setattr("app.routers.extract.ocr_processor.run", lambda _path: mock_layout)

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
    assert data["questions"][0]["question_text"] == "Mock question?"
