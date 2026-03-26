"""Scanned-PDF reader with OCR pipeline."""

import io
import os
import time
from concurrent.futures import ThreadPoolExecutor

import fitz  # PyMuPDF
from PIL import Image

from .base import BaseReader, BookData, ChapterData
from ..processors.ocr import OCRProcessor
from ..processors.chapter import ChapterDetector
from ..processors.text import merge_ocr_paragraphs
from ..utils import extract_book_title


def _extract_page_image(doc: fitz.Document, page_num: int, dpi: int) -> Image.Image:
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    return Image.open(io.BytesIO(pix.tobytes("png")))


class PdfReader(BaseReader):
    supported_extensions = [".pdf"]

    def read(self, filepath: str) -> BookData:
        config = self.config
        doc = fitz.open(filepath)
        total = doc.page_count
        print(f"[PDF] {os.path.basename(filepath)[:50]}  ({total} pages)")

        is_scanned = self._check_scanned(doc)
        if is_scanned:
            print("[PDF] Scanned PDF detected -> OCR mode")
        else:
            print("[PDF] Text-based PDF detected -> text extraction mode")

        start = (config["page_range"]["start"] or 1) - 1
        end = config["page_range"]["end"] or total
        end = min(end, total)

        if is_scanned:
            chapters = self._ocr_pipeline(doc, config, start, end)
        else:
            chapters = self._text_pipeline(doc, start, end)

        doc.close()
        title = extract_book_title(filepath)
        return BookData(title=title, chapters=chapters, format="pdf", source_path=filepath)

    @staticmethod
    def _check_scanned(doc: fitz.Document, sample_pages: int = 5) -> bool:
        n = min(sample_pages, doc.page_count)
        text_pages = sum(1 for i in range(n) if doc[i].get_text().strip())
        return text_pages < n / 2

    def _text_pipeline(self, doc, start, end) -> list[ChapterData]:
        parts = []
        for i in range(start, end):
            text = doc[i].get_text().strip()
            if text:
                parts.append(text)
        return [ChapterData(title="Full Text", level=1, content="\n\n".join(parts))]

    def _ocr_pipeline(self, doc, config, start, end) -> list[ChapterData]:
        dpi = config["ocr"]["dpi"]
        ocr_proc = OCRProcessor(config)
        ch_detect = ChapterDetector(config)

        page_texts: dict[int, str] = {}
        page_chapters: dict[int, list] = {}
        all_chapters: list[dict] = []
        total = end - start

        print(f"[PDF] OCR pipeline (DPI={dpi}, pages {start+1}-{end})")

        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="img") as pool:
            img_futures = {pn: pool.submit(_extract_page_image, doc, pn, dpi)
                          for pn in range(start, end)}

        postpool = ThreadPoolExecutor(max_workers=2)
        post_futures = []
        t0_total = time.time()

        def _post(pn, ocr_res):
            chs = ch_detect.detect(ocr_res, pn)
            txt = merge_ocr_paragraphs(ocr_res)
            return pn, chs, txt

        processed = 0
        for pn in range(start, end):
            t0 = time.time()
            img = img_futures[pn].result()
            ocr_res = ocr_proc.ocr_page(img, pn)
            del img
            post_futures.append(postpool.submit(_post, pn, ocr_res))
            processed += 1
            elapsed = time.time() - t0
            progress = processed / total * 100
            eta = (time.time() - t0_total) / processed * (total - processed) if processed > 2 else 0
            cached = " [cache]" if elapsed < 0.05 else ""
            print(f"  p.{pn+1:3d}  {elapsed:.2f}s{cached}  [{progress:5.1f}%]  ETA {eta:.0f}s   ", end="\r")

        for fut in post_futures:
            pn, chs, txt = fut.result()
            page_texts[pn] = txt
            if chs:
                page_chapters[pn] = chs
                all_chapters.extend(chs)
        postpool.shutdown()

        print(f"\n[PDF] OCR done. {len(all_chapters)} chapter markers found.")
        return self._build_chapter_tree(all_chapters, page_texts, page_chapters, start, end)

    def _build_chapter_tree(self, all_chapters, page_texts, page_chapters, start, end):
        events = []
        for pn, chs in sorted(page_chapters.items()):
            for ch in chs:
                events.append((pn, ch))

        if not events:
            content = "\n\n".join(
                page_texts.get(pn, "") for pn in range(start, end) if page_texts.get(pn, "").strip()
            )
            return [ChapterData(title="Full Text", level=1, content=content)]

        result = []
        for i, (pn, info) in enumerate(events):
            next_pn = events[i + 1][0] if i + 1 < len(events) else end
            content = "\n\n".join(
                page_texts.get(p, "") for p in range(pn, next_pn) if page_texts.get(p, "").strip()
            )
            if info["type"] == "part":
                result.append(ChapterData(
                    title=f"\u7b2c{info['number']}\u7bc7 {info['title']}",
                    level=1, content="", page=info["page"],
                ))
            else:
                result.append(ChapterData(
                    title=f"\u7b2c{info['number']}\u7ae0 {info['title']}",
                    level=2, content=content, page=info["page"],
                ))

        first_pn = events[0][0]
        if first_pn > start:
            preface = "\n\n".join(
                page_texts.get(p, "") for p in range(start, first_pn) if page_texts.get(p, "").strip()
            )
            if preface.strip():
                result.insert(0, ChapterData(title="\u524d\u8a00", level=1, content=preface))

        return result
