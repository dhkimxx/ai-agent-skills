#!/usr/bin/env python3
"""Read a specific ingested datasheet markdown file, optionally by anchor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ANCHOR_PREFIX = '<a id="'
ANCHOR_SUFFIX = '"></a>'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read datasheet markdown output from the knowledge folder.")
    parser.add_argument(
        "doc",
        help="Document id (e.g., exynos_spi_v1) or a markdown path.",
    )
    parser.add_argument(
        "--knowledge-dir",
        default=".context/knowledge",
        help="Knowledge directory produced by ingest_docs.py.",
    )
    parser.add_argument(
        "--anchor",
        help="Anchor id to read (e.g., section-4-2).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=160,
        help="Maximum lines to print.",
    )
    return parser


def resolve_doc_path(doc_arg: str, knowledge_dir: Path) -> Path:
    candidate = Path(doc_arg)
    if candidate.is_file():
        return candidate.resolve()

    if candidate.suffix.lower() == ".md":
        direct_path = (knowledge_dir / candidate).resolve()
        if direct_path.exists():
            return direct_path
        doc_id = candidate.stem
    else:
        doc_id = doc_arg

    structured_path = (knowledge_dir / doc_id / f"{doc_id}.md").resolve()
    if structured_path.exists():
        return structured_path

    legacy_path = (knowledge_dir / f"{doc_id}.md").resolve()
    if legacy_path.exists():
        return legacy_path

    raise FileNotFoundError(
        f"Spec markdown not found for doc '{doc_arg}'. "
        f"Tried: {structured_path}, {legacy_path}"
    )


def find_anchor_range(lines: list[str], anchor: str) -> tuple[int, int]:
    anchor_line = f'{ANCHOR_PREFIX}{anchor}{ANCHOR_SUFFIX}'
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == anchor_line:
            start = idx
            break
    if start < 0:
        raise ValueError(f"Anchor not found: {anchor}")

    end = len(lines)
    for idx in range(start + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith(ANCHOR_PREFIX) and stripped.endswith(ANCHOR_SUFFIX):
            end = idx
            break
    return start, end


def main() -> int:
    args = build_parser().parse_args()
    if args.max_lines <= 0:
        print("ERROR: --max-lines must be > 0", file=sys.stderr)
        return 2

    knowledge_dir = Path(args.knowledge_dir).resolve()
    if not knowledge_dir.exists():
        print(f"ERROR: knowledge directory not found: {knowledge_dir}", file=sys.stderr)
        return 2

    try:
        doc_path = resolve_doc_path(args.doc, knowledge_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    lines = doc_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        print(f"(empty file) {doc_path}")
        return 0

    start = 0
    end = len(lines)
    if args.anchor:
        try:
            start, end = find_anchor_range(lines, args.anchor)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

    selected = lines[start:end][: args.max_lines]
    print(f"# file: {doc_path}")
    if args.anchor:
        print(f"# anchor: {args.anchor}")
    print("\n".join(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
