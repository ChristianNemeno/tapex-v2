# Deployment Topology

Docker Compose layout showing containers, ports, volumes, and dependencies.

```mermaid
flowchart TD
    subgraph Host["Host Machine (NVIDIA RTX 3050 6 GB)"]
        subgraph Compose["docker-compose.yml"]
            subgraph MCQContainer["mcq-extractor container"]
                App["FastAPI App\nuvicorn app.main:app\n0.0.0.0:8000"]
            end

            subgraph OllamaContainer["ollama container"]
                OllamaServer["Ollama Server\n0.0.0.0:11434"]
                Gemma["Gemma 4 E4B model\n~9.6 GB on disk\n~5 GB VRAM"]
                OllamaServer --- Gemma
            end

            MCQContainer -->|"HTTP :11434\nollama SDK calls"| OllamaContainer
            MCQContainer -.->|"depends_on (healthy)"| OllamaContainer
        end

        subgraph Volumes["Named Volumes"]
            V1[("ollama_data\nmodel weights cache")]
            V2[("media_data\nextracted images")]
            V3[("uploads_data\ntemp uploads")]
        end

        OllamaContainer --- V1
        MCQContainer --- V2
        MCQContainer --- V3

        GPU["NVIDIA GPU\nCUDA"]
        OllamaContainer -->|"nvidia driver\nall GPUs"| GPU
    end

    Client(["External Client"])
    Client -->|"HTTP :8000"| MCQContainer
```

## Service Configuration

### `mcq-extractor`
| Setting | Value |
|---------|-------|
| Build context | `.` (local Dockerfile) |
| Base image | `python:3.11-slim` |
| Exposed port | `8000` |
| Env file | `.env` |
| Depends on | `ollama` (health check passes) |
| Volumes | `media_data:/app/media`, `uploads_data:/app/uploads` |

### `ollama`
| Setting | Value |
|---------|-------|
| Image | `ollama/ollama:latest` |
| Exposed port | `11434` |
| GPU | All NVIDIA GPUs (nvidia driver) |
| Volume | `ollama_data:/root/.ollama` |
| Health check | `curl -f http://localhost:11434/api/tags` |

## Environment Variables (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `MODEL_NAME` | `gemma4:e4b` | LLM model identifier |
| `TEMPERATURE` | `1.0` | Sampling temperature |
| `TOP_P` | `0.95` | Nucleus sampling |
| `TOP_K` | `64` | Top-k sampling |
| `TOKEN_BUDGET` | `1120` | Max token context for OCR |
| `MAX_RETRIES` | `2` | Retry attempts on JSON parse failure |
| `MEDIA_DIR` | `media` | Extracted images directory |
| `UPLOAD_DIR` | `uploads` | Temporary uploads directory |
