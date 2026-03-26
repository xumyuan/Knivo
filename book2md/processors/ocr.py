"""OCR processor with GPU acceleration and disk cache."""

import io
import json
import os
import sys

from PIL import Image


class OCRProcessor:
    """RapidOCR wrapper with DirectML/CUDA GPU support and JSON cache."""

    def __init__(self, config: dict):
        self.config = config
        self._init_ocr_engine()
        self.cache_enabled = config["cache"]["enabled"]
        self.cache_dir = config["cache"]["cache_dir"]
        if self.cache_enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

    @staticmethod
    def _setup_cuda_paths():
        if sys.platform != "win32":
            return
        try:
            import nvidia
            base = os.path.dirname(nvidia.__path__[0])
            nvidia_dir = os.path.join(base, "nvidia")
            for sub in os.listdir(nvidia_dir):
                bin_dir = os.path.join(nvidia_dir, sub, "bin")
                if os.path.isdir(bin_dir) and bin_dir not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        except ImportError:
            pass

    def _init_ocr_engine(self):
        from rapidocr_onnxruntime import RapidOCR
        self._setup_cuda_paths()
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            if "DmlExecutionProvider" in providers:
                print("[OCR] DirectML GPU acceleration")
                self.ocr = RapidOCR(det_use_dml=True, rec_use_dml=True, cls_use_dml=True)
                return
            if "CUDAExecutionProvider" in providers:
                print("[OCR] CUDA GPU acceleration")
                self.ocr = RapidOCR(det_use_cuda=True, rec_use_cuda=True, cls_use_cuda=True)
                return
        except Exception as e:
            print(f"[OCR] GPU init failed ({e}), using CPU")
        print("[OCR] CPU mode")
        self.ocr = RapidOCR()

    def _cache_path(self, page_num: int) -> str:
        return os.path.join(self.cache_dir, f"page_{page_num:04d}.json")

    def _load_cache(self, page_num: int):
        path = self._cache_path(page_num)
        if self.cache_enabled and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_cache(self, page_num: int, result: list):
        if self.cache_enabled:
            with open(self._cache_path(page_num), "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    def ocr_page(self, img: Image.Image, page_num: int) -> list:
        """OCR a single page. Returns [{"text", "bbox", "confidence"}, ...]"""
        cached = self._load_cache(page_num)
        if cached is not None:
            return cached
        result, _ = self.ocr(img)
        structured = []
        if result:
            for bbox, text, confidence in result:
                structured.append({"text": text, "bbox": bbox, "confidence": confidence})
        self._save_cache(page_num, structured)
        return structured
