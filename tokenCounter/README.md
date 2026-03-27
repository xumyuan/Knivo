# tokenCounter

Code repository token counter. Scans a codebase and reports token usage by file and language — useful for estimating LLM context consumption.

## Quick Start

```bash
# 1. Install dependency
pip install tiktoken

# 2. Run
python tokenCounter/count_tokens.py .                # current directory
python tokenCounter/count_tokens.py /path/to/repo     # specific repo
```

## Usage

```
python tokenCounter/count_tokens.py [OPTIONS] <path>
```

| Option | Description |
|---|---|
| `path` | Repository root directory (default: `.`) |
| `--model NAME` | Tokenizer model (default: `cl100k_base`, compatible with GPT-4 / Claude) |
| `--top N` | Show top N files by token count (default: 10) |
| `--ext EXTS` | Filter by language or extension, comma-separated (e.g. `cpp,py,json`) |
| `--exclude DIRS` | Exclude directories, comma-separated (e.g. `tests,third_party,build`) |
| `--no-ignore` | Don't apply `.gitignore` rules |

### Examples

```bash
# Count tokens for a Python + JS project
python tokenCounter/count_tokens.py myproject/ --ext py,js

# Show top 20 largest files
python tokenCounter/count_tokens.py . --top 20

# Exclude test and build directories
python tokenCounter/count_tokens.py . --exclude tests,build,dist

# Count everything (ignore .gitignore)
python tokenCounter/count_tokens.py . --no-ignore
```

## Language Support

The `--ext` flag supports language aliases that expand to all relevant extensions:

| Alias | Extensions |
|---|---|
| `cpp` / `c++` | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hxx`, `.inl`, `.ipp`, `.tpp`, `.tcc` |
| `py` | `.py`, `.pyw` |
| `js` | `.js`, `.mjs`, `.cjs`, `.jsx` |
| `ts` | `.ts`, `.tsx` |
| `sh` | `.sh`, `.bash`, `.zsh` |
| `css` | `.css`, `.scss`, `.sass`, `.less` |
| `md` | `.md`, `.mdx` |

And many more (Go, Rust, Java, Kotlin, Swift, C#, Ruby, PHP, SQL, Terraform, etc.)

## Output

The tool prints:

1. **Summary** — total tokens, lines, file size, and file count
2. **By-language breakdown** — tokens, lines, size, and percentage per language with a visual bar chart
3. **Top N files** — the largest files by token count

Example output:

```
📂 仓库路径 : /path/to/repo
🔤 Tokenizer: cl100k_base
────────────────────────────────────────────────────────────

════════════════════════════════════════════════════════════
  总 Token 数  :     45.2K  (45,203)
  总行数       :      3.1K  (3,102)
  总大小       :  178.5 KB  (182,784 bytes)
  文件数       : 42
════════════════════════════════════════════════════════════
```

## Auto-Ignored

The following are automatically excluded:

- **Directories**: `.git`, `node_modules`, `__pycache__`, `venv`, `dist`, `build`, `.idea`, `.vscode`, etc.
- **Extensions**: images, videos, archives, binaries, fonts, lock files, minified assets, etc.
- **`.gitignore` patterns**: respected by default (disable with `--no-ignore`)

## Fallback Mode

If `tiktoken` is not installed, the tool falls back to a character-based estimate (~4 chars/token). Install tiktoken for accurate counts:

```bash
pip install tiktoken
```

## Requirements

- Python 3.10+
- tiktoken (recommended)
