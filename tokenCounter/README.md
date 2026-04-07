# tokenCounter

Code repository token counter. Scans a codebase and reports token usage by file and language — useful for estimating LLM context consumption.

## Quick Start

```bash
# Install as global command (from Knivo root)
pip install -e .

# Run
tokens .                    # current directory
tokens /path/to/repo        # specific repo
tokens dir1 dir2            # multiple directories
```

## Usage

```
tokens [path ...] [OPTIONS]
```

| Option | Description |
|---|---|
| `path ...` | One or more repository directories (default: `.`) |
| `--model NAME` | Tokenizer model (default: `cl100k_base`, compatible with GPT-4 / Claude) |
| `--top N` | Show top N files by token count (default: 10) |
| `--ext EXTS` | Filter by language or extension, comma-separated (e.g. `cpp,py,json`) |
| `--exclude DIRS` | Exclude directories, comma-separated (e.g. `tests,third_party,build`) |
| `--group GROUPS` | Group languages for display (e.g. `"Shader:GLSL,HLSL,UE Shader"`) |
| `--no-ignore` | Don't apply `.gitignore` rules |

### Examples

```bash
# Count tokens for a Python + JS project
tokens myproject/ --ext py,js

# Show top 20 largest files
tokens . --top 20

# Exclude test and build directories
tokens . --exclude tests,build,dist

# Count everything (ignore .gitignore)
tokens . --no-ignore

# Scan multiple directories at once
tokens engine/src game/src plugins/

# Filter all shader files (GLSL + HLSL + UE Shader)
tokens /ue-project --ext shader

# Group languages into a single row
tokens . --group "Shader:GLSL,HLSL,UE Shader" "Web:HTML,CSS,JavaScript"
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
| `glsl` | `.glsl`, `.vert`, `.frag`, `.geom`, `.tesc`, `.tese`, `.comp`, `.glslv`, `.glslf` |
| `hlsl` | `.hlsl`, `.hlsli`, `.fx`, `.fxh` |
| `ue-shader` / `usf` / `ush` | `.usf`, `.ush` |
| `shader` | All GLSL + HLSL + UE Shader extensions |

And many more (Go, Rust, Java, Kotlin, Swift, C#, Ruby, PHP, SQL, Terraform, etc.)

## Composite Directories

Pass multiple paths to scan them all in one report:

```bash
tokens engine/shaders game/shaders
```

When multiple directories are given, file paths in the output are prefixed with the directory name to distinguish their origin.

## Language Grouping

Use `--group` to merge multiple languages into one row in the summary table:

```bash
tokens . --group "Shader:GLSL,HLSL,UE Shader"
```

Format: `"GroupName:Lang1,Lang2,..."` — language names must match the labels in the summary (e.g. `GLSL`, `C++`, `Python`).

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
