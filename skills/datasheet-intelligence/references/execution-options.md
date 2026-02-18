# Execution Options

Use this guide when choosing runtime flags for datasheet ingestion and retrieval scripts.

## Repository Hygiene

Before running ingestion in a new repo, ignore generated knowledge artifacts:

```bash
if [ -f .gitignore ] && grep -qE '^\.context(/|$)' .gitignore; then
  echo ".context ignore rule already exists"
else
  echo ".context/knowledge/" >> .gitignore
fi
```

If you want broader ignore coverage for skill outputs, prefer `.context/`.

## Prerequisites

Validate `uv` first:

```bash
uv --version
```

If `uv` is missing, install by OS:

```bash
# macOS (Homebrew)
brew install uv

# Linux (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (WinGet)
winget install --id=astral-sh.uv -e
```

Reopen the terminal after installation and run `uv --version` again.

## No-`uv` Fallback

Use this only when `uv` installation is blocked by policy or environment constraints.

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install docling

python3 scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge
python3 scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge
python3 scripts/read_docs.py exynos_spi_v1 --anchor section-4-2
```

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install docling

python scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge
python scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge
python scripts/read_docs.py exynos_spi_v1 --anchor section-4-2
```

## `scripts/ingest_docs.py`

Base command:

```bash
uv run --with docling python3 scripts/ingest_docs.py <source...> --output-dir .context/knowledge
```

### Options

- `--output-dir <path>`
  - Write artifacts to a custom knowledge folder.
  - Default: `.context/knowledge`
- `--chunk-max-chars <int>`
  - Maximum characters per retrieval chunk.
  - Default: `2200`
- `--chunk-overlap <int>`
  - Character overlap between adjacent chunks.
  - Default: `220`
- `--non-recursive`
  - Process only the top-level files in each source directory.
- `--no-ocr`
  - Disable PDF OCR for speed when text is already machine-readable.
- `--no-images`
  - Skip image extraction to reduce runtime and output size.
- `--fail-on-error`
  - Return non-zero exit code if any document fails conversion.
  - Use this for CI and automated checks.
- `-v`, `--verbose`
  - Print per-file progress and unexpected error logs.

### Preset Examples

```bash
# Balanced default run
uv run --with docling python3 scripts/ingest_docs.py docs/datasheets --output-dir .context/knowledge

# Faster run (no OCR, no nested folders)
uv run --with docling python3 scripts/ingest_docs.py docs/datasheets --non-recursive --no-ocr

# CI-safe run (fail fast on conversion errors)
uv run --with docling python3 scripts/ingest_docs.py docs/datasheets --fail-on-error -v
```

## `scripts/search_docs.py`

Base command:

```bash
uv run python3 scripts/search_docs.py "<query>" --knowledge-dir .context/knowledge
```

### Options

- `--knowledge-dir <path>`
  - Directory containing `*.sections.jsonl` outputs.
  - Default: `.context/knowledge`
- `--regex`
  - Treat `query` as a regular expression.
- `--case-sensitive`
  - Disable default case-insensitive matching.
- `--max-hits <int>`
  - Limit number of printed matches.
  - Default: `20`

### Preset Examples

```bash
# Literal keyword search
uv run python3 scripts/search_docs.py "SPI0 address" --knowledge-dir .context/knowledge

# Regex search for register names
uv run python3 scripts/search_docs.py "REG_[A-Z0-9_]+" --regex --max-hits 50

# Case-sensitive lookup
uv run python3 scripts/search_docs.py "CRC16" --case-sensitive
```

## `scripts/read_docs.py`

Base command:

```bash
uv run python3 scripts/read_docs.py <doc-id> --knowledge-dir .context/knowledge
```

### Options

- `--knowledge-dir <path>`
  - Directory containing normalized markdown docs.
  - Default: `.context/knowledge`
- `--anchor <id>`
  - Print only the section range starting at a specific anchor.
- `--max-lines <int>`
  - Limit output size for terminal readability.
  - Default: `160`

### Preset Examples

```bash
# Read beginning of a document
uv run python3 scripts/read_docs.py exynos_spi_v1 --max-lines 120

# Read a specific section by anchor
uv run python3 scripts/read_docs.py exynos_spi_v1 --anchor section-4-2 --max-lines 200
```

## Recommended Defaults

- Keep `--output-dir .context/knowledge` for consistent downstream discovery.
- Generated artifacts are grouped per document under `.context/knowledge/<doc_id>/`.
- Start with default chunk settings unless retrieval quality is clearly poor.
- Use `--fail-on-error` in CI; skip it for exploratory local batch runs.
