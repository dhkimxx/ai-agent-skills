# AI Agent Skills

Codex, Claude, Antigravity에서 공통으로 사용할 수 있는 vendor-neutral skill repository입니다.

## Skills 목록

| 스킬 이름 |  설치 명령어 |
| --- |  --- |
| `datasheet-intelligence` | `npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence` |


## `skills.sh` Installation Guide (`npx skills`)

```bash
# GitHub owner/repo 방식
npx skills add dhkimxx/ai-agent-skills --skill $SKILL_NAME

# GitHub URL 방식
npx skills add https://github.com/dhkimxx/ai-agent-skills --skill $SKILL_NAME

# global 설치
npx skills add dhkimxx/ai-agent-skills --skill $SKILL_NAME -g
```

이 repository 기준 기본 예시:

```bash
npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence
```

`npx skills` 기본 명령:

```bash
npx skills --help
npx skills add dhkimxx/ai-agent-skills
npx skills list
```

## Validate

```bash
python3 tools/validate_skills.py
```
