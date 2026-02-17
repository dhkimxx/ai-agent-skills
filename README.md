# AI Agent Skills

Vendor-neutral skill repository for Codex, Claude, and Antigravity.

## Layout

- `skills/<skill-name>/`: Canonical skill source (`SKILL.md`, scripts, references, optional metadata files).
- `tools/validate_skills.py`: Validate frontmatter and scripts.
- `tools/export_skills.py`: Build target-specific bundles.

## Validate

```bash
python tools/validate_skills.py
```

## Export

```bash
python tools/export_skills.py --target codex
python tools/export_skills.py --target claude
python tools/export_skills.py --target antigravity
```

Default exports go to:

- `dist/codex/skills/`
- `dist/claude/skills/`
- `dist/antigravity/skills/`

## Export Directly to a Runtime Folder

```bash
python tools/export_skills.py --target codex --runtime-root "$HOME/.codex/skills" --skill datasheet-preprocess
```
