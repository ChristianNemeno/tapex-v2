# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FastAPI service that extracts multiple-choice questions from PDFs/images using **PaddleOCR PP-Structure** for layout-aware OCR and a deterministic MCQ structurer. No cloud APIs. No LLMs. Target hardware is a 6GB VRAM NVIDIA GPU, though CPU works too. This is a personal-use project.

## Common commands

```bash
# Bring up the container (mcq-extractor on :8000)
docker compose up -d

# Tests — OCR is mocked; no GPU required
pytest tests/
pytest tests/test_extract.py::test_structure_basic_mcq   # single test

# Local dev server (without Docker)
# Requires: pip install -r requirements.txt + apt-get install libgl1 libglib2.0-0
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Smoke check
curl http://localhost:8000/health
```

## Architecture

Request flow for `POST /extract`:

1. **Upload** → `utils/file_utils.save_upload` stores to `UPLOAD_DIR` under a UUID name.
2. **Ingest** → `services/ingestion.ingest_file` dispatches by extension to `pdf_processor` or `image_processor`. Both return `List[PageData]`.
3. **Per-page routing** in `routers/extract.py`:
   - If `page_data.layout` is set → **digital PDF path**: the layout was built from PyMuPDF's text layer in `pdf_processor`.
   - If `page_data.layout` is `None` → **scanned/image path**: `services/ocr_processor.run()` feeds the full-page PNG through PaddleOCR PP-Structure and returns a `LayoutPage`.
4. **Structure** → `services/mcq_structurer.structure(layout)` — deterministic regex-based parser. Sorts text blocks by position, groups by question-number markers, parses option markers (A–E), detects `Answer: X` lines, associates FigureRegions to questions by vertical bbox overlap.
5. **Attach images** → `services/mcq_parser.attach_images` matches `has_image=True` questions to embedded images **positionally by order** (unchanged from original pipeline). Base64 thumbnails (200×200) inline in the response.
6. **Cleanup** → upload + full-page PNGs deleted; embedded images in `MEDIA_DIR` are kept.

### Key types (`app/models/schemas.py`)

- `TextBlock`, `FigureRegion`, `LayoutPage` — intermediate representation shared by both PDF and OCR paths
- `PageData` — carries `image_path`, `extracted_images`, `text`, and `layout: Optional[LayoutPage]`
- `MCQQuestion` / `MCQResponse` — the API contract (`answer: Optional[str]` is often `null` without an LLM)

### Key invariants and gotchas

- **`answer` is usually `null`**: without an LLM, the structurer only fills `answer` when the page contains an explicit `Answer: B` or `Ans: B` marker.
- **PaddleOCR is lazy-loaded**: `ocr_processor._engine` is `None` at import; first call to `run()` triggers PP-Structure init (~5–10 s). Tests that monkeypatch `ocr_processor.run` bypass this entirely.
- **`OCR_USE_GPU` and `OCR_LANG` are read at engine init time** (inside `_get_engine()`), not at import. Changing them after the engine is created has no effect without restarting.
- **Digital PDFs skip OCR entirely**: PyMuPDF's `get_text("dict")` produces `LayoutPage` with positional text blocks. Pages with < 50 chars of selectable text are treated as scanned.
- **Figure association is positional**: embedded images extracted from digital PDFs are matched to `FigureRegion` bbox entries in order (first unmatched figure gets the first extracted image file). For scanned pages, figures are detected but have no associated image file — `has_image=True` but `image=null` in the response.
- **MCQ structurer drops groups with ≤ 1 option** (noise filter). Confidence: `high` = 4+ options + non-empty stem; `medium` = 2–3 options; `low` = 1 option.
- **`SCANNED_TEXT_THRESHOLD = 50`** in `pdf_processor.py` controls digital vs scanned branching.

### Extending the pipeline

- **New file format** → add to `ingestion.SUPPORTED_IMAGE_EXTS` or branch in `ingest_file`; return a `PageData` with `layout=None`.
- **Tuning MCQ parsing** → edit regex patterns in `services/mcq_structurer.py`. Tests use fixture-based `LayoutPage` objects, so no OCR needed to iterate.
- **Swap OCR engine** → replace `services/ocr_processor.run()` to return a `LayoutPage`; everything downstream is engine-agnostic.

## Reference docs in repo

- `docs/` — architecture/flow/API docs (Mermaid diagrams). Code is the source of truth.
- `gemma4-reference.md` — historical Gemma 4 prompting notes; no longer used.
- `mcq-extractor-architecture.md` — original design doc for the LLM-based pipeline.
