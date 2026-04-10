# MCQ Extractor

Extracts multiple choice questions from PDF and image files using [Gemma 4 E4B](https://deepmind.google/models/gemma/gemma-4/) running locally via [Ollama](https://ollama.com). No cloud APIs — all inference runs on your machine.

**Hardware target:** NVIDIA RTX 3050 6GB (Gemma 4 E4B at Q4 fits in ~5GB VRAM)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) for GPU passthrough

### Install NVIDIA Container Toolkit (Ubuntu)

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

---

## Quickstart

### 1. Clone and configure

```bash
git clone <repo-url>
cd tapex-v2
```

Copy `.env` and adjust if needed (defaults work out of the box):

```bash
cp .env .env.local  # optional — docker-compose uses .env by default
```

### 2. Start the services

```bash
docker compose up -d
```

This starts two containers:
- **`ollama`** — local inference server (port `11434`)
- **`mcq-extractor`** — FastAPI app (port `8000`)

### 3. Pull the model (first run only)

The model download is ~9.6 GB. Run this once:

```bash
bash scripts/pull-model.sh
```

Or manually:

```bash
docker compose exec ollama ollama pull gemma4:e4b
```

### 4. Verify everything is running

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "ollama": "ok",
  "model": "gemma4:e4b",
  "model_available": true,
  "available_models": ["gemma4:e4b"]
}
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
  "processing_time_ms": 18400,
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
      "answer": "C",
      "confidence": "high"
    }
  ]
}
```

### Other endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/extract` | Upload PDF or image, returns extracted MCQs |
| `GET` | `/health` | Check Ollama and model availability |
| `GET` | `/models` | List all models available in Ollama |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Configuration

All settings are in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://ollama:11434` | Ollama server URL (overridden by compose) |
| `MODEL_NAME` | `gemma4:e4b` | Model to use for inference |
| `TEMPERATURE` | `1.0` | Sampling temperature |
| `TOP_P` | `0.95` | Top-p sampling |
| `TOP_K` | `64` | Top-k sampling |
| `TOKEN_BUDGET` | `1120` | Image token budget (1120 = max OCR quality) |
| `MAX_RETRIES` | `2` | Inference retries on malformed JSON |
| `MEDIA_DIR` | `media` | Directory for saved extracted images |
| `UPLOAD_DIR` | `uploads` | Temporary upload directory |

---

## Running without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama separately and pull the model
ollama serve &
ollama pull gemma4:e4b

# Run the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running tests

```bash
# With Docker
docker compose exec mcq-extractor pytest tests/

# Locally
pytest tests/
```

---

## Stopping

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers and delete all data (including model weights)
```
