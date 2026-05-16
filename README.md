# MCQ Extractor

Extracts multiple choice questions from PDF and image files using **PaddleOCR PP-Structure** running locally. No cloud APIs — all inference runs on your machine.

**Hardware target:** NVIDIA RTX 3050 6GB. PaddleOCR models are tiny (~10–50 MB each); GPU gives the best throughput but CPU works fine.

---

## How it works

- **Digital PDFs** (selectable text) → PyMuPDF extracts text + layout instantly; no OCR needed
- **Scanned PDFs / images** → PaddleOCR PP-Structure detects text regions and figures
- Both paths produce a unified layout representation that a deterministic MCQ structurer parses into questions

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for GPU passthrough (optional but recommended)

---

## Quickstart

### 1. Clone and configure

```bash
git clone <repo-url>
cd tapex-v2
```

### 2. Start the service

```bash
docker compose up -d
```

On first run, PaddleOCR auto-downloads its model weights (~200 MB) into the `paddle_data` volume.

### 3. Verify

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status": "ok", "ocr_backend": "paddleocr"}
```

---

## Usage

### Extract MCQs from a PDF

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@exam_paper.pdf" | jq
```

### Extract MCQs from an image

```bash
curl -X POST http://localhost:8000/extract \
  -F "file=@page.png" | jq
```

Supported formats: `.pdf`, `.png`, `.jpg`, `.jpeg`

### Example response

```json
{
  "source_file": "exam_paper.pdf",
  "total_pages": 3,
  "total_questions": 12,
  "processing_time_ms": 1800,
  "questions": [
    {
      "question_number": 1,
      "page": 1,
      "question_text": "Which of the following is a primary color?",
      "has_image": false,
      "image": null,
      "options": {
        "A": "Green",
        "B": "Orange",
        "C": "Blue",
        "D": "Purple"
      },
      "answer": null,
      "confidence": "high"
    }
  ]
}
```

> **Note on `answer`:** The `answer` field is populated only when the page contains an explicit marker like `Answer: B`. Without an LLM, answers are not inferred — `null` is the expected value for most exam papers.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/extract` | Upload PDF or image, returns extracted MCQs |
| `GET` | `/health` | Check PaddleOCR backend availability |
| `GET` | `/models` | Show active OCR configuration |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Configuration

All settings are in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OCR_LANG` | `en` | Language for OCR (see PaddleOCR docs for options) |
| `OCR_USE_GPU` | `true` | Set to `false` for CPU-only inference |
| `MEDIA_DIR` | `media` | Directory for saved extracted images |
| `UPLOAD_DIR` | `uploads` | Temporary upload directory |

---

## Running without Docker

```bash
# Install system deps (Debian/Ubuntu)
sudo apt-get install -y libgl1 libglib2.0-0

# Install Python deps
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running tests

```bash
# With Docker
docker compose exec mcq-extractor pytest tests/

# Locally (no GPU required — OCR is mocked in tests)
pytest tests/
```

---

## Stopping

```bash
docker compose down          # stop container, keep volumes
docker compose down -v       # stop container and delete all data (including OCR model cache)
```
