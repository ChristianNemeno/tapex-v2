# Service Dependency Map

Import and call dependency graph between all application modules.

```mermaid
flowchart TD
    subgraph Entrypoint
        Main["app/main.py\nFastAPI app + lifespan"]
    end

    subgraph Routers
        Extract["app/routers/extract.py\nHTTP handlers"]
    end

    subgraph Services
        Ingest["app/services/ingestion.py"]
        PDF["app/services/pdf_processor.py"]
        IMG["app/services/image_processor.py"]
        OC["app/services/ollama_client.py"]
        Parser["app/services/mcq_parser.py"]
    end

    subgraph Models
        Schemas["app/models/schemas.py\nPageData, MCQQuestion\nMCQImage, MCQResponse"]
    end

    subgraph Prompts
        Prompts["app/prompts/extraction.py\nSYSTEM_PROMPT\nbuild_user_prompt()"]
    end

    subgraph Utils
        FU["app/utils/file_utils.py\nensure_dirs, save_upload\ncleanup_file"]
        IU["app/utils/image_utils.py\nread_image_bytes\nencode_image_base64\ncreate_thumbnail"]
    end

    subgraph ExternalLibs["External Libraries"]
        Fitz["PyMuPDF (fitz)"]
        Pillow["Pillow (PIL)"]
        OllamaSDK["ollama SDK"]
        Pydantic["Pydantic v2"]
        Dotenv["python-dotenv"]
    end

    Main --> Extract
    Main --> FU

    Extract --> Ingest
    Extract --> OC
    Extract --> Parser
    Extract --> FU
    Extract --> Schemas

    Ingest --> PDF
    Ingest --> IMG
    Ingest --> Schemas

    PDF --> FU
    PDF --> IU
    PDF --> Schemas
    PDF --> Fitz

    IMG --> FU
    IMG --> Schemas
    IMG --> Pillow

    OC --> Prompts
    OC --> Schemas
    OC --> OllamaSDK
    OC --> IU
    OC --> Dotenv

    Parser --> IU
    Parser --> Schemas
    Parser --> Pydantic

    IU --> Pillow
```

## Dependency Table

| Module | Imports from (internal) | Uses (external) |
|--------|------------------------|-----------------|
| `app/main.py` | `routers/extract`, `utils/file_utils` | `fastapi`, `dotenv` |
| `routers/extract.py` | `services/ingestion`, `services/ollama_client`, `services/mcq_parser`, `utils/file_utils`, `models/schemas` | `fastapi` |
| `services/ingestion.py` | `services/pdf_processor`, `services/image_processor`, `models/schemas` | `fastapi` |
| `services/pdf_processor.py` | `utils/file_utils`, `utils/image_utils`, `models/schemas` | `fitz` (PyMuPDF) |
| `services/image_processor.py` | `utils/file_utils`, `models/schemas` | `Pillow` |
| `services/ollama_client.py` | `prompts/extraction`, `models/schemas`, `utils/image_utils` | `ollama`, `dotenv` |
| `services/mcq_parser.py` | `utils/image_utils`, `models/schemas` | `Pydantic`, `json` |
| `utils/file_utils.py` | — | `pathlib`, `uuid`, `shutil` |
| `utils/image_utils.py` | — | `Pillow`, `base64` |
| `prompts/extraction.py` | — | — |
| `models/schemas.py` | — | `Pydantic` |
