"""CLI entry point: python -m book2md [OPTIONS] <path>

Examples:
    python -m book2md inputs/                     # convert all books in a directory
    python -m book2md book.epub                   # convert a single EPUB
    python -m book2md book.pdf --dpi 300          # PDF with high-res OCR
    python -m book2md book.pdf --pages 20-50      # only certain pages
    python -m book2md inputs/ -o my_output/       # custom output directory
    python -m book2md inputs/ --no-cache          # force re-OCR (no cache)
"""

import argparse
import os
import sys
import textwrap

from . import __version__
from .config import load_config
from .converter import convert_file, convert_directory


_EPILOG = textwrap.dedent("""\
    supported formats:
      .epub          EPUB ebooks (text-based, fast)
      .azw3 .mobi    Kindle / MOBI (auto-extracts embedded EPUB)
      .pdf           PDF (auto-detects scanned vs text; scanned uses GPU OCR)

    examples:
      %(prog)s inputs/                      batch-convert everything in a folder
      %(prog)s novel.epub                   convert a single EPUB file
      %(prog)s textbook.pdf --dpi 300       higher OCR resolution for scans
      %(prog)s textbook.pdf --pages 1-50    convert only pages 1-50
      %(prog)s inputs/ -o markdown/         write output to markdown/ directory
      %(prog)s inputs/ --no-cache           ignore cached OCR results

    notes:
      - PDF scans use GPU-accelerated OCR (DirectML / CUDA) when available.
      - OCR results are cached in .cache/ to speed up repeated runs.
      - Each book is output as a folder of per-chapter Markdown files.
""")


def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="book2md",
        description="Convert ebooks (PDF / EPUB / AZW3) to Markdown, split by chapter.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path",
        help="ebook file or directory containing ebooks to convert",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="output directory (default: output/)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="path to YAML config file (default: config.yaml)",
    )
    parser.add_argument(
        "--dpi",
        type=int, default=None,
        help="OCR resolution for scanned PDFs (default: 200)",
    )
    parser.add_argument(
        "--pages",
        type=str, default=None,
        metavar="START-END",
        help="page range for PDF, e.g. '20-50' or '100' (default: all)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="disable OCR result cache (force re-OCR)",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Load config and apply CLI overrides
    config = load_config(args.config)
    if args.output:
        config["output_dir"] = args.output
    if args.dpi:
        config["ocr"]["dpi"] = args.dpi
    if args.pages:
        parts = args.pages.split("-")
        config["page_range"]["start"] = int(parts[0])
        if len(parts) > 1:
            config["page_range"]["end"] = int(parts[1])
    if args.no_cache:
        config["cache"]["enabled"] = False

    path = args.path
    if os.path.isdir(path):
        results = convert_directory(path, config)
        total = sum(len(v) for v in results.values())
        print(f"\n{'='*60}")
        print(f"All done!  {len(results)} book(s) -> {total} file(s)")
    elif os.path.isfile(path):
        convert_file(path, config)
    else:
        parser.error(f"path not found: {path}")


if __name__ == "__main__":
    main()
