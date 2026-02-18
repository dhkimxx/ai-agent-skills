---
name: datasheet-intelligence
description: Convert mixed-format datasheets and hardware reference files (PDF, DOCX, HTML, Markdown, XLSX/CSV) into normalized Markdown knowledge files for AI coding agents. Use when a user asks to ingest datasheets, register maps, pinout/timing sheets, revision histories, or internal hardware notes before searching datasheet content or generating code. Produce RAG-ready section chunks, anchors, image references, and metadata under .context/knowledge.
---

# Datasheet Intelligence

## Purpose

Ingest multi-format datasheets into a single Markdown-first knowledge base so agents can answer hardware questions using consistent structure.

## Prerequisites

Check `uv` first:

```bash
uv --version
```

If `uv` is not installed, install it by OS:

```bash
# macOS (Homebrew)
brew install uv

# Linux (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (WinGet)
winget install --id=astral-sh.uv -e
```

After installation, restart the shell and verify `uv --version` again.

## Workflow

1. Place source datasheets in a folder (for example `docs/datasheets/`).
2. Run `scripts/ingest_docs.py` with `uv run --with docling python3`.
3. Read outputs from `.context/knowledge/`:
   - `<doc>.md`: normalized markdown
   - `<doc>.sections.jsonl`: section chunks for retrieval
   - `<doc>.tables.md`: table-focused markdown
   - `<doc>.meta.json`: conversion metadata and validation info
   - `<doc>.docling.json`: raw Docling structured export
   - `knowledge.index.json`: corpus manifest
4. Use search/read helpers:
   - `scripts/search_docs.py` for corpus search
   - `scripts/read_docs.py` for focused section reads

## Commands

```bash
# Ingest all supported datasheets from a directory
uv run --with docling python3 scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge

# Ingest only top-level files and skip OCR for faster runs
uv run --with docling python3 scripts/ingest_docs.py docs/datasheets --non-recursive --no-ocr

# Search and focused read
uv run python3 scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge
uv run python3 scripts/read_docs.py exynos_spi_v1 --anchor section-4-2
```

## Operational Rules

- Use command-first guidance (above) instead of low-level converter internals.
- Prefer `uv run` commands and do not assume a global `python` alias.
- Keep output location at `.context/knowledge` unless user asks otherwise.
- Before the first run, ensure generated artifacts are ignored by git (`.context/` or `.context/knowledge/` in `.gitignore`).
- Preserve image presence in markdown with `![image_ref](path)` entries.
- Keep section anchors and normalize textual references like `See Table 4.2` into markdown links when anchor targets exist.
- Run on all provided files and summarize failures without stopping the whole batch unless explicitly requested.
- Emit a reusable system prompt hint file that tells downstream agents to check `.context/knowledge` first.
- For detailed CLI options and execution presets, read `references/execution-options.md`.
- If `uv` is unavailable, follow the fallback instructions in `references/execution-options.md`.

## Resources

- `scripts/ingest_docs.py`: main ingestion pipeline
- `scripts/search_docs.py`: chunk-level search helper
- `scripts/read_docs.py`: focused reader helper
- `references/output-contract.md`: output schema and retrieval contract
- `references/execution-options.md`: detailed runtime flags and command presets
