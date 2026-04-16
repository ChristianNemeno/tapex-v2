# MCQ Extractor — Documentation

MCQ Extractor is a FastAPI backend service that extracts multiple-choice questions from PDF and image files using the Gemma 4 E4B large language model running locally via Ollama.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 + Uvicorn |
| LLM Runtime | Ollama (Gemma 4 E4B) |
| PDF Processing | PyMuPDF (fitz) |
| Image Processing | Pillow |
| Validation | Pydantic v2 |
| Containerization | Docker + Docker Compose |
| Language | Python 3.11 |

## Documentation Index

### Architecture
- [System Overview](architecture/overview.md) — High-level flowchart of the full request pipeline
- [Component Diagram](architecture/components.md) — Class diagram of all modules and their interfaces
- [Deployment Topology](architecture/deployment.md) — Docker Compose service layout and volumes

### Data Models
- [Entity Relationship Diagram](data-models/erd.md) — Pydantic schema relationships (ERD)

### API Reference
- [Endpoints](api/endpoints.md) — All HTTP endpoints with request/response shapes and examples

### Request Flows
- [Extract from PDF](flows/extract-pdf.md) — Sequence diagram for `POST /extract` with a PDF file
- [Extract from Image](flows/extract-image.md) — Sequence diagram for `POST /extract` with an image file
- [Health & Models](flows/health-check.md) — Sequence diagrams for `GET /health` and `GET /models`

### Services
- [Service Dependency Map](services/service-map.md) — Module import and dependency graph
