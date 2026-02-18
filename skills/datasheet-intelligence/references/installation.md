# Installation Guide

## 1. Python Environment

Scripts in this skill are designed to run with **`uv run`** (zero-setup ephemeral environments).

If you prefer a persistent environment, see the [Manual Setup](#manual-setup-persistent-environment) section below.

### Install `uv`

If `uv` is not installed, install it by OS.

```bash
# macOS (Homebrew)
brew install uv

# Linux (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (WinGet)
winget install --id=astral-sh.uv -e
```

## 2. System Dependencies

These libraries must be installed on your OS for document processing to work correctly.

### PDFium C++ Library (Critical for PDF)

`docling` and `pypdfium2` rely on the PDFium library. While `pypdfium2` wheels usually bundle it, **Linux systems often require a manual install** to avoid runtime errors.

#### Linux (Debian/Ubuntu/RHEL)

If you encounter PDF processing errors, install the simplified PDFium binary manually:

1. **Download & Extract PDFium** (Select x64 or arm64):
   ```bash
   mkdir -p ~/lib_pdfium && cd ~/lib_pdfium
   # x64
   wget https://github.com/bblanchon/pdfium-binaries/releases/latest/download/pdfium-linux-x64.tgz
   # arm64: wget https://github.com/bblanchon/pdfium-binaries/releases/latest/download/pdfium-linux-arm64.tgz
   
   tar -xzf pdfium-linux-*.tgz
   rm pdfium-linux-*.tgz
   ```

2. **Configure Library Path**:
   ```bash
   # Current session
   export LD_LIBRARY_PATH=$HOME/lib_pdfium:$LD_LIBRARY_PATH
   
   # Permanent (add to ~/.bashrc or ~/.zshrc)
   echo 'export LD_LIBRARY_PATH=$HOME/lib_pdfium:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc
   ```

#### Windows / macOS
- **Windows**: `pypdfium2` wheels usually work out-of-the-box. If not, refer to [pypdfium2 documentation](https://pypdfium2.readthedocs.io).
- **macOS**: `brew install pdfium` is rarely needed but can be tried if the wheel fails.

### Tesseract OCR (Optional)

Required only if you need OCR for scanned documents (i.e., running without `--no-ocr`).

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y tesseract-ocr libtesseract-dev libleptonica-dev pkg-config

# Fedora/RHEL
sudo dnf install -y tesseract tesseract-devel leptonica-devel pkg-config

# macOS
brew install tesseract

# Windows (WinGet)
winget install --id UB-Mannheim.TesseractOCR -e
```

## 3. Manual Setup (Persistent Environment)

If you cannot use `uv run`'s ephemeral environments, use this traditional virtual environment setup.

### Using `uv` (Recommended)

```bash
# Create project and venv
mkdir datasheet_project && cd datasheet_project
uv venv

# Activate venv
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .\.venv\Scripts\Activate.ps1

# Install dependencies
uv pip install docling pypdfium2 docling-parse python-docx openpyxl pandas

# If system PDFium is needed (Linux):
PDFIUM_PLATFORM=system uv pip install --upgrade --force-reinstall pypdfium2
```

### Using Standard `pip` (No-uv Fallback)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install docling pypdfium2 docling-parse python-docx openpyxl pandas
```

After setup, run scripts directly with the python executable in the venv:
```bash
python3 scripts/check_deps.py
python3 scripts/ingest_docs.py ...
```
