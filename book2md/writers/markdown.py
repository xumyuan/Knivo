"""Markdown writer: split BookData into per-chapter .md files."""

import os

from ..readers.base import BookData, ChapterData
from ..utils import sanitize_filename, ensure_dir


class MarkdownWriter:
    def __init__(self, config: dict):
        self.config = config
        self.output_dir = config["output_dir"]

    def write(self, book: BookData):
        book_dir = os.path.join(self.output_dir, sanitize_filename(book.title))
        ensure_dir(book_dir)
        print(f"\n[Write] -> {book_dir}/")

        files_written = []
        toc_entries = []
        current_part_dir = book_dir

        for i, ch in enumerate(book.chapters):
            if ch.level == 1 and not ch.content and not ch.children:
                part_dir_name = sanitize_filename(ch.title)
                current_part_dir = os.path.join(book_dir, part_dir_name)
                ensure_dir(current_part_dir)
                toc_entries.append({"level": 1, "text": ch.title, "file": ""})
                continue

            if ch.level == 1 and ch.content:
                fname = sanitize_filename(f"{i:02d}_{ch.title}") + ".md"
                fpath = os.path.join(book_dir, fname)
                current_part_dir = book_dir
            else:
                fname = sanitize_filename(ch.title) + ".md"
                fpath = os.path.join(current_part_dir, fname)

            content = self._format_chapter(ch)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            files_written.append(fpath)
            rel = os.path.relpath(fpath, book_dir).replace("\\", "/")
            toc_entries.append({"level": ch.level, "text": ch.title, "file": rel})
            print(f"  + {rel}")

            for child in ch.children:
                cfname = sanitize_filename(child.title) + ".md"
                cfpath = os.path.join(current_part_dir, cfname)
                with open(cfpath, "w", encoding="utf-8") as f:
                    f.write(self._format_chapter(child))
                files_written.append(cfpath)
                crel = os.path.relpath(cfpath, book_dir).replace("\\", "/")
                toc_entries.append({"level": child.level, "text": child.title, "file": crel})
                print(f"  + {crel}")

        if self.config["output"].get("include_toc", True):
            toc_path = os.path.join(book_dir, "00_TOC.md")
            with open(toc_path, "w", encoding="utf-8") as f:
                f.write(self._generate_toc(book, toc_entries))
            files_written.append(toc_path)
            print(f"  + 00_TOC.md")

        print(f"[Write] Done: {len(files_written)} files")
        return files_written

    @staticmethod
    def _format_chapter(ch: ChapterData) -> str:
        prefix = "#" * max(1, ch.level)
        return f"{prefix} {ch.title}\n\n{ch.content}\n"

    @staticmethod
    def _generate_toc(book: BookData, entries: list) -> str:
        lines = [f"# {book.title}\n"]
        if book.author:
            lines.append(f"> {book.author}\n")
        lines.append("")
        for e in entries:
            indent = "  " * (e["level"] - 1)
            if e["file"]:
                lines.append(f"{indent}- [{e['text']}]({e['file']})")
            else:
                lines.append(f"{indent}- **{e['text']}**")
        lines.append("")
        return "\n".join(lines)
