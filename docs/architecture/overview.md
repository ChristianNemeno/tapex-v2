# System Architecture Overview

High-level view of the full request pipeline from client upload to MCQ JSON response.

```mermaid
flowchart TD
    Client([Client])

    subgraph Docker["Docker Compose"]
        subgraph API["mcq-extractor :8000"]
            Router["ExtractRouter\n/extract  /health  /models"]
            Ingest["IngestionService\nroutes by file type"]
            PDF["PDFProcessor\nPyMuPDF"]
            IMG["ImageProcessor\nPillow"]
            OC["OllamaClient\nasync inference"]
            Parser["MCQParser\nJSON validation"]
            FU["FileUtils\nsave / cleanup"]
            IU["ImageUtils\nbase64 thumbnails"]
        end

        subgraph OllamaService["ollama :11434"]
            Gemma["Gemma 4 E4B\n(quantized, ~5 GB VRAM)"]
        end
    end

    FS[("File System\n/uploads  /media")]

    Client -->|"POST /extract\nmultipart file"| Router
    Router --> FU
    FU -->|save upload| FS
    Router --> Ingest

    Ingest -->|".pdf"| PDF
    Ingest -->|".png / .jpg"| IMG

    PDF -->|"render pages\nextract images"| FS
    IMG -->|"copy to uploads"| FS

    PDF -->|"List[PageData]"| OC
    IMG -->|"PageData"| OC

    OC -->|"images + prompt"| Gemma
    Gemma -->|"raw JSON"| OC

    OC -->|"raw JSON"| Parser
    Parser --> IU
    IU -->|"base64 thumbnails"| Parser
    Parser -->|"List[MCQQuestion]"| Router

    Router -->|"MCQResponse JSON"| Client
    Router --> FU
    FU -->|"cleanup temp files"| FS
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Sequential page processing | Avoids VRAM overflow — one page in VRAM at a time |
| Scanned PDF detection | Text layer < 50 chars triggers full-page image render |
| Images sent before text | Gemma 4 best practice for multimodal accuracy |
| Retry on parse failure | Up to `MAX_RETRIES` (default 2) if Gemma 4 returns malformed JSON |
| Skip malformed questions | Partial extraction is better than a total page failure |
| Async executor pattern | Ollama Python SDK is synchronous; wrapped in `run_in_executor` to not block FastAPI event loop |
