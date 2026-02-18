#!/usr/bin/env python3
"""PDF/DOCX/XLSX 목차(TOC)를 추출한다.

기본 모드: PDF 북마크(Outline)만 추출 (빠름)
구조적 모드: docling으로 헤딩을 분석하여 목차 추출 (느림, 북마크 없는 PDF/DOCX 지원)
"""

import argparse
import json
import sys
from pathlib import Path


def extract_toc_fast(pdf_path: Path, filter_keywords: list[str] | None) -> list[dict]:
    """PDF 북마크 기반 고속 TOC 추출 (pypdfium2)"""
    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(pdf_path)
    except Exception as e:
        print(f"Error: PDF 열기 실패 — {e}", file=sys.stderr)
        return []

    toc = []
    try:
        for item in pdf.get_toc():
            if filter_keywords:
                if not any(k.lower() in item.title.lower() for k in filter_keywords):
                    continue
            toc.append(
                {
                    "level": item.level + 1,
                    "title": item.title,
                    "page": (
                        item.page_index + 1 if item.page_index is not None else None
                    ),
                }
            )
    except Exception as e:
        print(f"Warning: TOC 추출 실패 — {e}", file=sys.stderr)

    return toc


def extract_toc_structured(
    file_path: Path, filter_keywords: list[str] | None
) -> list[dict]:
    """docling 기반 구조적 TOC 추출 (모든 포맷 지원)"""
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.document import SectionHeaderItem
    except ImportError:
        print(
            "Error: --structured 모드는 docling이 필요합니다.\n"
            "실행 예시: uv run --project skills/datasheet-intelligence --with docling "
            "skills/datasheet-intelligence/scripts/toc.py <file> --structured",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[structured] {file_path.name} 구조 분석 중... (시간이 걸릴 수 있음)",
        file=sys.stderr,
    )

    try:
        converter = DocumentConverter()

        # docling은 기본적으로 PDF, DOCX, PPTX 등을 지원함
        result = converter.convert(file_path)
        doc = result.document

        toc = []
        # docling의 구조 트리 순회
        for item, level in doc.iterate_items(traverse_pictures=False):
            if isinstance(item, SectionHeaderItem):
                title = item.text.strip()
                if not title:
                    continue

                if filter_keywords:
                    # 필터링: 제목에 키워드가 포함되어야 함
                    if not any(k.lower() in title.lower() for k in filter_keywords):
                        continue

                # 페이지 정보 추출 (지원되는 경우)
                page_no = None
                if item.prov and len(item.prov) > 0:
                    page_no = item.prov[0].page_no

                toc.append(
                    {
                        "level": level,  # iterate_items가 반환한 계층 레벨을 그대로 사용
                        "title": title,
                        "page": page_no,
                    }
                )

        return toc

    except Exception as e:
        print(f"Error: 구조적 TOC 파싱 실패 — {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="문서 목차를 추출한다.")
    parser.add_argument("file_path", type=Path, help="문서 파일 경로 (PDF, DOCX 등)")
    parser.add_argument("--filter", help="쉼표로 구분된 필터 키워드 (예: 'I2C,GPIO')")
    parser.add_argument(
        "--structured",
        action="store_true",
        help="docling으로 헤딩 분석 (북마크 없는 PDF/DOCX용)",
    )
    args = parser.parse_args()

    if not args.file_path.exists():
        print(f"Error: 파일 없음 — {args.file_path}", file=sys.stderr)
        sys.exit(1)

    filters = [k.strip() for k in args.filter.split(",")] if args.filter else None

    # 모드 선택
    if args.structured:
        toc = extract_toc_structured(args.file_path, filters)
    elif args.file_path.suffix.lower() == ".pdf":
        toc = extract_toc_fast(args.file_path, filters)
    else:
        # PDF가 아닌데 --structured가 없으면 경고 후 구조적 모드로 전환하거나 에러
        # 여기서는 편의를 위해 구조적 모드로 자동 전환 시도 (단, 사용자에게 알림)
        print(
            f"Info: {args.file_path.suffix} 포맷은 --structured 모드로 처리합니다.",
            file=sys.stderr,
        )
        toc = extract_toc_structured(args.file_path, filters)

    if not toc and args.file_path.suffix.lower() == ".pdf" and not args.structured:
        # 기본 모드에서 실패했다면 구조적 모드를 제안
        import pypdfium2 as pdfium

        try:
            pdf = pdfium.PdfDocument(args.file_path)
            print(
                json.dumps(
                    {
                        "info": "북마크 없음. --structured 옵션을 사용해보세요.",
                        "total_pages": len(pdf),
                    }
                )
            )
        except:
            pass
        return

    if not toc:
        print(json.dumps({"info": "목차 항목 없음"}), file=sys.stderr)
        return

    for item in toc:
        print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
