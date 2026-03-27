#!/usr/bin/env python3
"""
count_tokens.py — 统计代码仓库的 token 数量

用法:
    python count_tokens.py [目录路径] [选项]

选项:
    --model     指定 tokenizer 模型（默认 cl100k_base，兼容 GPT-4/Claude 估算）
    --top       显示 token 最多的前 N 个文件（默认 10）
    --ext       按语言或扩展名过滤，逗号分隔，如 --ext cpp,py,json
                支持语言别名：cpp → .cpp/.cc/.cxx/.hpp, py → .py/.pyw 等
    --exclude   排除指定目录，逗号分隔，如 --exclude tests,third_party,build
    --no-ignore 不忽略 .gitignore 规则

依赖:
    pip install tiktoken
"""

import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# 尝试导入 tiktoken，否则退回字符估算
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# ── 默认忽略的目录和文件 ──────────────────────────────────────────────────────

IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", ".pnp",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "venv", ".venv", "env", ".env",
    "dist", "build", "out", ".next", ".nuxt",
    ".idea", ".vscode",
    "coverage", ".nyc_output",
    "vendor",                     # Go / PHP
}

IGNORE_EXTENSIONS = {
    # 二进制 / 媒体
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm",
    ".ttf", ".woff", ".woff2", ".eot",
    # 数据 / 锁文件（通常不放进 context）
    ".lock", ".sum",
    ".min.js", ".min.css",
    # 图像向量
    ".sketch", ".fig",
}

# 扩展名 → 语言标签（用于汇总表格）
EXT_LANG = {
    ".py": "Python", ".pyw": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
    ".hpp": "C++", ".hxx": "C++",
    ".inl": "C++", ".ipp": "C++", ".tpp": "C++", ".tcc": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "CSS", ".sass": "CSS", ".less": "CSS",
    ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown", ".mdx": "Markdown",
    ".sql": "SQL",
    ".tf": "Terraform", ".tfvars": "Terraform",
    ".proto": "Protobuf",
    ".graphql": "GraphQL", ".gql": "GraphQL",
    ".lua": "Lua",
    ".ex": "Elixir", ".exs": "Elixir",
    ".scala": "Scala",
    ".r": "R", ".R": "R",
    ".dart": "Dart",
    ".vim": "Vim",
}

# 语言别名 → 扩展名集合（从 EXT_LANG 反向生成 + 手动别名）
LANG_ALIASES: dict[str, set[str]] = {}
for _ext, _lang in EXT_LANG.items():
    LANG_ALIASES.setdefault(_lang.lower(), set()).add(_ext)

# .h 同时归属 C 和 C++
LANG_ALIASES.setdefault("c", set()).add(".h")
LANG_ALIASES.setdefault("c++", set()).add(".h")

# 额外常用别名
LANG_ALIASES.update({
    "c++":        LANG_ALIASES["c++"],
    "cpp":        LANG_ALIASES["c++"],
    "cc":         LANG_ALIASES["c++"],
    "cxx":        LANG_ALIASES["c++"],
    "c":          LANG_ALIASES["c"],
    "py":         LANG_ALIASES["python"],
    "js":         LANG_ALIASES["javascript"],
    "ts":         LANG_ALIASES["typescript"],
    "tsx":        LANG_ALIASES["typescript"],
    "jsx":        LANG_ALIASES["javascript"],
    "rb":         LANG_ALIASES["ruby"],
    "sh":         LANG_ALIASES["shell"],
    "bash":       LANG_ALIASES["shell"],
    "yml":        LANG_ALIASES["yaml"],
    "md":         LANG_ALIASES["markdown"],
    "cs":         LANG_ALIASES["c#"],
    "csharp":     LANG_ALIASES["c#"],
    "kt":         LANG_ALIASES["kotlin"],
    "gql":        LANG_ALIASES["graphql"],
    "tf":         LANG_ALIASES["terraform"],
    "ex":         LANG_ALIASES["elixir"],
})


def resolve_ext_filter(raw: str) -> set[str]:
    """将用户输入的 --ext 参数解析为扩展名集合，支持语言别名和直接扩展名混用。

    例: "cpp,py,json" → {".cpp",".cc",".cxx",".hpp",".py",".pyw",".json"}
    """
    result = set()
    for token in raw.split(","):
        token = token.strip().lower().lstrip(".")
        # 先查语言别名
        if token in LANG_ALIASES:
            result |= LANG_ALIASES[token]
        else:
            # 当作扩展名
            result.add("." + token)
    return result


# ── Token 计数 ───────────────────────────────────────────────────────────────

def make_encoder(model: str):
    """返回 (encode_fn, model_name) 元组"""
    if not TIKTOKEN_AVAILABLE:
        return None, "char-estimate"
    try:
        enc = tiktoken.get_encoding(model)
        return enc.encode, model
    except Exception:
        try:
            enc = tiktoken.encoding_for_model(model)
            return enc.encode, model
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
            return enc.encode, "cl100k_base (fallback)"


def count_tokens(text: str, encode_fn) -> int:
    if encode_fn is None:
        # 粗略估算：英文约 4 字符/token，中文约 1.5 字符/token
        return max(1, len(text) // 4)
    try:
        return len(encode_fn(text))
    except Exception:
        return max(1, len(text) // 4)


# ── .gitignore 解析（简版）───────────────────────────────────────────────────

def load_gitignore_patterns(root: Path):
    """读取 .gitignore，返回需要忽略的相对路径片段集合（简单版）"""
    patterns = set()
    gi = root / ".gitignore"
    if gi.exists():
        for line in gi.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # 去掉开头的 /，只保留名字部分用于简单匹配
                patterns.add(line.lstrip("/").rstrip("/"))
    return patterns


def is_gitignored(path: Path, root: Path, patterns: set) -> bool:
    parts = set(path.relative_to(root).parts)
    return bool(parts & patterns)


# ── 文件遍历 ──────────────────────────────────────────────────────────────────

def iter_files(root: Path, exts_filter: set | None, use_gitignore: bool,
               exclude_dirs: set | None = None):
    gi_patterns = load_gitignore_patterns(root) if use_gitignore else set()

    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)

        # 原地裁剪：跳过忽略目录
        dirnames[:] = [
            d for d in dirnames
            if d not in IGNORE_DIRS
            and (not exclude_dirs or d not in exclude_dirs)
            and (not use_gitignore or not is_gitignored(dirpath / d, root, gi_patterns))
        ]

        for fname in filenames:
            fpath = dirpath / fname
            suffix = fpath.suffix.lower()

            # 跳过忽略扩展名
            if suffix in IGNORE_EXTENSIONS:
                continue
            # 扩展名过滤
            if exts_filter and suffix not in exts_filter:
                continue
            # gitignore
            if use_gitignore and is_gitignored(fpath, root, gi_patterns):
                continue

            yield fpath


# ── 格式化工具 ────────────────────────────────────────────────────────────────

def human(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def human_size(n: int) -> str:
    """将字节数转换为人类可读的格式"""
    if n >= 1_073_741_824:
        return f"{n/1_073_741_824:.2f} GB"
    if n >= 1_048_576:
        return f"{n/1_048_576:.2f} MB"
    if n >= 1_024:
        return f"{n/1_024:.1f} KB"
    return f"{n} B"


def bar(frac: float, width: int = 20) -> str:
    filled = int(frac * width)
    return "█" * filled + "░" * (width - filled)


# ── 主函数 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="统计代码仓库的 token 数量",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=".", help="仓库根目录（默认当前目录）")
    parser.add_argument("--model", default="cl100k_base",
                        help="tiktoken 模型名（默认 cl100k_base）")
    parser.add_argument("--top", type=int, default=10,
                        help="显示 token 最多的前 N 个文件（默认 10）")
    parser.add_argument("--ext", default=None,
                        help="按语言或扩展名过滤，逗号分隔，如 cpp,py,json（cpp 自动包含 .cpp/.cc/.cxx/.hpp）")
    parser.add_argument("--exclude", default=None,
                        help="排除指定目录，逗号分隔，如 tests,third_party,build")
    parser.add_argument("--no-ignore", action="store_true",
                        help="不使用 .gitignore 过滤")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"错误：路径不存在或不是目录：{root}")
        sys.exit(1)

    exts_filter = None
    if args.ext:
        exts_filter = resolve_ext_filter(args.ext)

    exclude_dirs = None
    if args.exclude:
        exclude_dirs = {d.strip() for d in args.exclude.split(",")}

    encode_fn, model_name = make_encoder(args.model)
    if not TIKTOKEN_AVAILABLE:
        print("⚠️  未找到 tiktoken，使用字符估算（安装：pip install tiktoken）\n")

    print(f"📂 仓库路径 : {root}")
    print(f"🔤 Tokenizer: {model_name}")
    if exts_filter:
        print(f"📎 统计扩展名: {', '.join(sorted(exts_filter))}")
    if exclude_dirs:
        print(f"🚫 排除目录 : {', '.join(sorted(exclude_dirs))}")
    print(f"{'─' * 60}")

    # 统计
    file_stats: list[tuple[int, int, int, Path]] = []  # (tokens, lines, size, path)
    lang_tokens: dict[str, int] = defaultdict(int)
    lang_lines: dict[str, int] = defaultdict(int)
    lang_size: dict[str, int] = defaultdict(int)
    lang_files: dict[str, int] = defaultdict(int)
    total_tokens = 0
    total_lines = 0
    total_size = 0
    total_files = 0
    skipped = 0

    for fpath in iter_files(root, exts_filter, not args.no_ignore, exclude_dirs):
        try:
            text = fpath.read_text(errors="replace")
        except Exception:
            skipped += 1
            continue

        lines = text.count("\n") + 1
        tokens = count_tokens(text, encode_fn)
        size = fpath.stat().st_size
        rel = fpath.relative_to(root)
        lang = EXT_LANG.get(fpath.suffix.lower(), fpath.suffix or "other")

        file_stats.append((tokens, lines, size, rel))
        lang_tokens[lang] += tokens
        lang_lines[lang] += lines
        lang_size[lang] += size
        lang_files[lang] += 1
        total_tokens += tokens
        total_lines += lines
        total_size += size
        total_files += 1

        # 进度提示（每 200 文件一次）
        if total_files % 200 == 0:
            print(f"  已扫描 {total_files} 个文件…", end="\r")

    print(" " * 50, end="\r")  # 清除进度行

    if total_files == 0:
        print("未找到任何文件。")
        sys.exit(0)

    # ── 总览 ──
    print(f"\n{'═' * 60}")
    print(f"  总 Token 数  : {human(total_tokens):>10}  ({total_tokens:,})")
    print(f"  总行数       : {human(total_lines):>10}  ({total_lines:,})")
    print(f"  总大小       : {human_size(total_size):>10}  ({total_size:,} bytes)")
    print(f"  文件数       : {total_files:,}")
    if skipped:
        print(f"  跳过（读取失败）: {skipped}")
    print(f"{'═' * 60}")

    # ── 按语言汇总 ──
    print(f"\n{'─' * 84}")
    print(f"  {'语言':<18} {'文件数':>6}  {'行数':>10}  {'大小':>10}  {'Token 数':>10}  {'占比'}")
    print(f"{'─' * 84}")
    for lang, tok in sorted(lang_tokens.items(), key=lambda x: -x[1]):
        pct = tok / total_tokens
        print(f"  {lang:<18} {lang_files[lang]:>6}  {human(lang_lines[lang]):>10}  "
              f"{human_size(lang_size[lang]):>10}  {human(tok):>10}  {bar(pct)} {pct*100:5.1f}%")

    # ── Top N 文件 ──
    file_stats.sort(reverse=True)
    top_n = min(args.top, len(file_stats))
    print(f"\n{'─' * 84}")
    print(f"  Token 最多的 {top_n} 个文件")
    print(f"{'─' * 84}")
    for i, (tok, lines, size, rel) in enumerate(file_stats[:top_n], 1):
        pct = tok / total_tokens
        print(f"  {i:>2}. {str(rel):<40}  {human_size(size):>8}  {human(lines):>6} lines  {human(tok):>7} tokens  ({pct*100:.1f}%)")

    print(f"\n✅ 扫描完成\n")


if __name__ == "__main__":
    main()
