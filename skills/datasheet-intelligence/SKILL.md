---
name: datasheet-intelligence
description: "Use for datasheet/TRM-backed register tasks and init-code generation with citation evidence (page/section). High-signal cues: datasheet, register, bitfield, base address, reset value, init code, TRM, 데이터시트, 레지스터, 초기화 코드."
argument-hint: "[document-path] [task-or-keywords]"
---

# Datasheet Intelligence

## Manual Invocation (If Auto-Trigger Misses)

- Run `/datasheet-intelligence <document-path> <task-or-keywords>`.
- If invoked with slash arguments, treat `$ARGUMENTS` as the highest-priority input for document path and task keywords.
- Rephrase the user request with high-signal terms from the description (`datasheet`, `register`, `bitfield`, `init code`, `데이터시트`, `레지스터`).
- Include concrete targets (for example: peripheral name, register name, or timing parameter) so matching is less ambiguous.

## When To Trigger

Use this skill immediately when the request requires document-grounded hardware facts.

- Register-level code generation or review (addresses, bit masks, reset values).
- Datasheet-based initialization sequences (`I2C`, `SPI`, `UART`, `GPIO`, clocks, reset flow).
- Verification tasks that require evidence citation (`file + page/section`).
- Questions over provided hardware docs (`PDF`, `DOCX`, `XLSX`) rather than generic coding.

### High-Signal Prompt Cues

- English: `datasheet`, `register map`, `bitfield`, `base address`, `reset value`, `clock divider`, `pin mux`, `init code`.
- Korean or mixed: `데이터시트 기반`, `레지스터 근거`, `비트필드`, `초기화 코드`, `베이스 주소`, `클럭 분주`.

## When Not To Trigger

- Pure refactoring/style tasks with no datasheet or hardware-document evidence requirement.
- Generic programming Q&A unrelated to hardware manuals or register specifications.
- Tasks that can be solved from local source code alone without hardware documentation.

## Purpose

Help the agent read datasheets efficiently and produce evidence-grounded answers.

- `PDF`: use TOC + targeted page reads.
- `DOCX/XLSX`: search first, then read only relevant parts.
- `--structured`: use Docling when table/header fidelity is required.

## Context Loading Rules

- Keep default context lean: run `scripts/toc.py`, `scripts/search.py`, `scripts/read.py` directly first.
- Load `references/usage.md` only when detailed CLI flags or format-specific examples are needed.

## Prerequisites

Use `uv` with this skill's `pyproject.toml` and `uv.lock`.
Do not rely on PEP 723 inline script metadata.

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Use one of these execution contexts:

- Recommended (works from any directory): `uv run --project skills/datasheet-intelligence ...`
- Alternative: `cd skills/datasheet-intelligence && uv run ...`

All command examples below use the recommended `--project` style.

## Workflow

### PDF Datasheets

Choose the strategy by document size.

#### Small (< 50 pages)

1. Run `scripts/toc.py` (use `--structured` if bookmarks are missing).
2. Run `scripts/read.py --pages` for relevant sections.
3. Add `--structured` if tables are broken.

#### Medium (50-150 pages)

1. Run `scripts/toc.py --filter` to narrow sections.
2. Run `scripts/search.py` to locate exact pages.
3. Run `scripts/read.py --pages` for focused ranges (use `--structured` for table-heavy ranges).

#### Large (>= 150 pages)

Never read the whole document at once.

1. Run `scripts/toc.py` to map sections and page ranges.
2. If `scripts/toc.py` reports no bookmarks, switch immediately to `scripts/search.py` (search-first) instead of full `--structured` TOC.
3. Skip low-value sections (Legal, Revision History, Ordering Info, Package Drawing).
4. Run `scripts/search.py` for exact keyword locations (`--unique-pages` recommended for long documents).
5. Run `scripts/read.py --pages` in 10-30 page chunks.
6. Iterate: read -> discover new keywords -> search again -> read again.

High-priority large-PDF sections:

| Priority | Section | Why |
| --- | --- | --- |
| High | Register Map / List | Addresses, bit fields, reset values |
| High | Address Map | Base addresses, memory map |
| Medium | Pin Description / GPIO | Pin functions, function select |
| Medium | Electrical Characteristics | Voltage/current constraints |
| Medium | Clock / Timing | Timing formulas, divider rules |
| Low | Reset Controller | Reset release sequence |
| Lowest | Legal / Ordering / Revision | Usually not needed |

### DOCX / XLSX

1. Run `scripts/search.py` first to find candidate paragraphs/rows.
2. Run `scripts/read.py` for targeted reading.
3. Use `scripts/read.py --structured` when layout/table structure is critical.
4. If no hits, expand keywords and retry search before full reading.

## Quick Commands

Use `--structured` only when table/header fidelity is required.

```bash
SKILL_DIR="skills/datasheet-intelligence"

# 1) Find candidate pages first
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_CON" "I2C0_BASE" --unique-pages

# 2) Read only selected ranges
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 464-470

# 3) Switch to structured mode only if layout fidelity is critical
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 464-470 --structured
```

For full flags and format-specific examples, read `references/usage.md`.

## Operational Rules

- Start with TOC for PDF workflows.
- Do selective reading for large documents.
- If PDF bookmarks are missing, switch to search-first flow and avoid full structured TOC on very large files.
- Use search-first flow for DOCX/XLSX.
- Prefer fast mode by default; use `--structured` only for table/header fidelity issues.
- Keep explicit project context in every command (`uv run --project ...`).
- Read enough neighboring context to avoid missing table headers/footnotes.
- Cross-check register values against Address Map / Register List sections.
- Use iterative exploration (read -> search -> read).

## Output Contract

For datasheet-grounded answers or code:

- Provide evidence for each critical claim (address, bit position, reset value, formula): `source file + page/section`.
- Map important code settings to their evidence locations.
- Do not guess unverifiable values; mark them as unverified.
- If table/prose conflicts exist, report the conflict and separate uncertain items.

## Resources

| Script | Role | Formats | `--structured` |
| --- | --- | --- | --- |
| `scripts/toc.py` | TOC extraction | PDF, DOCX | Yes |
| `scripts/read.py` | Targeted reading | PDF, DOCX, XLSX | Yes |
| `scripts/search.py` | Keyword search | PDF, DOCX, XLSX | Yes |

See [usage.md](references/usage.md) for detailed examples.
