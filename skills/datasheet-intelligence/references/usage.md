# Usage Guide

All scripts auto-detect document format by file extension.
Use `uv run --project skills/datasheet-intelligence ...` as the default execution style.
When using `--structured`, add `--with docling`.
Recommended flow: `toc (when available) -> search -> read`. Use full-document reads only as a last resort.

---

## `scripts/toc.py` — TOC Extraction

Extracts table-of-contents entries from PDF bookmarks, then optionally filters by keywords to find relevant section pages.

```bash
SKILL_DIR="skills/datasheet-intelligence"

# Full TOC
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/toc.py" docs/rp2040.pdf

# Only I2C/GPIO-related sections
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/toc.py" docs/rp2040.pdf --filter "I2C,GPIO"

# Bookmark-less PDF or DOCX (heading analysis)
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/toc.py" docs/spec.docx --structured
```

**Output format** (JSON lines):

```json
{"level": 1, "title": "4.3. I2C", "page": 441}
```

| Argument | Description |
| :--- | :--- |
| `file_path` | Document file path |
| `--filter` | Comma-separated keyword filter |
| `--structured` | Heading analysis via docling (for bookmark-less PDF/DOCX) |

---

## `scripts/read.py` — Text Extraction

Extracts text with automatic format detection.

### PDF — Fast Mode (pypdfium2)

```bash
# Read selected pages
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 464-470

# Read multiple page ranges
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 25,441-445,464
```

If `--pages` is omitted, the script prints total page count guidance.

### PDF — Structured Mode (docling, table/heading fidelity)

Use this mode when table layout or heading fidelity is important. Passing selected pages to docling is much faster than parsing the full document.

```bash
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 464-470 --structured
```

> `--structured` must be run with `uv run --project ... --with docling`.

### DOCX / XLSX

```bash
# Narrow scope with search first
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/spec.docx "I2C0" "clock divider"
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/pinout.xlsx "GPIO" "FUNCSEL"

# Read only if needed
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/spec.docx
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/pinout.xlsx

# Structured parsing (docling, accurate markdown)
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/read.py" docs/spec.docx --structured
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/read.py" docs/pinout.xlsx --structured
```

| Argument | Description |
| :--- | :--- |
| `file_path` | Target file path (PDF/DOCX/XLSX) |
| `--pages` | PDF only. Page ranges (for example: `10`, `10-20`, `10,15,20`) |
| `--structured` | All formats. Structured parsing via docling (markdown output) |

---

## `scripts/search.py` — Keyword Search

Searches keywords with automatic format detection.

### PDF

Returns matches with a ±200 character context window.

```bash
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_CON"
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_CON" "I2C0_BASE"
```

Output: `{"keyword", "page", "context"}`

### DOCX

Returns full matched paragraphs.

```bash
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/spec.docx "I2C"
```

### XLSX

Returns matched row data.

```bash
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/pinout.xlsx "GPIO"
```

### Structured Search (docling)

Performs structure-aware search over heading/paragraph/table units.

```bash
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_CON" --structured
```

Output: `{"keyword", "section", "page", "type", "content_snippet"}`

| Argument | Description |
| :--- | :--- |
| `file_path` | Target file path (PDF/DOCX/XLSX) |
| `queries` | One or more search keywords |
| `--regex` | Treat queries as regular expressions |
| `--structured` | Structure-aware search via docling |
| `--max-hits` | Maximum result count (default: 20) |
