#!/usr/bin/env python3
"""Ingest multi-format datasheets into .context/knowledge artifacts."""

from __future__ import annotations

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "docling",
#     "pypdfium2",
#     "docling-core",
#     "python-docx",
#     "openpyxl",
#     "pandas",
# ]
# ///

import argparse
import json
import logging
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    CsvFormatOption,
    DocumentConverter,
    ExcelFormatOption,
    HTMLFormatOption,
    MarkdownFormatOption,
    PdfFormatOption,
    WordFormatOption,
)
from docling_core.types.doc import PictureItem
from docling_core.types.doc.base import ImageRefMode
from check_deps import CheckMessage, run_preflight_checks

EXTENSION_TO_FORMAT: dict[str, InputFormat] = {
    ".pdf": InputFormat.PDF,
    ".docx": InputFormat.DOCX,
    ".html": InputFormat.HTML,
    ".htm": InputFormat.HTML,
    ".md": InputFormat.MD,
    ".markdown": InputFormat.MD,
    ".xlsx": InputFormat.XLSX,
    ".xlsm": InputFormat.XLSX,
    ".csv": InputFormat.CSV,
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
ANCHOR_RE = re.compile(r'^<a id="([a-z0-9][a-z0-9-]*)"></a>$')
TABLE_REF_RE = re.compile(
    r"\b(?:See\s+)?(?P<label>Table|Figure|Section|Chapter)\s+(?P<num>\d+(?:\.\d+)*)\b",
    re.IGNORECASE,
)
HEADING_NUM_RE = re.compile(r"^(?P<num>\d+(?:\.\d+)*)\b")
TABLE_BLOCK_RE = re.compile(r"(?m)^\|.*\|\n\|\s*[-:| ]+\|")
PDF_BACKEND_CHOICES = ("docling_parse", "pypdfium2")
SUCCESS_STATUSES = {
    ConversionStatus.SUCCESS.value,
    ConversionStatus.PARTIAL_SUCCESS.value,
}


@dataclass
class Section:
    title: str
    anchor: str
    level: int
    text: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    return " ".join(text.replace("\u00a0", " ").split())


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def configure_logging(debug: bool) -> None:
    if not debug:
        return
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("docling").setLevel(logging.DEBUG)


def print_preflight_messages(
    checks: list[CheckMessage],
    verbose: bool,
    debug: bool,
) -> None:
    for item in checks:
        if item.level == "PASS" and not (verbose or debug):
            continue
        stream = sys.stderr if item.level in {"WARN", "FAIL"} else sys.stdout
        print(
            f"[preflight:{item.level.lower()}] {item.code}: {item.message}", file=stream
        )
        if item.hint:
            print(f"  hint: {item.hint}", file=stream)


def derive_failure_warnings(errors: list[str]) -> list[str]:
    combined = " ".join(errors).lower()
    hints: list[str] = []
    if "pdfium" in combined:
        hints.append(
            "PDF backend hint: retry with --no-ocr, then try --pdf-backend pypdfium2 "
            "(or docling_parse) and inspect this document's meta.json."
        )
    if "ocr" in combined or "tesseract" in combined:
        hints.append(
            "OCR hint: run with --no-ocr for text-first extraction or install/configure OCR engine dependencies."
        )
    if "timeout" in combined:
        hints.append(
            "Timeout hint: retry this file alone, reduce concurrent load, or increase conversion timeout upstream."
        )
    return hints


def resolve_format(path: Path) -> InputFormat | None:
    return EXTENSION_TO_FORMAT.get(path.suffix.lower())


def sanitize_doc_id(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return cleaned or "document"


def unique_doc_id(base: str, used: set[str]) -> str:
    if base not in used:
        used.add(base)
        return base

    index = 2
    while True:
        candidate = f"{base}_{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def dedupe_slug(slug: str, used: set[str]) -> str:
    if slug not in used:
        used.add(slug)
        return slug
    index = 2
    while True:
        candidate = f"{slug}-{index}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def escape_markdown_cell(text: str) -> str:
    return clean_text(text).replace("|", r"\|")


def escape_markdown_alt(text: str) -> str:
    return clean_text(text).replace("[", r"\[").replace("]", r"\]")


def make_ref_key(label: str, number: str) -> str:
    return f"{label.lower()}-{number.replace('.', '-')}"


def collect_sources(source_args: list[str], recursive: bool) -> list[Path]:
    files: set[Path] = set()

    for source in source_args:
        path = Path(source).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Source path not found: {path}")

        if path.is_file():
            if resolve_format(path):
                files.add(path.resolve())
            continue

        iterator = path.rglob("*") if recursive else path.glob("*")
        for child in iterator:
            if child.is_file() and resolve_format(child):
                files.add(child.resolve())

    return sorted(files)


def resolve_pdf_backend_class(pdf_backend: str) -> type[AbstractDocumentBackend]:
    if pdf_backend == "docling_parse":
        return DoclingParseDocumentBackend
    if pdf_backend == "pypdfium2":
        return PyPdfiumDocumentBackend
    raise ValueError(f"Unsupported PDF backend: {pdf_backend}")


def build_converter(
    no_ocr: bool,
    no_images: bool,
    pdf_backend: str,
    do_table_structure: bool = True,
) -> DocumentConverter:
    pdf_options = PdfPipelineOptions()
    pdf_options.do_table_structure = do_table_structure
    pdf_options.do_ocr = not no_ocr
    pdf_options.generate_picture_images = not no_images
    pdf_options.generate_page_images = False
    pdf_backend_class = resolve_pdf_backend_class(pdf_backend)

    format_options = {
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pdf_options,
            backend=pdf_backend_class,
        ),
        InputFormat.DOCX: WordFormatOption(),
        InputFormat.HTML: HTMLFormatOption(),
        InputFormat.MD: MarkdownFormatOption(),
        InputFormat.XLSX: ExcelFormatOption(),
        InputFormat.CSV: CsvFormatOption(),
    }

    return DocumentConverter(
        allowed_formats=list(format_options.keys()),
        format_options=format_options,
    )


def get_page_no(item: Any) -> int | None:
    prov = getattr(item, "prov", None) or []
    if not prov:
        return None
    first = prov[0]
    if isinstance(first, dict):
        page_no = safe_int(first.get("page_no"), 0)
    else:
        page_no = safe_int(getattr(first, "page_no", 0), 0)
    return page_no if page_no > 0 else None


def export_images(doc: Any, doc_id: str, doc_output_dir: Path) -> list[dict[str, Any]]:
    image_dir = doc_output_dir / "_images"
    image_dir.mkdir(parents=True, exist_ok=True)

    images: list[dict[str, Any]] = []
    image_index = 0
    for item, _ in doc.iterate_items(traverse_pictures=True):
        if not isinstance(item, PictureItem):
            continue
        image_index += 1

        image = item.get_image(doc)
        if image is None:
            continue

        file_name = f"{doc_id}_img_{image_index:03d}.png"
        image_path = image_dir / file_name
        image.save(image_path)

        alt_text = item.caption_text(doc) if hasattr(item, "caption_text") else ""
        if not alt_text:
            alt_text = f"{doc_id} image {image_index}"

        relative_path = image_path.relative_to(doc_output_dir).as_posix()
        images.append(
            {
                "index": image_index,
                "alt": clean_text(alt_text),
                "relative_path": relative_path,
                "page_no": get_page_no(item),
            }
        )

    if not images:
        try:
            image_dir.rmdir()
        except OSError:
            pass

    return images


def replace_image_placeholders(markdown: str, images: list[dict[str, Any]]) -> str:
    parts = markdown.split("<!-- image -->")
    if len(parts) == 1:
        return markdown

    output: list[str] = []
    for idx, part in enumerate(parts[:-1], start=1):
        output.append(part)
        if idx <= len(images):
            image = images[idx - 1]
            alt = escape_markdown_alt(image["alt"])
            output.append(f"![{alt}]({image['relative_path']})")
        else:
            output.append(f"![image_{idx:03d}](#image_{idx:03d})")
    output.append(parts[-1])
    return "".join(output)


def annotate_headings(markdown: str) -> tuple[str, dict[str, str]]:
    used_anchors: set[str] = set()
    ref_targets: dict[str, str] = {}
    lines_out: list[str] = []

    for line in markdown.splitlines():
        heading_match = HEADING_RE.match(line)
        if not heading_match:
            lines_out.append(line)
            continue

        heading_text = heading_match.group(2).strip()
        anchor = dedupe_slug(slugify(heading_text), used_anchors)
        lines_out.append(f'<a id="{anchor}"></a>')
        lines_out.append(line)

        ref_targets[anchor] = anchor

        number_match = HEADING_NUM_RE.match(heading_text)
        if number_match:
            ref_targets.setdefault(
                make_ref_key("section", number_match.group("num")),
                anchor,
            )

        for ref_match in TABLE_REF_RE.finditer(heading_text):
            ref_targets.setdefault(
                make_ref_key(ref_match.group("label"), ref_match.group("num")),
                anchor,
            )

    return "\n".join(lines_out), ref_targets


def normalize_cross_references(markdown: str, ref_targets: dict[str, str]) -> str:
    in_code_block = False
    normalized: list[str] = []

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            normalized.append(line)
            continue

        if in_code_block:
            normalized.append(line)
            continue

        def replace_ref(match: re.Match[str]) -> str:
            key = make_ref_key(match.group("label"), match.group("num"))
            anchor = ref_targets.get(key)
            if not anchor:
                return match.group(0)
            return f"[{match.group(0)}](#{anchor})"

        normalized.append(TABLE_REF_RE.sub(replace_ref, line))

    return "\n".join(normalized)


def extract_sections(markdown: str) -> list[Section]:
    sections: list[Section] = []
    pending_anchor: str | None = None

    current_title = "Document Start"
    current_anchor = "document-start"
    current_level = 1
    current_lines: list[str] = []

    for line in markdown.splitlines():
        anchor_match = ANCHOR_RE.match(line.strip())
        if anchor_match:
            pending_anchor = anchor_match.group(1)
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            if current_lines and any(piece.strip() for piece in current_lines):
                sections.append(
                    Section(
                        title=current_title,
                        anchor=current_anchor,
                        level=current_level,
                        text="\n".join(current_lines).strip(),
                    )
                )

            current_title = heading_match.group(2).strip()
            current_anchor = pending_anchor or slugify(current_title)
            current_level = len(heading_match.group(1))
            current_lines = [line]
            pending_anchor = None
            continue

        current_lines.append(line)
        pending_anchor = None

    if current_lines and any(piece.strip() for piece in current_lines):
        sections.append(
            Section(
                title=current_title,
                anchor=current_anchor,
                level=current_level,
                text="\n".join(current_lines).strip(),
            )
        )

    if sections:
        return sections

    text = markdown.strip()
    if not text:
        return []
    return [Section(title="Document", anchor="document", level=1, text=text)]


def chunk_text(text: str, max_chars: int, overlap: int) -> Iterable[str]:
    normalized = text.strip()
    if not normalized:
        return

    start = 0
    size = len(normalized)
    while start < size:
        end = min(size, start + max_chars)
        if end < size:
            cut_candidates = [
                normalized.rfind("\n\n", start + max_chars // 2, end),
                normalized.rfind("\n", start + max_chars // 2, end),
                normalized.rfind(" ", start + max_chars // 2, end),
            ]
            cut = max(cut_candidates)
            if cut > start + max_chars // 3:
                end = cut

        piece = normalized[start:end].strip()
        if piece:
            yield piece

        if end >= size:
            break
        start = max(0, end - overlap)


def build_section_chunks(
    doc_id: str,
    source_file: Path,
    sections: list[Section],
    max_chars: int,
    overlap: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for sec_index, section in enumerate(sections, start=1):
        for chunk_index, chunk in enumerate(
            chunk_text(section.text, max_chars=max_chars, overlap=overlap),
            start=1,
        ):
            rows.append(
                {
                    "chunk_id": f"{doc_id}_s{sec_index:03d}_c{chunk_index:03d}",
                    "doc_id": doc_id,
                    "source_file": str(source_file),
                    "section_title": section.title,
                    "section_anchor": section.anchor,
                    "section_level": section.level,
                    "text": chunk,
                    "char_count": len(chunk),
                }
            )
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def table_to_matrix(table: dict[str, Any]) -> list[list[str]]:
    data = table.get("data") or {}
    rows = safe_int(data.get("num_rows"), 0)
    cols = safe_int(data.get("num_cols"), 0)
    if rows <= 0 or cols <= 0:
        return []

    matrix = [["" for _ in range(cols)] for _ in range(rows)]
    for cell in data.get("table_cells", []):
        text = clean_text(str(cell.get("text") or ""))
        if not text:
            continue

        row_start = safe_int(cell.get("start_row_offset_idx"), -1)
        row_end = safe_int(cell.get("end_row_offset_idx"), row_start)
        col_start = safe_int(cell.get("start_col_offset_idx"), -1)
        col_end = safe_int(cell.get("end_col_offset_idx"), col_start)

        if row_start < 0 or col_start < 0:
            continue

        row_end = min(row_end, rows - 1)
        col_end = min(col_end, cols - 1)

        for row_idx in range(row_start, row_end + 1):
            for col_idx in range(col_start, col_end + 1):
                current = matrix[row_idx][col_idx]
                if current and text not in current:
                    matrix[row_idx][col_idx] = f"{current} / {text}"
                elif not current:
                    matrix[row_idx][col_idx] = text

    return [row for row in matrix if any(cell.strip() for cell in row)]


def render_table_markdown(matrix: list[list[str]]) -> list[str]:
    if not matrix:
        return []

    cols = max(len(row) for row in matrix)
    rows = [row + [""] * (cols - len(row)) for row in matrix]
    header = [
        cell if cell.strip() else f"col_{idx + 1}" for idx, cell in enumerate(rows[0])
    ]

    lines = [
        "| " + " | ".join(escape_markdown_cell(cell) for cell in header) + " |",
        "| " + " | ".join(["---"] * cols) + " |",
    ]
    for row in rows[1:]:
        lines.append(
            "| " + " | ".join(escape_markdown_cell(cell) for cell in row) + " |"
        )
    return lines


def write_tables_markdown(doc_dict: dict[str, Any], out_path: Path) -> int:
    tables = doc_dict.get("tables", [])
    if not tables:
        out_path.write_text("# Tables\n\n(No tables detected.)\n", encoding="utf-8")
        return 0

    lines = ["# Tables", ""]
    rendered = 0
    for index, table in enumerate(tables, start=1):
        matrix = table_to_matrix(table)
        if not matrix:
            continue

        page_no = "?"
        prov = table.get("prov") or []
        if prov:
            first = prov[0]
            if isinstance(first, dict):
                page_no = first.get("page_no", "?")
            else:
                page_no = getattr(first, "page_no", "?")

        lines.append(f"## Table {index} (page {page_no})")
        lines.append("")
        lines.extend(render_table_markdown(matrix))
        lines.append("")
        rendered += 1

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return rendered


def count_markdown_tables(markdown: str) -> int:
    return len(TABLE_BLOCK_RE.findall(markdown))


def build_doc_output_dir(doc_id: str, output_dir: Path) -> Path:
    return output_dir / doc_id


def build_output_files(doc_id: str, output_dir: Path) -> dict[str, str]:
    doc_output_dir = build_doc_output_dir(doc_id=doc_id, output_dir=output_dir)
    doc_output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "markdown": str(doc_output_dir / f"{doc_id}.md"),
        "sections_jsonl": str(doc_output_dir / f"{doc_id}.sections.jsonl"),
        "tables_markdown": str(doc_output_dir / f"{doc_id}.tables.md"),
        "meta_json": str(doc_output_dir / f"{doc_id}.meta.json"),
        "docling_json": str(doc_output_dir / f"{doc_id}.docling.json"),
    }


def build_meta(
    doc_id: str,
    source_path: Path,
    output_files: dict[str, str],
    status: str,
    errors: list[str],
    sections: int = 0,
    chunks: int = 0,
    images: int = 0,
    tables_detected: int = 0,
    tables_rendered: int = 0,
    table_blocks_in_markdown: int = 0,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "source_file": str(source_path),
        "input_format": str(resolve_format(source_path)),
        "status": status,
        "errors": errors,
        "generated_at_utc": now_utc_iso(),
        "output_files": output_files,
        "sections": sections,
        "chunks": chunks,
        "images": images,
        "tables_detected": tables_detected,
        "tables_rendered": tables_rendered,
        "table_blocks_in_markdown": table_blocks_in_markdown,
        "warnings": warnings or [],
    }


def write_meta_file(meta: dict[str, Any]) -> None:
    meta_path = Path(meta["output_files"]["meta_json"])
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def process_document_safe(
    source_path: Path,
    doc_id: str,
    converter: DocumentConverter,
    output_dir: Path,
    max_chars: int,
    overlap: int,
    no_images: bool,
    verbose: bool,
    debug: bool,
) -> dict[str, Any]:
    try:
        return process_document(
            source_path=source_path,
            doc_id=doc_id,
            converter=converter,
            output_dir=output_dir,
            max_chars=max_chars,
            overlap=overlap,
            no_images=no_images,
        )
    except Exception as exc:  # noqa: BLE001
        output_files = build_output_files(doc_id=doc_id, output_dir=output_dir)
        trace = traceback.format_exc()
        errors = [str(exc)]
        if debug:
            errors.append(trace)
        warnings = ["Unhandled exception occurred while processing this document."]
        warnings.extend(derive_failure_warnings(errors))
        meta = build_meta(
            doc_id=doc_id,
            source_path=source_path,
            output_files=output_files,
            status="UNEXPECTED_ERROR",
            errors=errors,
            warnings=warnings,
        )
        write_meta_file(meta)
        if verbose:
            print(f"[ingest-error] {source_path}: {exc}", file=sys.stderr)
        if debug:
            print(trace, file=sys.stderr)
        return meta


def should_retry_without_ocr(
    source_path: Path,
    status: str,
    no_ocr: bool,
    disable_retry: bool,
) -> bool:
    if disable_retry or no_ocr:
        return False
    if resolve_format(source_path) != InputFormat.PDF:
        return False
    return status not in SUCCESS_STATUSES


def process_document(
    source_path: Path,
    doc_id: str,
    converter: DocumentConverter,
    output_dir: Path,
    max_chars: int,
    overlap: int,
    no_images: bool,
) -> dict[str, Any]:
    result = converter.convert(source_path, raises_on_error=False)
    status_obj = getattr(result, "status", ConversionStatus.FAILURE)
    status_value = status_obj.value if hasattr(status_obj, "value") else str(status_obj)

    output_files = build_output_files(doc_id=doc_id, output_dir=output_dir)

    doc = getattr(result, "document", None)
    if doc is None or status_obj not in {
        ConversionStatus.SUCCESS,
        ConversionStatus.PARTIAL_SUCCESS,
    }:
        errors = [str(err) for err in getattr(result, "errors", [])]
        warnings = ["Conversion failed or returned no datasheet content."]
        warnings.extend(derive_failure_warnings(errors))
        meta = build_meta(
            doc_id=doc_id,
            source_path=source_path,
            output_files=output_files,
            status=status_value,
            errors=errors,
            warnings=warnings,
        )
        write_meta_file(meta)
        return meta

    raw_markdown = doc.export_to_markdown(
        image_mode=ImageRefMode.PLACEHOLDER,
        compact_tables=False,
    )
    doc_dict = doc.export_to_dict()

    images: list[dict[str, Any]] = []
    if not no_images:
        doc_output_dir = Path(output_files["markdown"]).parent
        images = export_images(doc=doc, doc_id=doc_id, doc_output_dir=doc_output_dir)

    markdown_with_images = replace_image_placeholders(raw_markdown, images)
    markdown_with_anchors, ref_targets = annotate_headings(markdown_with_images)
    normalized_markdown = normalize_cross_references(
        markdown_with_anchors,
        ref_targets=ref_targets,
    )

    sections = extract_sections(normalized_markdown)
    section_rows = build_section_chunks(
        doc_id=doc_id,
        source_file=source_path,
        sections=sections,
        max_chars=max_chars,
        overlap=overlap,
    )

    markdown_path = Path(output_files["markdown"])
    sections_path = Path(output_files["sections_jsonl"])
    tables_path = Path(output_files["tables_markdown"])
    docling_json_path = Path(output_files["docling_json"])

    markdown_path.write_text(normalized_markdown, encoding="utf-8")
    write_jsonl(sections_path, section_rows)
    docling_json_path.write_text(
        json.dumps(doc_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    tables_rendered = write_tables_markdown(doc_dict, tables_path)
    tables_detected = len(doc_dict.get("tables", []))
    markdown_table_blocks = count_markdown_tables(normalized_markdown)

    warnings: list[str] = []
    if tables_detected > 0 and markdown_table_blocks < tables_detected:
        warnings.append(
            "Markdown table blocks are fewer than detected tables; "
            "use .tables.md when table fidelity is critical."
        )

    meta = build_meta(
        doc_id=doc_id,
        source_path=source_path,
        output_files=output_files,
        status=status_value,
        errors=[str(err) for err in getattr(result, "errors", [])],
        sections=len(sections),
        chunks=len(section_rows),
        images=len(images),
        tables_detected=tables_detected,
        tables_rendered=tables_rendered,
        table_blocks_in_markdown=markdown_table_blocks,
        warnings=warnings,
    )
    write_meta_file(meta)
    return meta


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert PDF/DOCX/HTML/MD/XLSX/CSV datasheets into normalized Markdown artifacts.",
    )
    parser.add_argument(
        "sources",
        nargs="+",
        help="Input files or directories containing datasheets.",
    )
    parser.add_argument(
        "--output-dir",
        default=".context/knowledge",
        help="Destination for markdown knowledge artifacts (default: .context/knowledge).",
    )
    parser.add_argument(
        "--chunk-max-chars",
        type=int,
        default=2200,
        help="Max chars per retrieval chunk (default: 2200).",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=220,
        help="Chunk overlap chars (default: 220).",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Do not recurse into nested directories.",
    )
    parser.add_argument(
        "--pdf-backend",
        choices=PDF_BACKEND_CHOICES,
        default="docling_parse",
        help="PDF backend for conversion (default: docling_parse).",
    )
    parser.add_argument(
        "--no-ocr", action="store_true", help="Disable OCR in PDF pipeline."
    )
    parser.add_argument(
        "--no-retry-no-ocr",
        action="store_true",
        help="Disable automatic one-time retry with OCR disabled for failed PDFs.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: Force --no-ocr, --no-images, and disable table structure analysis.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip dependency preflight checks (not recommended).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logs and traceback output for failures.",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip picture extraction and keep image placeholders.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Return non-zero exit code if any datasheet fails conversion.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose progress output."
    )
    return parser


def check_pdf_pages(path: Path) -> int:
    try:
        import pypdfium2 as pdfium  # type: ignore

        pdf = pdfium.PdfDocument(str(path))
        count = len(pdf)
        pdf.close()
        return count
    except Exception:
        return 0


def main() -> int:
    args = build_parser().parse_args()
    configure_logging(args.debug)

    if args.fast:
        args.no_ocr = True
        args.no_images = True

    if args.chunk_max_chars <= 0:
        print("ERROR: --chunk-max-chars must be > 0", file=sys.stderr)
        return 2
    if args.chunk_overlap < 0:
        print("ERROR: --chunk-overlap must be >= 0", file=sys.stderr)
        return 2
    if args.chunk_overlap >= args.chunk_max_chars:
        print(
            "ERROR: --chunk-overlap must be smaller than --chunk-max-chars",
            file=sys.stderr,
        )
        return 2

    if not args.skip_preflight:
        preflight_ok, preflight_checks = run_preflight_checks(
            no_ocr=args.no_ocr,
            pdf_backend=args.pdf_backend,
            require_uv=False,
            require_tesseract=False,
        )
        print_preflight_messages(
            checks=preflight_checks,
            verbose=args.verbose,
            debug=args.debug,
        )
        if not preflight_ok:
            print(
                "ERROR: dependency preflight failed. "
                "Run scripts/check_deps.py directly for details.",
                file=sys.stderr,
            )
            return 2

    try:
        source_paths = collect_sources(args.sources, recursive=not args.non_recursive)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not source_paths:
        print("ERROR: no supported files found.", file=sys.stderr)
        print(
            f"Supported extensions: {', '.join(sorted(EXTENSION_TO_FORMAT.keys()))}",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    primary_converter = build_converter(
        no_ocr=args.no_ocr,
        no_images=args.no_images,
        pdf_backend=args.pdf_backend,
        do_table_structure=not args.fast,
    )
    retry_converter_without_ocr: DocumentConverter | None = None
    used_doc_ids: set[str] = set()
    metas: list[dict[str, Any]] = []

    for idx, source_path in enumerate(source_paths, start=1):
        doc_id = sanitize_doc_id(source_path.stem)
        doc_id = unique_doc_id(
            doc_id, used_doc_ids
        )  # Note: simple unique in this context

        # Pre-check large file size
        if resolve_format(source_path) == InputFormat.PDF:
            page_count = check_pdf_pages(source_path)
            if page_count > 0:
                print(
                    f"[{idx}/{len(source_paths)}] Processing {source_path.name} ({page_count} pages)..."
                )
                if page_count > 100 and not (args.fast or args.no_ocr):
                    print(
                        f"  [WARN] Large file detected (>100 pages). "
                        "If it hangs, try `--fast` or `--no-ocr`.",
                        file=sys.stderr,
                    )
            else:
                print(f"[{idx}/{len(source_paths)}] Processing {source_path.name}...")
        else:
            print(f"[{idx}/{len(source_paths)}] Processing {source_path.name}...")

        if args.verbose:
            print(f"[ingest] {source_path} -> {doc_id}")

        meta = process_document_safe(
            source_path=source_path,
            doc_id=doc_id,
            converter=primary_converter,
            output_dir=output_dir,
            max_chars=args.chunk_max_chars,
            overlap=args.chunk_overlap,
            no_images=args.no_images,
            verbose=args.verbose,
            debug=args.debug,
        )

        if should_retry_without_ocr(
            source_path=source_path,
            status=str(meta.get("status", "")),
            no_ocr=args.no_ocr,
            disable_retry=args.no_retry_no_ocr,
        ):
            if retry_converter_without_ocr is None:
                retry_converter_without_ocr = build_converter(
                    no_ocr=True,
                    no_images=args.no_images,
                    pdf_backend=args.pdf_backend,
                    do_table_structure=not args.fast,
                )
            initial_status = str(meta.get("status", "UNKNOWN"))
            if args.verbose:
                print(
                    f"[retry-no-ocr] {source_path} (initial status: {initial_status})",
                    file=sys.stderr,
                )

            retry_meta = process_document_safe(
                source_path=source_path,
                doc_id=doc_id,
                converter=retry_converter_without_ocr,
                output_dir=output_dir,
                max_chars=args.chunk_max_chars,
                overlap=args.chunk_overlap,
                no_images=args.no_images,
                verbose=args.verbose,
                debug=args.debug,
            )
            retry_warnings = retry_meta.setdefault("warnings", [])
            retry_warnings.append(
                f"Initial conversion status was {initial_status}; retried once with OCR disabled (--no-ocr)."
            )
            write_meta_file(retry_meta)
            meta = retry_meta

        metas.append(meta)
        print(f"{doc_id}: {meta['status']}")

    index = {
        "generated_at_utc": now_utc_iso(),
        "knowledge_dir": str(output_dir),
        "documents": metas,
    }
    index_path = output_dir / "knowledge.index.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    successes = [meta for meta in metas if meta["status"] in SUCCESS_STATUSES]
    failures = [meta for meta in metas if meta not in successes]

    print(f"processed: {len(metas)}")
    print(f"success: {len(successes)}")
    print(f"failure: {len(failures)}")
    print(f"index: {index_path}")

    if failures and args.fail_on_error:
        return 1
    if not successes:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
