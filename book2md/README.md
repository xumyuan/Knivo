# book2md

Multi-format ebook to Markdown converter. Supports **PDF** (scanned & text), **EPUB**, and **AZW3/MOBI**.

Each book is converted into a folder of per-chapter Markdown files with an auto-generated table of contents.

## Quick Start

```bash
# 1. Install dependencies
pip install -r book2md/requirements.txt

# 2. (Recommended) Install GPU acceleration for scanned PDF OCR
pip install onnxruntime-directml     # Windows, any GPU
# or
pip install onnxruntime-gpu          # Linux/Windows, NVIDIA CUDA

# 3. Run
python -m book2md inputs/            # convert all books in a folder
python -m book2md book.epub          # convert a single file
```

## Usage

```
python -m book2md [OPTIONS] <path>
```

| Option | Description |
|---|---|
| `path` | File or directory to convert |
| `-o, --output DIR` | Output directory (default: `output/`) |
| `--dpi N` | OCR resolution for scanned PDFs (default: 200) |
| `--pages START-END` | Page range for PDF, e.g. `20-50` |
| `--no-cache` | Disable OCR cache, force re-OCR |
| `--config FILE` | Path to YAML config (default: `config.yaml`) |
| `-v, --version` | Show version |
| `-h, --help` | Show help |

### Examples

```bash
# Batch convert everything in inputs/
python -m book2md inputs/

# Single EPUB
python -m book2md "my book.epub"

# Scanned PDF with higher resolution OCR
python -m book2md textbook.pdf --dpi 300

# Only pages 100-200 of a PDF
python -m book2md textbook.pdf --pages 100-200

# Custom output directory
python -m book2md inputs/ -o markdown_output/

# Re-OCR without cache
python -m book2md textbook.pdf --no-cache
```

## Supported Formats

| Format | Extensions | Method |
|---|---|---|
| EPUB | `.epub` | Text extraction (instant) |
| Kindle | `.azw3`, `.azw`, `.mobi` | Auto-extract embedded EPUB (instant) |
| PDF (text) | `.pdf` | Direct text extraction (fast) |
| PDF (scanned) | `.pdf` | GPU-accelerated OCR (auto-detected) |

## Output Structure

```
output/
  Book Title/
    00_TOC.md                   # Auto-generated table of contents
    Chapter 1 Title.md
    Chapter 2 Title.md
    Part Name/                  # Sub-folder per part (if applicable)
      Chapter 3 Title.md
      Chapter 4 Title.md
```

## Configuration

Copy `config.yaml` to your working directory and edit as needed. All settings are optional.

Key settings:

```yaml
output_dir: "output"       # Where to write Markdown files
ocr:
  dpi: 200                 # Higher = better OCR but slower (try 300 for poor scans)
cache:
  enabled: true            # Cache OCR results for resume/re-run
  cache_dir: ".cache"
```

See `book2md/config.yaml` for all available options.

## Project Structure

```
book2md/
  __init__.py              # Package info & version
  __main__.py              # CLI entry point (python -m book2md)
  config.py                # Configuration loader
  converter.py             # Format detection & dispatch
  utils.py                 # Filename sanitization, title extraction
  readers/
    base.py                # BaseReader, BookData, ChapterData
    epub_reader.py         # EPUB parser
    azw3_reader.py         # AZW3/MOBI unpacker -> delegates to EPUB
    pdf_reader.py          # PDF reader with OCR pipeline
  processors/
    ocr.py                 # GPU-accelerated OCR (DirectML / CUDA)
    chapter.py             # Chapter title detection for scanned PDFs
    text.py                # Paragraph merging & HTML-to-Markdown
  writers/
    markdown.py            # Per-chapter Markdown file writer
  config.yaml              # Default configuration
  requirements.txt         # Python dependencies
```

## Requirements

- Python 3.10+
- GPU recommended for scanned PDFs (NVIDIA or any DirectX 12 GPU on Windows)
- ~16 GB RAM for large scanned PDFs

## Performance

Tested on RTX 5080:

| Format | Speed |
|---|---|
| EPUB / AZW3 | < 1 second |
| PDF (text) | < 1 second |
| PDF (scanned, 380 pages) | ~6 minutes (GPU) |
| PDF (scanned, cached re-run) | ~1 minute |
