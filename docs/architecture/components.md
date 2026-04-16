# Component Diagram

Class diagram of all modules, their responsibilities, and public interfaces.

```mermaid
classDiagram
    class ExtractRouter {
        +extract(file: UploadFile) MCQResponse
        +health() dict
        +models() dict
    }

    class IngestionService {
        +ingest_file(file_path: Path, upload_dir: Path, media_dir: Path) List~PageData~
    }

    class PDFProcessor {
        -SCANNED_TEXT_THRESHOLD: int = 50
        -RENDER_DPI: int = 200
        +extract_pages(pdf_path: Path, upload_dir: Path, media_dir: Path) List~PageData~
    }

    class ImageProcessor {
        +process_image(image_path: Path, upload_dir: Path) PageData
    }

    class OllamaClient {
        -_client: ollama.Client
        -model: str
        -temperature: float
        -top_p: float
        -top_k: int
        -token_budget: int
        +extract_mcqs(page_data: PageData) str
        +health_check() dict
        +list_models() List~str~
    }

    class MCQParser {
        +parse_mcq_response(raw: str, page_num: int) List~MCQQuestion~
        +attach_images(questions: List~MCQQuestion~, page_data: PageData, media_dir: Path) List~MCQQuestion~
    }

    class FileUtils {
        +ensure_dirs(*dirs: Path) None
        +save_upload(file: UploadFile, upload_dir: Path) Path
        +cleanup_file(path: Path) None
    }

    class ImageUtils {
        +read_image_bytes(path: Path) bytes
        +encode_image_base64(path: Path) str
        +create_thumbnail(image_path: Path, max_size: int) str
    }

    class ExtractionPrompts {
        +SYSTEM_PROMPT: str
        +build_user_prompt(page_num: int, has_images: bool) str
    }

    class PageData {
        +page_num: int
        +image_path: Optional~Path~
        +extracted_images: List~Path~
        +text: str
    }

    class MCQImage {
        +filename: str
        +description: str
        +base64_thumbnail: str
    }

    class MCQQuestion {
        +question_number: int
        +page: int
        +question_text: str
        +has_image: bool
        +image: Optional~MCQImage~
        +options: Dict~str_str~
        +answer: Optional~str~
        +confidence: str
    }

    class MCQResponse {
        +source_file: str
        +total_pages: int
        +total_questions: int
        +processing_time_ms: int
        +questions: List~MCQQuestion~
    }

    ExtractRouter --> IngestionService : calls
    ExtractRouter --> OllamaClient : calls
    ExtractRouter --> MCQParser : calls
    ExtractRouter --> FileUtils : calls
    ExtractRouter --> MCQResponse : returns

    IngestionService --> PDFProcessor : delegates PDF
    IngestionService --> ImageProcessor : delegates image
    IngestionService --> PageData : produces

    PDFProcessor --> PageData : produces
    PDFProcessor --> FileUtils : uses
    PDFProcessor --> ImageUtils : uses

    ImageProcessor --> PageData : produces

    OllamaClient --> ExtractionPrompts : uses
    OllamaClient ..> PageData : reads

    MCQParser --> MCQQuestion : produces
    MCQParser --> ImageUtils : uses
    MCQParser ..> PageData : reads

    MCQResponse "1" *-- "0..*" MCQQuestion : contains
    MCQQuestion "1" *-- "0..1" MCQImage : has
```

## Module Responsibilities

| Module | Path | Responsibility |
|--------|------|---------------|
| `ExtractRouter` | `app/routers/extract.py` | HTTP endpoint handlers, orchestration, error handling |
| `IngestionService` | `app/services/ingestion.py` | Routes file to correct processor based on extension |
| `PDFProcessor` | `app/services/pdf_processor.py` | Opens PDF, detects scanned pages, renders PNGs, extracts embedded images |
| `ImageProcessor` | `app/services/image_processor.py` | Wraps a single image file as a one-page `PageData` |
| `OllamaClient` | `app/services/ollama_client.py` | Sends page images + prompt to Gemma 4, returns raw JSON |
| `MCQParser` | `app/services/mcq_parser.py` | Parses and validates Gemma 4 JSON output, attaches image thumbnails |
| `FileUtils` | `app/utils/file_utils.py` | Directory creation, upload saving, temp file cleanup |
| `ImageUtils` | `app/utils/image_utils.py` | Image byte reading, base64 encoding, thumbnail generation |
| `ExtractionPrompts` | `app/prompts/extraction.py` | System and user prompt templates for MCQ extraction |
