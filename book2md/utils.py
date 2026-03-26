"""Shared utility helpers."""

import os
import re


def sanitize_filename(name: str) -> str:
    """Remove characters illegal in Windows/Unix file names."""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip('. ')
    return name or "untitled"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def extract_book_title(filepath: str) -> str:
    """Best-effort short title from a (possibly very long) filename."""
    base = os.path.splitext(os.path.basename(filepath))[0]
    # Strip leading brackets: [xxx] -> xxx
    base = re.sub(r'^[\[【]([^\]】]+)[\]】]', r'\1', base)
    # Remove embedded extension remnants like ".pdf (other.pdf"
    base = re.sub(r'\.\w{2,4}\s*\(.*$', '', base)
    # Strip author in Chinese format: .（美）曼昆
    base = re.sub(r'[.．]（.{1,2}）.+$', '', base)
    # Trim z-library noise
    base = re.split(r'\s*\((?:z-library|Z-Library|[a-z]+-lib)', base, maxsplit=1)[0]
    # Trim trailing parenthetical if very long (>50 chars)
    base = re.sub(r'\s*[\(\[（].{50,}$', '', base)
    # Trim " = English Title ..." patterns
    base = re.split(r'\s*=\s*[A-Z]', base, maxsplit=1)[0]
    return base.strip() or "untitled"
