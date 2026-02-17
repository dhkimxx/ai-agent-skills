#!/usr/bin/env python3
"""Validate canonical skill folders before export."""

from __future__ import annotations

import argparse
import py_compile
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n?", re.DOTALL)


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("Missing YAML frontmatter block.")

    fields: dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def validate_skill(skill_dir: Path) -> ValidationResult:
    result = ValidationResult()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result.errors.append(f"{skill_dir.name}: missing SKILL.md")
        return result

    try:
        fields = parse_frontmatter(skill_md)
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"{skill_dir.name}: invalid frontmatter ({exc})")
        return result

    name = fields.get("name", "")
    description = fields.get("description", "")
    if not name:
        result.errors.append(f"{skill_dir.name}: frontmatter 'name' is empty")
    if not description:
        result.errors.append(f"{skill_dir.name}: frontmatter 'description' is empty")
    if name and name != skill_dir.name:
        result.errors.append(
            f"{skill_dir.name}: frontmatter name '{name}' must match folder name"
        )

    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        with tempfile.TemporaryDirectory() as temp_dir:
            compile_root = Path(temp_dir)
            for py_file in sorted(scripts_dir.glob("*.py")):
                try:
                    cfile = compile_root / f"{py_file.stem}.pyc"
                    py_compile.compile(str(py_file), cfile=str(cfile), doraise=True)
                except py_compile.PyCompileError as exc:
                    result.errors.append(f"{skill_dir.name}: python compile failed ({exc})")

    for cache_dir in skill_dir.rglob("__pycache__"):
        result.warnings.append(f"{skill_dir.name}: remove cache directory {cache_dir}")

    return result


def list_skill_dirs(skills_root: Path) -> list[Path]:
    if not skills_root.exists():
        raise FileNotFoundError(f"Skills root not found: {skills_root}")
    return sorted(
        [
            path
            for path in skills_root.iterdir()
            if path.is_dir() and (path / "SKILL.md").exists()
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate canonical skills.")
    parser.add_argument(
        "--skills-root",
        default=str(Path(__file__).resolve().parents[1] / "skills"),
        help="Root directory containing canonical skills.",
    )
    parser.add_argument(
        "--skill",
        action="append",
        help="Skill folder name to validate (repeat for multiple). Defaults to all.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    skills_root = Path(args.skills_root).resolve()

    try:
        all_skills = list_skill_dirs(skills_root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.skill:
        lookup = {skill.name: skill for skill in all_skills}
        selected: list[Path] = []
        for name in args.skill:
            if name not in lookup:
                print(f"ERROR: unknown skill '{name}'", file=sys.stderr)
                return 2
            selected.append(lookup[name])
    else:
        selected = all_skills

    if not selected:
        print("No skills to validate.")
        return 0

    total_errors = 0
    total_warnings = 0

    for skill_dir in selected:
        check = validate_skill(skill_dir)
        if check.errors:
            for error in check.errors:
                print(f"ERROR: {error}")
        if check.warnings:
            for warning in check.warnings:
                print(f"WARN: {warning}")

        if not check.errors and not check.warnings:
            print(f"OK: {skill_dir.name}")
        total_errors += len(check.errors)
        total_warnings += len(check.warnings)

    print(f"errors: {total_errors}")
    print(f"warnings: {total_warnings}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
