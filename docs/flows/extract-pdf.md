# Sequence Diagram: POST /extract (PDF)

Full end-to-end flow when a client uploads a PDF file.

```mermaid
sequenceDiagram
    autonumber
    participant Client
    participant Router as ExtractRouter
    participant FU as FileUtils
    participant Ingest as IngestionService
    participant PDF as PDFProcessor
    participant OC as OllamaClient
    participant Ollama as Ollama (Gemma 4)
    participant Parser as MCQParser
    participant IU as ImageUtils

    Client->>Router: POST /extract (multipart: exam.pdf)
    Router->>FU: save_upload(file, UPLOAD_DIR)
    FU-->>Router: /uploads/{uuid}.pdf

    Router->>Ingest: ingest_file(path, upload_dir, media_dir)
    Ingest->>PDF: extract_pages(pdf_path, upload_dir, media_dir)

    loop For each page in PDF
        PDF->>PDF: page.get_text() → text
        PDF->>PDF: detect scanned (len(text) < 50?)
        PDF->>PDF: page.get_pixmap(dpi=200) → render PNG
        PDF->>FU: save page PNG → /uploads/{page}.png
        alt Not scanned (has text layer)
            PDF->>PDF: page.get_images() → extract embedded images
            PDF->>FU: save embedded images → /media/
        end
        PDF-->>Ingest: PageData(page_num, image_path, extracted_images, text)
    end

    Ingest-->>Router: List[PageData]

    loop For each PageData (with retry up to MAX_RETRIES)
        Router->>OC: extract_mcqs(page_data)
        OC->>IU: encode_image_base64(image_path) → page image bytes
        OC->>IU: encode_image_base64(img) × N embedded images
        OC->>Ollama: chat(model, messages=[system, user+images], options)
        Note over OC,Ollama: images sent BEFORE text prompt
        Ollama-->>OC: raw JSON string
        OC-->>Router: raw JSON string

        Router->>Parser: parse_mcq_response(raw, page_num)
        Parser->>Parser: strip markdown fences
        Parser->>Parser: json.loads()
        Parser->>Parser: validate each question with Pydantic
        Parser-->>Router: List[MCQQuestion]

        Router->>Parser: attach_images(questions, page_data, media_dir)
        Parser->>IU: create_thumbnail(img_path) → base64 (max 200×200)
        IU-->>Parser: base64_thumbnail
        Parser->>Parser: assign MCQImage to matching MCQQuestion
        Parser-->>Router: List[MCQQuestion] (with images)

        Router->>FU: cleanup_file(page_png)
    end

    Router->>FU: cleanup_file(/uploads/{uuid}.pdf)

    Router-->>Client: MCQResponse(source_file, total_pages, total_questions, processing_time_ms, questions)
```

## Notes

- **Scanned PDF**: If a page has fewer than 50 characters of text, it is treated as a scanned image. Only the full-page PNG is sent; no embedded image extraction is attempted.
- **Text-based PDF**: Both the rendered page PNG and any embedded images are extracted and sent to Gemma 4.
- **Retry logic**: If `parse_mcq_response` raises a `ValueError` (bad JSON), the `extract_mcqs` + parse cycle is retried up to `MAX_RETRIES` times for that page.
- **Partial failure**: If a question within a page fails Pydantic validation, it is skipped silently rather than failing the entire page.
- **Async**: `OllamaClient.extract_mcqs()` is `async` and uses `run_in_executor` to call the synchronous Ollama SDK without blocking FastAPI's event loop.
