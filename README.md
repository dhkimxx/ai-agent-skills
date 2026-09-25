# AI Agent Skills

Codex · Claude · Antigravity에서 함께 쓰는 **벤더 중립 스킬 저장소**입니다.
각 스킬 폴더의 `README.md`에 개요·설치·사용 예시가 있습니다.

## 사전 준비

- **Node.js 18+** — `npx skills`(스킬 설치 CLI) 실행용
- **uv** — Python 스크립트를 쓰는 스킬(`datasheet-intelligence`, `meta-docs`, `naver-land-scouter`) 실행용
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

설치 후 확인:

```bash
npx skills list        # 설치된 스킬 목록
npx skills check       # 업데이트 확인
npx skills update      # 업데이트 적용
```

## 스킬 목록

| 스킬 | 설명 | 설치 |
| --- | --- | --- |
| [datasheet-intelligence](skills/datasheet-intelligence) | 데이터시트(PDF/DOCX/XLSX)에서 근거 있는 하드웨어 사실과 초기화 코드를 추출 | `npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence` |
| [go-gorm-persistence](skills/go-gorm-persistence) | Go 백엔드 GORM persistence 관례 — 엔터티 설계, scope, 페이지네이션, 트랜잭션, 마이그레이션, DB 테스트 | `npx skills add dhkimxx/ai-agent-skills --skill go-gorm-persistence` |
| [korean-tech-writing](skills/korean-tech-writing) | 한국어 기술문서 작성 — 문서 유형별 골격, 용어 풀이 패턴, 문체·표기 규칙, 발행 체크리스트 | `npx skills add dhkimxx/ai-agent-skills --skill korean-tech-writing` |
| [meta-docs](skills/meta-docs) | frontmatter 우선 문서 관리 — 검색·열람·갱신·생성 | `npx skills add dhkimxx/ai-agent-skills --skill meta-docs` |
| [naver-land-scouter](skills/naver-land-scouter) | 네이버 부동산 단지·매물 분석과 리포트 생성 | `npx skills add dhkimxx/ai-agent-skills --skill naver-land-scouter` |

## 스킬 추가

1. `skills/<이름>/` 폴더를 만들고 `SKILL.md`(에이전트 지침)와 `README.md`(사람용 문서)를 작성합니다.
   - `SKILL.md`의 `name`은 폴더 이름과 같아야 합니다.
2. 검증기를 통과시킵니다.

```bash
python3 tools/validate_skills.py
```

3. 루트 README의 스킬 목록에 한 줄 추가합니다.
