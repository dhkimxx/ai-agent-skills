#!/usr/bin/env python3
"""Git 이력 기반 코드베이스 진단 리포트를 생성한다."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


class GitCommandError(RuntimeError):
    """Git 실행 실패를 감싼다."""


@dataclass(frozen=True)
class ContributorRow:
    """작성자 통계를 표현한다."""

    name: str
    commits: int
    share: float
    last_active: str
    recent_commits: int


@dataclass(frozen=True)
class OverlapRow:
    """변경 빈도와 버그 집중도가 겹치는 파일을 표현한다."""

    path: str
    churn_count: int
    bug_count: int
    risk_score: int


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Git 이력으로 코드베이스 위험 신호를 빠르게 요약합니다."
    )
    parser.add_argument("--repo", default=".", help="분석할 Git 저장소 경로")
    parser.add_argument(
        "--since",
        default="1 year ago",
        help="변경 빈도/버그/긴급 대응 분석 기준 기간",
    )
    parser.add_argument(
        "--activity-since",
        default="24 months ago",
        help="월별 커밋 추세를 집계할 기준 기간",
    )
    parser.add_argument(
        "--recent-activity-since",
        default="6 months ago",
        help="최근 활동 공백을 판정할 기준 기간",
    )
    parser.add_argument(
        "--limit",
        default=20,
        type=int,
        help="표에 표시할 최대 행 수",
    )
    parser.add_argument(
        "--bug-pattern",
        default="fix|bug|broken",
        help="버그 커밋을 찾을 정규식",
    )
    parser.add_argument(
        "--incident-pattern",
        default="revert|hotfix|emergency|rollback",
        help="긴급 대응 커밋을 찾을 정규식",
    )
    return parser


def run_git_command(repo_root: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_text = result.stderr.strip() or "알 수 없는 Git 오류"
        raise GitCommandError(stderr_text)
    return result.stdout


def resolve_repo_root(repo_path: str) -> Path:
    raw_output = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if raw_output.returncode != 0:
        stderr_text = raw_output.stderr.strip() or "Git 저장소를 찾지 못했습니다."
        raise GitCommandError(stderr_text)
    return Path(raw_output.stdout.strip()).resolve()


def count_named_lines(raw_text: str) -> Counter[str]:
    return Counter(line.strip() for line in raw_text.splitlines() if line.strip())


def parse_ranked_counts(raw_text: str) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for raw_line in raw_text.splitlines():
        stripped_line = raw_line.strip()
        if not stripped_line:
            continue
        parts = stripped_line.split(None, 1)
        if len(parts) != 2:
            continue
        count_text, value = parts
        rows.append((int(count_text), value))
    return rows


def collect_file_counts(
    repo_root: Path,
    since: str,
    limit: int,
    grep_pattern: str | None = None,
) -> list[tuple[int, str]]:
    arguments = ["log", "--format=format:", "--name-only", f"--since={since}"]
    if grep_pattern:
        arguments.extend(["-i", "-E", f"--grep={grep_pattern}"])
    counter = count_named_lines(run_git_command(repo_root, arguments))
    return sort_counter(counter, limit)


def collect_contributor_rows(
    repo_root: Path,
    recent_activity_since: str,
) -> tuple[list[ContributorRow], int]:
    total_rows = parse_ranked_counts(
        run_git_command(repo_root, ["shortlog", "-sn", "--no-merges", "HEAD"])
    )
    recent_rows = parse_ranked_counts(
        run_git_command(
            repo_root,
            ["shortlog", "-sn", "--no-merges", f"--since={recent_activity_since}", "HEAD"],
        )
    )
    recent_count_by_name = {name: count for count, name in recent_rows}
    last_active_by_name = collect_last_active_dates(repo_root)
    total_commits = sum(count for count, _ in total_rows)

    contributors: list[ContributorRow] = []
    for commit_count, name in total_rows:
        share = 0.0 if total_commits == 0 else (commit_count / total_commits) * 100
        contributors.append(
            ContributorRow(
                name=name,
                commits=commit_count,
                share=share,
                last_active=last_active_by_name.get(name, "-"),
                recent_commits=recent_count_by_name.get(name, 0),
            )
        )

    return contributors, len(recent_rows)


def collect_last_active_dates(repo_root: Path) -> dict[str, str]:
    output = run_git_command(
        repo_root,
        ["log", "--format=%ad%x09%an", "--date=short", "--no-merges", "HEAD"],
    )
    last_active_by_name: dict[str, str] = {}
    for raw_line in output.splitlines():
        if not raw_line.strip():
            continue
        date_text, name = raw_line.split("\t", 1)
        if name not in last_active_by_name:
            last_active_by_name[name] = date_text
    return last_active_by_name


def collect_monthly_commit_counts(
    repo_root: Path,
    activity_since: str,
    limit: int,
) -> list[tuple[str, int]]:
    output = run_git_command(
        repo_root,
        ["log", "--format=%ad", "--date=format:%Y-%m", f"--since={activity_since}"],
    )
    counter = count_named_lines(output)
    rows = sorted(counter.items(), key=lambda item: item[0])
    if len(rows) <= limit:
        return rows
    return rows[-limit:]


def collect_incident_commits(
    repo_root: Path,
    since: str,
    incident_pattern: str,
    limit: int,
) -> list[str]:
    output = run_git_command(repo_root, ["log", "--oneline", f"--since={since}"])
    matches = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and re.search(incident_pattern, line, flags=re.IGNORECASE)
    ]
    return matches[:limit]


def sort_counter(counter: Counter[str], limit: int) -> list[tuple[int, str]]:
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [(count, name) for name, count in rows[:limit]]


def build_overlap_rows(
    churn_rows: Iterable[tuple[int, str]],
    bug_rows: Iterable[tuple[int, str]],
    limit: int,
) -> list[OverlapRow]:
    churn_by_path = {path: count for count, path in churn_rows}
    bug_by_path = {path: count for count, path in bug_rows}
    overlaps: list[OverlapRow] = []
    for path in churn_by_path.keys() & bug_by_path.keys():
        churn_count = churn_by_path[path]
        bug_count = bug_by_path[path]
        overlaps.append(
            OverlapRow(
                path=path,
                churn_count=churn_count,
                bug_count=bug_count,
                risk_score=churn_count * bug_count,
            )
        )
    overlaps.sort(
        key=lambda row: (-row.risk_score, -row.bug_count, -row.churn_count, row.path)
    )
    return overlaps[:limit]


def build_contributor_findings(
    contributors: list[ContributorRow],
    recent_active_contributor_count: int,
    recent_activity_since: str,
) -> list[str]:
    if not contributors:
        return ["기여자 정보가 없습니다."]

    findings: list[str] = []
    top_contributor = contributors[0]
    findings.append(
        f"상위 기여자 `{top_contributor.name}`는 비병합 커밋의 {top_contributor.share:.1f}%를 차지합니다."
    )
    if top_contributor.share >= 60.0:
        findings.append(
            "상위 1명 집중도가 60% 이상이므로 버스 팩터 위험 신호로 봅니다."
        )
    if top_contributor.recent_commits == 0:
        findings.append(
            f"상위 기여자가 `{recent_activity_since}` 기준 활동 기록이 없어 유지보수 공백 가능성이 있습니다."
        )
    findings.append(
        f"최근 활동 작성자는 {recent_active_contributor_count}명 / 전체 {len(contributors)}명입니다."
    )
    return findings


def build_incident_findings(incident_commits: list[str], since: str) -> list[str]:
    if not incident_commits:
        return [f"`{since}` 기준 긴급 대응 키워드 커밋은 보이지 않습니다."]
    findings = [f"`{since}` 기준 긴급 대응 키워드 커밋 {len(incident_commits)}건을 찾았습니다."]
    if len(incident_commits) >= 6:
        findings.append("긴급 대응 신호가 잦으므로 배포 안정성 점검이 필요합니다.")
    return findings


def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "- 없음"

    escaped_headers = [escape_markdown_cell(value) for value in headers]
    escaped_rows = [
        [escape_markdown_cell(value) for value in row]
        for row in rows
    ]
    header_line = "| " + " | ".join(escaped_headers) + " |"
    divider_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_lines = [
        "| " + " | ".join(row) + " |"
        for row in escaped_rows
    ]
    return "\n".join([header_line, divider_line, *body_lines])


def escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|")


def render_file_count_rows(rows: list[tuple[int, str]]) -> list[list[str]]:
    return [[str(count), f"`{path}`"] for count, path in rows]


def render_contributor_rows(rows: list[ContributorRow], limit: int) -> list[list[str]]:
    rendered_rows: list[list[str]] = []
    for contributor in rows[:limit]:
        rendered_rows.append(
            [
                str(contributor.commits),
                f"{contributor.share:.1f}%",
                str(contributor.recent_commits),
                contributor.last_active,
                contributor.name,
            ]
        )
    return rendered_rows


def render_overlap_rows(rows: list[OverlapRow]) -> list[list[str]]:
    return [
        [
            str(row.risk_score),
            str(row.churn_count),
            str(row.bug_count),
            f"`{row.path}`",
        ]
        for row in rows
    ]


def render_monthly_rows(rows: list[tuple[str, int]]) -> list[list[str]]:
    return [[month, str(count)] for month, count in rows]


def render_incident_rows(rows: list[str]) -> list[list[str]]:
    return [[f"`{row}`"] for row in rows]


def build_report(
    repo_root: Path,
    since: str,
    activity_since: str,
    recent_activity_since: str,
    churn_rows: list[tuple[int, str]],
    bug_rows: list[tuple[int, str]],
    contributors: list[ContributorRow],
    recent_active_contributor_count: int,
    monthly_rows: list[tuple[str, int]],
    incident_commits: list[str],
    limit: int,
) -> str:
    overlap_rows = build_overlap_rows(churn_rows, bug_rows, min(limit, 10))
    contributor_findings = build_contributor_findings(
        contributors,
        recent_active_contributor_count,
        recent_activity_since,
    )
    incident_findings = build_incident_findings(incident_commits, since)
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    incident_table = (
        render_markdown_table(["커밋"], render_incident_rows(incident_commits))
        if incident_commits
        else ""
    )

    sections = [
        "# Git Codebase Audit",
        "",
        f"- 저장소: `{repo_root}`",
        f"- 변경/버그/긴급 대응 기준 기간: `{since}`",
        f"- 활동 추세 기준 기간: `{activity_since}`",
        f"- 최근 활동 공백 기준 기간: `{recent_activity_since}`",
        f"- 생성 시각: `{generated_at}`",
        "",
        "## 1. 변경 빈도 상위 파일",
        "",
        render_markdown_table(["변경 수", "파일"], render_file_count_rows(churn_rows)),
        "",
        "## 2. 버그 관련 커밋 상위 파일",
        "",
        render_markdown_table(["버그 커밋 수", "파일"], render_file_count_rows(bug_rows)),
        "",
        "## 3. 겹치는 고위험 파일",
        "",
        render_markdown_table(
            ["위험 점수", "변경 수", "버그 수", "파일"],
            render_overlap_rows(overlap_rows),
        ),
        "",
        "## 4. 기여자 분포",
        "",
        render_markdown_table(
            ["커밋 수", "비중", f"최근 활동({recent_activity_since})", "최근 활동일", "작성자"],
            render_contributor_rows(contributors, limit),
        ),
        "",
        "### 해석",
        "",
        *[f"- {finding}" for finding in contributor_findings],
        "",
        "## 5. 월별 커밋 추세",
        "",
        render_markdown_table(["월", "커밋 수"], render_monthly_rows(monthly_rows)),
        "",
        "## 6. 긴급 대응 신호",
        "",
        *[f"- {finding}" for finding in incident_findings],
        "",
        incident_table,
        "",
        "## 7. 해석 주의사항",
        "",
        "- squash merge 전략은 실제 작성자 분포를 왜곡할 수 있습니다.",
        "- `fix`/`bug`/`hotfix` 키워드 사용 습관이 약하면 버그/긴급 대응 탐지가 과소집계될 수 있습니다.",
        "- 생성 파일, 락 파일, 대규모 포맷 변경은 churn 수치를 부풀릴 수 있습니다.",
        "- 겹치는 고위험 파일부터 읽고, 그다음 인접 서비스나 공통 유틸리티로 확장하는 흐름이 가장 효율적입니다.",
    ]
    return "\n".join(sections)


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    try:
        repo_root = resolve_repo_root(args.repo)
        churn_rows = collect_file_counts(repo_root, args.since, args.limit)
        bug_rows = collect_file_counts(
            repo_root,
            args.since,
            args.limit,
            grep_pattern=args.bug_pattern,
        )
        contributors, recent_active_contributor_count = collect_contributor_rows(
            repo_root,
            args.recent_activity_since,
        )
        monthly_rows = collect_monthly_commit_counts(
            repo_root,
            args.activity_since,
            args.limit,
        )
        incident_commits = collect_incident_commits(
            repo_root,
            args.since,
            args.incident_pattern,
            args.limit,
        )
    except GitCommandError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(
        build_report(
            repo_root=repo_root,
            since=args.since,
            activity_since=args.activity_since,
            recent_activity_since=args.recent_activity_since,
            churn_rows=churn_rows,
            bug_rows=bug_rows,
            contributors=contributors,
            recent_active_contributor_count=recent_active_contributor_count,
            monthly_rows=monthly_rows,
            incident_commits=incident_commits,
            limit=args.limit,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
