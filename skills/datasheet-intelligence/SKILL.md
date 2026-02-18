---
name: datasheet-intelligence
description: Trigger this skill first for datasheet-backed hardware tasks: register map/address lookup, bitfield/reset-value checks, pin mux and timing/clock constraints, and C/firmware init code that must cite page/section evidence. High-signal terms include datasheet, register, bitfield, base address, reset value, init code, clock divider, I2C/SPI/UART/GPIO, TRM, 데이터시트, 레지스터, 초기화 코드.
---

# Datasheet Intelligence

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
2. Skip low-value sections (Legal, Revision History, Ordering Info, Package Drawing).
3. Run `scripts/search.py` for exact keyword locations.
4. Run `scripts/read.py --pages` in 10-30 page chunks.
5. Iterate: read -> discover new keywords -> search again -> read again.

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

## Commands

Use `--structured` with `uv run --project ... --with docling`.

```bash
SKILL_DIR="skills/datasheet-intelligence"

# TOC
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/toc.py" docs/rp2040.pdf
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/toc.py" docs/rp2040.pdf --filter "I2C,GPIO,RESET"
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/toc.py" docs/spec.docx --structured

# Read
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 464-470
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/read.py" docs/spec.docx
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/read.py" docs/rp2040.pdf --pages 464-470 --structured
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/read.py" docs/spec.docx --structured

# Search
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_CON" "I2C0_BASE"
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/spec.docx "I2C0" "clock divider"
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/pinout.xlsx "GPIO" "FUNCSEL"
uv run --project "$SKILL_DIR" --with docling "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_CON" --structured

# Regex search
uv run --project "$SKILL_DIR" "$SKILL_DIR/scripts/search.py" docs/rp2040.pdf "IC_\\w+" --regex --max-hits 10
```

## Operational Rules

- Start with TOC for PDF workflows.
- Do selective reading for large documents.
- Use search-first flow for DOCX/XLSX.
- Use `--structured` for register/electrical/timing tables when fidelity matters.
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
