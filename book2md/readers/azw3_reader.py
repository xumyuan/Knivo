"""AZW3 / Kindle reader: unpack to EPUB then delegate."""

import glob
import os

from .base import BaseReader, BookData
from .epub_reader import EpubReader
from ..utils import extract_book_title


class Azw3Reader(BaseReader):
    supported_extensions = [".azw3", ".azw", ".mobi"]

    def read(self, filepath: str) -> BookData:
        import mobi

        print(f"[AZW3] Extracting: {os.path.basename(filepath)[:50]}...")
        tmpdir, _ = mobi.extract(filepath)

        epub_path = self._find_epub(tmpdir)
        if epub_path:
            print("[AZW3] Found embedded EPUB, delegating to EpubReader")
            reader = EpubReader(self.config)
            book = reader.read(epub_path)
        else:
            print("[AZW3] No embedded EPUB, parsing HTML from mobi7/")
            book = self._parse_mobi7_html(tmpdir, filepath)

        book.format = "azw3"
        book.source_path = filepath
        if not book.title or book.title == "Untitled":
            book.title = extract_book_title(filepath)
        return book

    @staticmethod
    def _find_epub(tmpdir: str) -> str | None:
        for pattern in [
            os.path.join(tmpdir, "mobi8", "**", "*.epub"),
            os.path.join(tmpdir, "mobi8", "*.epub"),
        ]:
            matches = glob.glob(pattern, recursive=True)
            if matches:
                return matches[0]
        return None

    def _parse_mobi7_html(self, tmpdir: str, filepath: str) -> BookData:
        from ..processors.text import html_to_markdown
        from .base import ChapterData

        html_dir = os.path.join(tmpdir, "mobi7")
        chapters = []
        for fn in sorted(os.listdir(html_dir)):
            if fn.endswith((".html", ".htm", ".xhtml")):
                fp = os.path.join(html_dir, fn)
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    raw = f.read()
                md = html_to_markdown(raw)
                if md.strip():
                    chapters.append(ChapterData(title=fn, level=2, content=md))

        return BookData(
            title=extract_book_title(filepath), chapters=chapters,
            format="azw3", source_path=filepath,
        )
