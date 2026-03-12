#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import io
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

FRONTMATTER_DELIMITER = "---"
DEFAULT_LOG_TYPE = "log"


class DocManagerError(Exception):
    pass


def extract_root_arg(argv: List[str]) -> Tuple[Optional[str], List[str]]:
    root_value: Optional[str] = None
    cleaned: List[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--root":
            if index + 1 >= len(argv):
                raise DocManagerError("--root 값이 비어 있습니다.")
            root_value = argv[index + 1]
            index += 2
            continue
        if arg.startswith("--root="):
            root_value = arg.split("=", 1)[1]
            if not root_value:
                raise DocManagerError("--root 값이 비어 있습니다.")
            index += 1
            continue
        cleaned.append(arg)
        index += 1
    return root_value, cleaned


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doc_manager.py",
        description="docs/ 문서를 frontmatter 중심으로 검색/열람/갱신합니다.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="프로젝트 루트 경로(기본: 현재 디렉토리).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser(
        "search",
        help="frontmatter만 파싱하여 문서를 검색합니다.",
    )
    search_parser.add_argument(
        "--tags",
        default="",
        help="검색할 태그(쉼표 또는 공백으로 구분).",
    )
    search_parser.add_argument(
        "--type",
        default="",
        help="검색할 문서 타입(쉼표 또는 공백으로 구분).",
    )
    search_parser.add_argument(
        "--dir",
        default="",
        help="검색 대상 디렉토리(docs/ 하위 경로).",
    )

    read_parser = subparsers.add_parser(
        "read",
        help="지정한 문서의 본문만 반환합니다.",
    )
    read_parser.add_argument("--path", required=True, help="읽을 문서 경로.")

    update_parser = subparsers.add_parser(
        "update",
        help="frontmatter의 updated/history를 갱신합니다.",
    )
    update_parser.add_argument("--path", required=True, help="갱신할 문서 경로.")
    update_parser.add_argument("--log", required=True, help="변경 요약 로그.")

    create_parser = subparsers.add_parser(
        "create",
        help="단발성 로그 문서를 생성합니다.",
    )
    create_parser.add_argument("--title", required=True, help="문서 제목.")
    create_parser.add_argument("--tags", required=True, help="태그(쉼표/공백 구분).")
    create_parser.add_argument("--content", required=True, help="본문 내용.")
    create_parser.add_argument("--type", default=DEFAULT_LOG_TYPE, help="문서 타입(기본: log).")

    return parser


def get_today_date() -> str:
    return date.today().isoformat()


def is_frontmatter_delimiter(line: str) -> bool:
    return line.strip() == FRONTMATTER_DELIMITER


def parse_tags_input(tags_input: str) -> List[str]:
    if not tags_input:
        return []
    parts = re.split(r"[\s,]+", tags_input.strip())
    return [part for part in parts if part]


def parse_types_input(types_input: str) -> List[str]:
    if not types_input:
        return []
    parts = re.split(r"[\s,]+", types_input.strip())
    return [part for part in parts if part]


def normalize_tags_value(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    tags: List[str] = []
    for item in raw_items:
        if item is None:
            continue
        if isinstance(item, str):
            parts = re.split(r"[\s,]+", item.strip())
            tags.extend(part for part in parts if part)
        else:
            text = str(item).strip()
            if text:
                tags.append(text)
    return tags


def normalize_types_value(value: object) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    types: List[str] = []
    for item in raw_items:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            types.append(text)
    return types


def normalize_dir_option(dir_option: str) -> Optional[str]:
    if not dir_option:
        return None
    cleaned = dir_option.strip().lstrip("/")
    if cleaned.startswith("docs/"):
        cleaned = cleaned[len("docs/") :]
    if not cleaned:
        return None
    return cleaned


def resolve_project_root(root_input: str) -> Path:
    root_path = Path(root_input).expanduser().resolve()
    if not root_path.exists():
        raise DocManagerError("--root 경로가 존재하지 않습니다.")
    return root_path


def resolve_docs_directory(project_root: Path, dir_option: Optional[str]) -> Path:
    docs_root = project_root / "docs"
    if not docs_root.exists():
        raise DocManagerError("docs 디렉토리를 찾을 수 없습니다.")

    if not dir_option:
        return docs_root

    candidate = (docs_root / dir_option).resolve()
    if candidate != docs_root and docs_root.resolve() not in candidate.parents:
        raise DocManagerError("--dir 값이 docs/ 하위가 아닙니다.")
    if not candidate.exists():
        raise DocManagerError("지정한 디렉토리가 존재하지 않습니다.")
    return candidate


def resolve_docs_path(project_root: Path, path_input: str) -> Path:
    input_path = Path(path_input).expanduser()
    if input_path.is_absolute():
        resolved = input_path.resolve()
    else:
        resolved = (project_root / input_path).resolve()

    docs_root = (project_root / "docs").resolve()
    if resolved != docs_root and docs_root not in resolved.parents:
        raise DocManagerError("docs/ 하위 경로만 접근할 수 있습니다.")
    if not resolved.exists():
        raise DocManagerError("지정한 파일이 존재하지 않습니다.")
    return resolved


def format_relative_path(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def get_git_user_info(project_root: Path) -> Tuple[Optional[str], Optional[str]]:
    name = run_git_config(project_root, "user.name")
    email = run_git_config(project_root, "user.email")
    return name, email


def run_git_config(project_root: Path, key: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        return None
    return value


def resolve_editor_identity(project_root: Path) -> str:
    name, email = get_git_user_info(project_root)
    if name and email:
        return f"{name} <{email}>"
    if name:
        return name
    if email:
        return email
    return getpass.getuser()


def read_frontmatter_text_only(path: Path) -> Optional[str]:
    try:
        with path.open("r", encoding="utf-8") as file:
            first_line = file.readline()
            if not first_line:
                return None
            first_line = first_line.lstrip("\ufeff")
            if not is_frontmatter_delimiter(first_line):
                return None

            # 본문을 읽지 않아 검색 단계에서 컨텍스트 소모를 줄이기 위함
            frontmatter_lines: List[str] = []
            for line in file:
                if is_frontmatter_delimiter(line):
                    return "".join(frontmatter_lines)
                frontmatter_lines.append(line)
    except UnicodeDecodeError:
        print_error(f"UTF-8 디코딩 실패: {path}")
        return None

    return None


def split_frontmatter_and_body(path: Path) -> Tuple[Optional[str], str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise DocManagerError(f"UTF-8 디코딩 실패: {path}")

    lines = content.splitlines(keepends=True)
    if not lines:
        return None, ""

    first_line = lines[0].lstrip("\ufeff")
    if not is_frontmatter_delimiter(first_line):
        return None, content

    for index in range(1, len(lines)):
        if is_frontmatter_delimiter(lines[index]):
            frontmatter_text = "".join(lines[1:index])
            body_text = "".join(lines[index + 1 :])
            return frontmatter_text, body_text

    return None, content


def get_yaml_parser(round_trip: bool) -> YAML:
    yaml = YAML(typ="rt" if round_trip else "safe")
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=2, offset=0)
    return yaml


def load_frontmatter_data(path: Path) -> Optional[dict]:
    frontmatter_text = read_frontmatter_text_only(path)
    if frontmatter_text is None:
        return None

    yaml = get_yaml_parser(round_trip=False)
    try:
        data = yaml.load(frontmatter_text) or {}
    except YAMLError as exc:
        print_error(f"YAML 파싱 실패: {path} ({exc})")
        return None

    if not isinstance(data, dict):
        print_error(f"YAML 최상위 구조가 맵이 아닙니다: {path}")
        return None

    return data


def dump_frontmatter_text(data: dict) -> str:
    yaml = get_yaml_parser(round_trip=True)
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    text = buffer.getvalue()
    if not text.endswith("\n"):
        text += "\n"
    return text


def slugify_title(title: str) -> str:
    lowered = title.strip().lower()
    lowered = re.sub(r"\s+", "-", lowered)
    lowered = re.sub(r"[^a-z0-9_-]", "", lowered)
    lowered = re.sub(r"-+", "-", lowered)
    lowered = lowered.strip("-_")
    if not lowered:
        raise DocManagerError(
            "파일명에 사용할 유효한 TITLE을 만들 수 없습니다. "
            "영문 소문자/숫자/-/_ 조합으로 입력하세요."
        )
    return lowered


def collect_markdown_paths(docs_root: Path) -> List[Path]:
    return sorted(path for path in docs_root.rglob("*.md") if path.is_file())


def matches_tags(document_tags: List[str], required_tags: List[str]) -> bool:
    if not required_tags:
        return True
    document_tag_set = {tag.lower() for tag in document_tags}
    return all(tag.lower() in document_tag_set for tag in required_tags)


def matches_types(document_types: List[str], required_types: List[str]) -> bool:
    if not required_types:
        return True
    document_type_set = {doc_type.lower() for doc_type in document_types}
    return any(req_type.lower() in document_type_set for req_type in required_types)


def handle_search(project_root: Path, tags_input: str, types_input: str, dir_option: str) -> int:
    normalized_dir = normalize_dir_option(dir_option)
    docs_root = resolve_docs_directory(project_root, normalized_dir)
    required_tags = parse_tags_input(tags_input)
    required_types = parse_types_input(types_input)

    results = []
    for path in collect_markdown_paths(docs_root):
        frontmatter = load_frontmatter_data(path)
        if frontmatter is None:
            continue

        tags = normalize_tags_value(frontmatter.get("tags"))
        if not matches_tags(tags, required_tags):
            continue

        types = normalize_types_value(frontmatter.get("type"))
        if not matches_types(types, required_types):
            continue

        title = frontmatter.get("title")
        updated = frontmatter.get("updated")
        result = {
            "file_path": format_relative_path(project_root, path),
            "title": str(title) if title is not None else None,
            "updated": str(updated) if updated is not None else None,
            "tags": tags,
            "type": types[0] if types else None,
        }
        results.append(result)

    print(json.dumps(results, ensure_ascii=False, separators=(",", ":")))
    return 0


def handle_read(project_root: Path, path_input: str) -> int:
    target_path = resolve_docs_path(project_root, path_input)
    frontmatter_text, body_text = split_frontmatter_and_body(target_path)
    if frontmatter_text is None:
        print(body_text, end="")
        return 0

    print(body_text, end="")
    return 0


def handle_update(project_root: Path, path_input: str, log: str) -> int:
    if not log.strip():
        raise DocManagerError("--log 값이 비어 있습니다.")

    target_path = resolve_docs_path(project_root, path_input)
    frontmatter_text, body_text = split_frontmatter_and_body(target_path)
    if frontmatter_text is None:
        raise DocManagerError("frontmatter가 없는 문서는 갱신할 수 없습니다.")

    yaml = get_yaml_parser(round_trip=True)
    try:
        data = yaml.load(frontmatter_text) or {}
    except YAMLError as exc:
        raise DocManagerError(f"YAML 파싱 실패: {target_path} ({exc})")

    if not isinstance(data, dict):
        raise DocManagerError("YAML 최상위 구조가 맵이 아닙니다.")

    today = get_today_date()
    editor = resolve_editor_identity(project_root)
    data["updated"] = today
    if not data.get("author"):
        # 누락된 author를 보완해 메타데이터 일관성을 유지한다.
        data["author"] = editor

    editors = data.get("editors")
    if editors is None:
        editors = []
        data["editors"] = editors
    if not isinstance(editors, list):
        editors = [str(editors)]
        data["editors"] = editors
    if editor not in editors:
        editors.append(editor)

    history = data.get("history")
    if history is None:
        history = []
        data["history"] = history
    if not isinstance(history, list):
        history = [str(history)]
        data["history"] = history

    entry = f"{today} {editor}: {log.strip()}"
    if not history or str(history[-1]) != entry:
        history.append(entry)

    new_frontmatter = dump_frontmatter_text(data)
    new_content = f"{FRONTMATTER_DELIMITER}\n{new_frontmatter}{FRONTMATTER_DELIMITER}\n{body_text}"
    target_path.write_text(new_content, encoding="utf-8")

    output = {
        "file_path": format_relative_path(project_root, target_path),
        "updated": today,
    }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


def handle_create(
    project_root: Path, title: str, tags_input: str, content: str, doc_type: str
) -> int:
    if not title.strip():
        raise DocManagerError("--title 값이 비어 있습니다.")
    if not tags_input.strip():
        raise DocManagerError("--tags 값이 비어 있습니다.")
    if not doc_type.strip():
        raise DocManagerError("--type 값이 비어 있습니다.")

    tags = parse_tags_input(tags_input)
    if not tags:
        raise DocManagerError("--tags 값이 비어 있습니다.")

    today = get_today_date()
    editor = resolve_editor_identity(project_root)
    date_prefix = today.replace("-", "")

    log_dir = resolve_docs_directory(project_root, None)

    slug = slugify_title(title)
    filename = f"{date_prefix}-{slug}.md"
    target_path = log_dir / filename
    if target_path.exists():
        counter = 2
        while True:
            candidate = log_dir / f"{date_prefix}-{slug}-{counter}.md"
            if not candidate.exists():
                target_path = candidate
                break
            counter += 1

    frontmatter = {
        "title": title,
        "created": today,
        "updated": today,
        "author": editor,
        "editors": [editor],
        "type": doc_type.strip(),
        "tags": tags,
        "history": [f"{today} {editor}: 최초 작성"],
    }

    frontmatter_text = dump_frontmatter_text(frontmatter)
    body_text = content.rstrip() + "\n"
    file_content = (
        f"{FRONTMATTER_DELIMITER}\n{frontmatter_text}"
        f"{FRONTMATTER_DELIMITER}\n{body_text}"
    )
    target_path.write_text(file_content, encoding="utf-8")

    output = {
        "file_path": format_relative_path(project_root, target_path),
        "created": today,
    }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


def print_error(message: str) -> None:
    print(message, file=sys.stderr)


def main() -> None:
    parser = build_argument_parser()
    root_override, cleaned_argv = extract_root_arg(sys.argv[1:])
    args = parser.parse_args(cleaned_argv)
    if root_override is not None:
        args.root = root_override

    try:
        project_root = resolve_project_root(args.root)

        if args.command == "search":
            exit_code = handle_search(project_root, args.tags, args.type, args.dir)
        elif args.command == "read":
            exit_code = handle_read(project_root, args.path)
        elif args.command == "update":
            exit_code = handle_update(project_root, args.path, args.log)
        elif args.command == "create":
            exit_code = handle_create(
                project_root, args.title, args.tags, args.content, args.type
            )
        else:
            raise DocManagerError("지원하지 않는 명령입니다.")
    except DocManagerError as exc:
        print_error(str(exc))
        sys.exit(1)
    except Exception as exc:
        print_error(f"예상치 못한 오류: {exc}")
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
