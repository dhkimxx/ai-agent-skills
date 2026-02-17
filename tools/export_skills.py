#!/usr/bin/env python3
"""Export vendor-neutral skills into platform-specific bundles."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TARGETS = ("codex", "claude", "antigravity")
COMMON_SKIP_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def copy_tree_filtered(src: Path, dst: Path, skip_parts: set[str]) -> None:
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        if any(part in skip_parts for part in rel.parts):
            continue
        if item.suffix in SKIP_SUFFIXES:
            continue

        out_path = dst / rel
        if item.is_dir():
            out_path.mkdir(parents=True, exist_ok=True)
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, out_path)


def list_skill_dirs(skills_root: Path) -> list[Path]:
    if not skills_root.exists():
        raise FileNotFoundError(f"Skills root not found: {skills_root}")

    dirs = []
    for child in sorted(skills_root.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            dirs.append(child)
    return dirs


def select_skills(skills_root: Path, names: list[str] | None) -> list[Path]:
    available = {path.name: path for path in list_skill_dirs(skills_root)}
    if not names:
        return list(available.values())

    selected = []
    for name in names:
        if name not in available:
            raise ValueError(f"Unknown skill: {name}")
        selected.append(available[name])
    return selected


def resolve_output_root(
    target: str,
    dist_root: Path,
    runtime_root: Path | None,
) -> Path:
    if runtime_root is not None:
        return runtime_root.resolve()
    return (dist_root / target / "skills").resolve()


def export_skill(
    skill_dir: Path,
    output_root: Path,
    clean: bool,
) -> Path:
    destination = output_root / skill_dir.name
    if clean and destination.exists():
        shutil.rmtree(destination)

    destination.mkdir(parents=True, exist_ok=True)
    copy_tree_filtered(skill_dir, destination, skip_parts=COMMON_SKIP_PARTS)

    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export skills for codex, claude, or antigravity runtimes.",
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=TARGETS,
        help="Runtime target for output path selection.",
    )
    parser.add_argument(
        "--skills-root",
        default=str(Path(__file__).resolve().parents[1] / "skills"),
        help="Root directory containing canonical skills.",
    )
    parser.add_argument(
        "--dist-root",
        default=str(Path(__file__).resolve().parents[1] / "dist"),
        help="Output root when --runtime-root is not set.",
    )
    parser.add_argument(
        "--runtime-root",
        help="Export directly into an installed runtime skills folder.",
    )
    parser.add_argument(
        "--skill",
        action="append",
        help="Skill name to export (repeat for multiple). Defaults to all skills.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete destination skill folders before export.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available skills and exit.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    skills_root = Path(args.skills_root).resolve()

    try:
        available = list_skill_dirs(skills_root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.list:
        if not available:
            print("(no skills found)")
            return 0
        for skill_dir in available:
            print(skill_dir.name)
        return 0

    try:
        selected = select_skills(skills_root, args.skill)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not selected:
        print("ERROR: no skills selected for export.", file=sys.stderr)
        return 2

    runtime_root = Path(args.runtime_root) if args.runtime_root else None
    output_root = resolve_output_root(
        target=args.target,
        dist_root=Path(args.dist_root).resolve(),
        runtime_root=runtime_root,
    )
    output_root.mkdir(parents=True, exist_ok=True)

    clean = not args.no_clean
    exported = []
    for skill_dir in selected:
        out = export_skill(
            skill_dir=skill_dir,
            output_root=output_root,
            clean=clean,
        )
        exported.append(out)
        print(f"exported {skill_dir.name} -> {out}")

    print(f"target: {args.target}")
    print(f"exported_count: {len(exported)}")
    print(f"output_root: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
