---
name: datasheet-intelligence
description: Prioritize this skill for any hardware task that requires datasheet-grounded facts or code (register addresses, bit fields, init sequences, timing/pin constraints). Ingest mixed-format sources (PDF, DOCX, HTML, Markdown, XLSX/CSV) with scripts/ingest_docs.py, then answer from .context/knowledge artifacts. Use this even when the user asks directly for code generation from datasheets; avoid ad-hoc source parsers (pdftotext, docx2txt, xlsx2csv, etc.) unless ingestion is blocked or fails.
---

# Datasheet Intelligence

## Purpose

Ingest multi-format datasheets into a single Markdown-first knowledge base so agents can answer hardware questions using consistent structure.

## Prerequisites

This skill requires `uv` for dependency management and optionally `tesseract` for OCR.

1. **Check `uv`**: Run `uv --version`.
2. **Check Dependencies**: Run `uv run python3 scripts/check_deps.py` (checks docling, pdfium, and tesseract).

> [!NOTE]
> If `uv` or `tesseract` are missing, see [installation.md](references/installation.md). Tesseract is optional but recommended for scanned PDFs.

Scripts in this skill use **PEP 723 inline metadata**. `uv run` will automatically install all required dependencies (docling, pypdfium2, etc.) in an ephemeral environment.

## Workflow

1. If required docs are already ingested in `.context/knowledge/`, skip re-ingest.
2. If docs are missing, run `scripts/check_deps.py` then `scripts/ingest_docs.py`.
3. Read outputs from `.context/knowledge/`. See [output-contract.md](references/output-contract.md) for the file structure.
4. Use `scripts/search_docs.py` and `scripts/read_docs.py` to find and read specific sections.
5. Draft the final answer citing specific `doc_id` and sections.

## Commands

```bash
# Check runtime dependencies
uv run python3 scripts/check_deps.py

# Ingest all supported datasheets (Standard)
uv run python3 scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge

# Ingest large files quickly (No OCR, No Tables, No Images) - Recommended for >100 pages
uv run python3 scripts/ingest_docs.py docs/datasheets --fast

# Ingest only top-level files without OCR
uv run python3 scripts/ingest_docs.py docs/datasheets --non-recursive --no-ocr

# If PDF conversion is unstable, switch backend explicitly
uv run python3 scripts/ingest_docs.py docs/datasheets --pdf-backend pypdfium2

# Debug mode (traceback + debug logs)
uv run python3 scripts/ingest_docs.py docs/datasheets --debug -v

# Search and focused read
uv run python3 scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge
uv run python3 scripts/read_docs.py exynos_spi_v1 --anchor section-4-2
```

## Operational Rules

- Use command-first guidance (above) instead of low-level converter internals.
- Prefer `uv run` commands and do not assume a global `python` alias.
- For datasheet-grounded tasks, this skill has higher priority than generic text extraction flows.
- Keep output location at `.context/knowledge` unless user asks otherwise.
- Preserve image presence in markdown with `![image_ref](path)` entries.
- Keep section anchors and normalize textual references like `See Table 4.2` into markdown links when anchor targets exist.
- Run on all provided files and summarize failures without stopping the whole batch unless explicitly requested.
- Run `scripts/check_deps.py` before large ingestion batches to surface environment issues early.
- Do not parse source files directly with ad-hoc tools (`pdftotext`, `pdfplumber`, `docx2txt`, `antiword`, `xlsx2csv`, `pandoc`, custom regex scraping) before trying `scripts/ingest_docs.py`.
- For Word/Excel/PDF inputs, treat `scripts/ingest_docs.py` as the default and only extraction path.
- Use `--debug` when failures are opaque and keep traceback logs with each failed `<doc>.meta.json`.
- If ingestion fails for specific PDF files, check each `<doc>.meta.json` first, then retry deterministically with `--no-ocr` or `--pdf-backend pypdfium2` before proposing non-skill parsers.
- `scripts/ingest_docs.py` automatically retries failed PDF documents once with OCR disabled unless `--no-retry-no-ocr` is set.
- If both retries fail, report the concrete error from `.meta.json` and request approval before using any fallback parser.
- For generated code or factual claims, cite the source from `.context/knowledge` (document + anchor/section; include table source when register values come from tables).
- For detailed CLI options and execution presets, read `references/execution-options.md`.
- If `uv` is unavailable, follow the fallback instructions in `references/execution-options.md`.

## Resources

- `scripts/ingest_docs.py`: main ingestion pipeline
- `scripts/check_deps.py`: preflight dependency checks
- `scripts/search_docs.py`: chunk-level search helper
- `scripts/read_docs.py`: focused reader helper
- `references/output-contract.md`: output schema and retrieval contract
- `references/execution-options.md`: detailed runtime flags and command presets
