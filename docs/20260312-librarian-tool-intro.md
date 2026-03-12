---
title: "librarian-tool 소개"
created: 2026-03-12
updated: 2026-03-12
author: "dhkimxx <dhkimxx@naver.com>"
editors: ["dhkimxx <dhkimxx@naver.com>"]
type: "guide"
tags: ["librarian-tool", "docs", "metadata", "frontmatter", "workflow"]
history:
  - "2026-03-12 dhkimxx <dhkimxx@naver.com>: 최초 작성"
  - "2026-03-12 dhkimxx <dhkimxx@naver.com>: 가이드 톤 개선 및 흐름 보강"
---

# librarian-tool 소개

문서를 쌓아가다 보면 금방 이런 문제가 생깁니다.

- 문서가 늘수록 찾는 데 시간이 걸린다.
- 본문을 통째로 읽느라 컨텍스트가 낭비된다.
- 누가 언제 무엇을 바꿨는지 추적하기 어렵다.

`librarian-tool`은 이 문제를 **"메타데이터 먼저, 본문은 나중"**이라는 원칙으로 풀어냅니다.

## 어떤 방식으로 동작하나요?

핵심은 아주 단순합니다.

1. **`search`**로 frontmatter(메타데이터)만 읽어 후보 문서를 좁힙니다.
2. **`read`**로 꼭 필요한 문서 본문만 열람합니다.
3. 변경이 있으면 **`update`**로 `updated`와 `history`를 갱신합니다.
4. 문제 해결 기록은 **`create`**로 로그 문서를 남깁니다.

이 흐름만 지키면 문서가 커져도 **검색 비용과 컨텍스트 낭비**가 급격히 줄어듭니다.

## 메타데이터 규약 요약

- 모든 문서는 `docs/` 아래에 위치합니다.
- 분류는 `type` 필드(단일 문자열)로 통일합니다.
- 권장 타입 예시: `design`, `spec`, `guide`, `log`, `reference`, `decision`, `research`, `meeting`, `incident`, `runbook`, `roadmap`, `report`, `checklist`, `retro`, `note`

필수 YAML Frontmatter 필드:

- `title`
- `created`
- `updated`
- `author`
- `editors`
- `type`
- `tags`
- `history`

## 추천 워크플로우

1. `search`로 후보 문서를 추려서
2. `read`로 최소 문서만 열람하고
3. 변경 사항은 `update`로 즉시 기록하고
4. 복잡한 해결 과정은 `create`로 로그를 남깁니다.

## 커맨드 예시

```bash
# 1) 메타데이터 검색
uv run --project skills/librarian-tool skills/librarian-tool/doc_manager.py search --tags "docs metadata" --type "guide"

# 2) 본문 열람
uv run --project skills/librarian-tool skills/librarian-tool/doc_manager.py read --path "docs/20260312-librarian-tool-intro.md"

# 3) 히스토리 갱신
uv run --project skills/librarian-tool skills/librarian-tool/doc_manager.py update --path "docs/20260312-librarian-tool-intro.md" --log "문서 규약 보강"

# 4) 로그 생성
uv run --project skills/librarian-tool skills/librarian-tool/doc_manager.py create --title "api-timeout" --tags "infra troubleshooting" --content "타임아웃 원인과 조치 내용"
```

## 기대 효과

- **컨텍스트 비용 절감**: 본문 전체를 읽지 않고도 필요한 문서를 찾을 수 있습니다.
- **일관된 기록**: `history`와 `updated`가 항상 최신 상태로 유지됩니다.
- **가독성 개선**: 문서가 늘어도 구조와 기준이 유지됩니다.

## 운영 팁

- `tags`는 검색의 핵심이므로 과하게 넓지 않게 잡는 게 좋습니다.
- `type`은 분류 기준이므로 한 프로젝트 안에서는 가능한 한 일관되게 씁니다.
- `history`는 사람이 읽기 쉬운 문자열 포맷을 유지합니다.
