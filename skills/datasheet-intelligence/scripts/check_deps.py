#!/usr/bin/env python3
"""Pre-flight dependency checks for datasheet ingestion."""

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
import importlib
import subprocess
import sys
from dataclasses import dataclass
from importlib import metadata
from shutil import which

PDF_BACKEND_CHOICES = ("docling_parse", "pypdfium2")
LEVEL_PASS = "PASS"
LEVEL_WARN = "WARN"
LEVEL_FAIL = "FAIL"


@dataclass
class CheckMessage:
    level: str
    code: str
    message: str
    hint: str | None = None


def run_command(args: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=6,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode == 0, output


def check_python_version() -> CheckMessage:
    req_major, req_minor = 3, 10
    cur = sys.version_info
    if cur < (req_major, req_minor):
        return CheckMessage(
            level=LEVEL_FAIL,
            code="python_version_too_old",
            message=f"Python {cur.major}.{cur.minor} is unsupported. Requires >={req_major}.{req_minor}",
            hint="Upgrade Python or use a newer `uv python` version.",
        )
    return CheckMessage(
        level=LEVEL_PASS,
        code="python_version_ok",
        message=f"Python {cur.major}.{cur.minor}.{cur.micro}",
    )


def check_uv(require_uv: bool) -> CheckMessage:
    uv_path = which("uv")
    if not uv_path:
        level = LEVEL_FAIL if require_uv else LEVEL_WARN
        return CheckMessage(
            level=level,
            code="uv_not_found",
            message="`uv` command not found in PATH.",
            hint="Install uv or use the no-uv fallback documented in references/execution-options.md.",
        )

    ok, output = run_command(["uv", "--version"])
    if not ok:
        level = LEVEL_FAIL if require_uv else LEVEL_WARN
        return CheckMessage(
            level=level,
            code="uv_unhealthy",
            message=f"`uv --version` failed: {output}",
            hint="Reinstall uv and reopen the terminal.",
        )

    return CheckMessage(
        level=LEVEL_PASS,
        code="uv_ok",
        message=f"{output} ({uv_path})",
    )


def check_docling_import() -> CheckMessage:
    try:
        importlib.import_module("docling")
        version = metadata.version("docling")
    except Exception as exc:  # noqa: BLE001
        return CheckMessage(
            level=LEVEL_FAIL,
            code="docling_import_failed",
            message=f"Cannot import `docling`: {exc}",
            hint="Run with `uv run` to automatically install dependencies defined in the script header.",
        )

    return CheckMessage(
        level=LEVEL_PASS,
        code="docling_ok",
        message=f"docling=={version}",
    )


def check_extra_imports() -> list[CheckMessage]:
    results = []
    for pkg, mod in [
        ("python-docx", "docx"),
        ("openpyxl", "openpyxl"),
        ("pandas", "pandas"),
    ]:
        try:
            importlib.import_module(mod)
            ver = "unknown"
            try:
                ver = metadata.version(pkg)
            except metadata.PackageNotFoundError:
                pass
            results.append(CheckMessage(LEVEL_PASS, f"{mod}_ok", f"{pkg} ({ver})"))
        except Exception as exc:  # noqa: BLE001
            results.append(
                CheckMessage(
                    LEVEL_FAIL,
                    f"{mod}_import_failed",
                    f"Cannot import `{mod}`: {exc}",
                    hint="Run with `uv run` to install dependencies.",
                )
            )
    return results


def check_backend_import(pdf_backend: str) -> CheckMessage:
    if pdf_backend == "pypdfium2":
        module_name = "docling.backend.pypdfium2_backend"
    else:
        module_name = "docling.backend.docling_parse_backend"

    try:
        importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        return CheckMessage(
            level=LEVEL_FAIL,
            code="backend_import_failed",
            message=f"Cannot import selected PDF backend module `{module_name}`: {exc}",
            hint="Check docling installation version and reinstall dependencies in the same environment.",
        )

    return CheckMessage(
        level=LEVEL_PASS,
        code="backend_ok",
        message=f"Selected backend module loaded: {module_name}",
    )


def check_pypdfium2_runtime(pdf_backend: str) -> CheckMessage:
    strict = pdf_backend == "pypdfium2"
    try:
        import pypdfium2 as pdfium  # type: ignore

        doc = pdfium.PdfDocument.new()
        doc.close()
        version = metadata.version("pypdfium2")
    except Exception as exc:  # noqa: BLE001
        level = LEVEL_FAIL if strict else LEVEL_WARN
        return CheckMessage(
            level=level,
            code="pypdfium2_runtime_failed",
            message=f"pypdfium2 runtime check failed: {exc}",
            hint=(
                "If PDF parsing fails, try `--pdf-backend docling_parse` or install a platform-compatible "
                "pypdfium2/pdfium runtime."
            ),
        )

    return CheckMessage(
        level=LEVEL_PASS,
        code="pypdfium2_ok",
        message=f"pypdfium2=={version} runtime smoke test passed.",
    )


def check_tesseract(no_ocr: bool, require_tesseract: bool) -> CheckMessage:
    if no_ocr:
        return CheckMessage(
            level=LEVEL_PASS,
            code="ocr_skipped",
            message="OCR disabled by --no-ocr.",
        )

    tesseract_path = which("tesseract")
    if not tesseract_path:
        level = LEVEL_FAIL if require_tesseract else LEVEL_WARN
        return CheckMessage(
            level=level,
            code="tesseract_not_found",
            message="`tesseract` executable not found.",
            hint=(
                "Tesseract is missing. For OCR support, install it via `brew install tesseract` (macOS), "
                "`sudo apt-get install tesseract-ocr` (Linux), or use format-specific installers (Windows). "
                "Otherwise, use `--no-ocr` to disable OCR."
            ),
        )

    ok, output = run_command(["tesseract", "--version"])
    if not ok:
        level = LEVEL_FAIL if require_tesseract else LEVEL_WARN
        return CheckMessage(
            level=level,
            code="tesseract_unhealthy",
            message=f"`tesseract --version` failed: {output}",
            hint="Reinstall Tesseract and ensure it is available in PATH.",
        )

    first_line = output.splitlines()[0] if output else "tesseract detected"
    return CheckMessage(
        level=LEVEL_PASS,
        code="tesseract_ok",
        message=f"{first_line} ({tesseract_path})",
    )


def run_preflight_checks(
    no_ocr: bool,
    pdf_backend: str,
    require_uv: bool = False,
    require_tesseract: bool = False,
) -> tuple[bool, list[CheckMessage]]:
    checks = [
        check_python_version(),
        check_uv(require_uv=require_uv),
        check_docling_import(),
        *check_extra_imports(),
        check_backend_import(pdf_backend=pdf_backend),
        check_pypdfium2_runtime(pdf_backend=pdf_backend),
        check_tesseract(no_ocr=no_ocr, require_tesseract=require_tesseract),
    ]
    is_ok = not any(item.level == LEVEL_FAIL for item in checks)
    return is_ok, checks


def print_messages(messages: list[CheckMessage], verbose: bool) -> None:
    for item in messages:
        if item.level == LEVEL_PASS and not verbose:
            continue

        stream = sys.stderr if item.level in {LEVEL_WARN, LEVEL_FAIL} else sys.stdout
        print(f"[{item.level}] {item.code}: {item.message}", file=stream)
        if item.hint:
            print(f"  hint: {item.hint}", file=stream)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check datasheet-intelligence runtime dependencies."
    )
    parser.add_argument(
        "--pdf-backend",
        choices=PDF_BACKEND_CHOICES,
        default="docling_parse",
        help="Target PDF backend for ingestion checks.",
    )
    parser.add_argument("--no-ocr", action="store_true", help="Skip OCR checks.")
    parser.add_argument(
        "--require-uv",
        action="store_true",
        help="Treat missing/unhealthy uv as failure.",
    )
    parser.add_argument(
        "--require-tesseract",
        action="store_true",
        help="Treat missing/unhealthy tesseract as failure when OCR is enabled.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print pass-level checks too."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    is_ok, messages = run_preflight_checks(
        no_ocr=args.no_ocr,
        pdf_backend=args.pdf_backend,
        require_uv=args.require_uv,
        require_tesseract=args.require_tesseract,
    )
    print_messages(messages=messages, verbose=args.verbose)
    return 0 if is_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
