# AI Agent Skills

Vendor-neutral skill repository for Codex, Claude, and Antigravity.

## Skills

| Skill | Description | Install |
| --- | --- | --- |
| [datasheet-intelligence](skills/datasheet-intelligence) | Datasheet-grounded hardware facts extraction & code generation | `npx skills add dhkimxx/ai-agent-skills --skill datasheet-intelligence` |
| [git-codebase-audit](skills/git-codebase-audit) | Git-history-first codebase audit for churn, hotspots, contributors, and release risk | `npx skills add dhkimxx/ai-agent-skills --skill git-codebase-audit` |
| [go-gorm-persistence](skills/go-gorm-persistence) | Go backend persistence patterns for GORM repositories, scopes, pagination, transactions, migrations, and DB tests | `npx skills add dhkimxx/ai-agent-skills --skill go-gorm-persistence` |
| [meta-docs](skills/meta-docs) | Frontmatter-first docs management (search/read/update/create) | `npx skills add dhkimxx/ai-agent-skills --skill meta-docs` |
| [naver-land-scouter](skills/naver-land-scouter) | Naver Land listings/complex analysis & reporting | `npx skills add dhkimxx/ai-agent-skills --skill naver-land-scouter` |

## Validate

```bash
python3 tools/validate_skills.py
```
