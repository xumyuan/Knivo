"""Converter: detect format, dispatch to reader, write output."""

import os
import time

from .readers.base import BaseReader
from .readers.pdf_reader import PdfReader
from .readers.epub_reader import EpubReader
from .readers.azw3_reader import Azw3Reader
from .writers.markdown import MarkdownWriter

# Reader registry (checked in order)
_READERS: list[type[BaseReader]] = [EpubReader, Azw3Reader, PdfReader]


def get_reader(filepath: str, config: dict) -> BaseReader:
    """Return the appropriate reader for *filepath*."""
    for cls in _READERS:
        if cls.can_handle(filepath):
            return cls(config)
    ext = os.path.splitext(filepath)[1]
    raise ValueError(
        f"Unsupported format '{ext}'. "
        f"Supported: {', '.join(e for c in _READERS for e in c.supported_extensions)}"
    )


def convert_file(filepath: str, config: dict) -> list[str]:
    """Convert a single ebook file to Markdown. Returns list of written files."""
    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return []

    ext = os.path.splitext(filepath)[1].lower()
    print(f"\n{'='*60}")
    print(f"  File:   {os.path.basename(filepath)[:55]}")
    print(f"  Format: {ext}")
    print(f"{'='*60}")

    t0 = time.time()
    reader = get_reader(filepath, config)
    book = reader.read(filepath)
    print(f"[Read] title={book.title!r}  chapters={len(book.chapters)}  ({time.time()-t0:.1f}s)")

    writer = MarkdownWriter(config)
    files = writer.write(book)
    print(f"[Done] {time.time()-t0:.1f}s total")
    return files


def convert_directory(dirpath: str, config: dict) -> dict[str, list[str]]:
    """Convert all supported ebooks in a directory."""
    results = {}
    supported_ext = set()
    for cls in _READERS:
        supported_ext.update(cls.supported_extensions)

    found = [fn for fn in sorted(os.listdir(dirpath))
             if os.path.splitext(fn)[1].lower() in supported_ext]

    if not found:
        print(f"[WARN] No supported ebooks found in {dirpath}/")
        print(f"       Supported extensions: {', '.join(sorted(supported_ext))}")
        return results

    print(f"Found {len(found)} ebook(s) in {dirpath}/")
    for fn in found:
        fp = os.path.join(dirpath, fn)
        try:
            results[fn] = convert_file(fp, config)
        except Exception as e:
            print(f"\n[ERROR] Failed to convert {fn}: {e}")
            import traceback
            traceback.print_exc()
            results[fn] = []

    return results
