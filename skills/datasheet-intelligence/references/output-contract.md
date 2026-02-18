# Output Contract

Use this schema when consuming generated artifacts from `.context/knowledge`.
For CLI runtime flags and presets, see [execution-options.md](execution-options.md).

## Files Per Datasheet

- `<doc>/<doc>.md`
  - Normalized markdown.
  - Heading anchors injected as `<a id="..."></a>`.
  - Image placeholders replaced with `![image_ref](path)` when extraction succeeds.
  - Cross-references like `See Table 4.2` linked when anchor targets exist.
- `<doc>/<doc>.sections.jsonl`
  - One JSON object per chunk.
  - Fields: `chunk_id`, `doc_id`, `source_file`, `section_title`, `section_anchor`, `section_level`, `text`, `char_count`.
- `<doc>/<doc>.tables.md`
  - Table-focused markdown rendered from Docling structured tables.
  - Prefer this file when merged cells or dense register tables are critical.
- `<doc>/<doc>.docling.json`
  - Full Docling structured export.
- `<doc>/<doc>.meta.json`
  - Datasheet conversion status, warnings, output file paths, and counts.
- `<doc>/_images/*`
  - Extracted images for markdown references.

## Corpus Files

- `knowledge.index.json`
  - Manifest for all processed datasheets and run-level timestamp.

## Retrieval Pattern

1. Search `.sections.jsonl` using `scripts/search_docs.py`.
2. Open matching markdown via `scripts/read_docs.py`.
3. Resolve details from `.tables.md` when tabular values conflict with prose.

## Evidence Contract (For Answers/Code)

When producing datasheet-grounded output, include evidence mapped from ingested artifacts:

- Minimum citation unit: `doc_id + section_anchor` (or equivalent section identifier).
- If register values come from tables, add the `.tables.md` source note.
- For each critical claim (address, bit position, reset value, formula), provide at least one citation unit.
- If evidence cannot be located in `.context/knowledge`, mark the claim as unverified and request additional source ingestion instead of guessing.
