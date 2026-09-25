# meta-docs

> 문서를 **메타데이터(frontmatter) 먼저, 본문은 나중** 원칙으로 관리하는 스킬.
> 검색·열람·갱신을 분리해 컨텍스트 낭비를 줄입니다.

- **설치**: `npx skills add dhkimxx/ai-agent-skills --skill meta-docs`
- **요구 사항**: Node.js(npx), `uv`
- 최초 작성 2026-03-12

## 어떤 문제를 푸나

- 문서가 늘수록 찾는 데 시간이 걸린다
- 본문을 통째로 읽느라 컨텍스트가 낭비된다
- 누가 언제 무엇을 바꿨는지 추적하기 어렵다

## 동작 4단계

1. `search` — frontmatter만 읽어 후보 문서를 좁힌다
2. `read` — 꼭 필요한 본문만 연다
3. `update` — `updated`·`history`를 갱신한다
4. `create` — 문제 해결 로그를 남긴다

## 메타데이터 규약

- 모든 문서는 `docs/` 아래에 둔다
- 분류는 `type`(단일 문자열): `design` `spec` `guide` `log` `reference` `decision` `research`
  `meeting` `incident` `runbook` `roadmap` `report` `checklist` `retro` `note`
- 필수 필드: `title` `created` `updated` `author` `editors` `type` `tags` `history`

## 사용 예

```bash
# 검색
uv run --project skills/meta-docs skills/meta-docs/doc_manager.py search --tags "docs metadata" --type guide

# 열람
uv run --project skills/meta-docs skills/meta-docs/doc_manager.py read --path "docs/example.md"

# 갱신
uv run --project skills/meta-docs skills/meta-docs/doc_manager.py update --path "docs/example.md" --log "규약 보강"
```

## 구성 파일

| 파일 | 역할 |
|---|---|
| `SKILL.md` | 에이전트 지침 |
| `doc_manager.py` | `search` / `read` / `update` / `create` CLI |
| `pyproject.toml` · `uv.lock` | 의존성(uv) |

## 운영 팁

- `tags`는 검색의 핵심 — 너무 넓게 잡지 않는다
- `type`은 프로젝트 안에서 일관되게 쓴다
- `history`는 사람이 읽기 쉬운 문자열로 유지한다
