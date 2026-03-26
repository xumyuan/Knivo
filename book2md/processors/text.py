"""Text processing: OCR paragraph merging and HTML-to-Markdown conversion."""

import re
import warnings

from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------------------
#  OCR text merging (for scanned PDFs)
# ---------------------------------------------------------------------------

_PUNCT_END = set(
    "\u3002\uff01\uff1f\uff1b\uff1a\u2026\u300d\uff09\u3011\u300b\u201d\u2019!?;:"
)

_NEW_PARA = re.compile(
    r"^("
    r"\u7b2c\d+[\u7ae0\u7bc7\u8282]"
    r"|[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+[\u3001.]"
    r"|\d+[\u3001.\s]"
    r"|[\uff08(]\d+[\uff09)]"
    r"|[\u25cf\u2022\u25aa\u25a0\u25a1\u25c6]"
    r"|\u56fe\d|\u8868\d"
    r"|\u6848\u4f8b\u7814\u7a76|\u65b0\u95fb\u6458\u5f55|\u5373\u95ee\u5373\u7b54"
    r"|\u53c2\u8003\u8d44\u6599|\u5185\u5bb9\u63d0\u8981|\u590d\u4e60\u9898"
    r"|\u95ee\u9898\u4e0e\u5e94\u7528|\u5feb\u901f\u6d4b\u9a8c"
    r")"
)


def merge_ocr_paragraphs(ocr_results: list) -> str:
    """Join OCR text lines into coherent paragraphs."""
    if not ocr_results:
        return ""
    lines = [item["text"] for item in ocr_results]
    merged, buf = [], ""
    for line in lines:
        line = line.strip()
        if not line:
            if buf:
                merged.append(buf)
                buf = ""
            continue
        if not buf:
            buf = line
            continue
        if _NEW_PARA.match(line) or (buf and buf[-1] in _PUNCT_END):
            merged.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        merged.append(buf)
    return "\n\n".join(merged)


# ---------------------------------------------------------------------------
#  HTML to Markdown (for EPUB / AZW3)
# ---------------------------------------------------------------------------

def html_to_markdown(html: str) -> str:
    """Convert an HTML string to simple Markdown."""
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    parts: list[str] = []
    body = soup.body or soup
    _walk(body, parts)
    text = "\n".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _walk(node, parts: list[str]):
    for child in node.children:
        if isinstance(child, NavigableString):
            text = child.strip()
            if text:
                parts.append(text)
        elif isinstance(child, Tag):
            name = child.name.lower()
            if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                level = int(name[1])
                inner = child.get_text(strip=True)
                if inner:
                    parts.append(f"\n{'#' * level} {inner}\n")
            elif name == "p":
                inner = _inline(child)
                if inner:
                    parts.append(f"\n{inner}\n")
            elif name == "blockquote":
                inner = child.get_text(strip=True)
                if inner:
                    for line in inner.split("\n"):
                        parts.append(f"> {line.strip()}")
                    parts.append("")
            elif name in ("ul", "ol"):
                _list(child, parts, ordered=(name == "ol"))
                parts.append("")
            elif name == "br":
                parts.append("")
            elif name == "img":
                parts.append(f"[{child.get('alt', 'image')}]")
            elif name in ("div", "section", "article", "main", "aside", "nav",
                          "header", "footer", "figure", "figcaption"):
                _walk(child, parts)
            else:
                inner = _inline(child)
                if inner:
                    parts.append(inner)


def _inline(node) -> str:
    if isinstance(node, NavigableString):
        return node.strip()
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower()
    inner = "".join(_inline(c) for c in node.children)
    if name in ("strong", "b"):
        return f"**{inner}**" if inner else ""
    if name in ("em", "i"):
        return f"*{inner}*" if inner else ""
    if name == "a":
        return inner
    if name == "br":
        return "\n"
    if name == "img":
        return f"[{node.get('alt', 'image')}]"
    return inner


def _list(node, parts: list[str], ordered: bool = False, depth: int = 0):
    indent = "  " * depth
    counter = 1
    for child in node.children:
        if isinstance(child, Tag) and child.name.lower() == "li":
            prefix = f"{counter}." if ordered else "-"
            nested = child.find(["ul", "ol"])
            if nested:
                text_before = ""
                for c in child.children:
                    if isinstance(c, Tag) and c.name.lower() in ("ul", "ol"):
                        break
                    text_before += _inline(c)
                parts.append(f"{indent}{prefix} {text_before.replace(chr(10), ' ').strip()}")
                _list(nested, parts, ordered=(nested.name.lower() == "ol"), depth=depth + 1)
            else:
                text = _inline(child).replace("\n", " ").strip()
                parts.append(f"{indent}{prefix} {text}")
            counter += 1
