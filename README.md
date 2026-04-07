# Knivo

A collection of practical command-line tools for working with books, documents, and LLM-related workflows.

## Installation

```bash
pip install -e .
```

This registers all tools as global commands — use them from any directory:

| Command | Tool | Description |
|---|---|---|
| `tokens` | [tokenCounter](tokenCounter/) | Code repository token counter for estimating LLM context usage |
| `book2md` | [book2md](book2md/) | Multi-format ebook to Markdown converter (PDF, EPUB, AZW3/MOBI) |
| `picmp` | [picmp](picmp/) | Image quality comparison tool with metrics, diff visualization and HTML report |

Each tool has its own `--help` and detailed README.

## Quick Start

```bash
# Token counter — scan a codebase
tokens .                                    # current directory
tokens dir1 dir2 --ext shader              # multiple dirs, filter by language
tokens . --group "Shader:GLSL,HLSL,UE Shader"  # group languages

# Book converter — ebooks to Markdown
book2md inputs/                             # batch convert a folder
book2md book.epub                           # single file
book2md textbook.pdf --dpi 300 --pages 1-50 # scanned PDF with options

# Image comparison — quality metrics + HTML report
picmp img_a.png img_b.png                   # single pair
picmp --batch dir_a/ dir_b/                 # batch (recursive)
```

## Tool-Specific Dependencies

```bash
# tokens — optional but recommended
pip install tiktoken

# book2md
pip install -r book2md/requirements.txt

# picmp
pip install -r picmp/requirements.txt
```

## Requirements

- Python 3.10+
- See each tool's README for full documentation:
  - [tokenCounter/README.md](tokenCounter/README.md)
  - [book2md/README.md](book2md/README.md)
  - [picmp/README.md](picmp/README.md)
