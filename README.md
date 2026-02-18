# AI Agent Skills

Vendor-neutral skill repository for Codex, Claude, and Antigravity.

## Skills

| Skill Name | Path | Install Command |
| --- | --- | --- |
| `datasheet-intelligence` | `skills/datasheet-intelligence` | `npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence` |

## `skills.sh` Installation Guide (`npx skills`)

```bash
# GitHub owner/repo format
npx skills add dhkimxx/ai-agent-skills --skill $SKILL_NAME

# GitHub URL format
npx skills add https://github.com/dhkimxx/ai-agent-skills --skill $SKILL_NAME

# Global installation
npx skills add dhkimxx/ai-agent-skills --skill $SKILL_NAME -g
```

Default example for this repository:

```bash
npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence
```

Common `npx skills` commands:

```bash
npx skills --help
npx skills add dhkimxx/ai-agent-skills
npx skills list
```

## Validate

```bash
python3 tools/validate_skills.py
```
