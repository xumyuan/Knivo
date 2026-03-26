"""Configuration loader with sensible defaults."""

import copy
import os

import yaml

_DEFAULTS = {
    "output_dir": "output",
    "ocr": {"dpi": 200, "language": "ch"},
    "chapter_patterns": [
        {"pattern": r"\u7b2c(\d+)\u7bc7\s*(.*)", "level": 1, "type": "part"},   # 第X篇
        {"pattern": r"\u7b2c(\d+)\u7ae0\s*(.*)", "level": 2, "type": "chapter"}, # 第X章
    ],
    "page_range": {"start": None, "end": None},
    "output": {
        "keep_page_markers": True,
        "merge_paragraphs": True,
        "include_toc": True,
    },
    "cache": {"enabled": True, "cache_dir": ".cache"},
}


def _deep_merge(base: dict, override: dict):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_config(config_path: str = "config.yaml") -> dict:
    """Load YAML config file and merge with built-in defaults.

    The config file is optional; all settings have sensible defaults.
    """
    cfg = copy.deepcopy(_DEFAULTS)
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        _deep_merge(cfg, user)
    return cfg
