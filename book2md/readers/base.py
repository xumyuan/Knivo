"""Data models and base classes for ebook readers."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChapterData:
    """A single chapter or section of a book."""
    title: str
    level: int = 1              # 1 = part/top-level, 2 = chapter, 3 = section
    content: str = ""           # Markdown-formatted text
    children: list[ChapterData] = field(default_factory=list)
    page: Optional[int] = None  # Source page number (PDF only)


@dataclass
class BookData:
    """Unified representation of a parsed book."""
    title: str
    author: str = ""
    language: str = ""
    chapters: list[ChapterData] = field(default_factory=list)
    format: str = ""            # "pdf", "epub", "azw3"
    source_path: str = ""


class BaseReader:
    """Abstract base class for all format readers.

    Subclasses must set ``supported_extensions`` and implement ``read()``.
    """

    supported_extensions: list[str] = []

    def __init__(self, config: dict):
        self.config = config

    def read(self, filepath: str) -> BookData:
        """Parse *filepath* and return a BookData object."""
        raise NotImplementedError

    @classmethod
    def can_handle(cls, filepath: str) -> bool:
        import os
        ext = os.path.splitext(filepath)[1].lower()
        return ext in cls.supported_extensions
