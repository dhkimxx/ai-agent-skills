#!/usr/bin/env python3
"""Search section chunks in .context/knowledge."""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Search ingested datasheets.")
    parser.add_argument("query", help="Search keyword or regex pattern.")
    parser.add_argument(
        "--knowledge-dir",
        default=".context/knowledge",
        help="Knowledge directory produced by ingest_docs.py.",
    )
    parser.add_argument("--regex", action="store_true", help="Treat query as regex.")
    parser.add_argument(
        "--case-sensitive", action="store_true", help="Case-sensitive matching."
    )
    parser.add_argument(
        "--max-hits", type=int, default=20, help="Maximum hits to print."
    )
    return parser


def compile_pattern(
    query: str, as_regex: bool, case_sensitive: bool
) -> re.Pattern[str]:
    flags = 0 if case_sensitive else re.IGNORECASE
    if as_regex:
        return re.compile(query, flags)
    return re.compile(re.escape(query), flags)


def search_sections(
    knowledge_dir: Path,
    pattern: re.Pattern[str],
    max_hits: int,
) -> int:
    hits = 0
    section_files = sorted(knowledge_dir.rglob("*.sections.jsonl"))
    for path in section_files:
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue

                text = str(row.get("text") or "")
                if not pattern.search(text):
                    continue

                preview = " ".join(text.split())
                if len(preview) > 220:
                    preview = preview[:220] + "..."

                print(
                    json.dumps(
                        {
                            "file": str(path),
                            "line": line_no,
                            "chunk_id": row.get("chunk_id"),
                            "doc_id": row.get("doc_id"),
                            "section_anchor": row.get("section_anchor"),
                            "section_title": row.get("section_title"),
                            "preview": preview,
                        },
                        ensure_ascii=False,
                    )
                )

                hits += 1
                if hits >= max_hits:
                    return hits
    return hits


def main() -> int:
    args = build_parser().parse_args()
    if args.max_hits <= 0:
        print("ERROR: --max-hits must be > 0", file=sys.stderr)
        return 2

    knowledge_dir = Path(args.knowledge_dir).resolve()
    if not knowledge_dir.exists():
        print(f"ERROR: knowledge directory not found: {knowledge_dir}", file=sys.stderr)
        return 2

    try:
        pattern = compile_pattern(
            query=args.query,
            as_regex=args.regex,
            case_sensitive=args.case_sensitive,
        )
    except re.error as exc:
        print(f"ERROR: invalid regex pattern: {exc}", file=sys.stderr)
        return 2
    hits = search_sections(
        knowledge_dir=knowledge_dir, pattern=pattern, max_hits=args.max_hits
    )
    print(f"hits: {hits}")
    return 0 if hits > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
