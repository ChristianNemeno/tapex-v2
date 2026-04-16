# Sequence Diagram: POST /extract (Image)

Flow when a client uploads a standalone image file (PNG, JPG, JPEG).

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Router as ExtractRouter
    participant FU as FileUtils
    participant Ingest as IngestionService
    participant IMG as ImageProcessor
    participant OC as OllamaClient
    participant Ollama as Ollama (Gemma 4)
    participant Parser as MCQParser
    participant IU as ImageUtils

    Client->>Router: POST /extract (multipart: page.png)
    Router->>FU: save_upload(file, UPLOAD_DIR)
    FU-->>Router: /uploads/{uuid}.png

    Router->>Ingest: ingest_file(path, upload_dir, media_dir)
    Ingest->>IMG: process_image(image_path, upload_dir)
    IMG->>FU: copy image → /uploads/{uuid2}.png
    IMG-->>Ingest: PageData(page_num=1, image_path, extracted_images=[], text="")
    Ingest-->>Router: [PageData]

    Router->>OC: extract_mcqs(page_data)
    OC->>IU: encode_image_base64(image_path) → image bytes
    Note over OC: No extracted_images for standalone images
    OC->>Ollama: chat(model, messages=[system, user+image], options)
    Ollama-->>OC: raw JSON string
    OC-->>Router: raw JSON string

    Router->>Parser: parse_mcq_response(raw, page_num=1)
    Parser->>Parser: strip markdown fences
    Parser->>Parser: json.loads()
    Parser->>Parser: validate each question with Pydantic
    Parser-->>Router: List[MCQQuestion]

    Router->>Parser: attach_images(questions, page_data, media_dir)
    Note over Parser: extracted_images=[] so no thumbnails attached
    Parser-->>Router: List[MCQQuestion] (unchanged)

    Router->>FU: cleanup_file(/uploads/{uuid}.png)
    Router->>FU: cleanup_file(/uploads/{uuid2}.png)

    Router-->>Client: MCQResponse(source_file, total_pages=1, total_questions, processing_time_ms, questions)
```

## Differences from PDF Flow

| Aspect | PDF | Image |
|--------|-----|-------|
| Pages | Multiple | Always 1 |
| Page rendering | PyMuPDF → 200 DPI PNG | File used as-is |
| Embedded image extraction | Yes (non-scanned) | No |
| Image thumbnails in response | Possible | Not applicable |
| Temp files created | Page PNGs + upload | Upload copy only |
| Scanned detection | Yes | N/A (already an image) |
