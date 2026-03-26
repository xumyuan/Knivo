"""EPUB reader: parse .epub files into BookData."""

import os
import re

import ebooklib
from ebooklib import epub

from .base import BaseReader, BookData, ChapterData
from ..processors.text import html_to_markdown
from ..utils import extract_book_title


class EpubReader(BaseReader):
    supported_extensions = [".epub"]

    def read(self, filepath: str) -> BookData:
        book = epub.read_epub(filepath)

        title = self._meta(book, "title") or extract_book_title(filepath)
        author = self._meta(book, "creator") or ""
        language = self._meta(book, "language") or ""

        item_map: dict[str, ebooklib.epub.EpubHtml] = {}
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            item_map[item.get_name()] = item

        chapters = self._parse_toc(book.toc, item_map)
        if not chapters:
            chapters = self._fallback_spine(book, item_map)

        return BookData(
            title=title, author=author, language=language,
            chapters=chapters, format="epub", source_path=filepath,
        )

    def _parse_toc(self, toc, item_map) -> list[ChapterData]:
        chapters = []
        for entry in toc:
            if isinstance(entry, tuple):
                section, children = entry
                ch = self._toc_entry_to_chapter(section, item_map, level=1)
                ch.children = self._parse_toc(children, item_map)
                chapters.append(ch)
            elif isinstance(entry, epub.Link):
                chapters.append(self._toc_entry_to_chapter(entry, item_map, level=2))
            elif isinstance(entry, epub.Section):
                chapters.append(ChapterData(title=entry.title or "Section", level=1))
        return chapters

    def _toc_entry_to_chapter(self, entry, item_map, level: int) -> ChapterData:
        title = getattr(entry, "title", "") or "Untitled"
        href = getattr(entry, "href", "") or ""
        base_href = href.split("#")[0]

        content = ""
        item = item_map.get(base_href)
        if item is None:
            fname = os.path.basename(base_href)
            for key, val in item_map.items():
                if os.path.basename(key) == fname:
                    item = val
                    break

        if item is not None:
            raw = item.get_content().decode("utf-8", errors="replace")
            content = html_to_markdown(raw)

        return ChapterData(title=title, level=level, content=content)

    def _fallback_spine(self, book, item_map) -> list[ChapterData]:
        chapters = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            raw = item.get_content().decode("utf-8", errors="replace")
            md = html_to_markdown(raw)
            if not md.strip():
                continue
            title = self._extract_first_heading(md) or item.get_name()
            chapters.append(ChapterData(title=title, level=2, content=md))
        return chapters

    @staticmethod
    def _extract_first_heading(md: str) -> str:
        m = re.search(r"^#{1,3}\s+(.+)$", md, re.MULTILINE)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _meta(book, key: str) -> str:
        vals = book.get_metadata("DC", key)
        return vals[0][0] if vals else ""
