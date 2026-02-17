---
name: datasheet-preprocess
description: Convert mixed-format datasheets and hardware reference files (PDF, DOCX, HTML, Markdown, XLSX/CSV) into normalized Markdown knowledge files for AI coding agents. Use when a user asks to ingest datasheets, register maps, pinout/timing sheets, revision histories, or internal hardware notes before searching datasheet content or generating code. Produce RAG-ready section chunks, anchors, image references, and metadata under .context/knowledge.
---

# Datasheet Preprocess

## Purpose

Ingest multi-format datasheets into a single Markdown-first knowledge base so agents can answer hardware questions using consistent structure.

## Workflow

1. Place source datasheets in a folder (for example `docs/datasheets/`).
2. Run `scripts/ingest_tech_docs.py` with file or directory paths.
3. Read outputs from `.context/knowledge/`:
   - `<doc>.md`: normalized markdown
   - `<doc>.sections.jsonl`: section chunks for retrieval
   - `<doc>.tables.md`: table-focused markdown
   - `<doc>.meta.json`: conversion metadata and validation info
   - `<doc>.docling.json`: raw Docling structured export
   - `knowledge.index.json`: corpus manifest
4. Use search/read helpers:
   - `scripts/search_docs.py` for corpus search
   - `scripts/read_spec.py` for focused section reads

## Commands

```bash
python scripts/ingest_tech_docs.py docs/datasheets --output-dir .context/knowledge
python scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge
python scripts/read_spec.py exynos_spi_v1 --anchor section-4-2
```

## Operational Rules

- Use `DocumentConverter` with explicit `allowed_formats`.
- Keep output location at `.context/knowledge` unless user asks otherwise.
- Preserve image presence in markdown with `![image_ref](path)` entries.
- Keep section anchors and normalize textual references like `See Table 4.2` into markdown links when anchor targets exist.
- Run on all provided files and summarize failures without stopping the whole batch unless explicitly requested.
- Emit a reusable system prompt hint file that tells downstream agents to check `.context/knowledge` first.

## Resources

- `scripts/ingest_tech_docs.py`: main ingestion pipeline
- `scripts/search_docs.py`: chunk-level search helper
- `scripts/read_spec.py`: focused reader helper
- `references/output-contract.md`: output schema and retrieval contract
