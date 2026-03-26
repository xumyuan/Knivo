"""Chapter / section title detector for scanned PDFs."""

import re


class ChapterDetector:
    """Detect chapter headings in OCR output using bbox-height filtering."""

    def __init__(self, config: dict):
        self.patterns = []
        for p in config["chapter_patterns"]:
            self.patterns.append({
                "regex": re.compile(p["pattern"]),
                "level": p["level"],
                "type": p["type"],
            })

    def detect(self, ocr_results: list, page_num: int) -> list:
        found = []
        for item in ocr_results:
            text = item["text"].strip()
            for pat in self.patterns:
                m = pat["regex"].search(text)
                if m:
                    bbox = item["bbox"]
                    height = y_top = 0
                    if isinstance(bbox, list) and len(bbox) >= 4:
                        y_top = min(pt[1] for pt in bbox)
                        y_bot = max(pt[1] for pt in bbox)
                        height = y_bot - y_top
                    if height < 70 or y_top > 1700:
                        continue
                    number = m.group(1)
                    title = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else ""
                    found.append({
                        "type": pat["type"], "level": pat["level"],
                        "number": number, "title": title,
                        "page": page_num + 1, "bbox_height": height,
                        "full_text": text,
                    })
        return self._merge_split_titles(found, ocr_results)

    @staticmethod
    def _merge_split_titles(found: list, ocr_results: list) -> list:
        if not found:
            return found
        for ch in found:
            ch_text = ch["full_text"]
            found_idx = None
            for i, item in enumerate(ocr_results):
                if item["text"].strip() == ch_text:
                    found_idx = i
                    break
            if found_idx is None:
                continue
            title_parts = []
            for j in range(found_idx - 1, max(found_idx - 4, -1), -1):
                bbox = ocr_results[j]["bbox"]
                if isinstance(bbox, list) and len(bbox) >= 4:
                    if abs(bbox[2][1] - bbox[0][1]) >= 70:
                        title_parts.insert(0, ocr_results[j]["text"].strip())
                    else:
                        break
                else:
                    break
            for j in range(found_idx + 1, min(found_idx + 5, len(ocr_results))):
                bbox = ocr_results[j]["bbox"]
                if isinstance(bbox, list) and len(bbox) >= 4:
                    if abs(bbox[2][1] - bbox[0][1]) >= 70:
                        title_parts.append(ocr_results[j]["text"].strip())
                    else:
                        break
                else:
                    break
            if title_parts:
                if ch["title"]:
                    title_parts.insert(0, ch["title"])
                ch["title"] = "".join(title_parts)
        return found
