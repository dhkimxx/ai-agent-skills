# AI Agent Skills

Vendor-neutral skill repository for Codex, Claude, and Antigravity.

각 스킬 폴더의 `README.md`에 개요·설치·사용 예시가 있습니다.

## 사전 준비

- **Node.js 18+** — `npx skills`(스킬 설치 CLI) 실행용
- **uv** — Python 스크립트를 쓰는 스킬(`datasheet-intelligence`, `meta-docs`, `naver-land-scouter`) 실행용
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

## Skills

| Skill | Description | Install |
| --- | --- | --- |
| [datasheet-intelligence](skills/datasheet-intelligence) | Datasheet-grounded hardware facts extraction & code generation | `npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence` |
| [go-gorm-persistence](skills/go-gorm-persistence) | Go backend persistence patterns for GORM repositories, scopes, pagination, transactions, migrations, and DB tests | `npx skills add dhkimxx/ai-agent-skills --skill go-gorm-persistence` |
| [korean-tech-writing](skills/korean-tech-writing) | 한국어 기술문서 작성 — 문서 유형별 골격, 용어 풀이 패턴, 문체·표기 규칙, 발행 체크리스트 | `npx skills add dhkimxx/ai-agent-skills --skill korean-tech-writing` |
| [meta-docs](skills/meta-docs) | Frontmatter-first docs management (search/read/update/create) | `npx skills add dhkimxx/ai-agent-skills --skill meta-docs` |
| [naver-land-scouter](skills/naver-land-scouter) | Naver Land listings/complex analysis & reporting | `npx skills add dhkimxx/ai-agent-skills --skill naver-land-scouter` |

## Validate

```bash
python3 tools/validate_skills.py
```
