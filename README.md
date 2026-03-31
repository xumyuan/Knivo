# AI Toolkit

A collection of practical command-line tools for working with books, documents, and LLM-related workflows.

## Tools

| Tool | Description |
|---|---|
| [book2md](book2md/) | Multi-format ebook to Markdown converter (PDF, EPUB, AZW3/MOBI) |
| [tokenCounter](tokenCounter/) | Code repository token counter for estimating LLM context usage |
| [picmp](picmp/) | Image quality comparison tool with metrics, diff visualization and HTML report |

## book2md

Converts ebooks into clean, chapter-split Markdown files. Supports text-based and scanned PDFs (with GPU-accelerated OCR), EPUB, and Kindle formats.

```bash
pip install -r book2md/requirements.txt
python -m book2md inputs/          # batch convert a folder
python -m book2md book.epub        # single file
```

See [book2md/README.md](book2md/README.md) for full documentation.

## tokenCounter

Scans a codebase and reports token counts by file and language — useful for estimating how much of a repo fits into an LLM context window.

```bash
pip install tiktoken
python tokenCounter/count_tokens.py .                 # scan current directory
python tokenCounter/count_tokens.py src/ --ext py,ts   # filter by language
```

See [tokenCounter/README.md](tokenCounter/README.md) for full documentation.

## picmp

Image quality comparison tool — compares single or batch image pairs, computes PSNR/SSIM/MSE and more, generates diff heatmaps and an interactive HTML report.

```bash
pip install -r picmp/requirements.txt
python picmp/picmp.py img_a.png img_b.png              # single pair
python picmp/picmp.py --batch dir_a/ dir_b/            # batch (recursive)
```

See [picmp/README.md](picmp/README.md) for full documentation.

## Requirements

- Python 3.10+
- See each tool's README for tool-specific dependencies
