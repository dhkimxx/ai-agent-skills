# AI Agent Skills

Codex, Claude, Antigravity에서 공통으로 사용할 수 있는 vendor-neutral skill repository입니다.

## Skills Table

| 스킬 이름 | 경로 | `skills.sh` Install Command (`npx`) |
| --- | --- | --- |
| `datasheet-intelligence` | `skills/datasheet-intelligence` | `npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence` |

## Layout

- `skills/<skill-name>/`: Canonical skill source (`SKILL.md`, `scripts/`, `references/`, optional metadata files)를 저장합니다.
- `tools/validate_skills.py`: Frontmatter와 Python scripts를 Validate합니다.
- `tools/export_skills.py`: target별 bundle을 Export합니다.

## `skills.sh` Installation Guide (`npx skills`)

```bash
# GitHub owner/repo 방식
npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence

# GitHub URL 방식
npx skills add https://github.com/dhkimxx/ai-agent-skills --skill datasheet-intelligence

# prompt 없이 global 설치
npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence -g -y
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

로컬 repository에서 바로 설치/배포해야 하면 `tools/export_skills.py`를 대안으로 사용할 수 있습니다:

```bash
python3 tools/export_skills.py --target codex --runtime-root "$HOME/.codex/skills" --skill datasheet-intelligence
```

## Validate

```bash
python3 tools/validate_skills.py
```

## Export

```bash
python3 tools/export_skills.py --target codex
python3 tools/export_skills.py --target claude
python3 tools/export_skills.py --target antigravity
```

Default export 경로:

- `dist/codex/skills/`
- `dist/claude/skills/`
- `dist/antigravity/skills/`

## Export Directly to a Runtime Folder

```bash
python3 tools/export_skills.py --target codex --runtime-root "$HOME/.codex/skills" --skill datasheet-intelligence
```
