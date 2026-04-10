# MCQ Extraction Backend — Application Architecture

> Stack: FastAPI · Gemma 4 E4B · Ollama · PyMuPDF · Python 3.11+
> Hardware Target: NVIDIA RTX 3050 6GB Laptop GPU

---

## System Overview

This backend accepts PDF or image input, extracts Multiple Choice Questions (MCQs) including any embedded images, and returns structured JSON output. All inference runs **locally** via Ollama + Gemma 4 E4B — no cloud API required.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────┐
│                   CLIENT / FRONTEND                  │
│           (REST API consumer or web UI)              │
└────────────────────────┬─────────────────────────────┘
                         │ HTTP POST /extract
                         │ multipart/form-data (PDF or Image)
                         ▼
┌──────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                    │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐  ┌───────────┐  │
│  │   Ingestion │   │  Processing  │  │  Response │  │
│  │    Layer    │──▶│    Layer     │─▶│  Builder  │  │
│  └─────────────┘   └──────────────┘  └───────────┘  │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                  OLLAMA + GEMMA 4 E4B                │
│            Local Inference (RTX 3050 6GB)            │
└──────────────────────────────────────────────────────┘
```

---

## Detailed Layer Breakdown

### 1. Ingestion Layer

Responsible for receiving files and routing them to the correct preprocessor.

```
Input File
    │
    ├── .pdf  ──▶  PDF Preprocessor (PyMuPDF)
    │                   │
    │                   ├── Text-extractable PDF?
    │                   │       ├── YES → extract text + embedded images
    │                   │       └── NO  → render pages as PNG (DPI=200)
    │                   │
    │                   └── Output: List[PageData]
    │                              { page_num, image_path, extracted_images[], text }
    │
    └── .png/.jpg/.jpeg ──▶  Image Preprocessor
                                │
                                └── Output: List[PageData]
                                           { page_num, image_path }
```

**Key decisions in ingestion:**
- Each PDF page is processed independently to manage VRAM
- Scanned PDFs (no text layer) are rendered as full-page images at 200 DPI for clarity
- Embedded images per page are extracted using PyMuPDF's `get_images()` with bounding boxes recorded

---

### 2. Processing Layer

The core pipeline — takes `PageData` and runs inference.

```
PageData (per page)
    │
    ├── Step 1: Image Association
    │       Determine if page has embedded images
    │       Record bounding box positions relative to text blocks
    │
    ├── Step 2: Build Ollama Payload
    │       [page_image] + [embedded_images] + [extraction_prompt]
    │       Images placed BEFORE text (Gemma 4 best practice)
    │
    ├── Step 3: Gemma 4 Inference (via Ollama)
    │       Model: gemma4:e4b
    │       Token budget: 1120 (max detail for OCR/document parsing)
    │       Thinking mode: DISABLED (faster, structured output)
    │       Returns: raw JSON string
    │
    ├── Step 4: Parse & Validate
    │       Pydantic model validation
    │       Retry once on malformed JSON (with correction prompt)
    │
    └── Step 5: Image Attachment
            Save extracted question images to /media/
            Embed base64 thumbnail in response JSON
            Store full image as file reference
```

---

### 3. Response Builder

Aggregates all pages into a final structured response.

```python
{
  "source_file": "exam_paper.pdf",
  "total_pages": 5,
  "total_questions": 20,
  "processing_time_ms": 4200,
  "questions": [
    {
      "question_number": 1,
      "page": 1,
      "question_text": "What is the powerhouse of the cell?",
      "has_image": false,
      "image": null,
      "options": {
        "A": "Nucleus",
        "B": "Mitochondria",
        "C": "Ribosome",
        "D": "Golgi Apparatus"
      },
      "answer": "B",
      "confidence": "high"
    },
    {
      "question_number": 5,
      "page": 2,
      "question_text": "What structure is labeled X in the diagram?",
      "has_image": true,
      "image": {
        "filename": "q5_page2_img0.png",
        "description": "Biology cell diagram with labeled organelles",
        "base64_thumbnail": "data:image/png;base64,..."
      },
      "options": {
        "A": "Cell Wall",
        "B": "Vacuole",
        "C": "Chloroplast",
        "D": "Cytoplasm"
      },
      "answer": null,
      "confidence": "medium"
    }
  ]
}
```

---

## Directory Structure

```
mcq-extractor/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── routers/
│   │   └── extract.py           # POST /extract endpoint
│   ├── services/
│   │   ├── ingestion.py         # File routing + PDF/image preprocessing
│   │   ├── pdf_processor.py     # PyMuPDF logic (text + image extraction)
│   │   ├── image_processor.py   # Image file handling
│   │   ├── ollama_client.py     # Gemma 4 inference wrapper
│   │   └── mcq_parser.py        # JSON parsing + Pydantic validation
│   ├── models/
│   │   └── schemas.py           # Pydantic models (MCQQuestion, MCQResponse)
│   ├── prompts/
│   │   └── extraction.py        # System + user prompt templates
│   └── utils/
│       ├── image_utils.py       # Image save, base64, thumbnail
│       └── file_utils.py        # Temp file management
├── media/                       # Extracted question images stored here
├── uploads/                     # Temp upload storage
├── tests/
│   ├── test_pdf_processor.py
│   ├── test_ollama_client.py
│   └── sample_exams/
├── .env                         # OLLAMA_HOST, MODEL_NAME, etc.
├── requirements.txt
└── README.md
```

---

## API Endpoints

### `POST /extract`

Upload a PDF or image and extract MCQs.

**Request:**
```
Content-Type: multipart/form-data

file: <PDF or image file>
options: {
  "model": "gemma4:e4b",          // optional, default: gemma4:e4b
  "thinking_mode": false,          // optional, default: false
  "token_budget": 1120,            // optional, default: 1120 (max OCR quality)
  "include_images": true           // optional, default: true
}
```

**Response:** `200 OK`
```json
{
  "source_file": "exam.pdf",
  "total_pages": 3,
  "total_questions": 15,
  "processing_time_ms": 3800,
  "questions": [ ... ]
}
```

**Error Responses:**
- `422 Unprocessable Entity` — unsupported file type
- `500 Internal Server Error` — inference failure
- `503 Service Unavailable` — Ollama not running

---

### `GET /health`

Check if Ollama and the model are available.

**Response:**
```json
{
  "status": "ok",
  "ollama": "running",
  "model": "gemma4:e4b",
  "model_loaded": true
}
```

---

### `GET /models`

List available local models.

**Response:**
```json
{
  "models": ["gemma4:e4b", "gemma4:e2b"]
}
```

---

## Pydantic Data Models

```python
from pydantic import BaseModel
from typing import Optional

class MCQImage(BaseModel):
    filename: str
    description: str
    base64_thumbnail: Optional[str] = None

class MCQQuestion(BaseModel):
    question_number: int
    page: int
    question_text: str
    has_image: bool
    image: Optional[MCQImage] = None
    options: dict[str, str]       # {"A": "...", "B": "...", "C": "...", "D": "..."}
    answer: Optional[str] = None  # None if answer key not present
    confidence: str               # "high" | "medium" | "low"

class MCQResponse(BaseModel):
    source_file: str
    total_pages: int
    total_questions: int
    processing_time_ms: int
    questions: list[MCQQuestion]
```

---

## Gemma 4 Prompt Design

### System Prompt

```python
SYSTEM_PROMPT = """You are a precise MCQ extraction engine.

Your task is to extract Multiple Choice Questions from the provided document page.

Rules:
- Extract ALL questions visible on the page
- Preserve exact question text and option text
- If a question references an image in the page, set has_image to true
- If an answer key is visible, include the correct answer letter
- If no answer is shown, set answer to null
- Respond ONLY with valid JSON — no markdown, no explanation

Output format:
{
  "questions": [
    {
      "question_number": <int>,
      "question_text": "<string>",
      "has_image": <bool>,
      "image_description": "<string or null>",
      "options": {
        "A": "<string>",
        "B": "<string>",
        "C": "<string>",
        "D": "<string>"
      },
      "answer": "<A|B|C|D or null>",
      "confidence": "<high|medium|low>"
    }
  ]
}
"""
```

### User Prompt (per page)

```python
USER_PROMPT = """Extract all MCQs from this document page.
Page number: {page_num}
Note: If any question references a diagram or image visible on this page, 
set has_image to true and describe the image in image_description."""
```

> Images are placed **before** the text prompt in the Ollama message payload, following Gemma 4's modality order best practice.

---

## Image Extraction Strategy

### Two-Tier Approach

**Tier 1 — Let Gemma 4 handle layout (recommended)**

Send the entire page rendered as a PNG to Gemma 4. The model uses its native document understanding to identify which images belong to which questions.

```
[Full page PNG] + [Extraction prompt]
        ↓
Gemma 4 E4B
        ↓
{ "has_image": true, "image_description": "Bar chart showing..." }
```

**Tier 2 — PyMuPDF positional extraction (precise)**

Extract embedded images using bounding box coordinates. Associate each image to the nearest question text block by Y-axis proximity.

```python
# Get image bounding boxes
for img in page.get_images(full=True):
    bbox = page.get_image_bbox(img[7])  # image name
    # find nearest text block above this bbox
    # associate with question
```

Use Tier 1 by default. Fall back to Tier 2 for complex multi-column layouts.

---

## Ollama Client Configuration

```python
# .env
OLLAMA_HOST=http://localhost:11434
MODEL_NAME=gemma4:e4b
TEMPERATURE=1.0
TOP_P=0.95
TOP_K=64
TOKEN_BUDGET=1120     # max OCR quality
THINKING_MODE=false   # disable for structured output
MAX_RETRIES=2
```

```python
# ollama_client.py
import ollama
import os

class OllamaClient:
    def __init__(self):
        self.model = os.getenv("MODEL_NAME", "gemma4:e4b")
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def extract_mcqs(self, page_image_bytes: bytes, page_num: int) -> str:
        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": USER_PROMPT.format(page_num=page_num),
                    "images": [page_image_bytes],  # image BEFORE text
                }
            ],
            options={
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 64,
            }
        )
        return response.message.content
```

---

## Dependency Stack

```
# requirements.txt
fastapi==0.115.x
uvicorn[standard]==0.29.x
python-multipart==0.0.9      # file upload support
pymupdf==1.24.x              # PDF processing (fitz)
ollama==0.3.x                # Ollama Python SDK
pydantic==2.x
Pillow==10.x                 # image manipulation
python-dotenv==1.0.x
```

---

## Setup & Run

```bash
# 1. Clone and install
git clone <repo>
cd mcq-extractor
pip install -r requirements.txt

# 2. Start Ollama and pull model
ollama serve
ollama pull gemma4:e4b

# 3. Configure environment
cp .env.example .env

# 4. Run the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Test the endpoint
curl -X POST http://localhost:8000/extract \
  -F "file=@sample_exam.pdf" \
  -F 'options={"include_images": true}'
```

---

## Performance Notes (RTX 3050 6GB)

| Scenario | Estimated Time |
|---|---|
| Single page, no images | ~2–4 seconds |
| Single page, with images | ~4–7 seconds |
| 10-page PDF, text only | ~25–40 seconds |
| 10-page PDF, mixed images | ~50–90 seconds |

**Optimization tips:**
- Process pages sequentially (not parallel) to avoid VRAM overflow
- Use `token_budget=560` if speed is priority over OCR quality
- Keep Ollama's `num_gpu=-1` to use all available GPU layers
- Avoid running other GPU-intensive processes simultaneously

---

## Future Enhancements

- [ ] Batch job queue (Redis + Celery) for large exam papers
- [ ] WebSocket endpoint for real-time progress updates
- [ ] Support for `.docx` input files
- [ ] Answer key matching across separate answer sheet uploads
- [ ] Fine-tuned Gemma 4 E4B on MCQ-specific dataset for higher accuracy
- [ ] Export to JSON / CSV / Anki flashcard format
