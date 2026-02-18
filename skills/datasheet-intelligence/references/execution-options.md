# Execution Options

Use this guide when choosing runtime flags for datasheet ingestion and retrieval scripts.

## Priority Policy

When a task requires datasheet evidence (for example register-level code generation, bit setting validation, timing/pin constraints), run this pipeline first:

1. `scripts/check_deps.py`
2. `scripts/ingest_docs.py`
3. `scripts/search_docs.py`
4. `scripts/read_docs.py`

This policy applies even when the user directly asks for code and even when source files are Word/Excel.
Avoid direct source parsing commands (`pdftotext`, `docx2txt`, `antiword`, `xlsx2csv`, `pandoc`, ad-hoc regex scraping) unless ingestion is blocked or fails.

## Command Order (Recommended)

```bash
# 1) Preflight dependency checks
uv run python3 scripts/check_deps.py --pdf-backend docling_parse

# 2) Ingest mixed-format source files (PDF/DOCX/XLSX/CSV/HTML/MD)
uv run python3 scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge

# 3) Search candidate sections for required facts
uv run python3 scripts/search_docs.py "I2C0 clock divider" --knowledge-dir .context/knowledge

# 4) Read the exact section/table before answering
uv run python3 scripts/read_docs.py rp2040 --anchor i2c-controller --max-lines 200
```

## Repository Hygiene

Before running ingestion in a new repo, ignore generated knowledge artifacts:

```bash
if [ -f .gitignore ] && grep -qE '^\.context(/|$)' .gitignore; then
  echo ".context ignore rule already exists"
else
  echo ".context/knowledge/" >> .gitignore
fi
```

If you want broader ignore coverage for skill outputs, prefer `.context/`.

## Prerequisites

See [installation.md](installation.md) for setup instructions (including `uv`, OCR, and non-uv fallbacks).

## `scripts/ingest_docs.py`

Base command:

```bash
uv run python3 scripts/ingest_docs.py <source...> --output-dir .context/knowledge
```

### Options

- `--output-dir <path>`
  - Write artifacts to a custom knowledge folder.
  - Default: `.context/knowledge`
- `--chunk-max-chars <int>`
  - Maximum characters per retrieval chunk.
  - Default: `2200`
- `--chunk-overlap <int>`
  - Character overlap between adjacent chunks.
  - Default: `220`
- `--non-recursive`
  - Process only the top-level files in each source directory.
- `--pdf-backend {docling_parse,pypdfium2}`
  - Select PDF backend explicitly.
  - Default: `docling_parse`
- `--no-ocr`
  - Disable PDF OCR for speed when text is already machine-readable.
- `--no-retry-no-ocr`
  - Disable automatic one-time PDF retry with OCR disabled.
- `--fast`
  - Enable fast mode (Force `--no-ocr`, `--no-images`, and disable table structure analysis).
  - Recommended for large files (>100 pages) or when only text is needed.
- `--skip-preflight`
  - Skip dependency checks from `scripts/check_deps.py`.
- `--debug`
  - Enable traceback output and debug logs for failure diagnostics.
- `--no-images`
  - Skip image extraction to reduce runtime and output size.
- `--fail-on-error`
  - Return non-zero exit code if any document fails conversion.
  - Use this for CI and automated checks.
- `-v`, `--verbose`
  - Print per-file progress and unexpected error logs.

### Preset Examples

```bash
# Balanced default run
uv run python3 scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge

# Faster run (no OCR, no nested folders)
uv run python3 scripts/ingest_docs.py docs/datasheets --non-recursive --no-ocr

# CI-safe run (fail fast on conversion errors)
uv run python3 scripts/ingest_docs.py docs/datasheets --fail-on-error -v

# Force pypdfium2 backend for PDF parsing
uv run python3 scripts/ingest_docs.py docs/datasheets --pdf-backend pypdfium2

# Debug run for deeper error diagnostics
uv run python3 scripts/ingest_docs.py docs/datasheets --debug -v
```

### Large Files & Performance

For documents exceeding 100 pages (e.g., full MCU datasheets), the default pipeline may be slow due to table structure analysis and OCR.

| Flag | Disables | Use Case |
| :--- | :--- | :--- |
| `--fast` | OCR, Tables, Images | **Recommended**: Maximum speed for large files when you only need text search. |
| `--no-ocr` | OCR | Balanced speed for digital-native PDFs where table structure is important. |
| `--no-images` | Images | Reduces output size but keeps text/tables. |

> [!TIP]
> Use `--fast` first for 500+ page documents. If you miss table data, try `--no-ocr`.

## `scripts/check_deps.py`

Base command:

```bash
uv run python3 scripts/check_deps.py --pdf-backend docling_parse
```

### Options

- `--pdf-backend {docling_parse,pypdfium2}`
  - Validate dependency health for the selected backend.
- `--no-ocr`
  - Skip OCR binary checks.
- `--require-uv`
  - Treat missing/unhealthy `uv` as failure.
- `--require-tesseract`
  - Treat missing/unhealthy `tesseract` as failure when OCR is enabled.
- `-v`, `--verbose`
  - Print pass-level checks too.

### Preset Examples

```bash
# Default preflight for docling_parse backend
uv run python3 scripts/check_deps.py --pdf-backend docling_parse -v

# Strict OCR preflight for Tesseract path
uv run python3 scripts/check_deps.py --pdf-backend pypdfium2 --require-tesseract
```

## `scripts/search_docs.py`

Base command:

```bash
uv run python3 scripts/search_docs.py "<query>" --knowledge-dir .context/knowledge
```

### Options

- `--knowledge-dir <path>`
  - Directory containing `*.sections.jsonl` outputs.
  - Default: `.context/knowledge`
- `--regex`
  - Treat `query` as a regular expression.
- `--case-sensitive`
  - Disable default case-insensitive matching.
- `--max-hits <int>`
  - Limit number of printed matches.
  - Default: `20`

### Preset Examples

```bash
# Literal keyword search
uv run python3 scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge

# Regex search for register names
uv run python3 scripts/search_docs.py "REG_[A-Z0-9_]+" --regex --max-hits 50

# Case-sensitive lookup
uv run python3 scripts/search_docs.py "CRC16" --case-sensitive
```

## `scripts/read_docs.py`

Base command:

```bash
uv run python3 scripts/read_docs.py <doc-id> --knowledge-dir .context/knowledge
```

### Options

- `--knowledge-dir <path>`
  - Directory containing normalized markdown docs.
  - Default: `.context/knowledge`
- `--anchor <id>`
  - Print only the section range starting at a specific anchor.
- `--max-lines <int>`
  - Limit output size for terminal readability.
  - Default: `160`

### Preset Examples

```bash
# Read beginning of a document
uv run python3 scripts/read_docs.py exynos_spi_v1 --max-lines 120

# Read a specific section by anchor
uv run python3 scripts/read_docs.py exynos_spi_v1 --anchor section-4-2 --max-lines 200
```

## Recommended Defaults

- Keep `--output-dir .context/knowledge` for consistent downstream discovery.
- Generated artifacts are grouped per document under `.context/knowledge/<doc_id>/`.
- Start with default chunk settings unless retrieval quality is clearly poor.
- Use `--fail-on-error` in CI; skip it for exploratory local batch runs.

## Troubleshooting OCR/PDF Errors

If you see OCR- or PDF-backend-related failures, follow this order:

1. Run dependency preflight:

```bash
uv run python3 scripts/check_deps.py --pdf-backend docling_parse -v
```

2. Inspect `.context/knowledge/<doc_id>/<doc_id>.meta.json` to identify the concrete error message.
3. Re-run with OCR disabled:

```bash
uv run python3 scripts/ingest_docs.py docs/datasheets --no-ocr -v
```

4. If failure persists, switch backend:

```bash
uv run python3 scripts/ingest_docs.py docs/datasheets --pdf-backend pypdfium2 -v
```

5. If failures are opaque, re-run with debug:

```bash
uv run python3 scripts/ingest_docs.py docs/datasheets --debug -v
```

6. If both backend/ocr retries fail, keep the `.meta.json` errors in the report and avoid speculative root-cause claims.

Notes:

- `Cannot close object; pdfium library is destroyed` can appear as a follow-up warning after earlier PDF processing failures.
- `scripts/ingest_docs.py` already retries failed PDF conversions once with OCR disabled unless `--no-retry-no-ocr` is specified.

## Anti-Patterns

- Do not mix raw-file parser output and `.context/knowledge` output in the same factual answer.
- Do not cite register addresses/bitfields without an anchorable source from ingested artifacts.
- Do not skip `search_docs.py`/`read_docs.py` when the answer requires datasheet-backed precision.

## Official References

- Docling installation (OCR engine system packages): https://docling-project.github.io/docling/usage/
- Docling OCR model options (Tesseract/Tesseract-CLI behavior): https://docling-project.github.io/docling/reference/pipeline_options/
- pypdfium2 runtime notes (bundled wheels and fallback setup): https://github.com/pypdfium2-team/pypdfium2
