# Generating Output Documents (Merged Markdown + PDF)

When a project task involves converting multiple source documents (DOCX, old-format DOC, XLSX) and merging them into a consolidated output, follow this pattern.

## Typical Use Cases

- Policy document collection from multiple government sources
- Competitor analysis report from multiple vendor documents
- Research paper compilation from multiple papers/drafts
- Any batch of Chinese-language office documents needing a unified markdown output

## Tools

| Tool | Purpose | Install |
|------|---------|---------|
| `pandoc` | .docx → markdown | System package |
| `olefile` | Extract text from old .doc (OLE2) | `uv pip install olefile` |
| `openpyxl` | .xlsx → markdown tables | `uv pip install openpyxl` |
| `weasyprint` | markdown → PDF | `uv pip install weasyprint` |

**Note:** pandoc does NOT support old-format .doc — only .docx. libreoffice is usually not available on servers. olefile extracts readable text directly from the OLE2 binary stream.

## Pipeline

### Phase 1 — Convert Source Files to Markdown

Write a Python script (not inline heredocs — quoting issues guaranteed) that:

1. **.docx → markdown** via pandoc subprocess:
   ```python
   subprocess.run(["pandoc", str(src), "-f", "docx", "-t", "markdown",
                    "--wrap=none"], capture_output=True, text=True, timeout=120)
   ```

2. **.doc → text** via olefile:
   ```python
   ole = olefile.OleFileIO(src_path)
   data = ole.openstream('WordDocument').read()
   # Scan binary data for readable text sequences
   # Filter: ASCII printable 0x20-0x7e, newlines, UTF-8 sequences
   ole.close()
   ```

3. **.xlsx → markdown table** via openpyxl:
   ```python
   wb = openpyxl.load_workbook(src_path, data_only=True)
   for sheet_name in wb.sheetnames:
       ws = wb[sheet_name]
       # Find header row, build markdown table (header + align + rows)
   ```

**Output:** Each source file → `docs/policy-<sanitized-name>.md` with H1 = original filename, quote block indicating source file, and body text.

**Logging:** Each conversion writes to `logs/convert-<name>.log` with pandoc stdout/stderr and exit code.

### Phase 2 — Merge Into Comprehensive Document

Organize by region/theme with the structure:
```
## [[Region]]
### [Document Name]
[full text body]
```

1. Define document groups with descriptions
2. For each group, read the markdown from docs/
3. Strip auto-generated duplicate headers (h1 + source line)
4. Insert under the appropriate h2 section header
5. Generate table of contents

### Phase 3 — Generate Summary + Time Annotations

When the source documents are policies or regulatory filings, extract and annotate time metadata:

- **Policy validity periods** — title-embedded ranges (e.g. "2025—2027年")
- **Milestone targets** — "到2027年" goals (bed counts, coverage rates, etc.)
- **Effective/enforcement dates** — "自...起施行" or "印发之日起"
- **Application deadlines** — "于...前报送" or "申报截止"
- **Funding/subsidy cutoffs** — per-item expiration dates
- **Project execution periods** — "实施周期不超过3年" clauses

Add a `> **发文：** ... ｜ **文号：** ... ｜ **目标节点：** ...` line after each h3 policy heading in the merged document. See `references/policy-time-metadata.md` for the full category breakdown.

### Phase 4 — Generate Summary + PDF

1. Write `summary.md` with: overview, per-group summary tables, cross-cutting theme analysis, key data points, and the time metadata section.

2. Convert to PDF via markdown → HTML → weasyprint. **CRITICAL: Pandoc's default HTML5 output does NOT produce a full HTML document.** Without `--standalone` / `-s`, pandoc outputs only body content — no `<html>`, `<head>`, or `<style>` tags. CSS injection via `</head>` replacement **fails silently**, and weasyprint falls back to a font without CJK glyphs → garbled PDF.

   **The Fix — Always wrap pandoc output in a complete HTML document:**

   ```python
   import subprocess
   from pathlib import Path

   md_path = Path("summary.md")
   pdf_path = Path("summary.pdf")

   # Step 1: Get body HTML from pandoc (capture stdout, no -o flag)
   result = subprocess.run(
       ["pandoc", str(md_path), "-f", "markdown", "-t", "html5",
        "--wrap=none", "--quiet"],
       capture_output=True, text=True, timeout=30
   )
   body_html = result.stdout

   # Step 2: Wrap in full HTML document with CSS
   full_html = f"""<!DOCTYPE html>
   <html lang="zh-CN">
   <head>
   <meta charset="utf-8">
   <title>{title}</title>
   <style>
     @page {{ size: A4; margin: 2cm; }}
     body {{ font-family: 'WenQuanYi Zen Hei', 'Noto Sans CJK SC', sans-serif;
            font-size: 11pt; line-height: 1.7; }}
     h1 {{ font-size: 20pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c; }}
     h2 {{ font-size: 16pt; color: #2a5a8c; margin-top: 24px; }}
     table {{ border-collapse: collapse; width: 100%; }}
     th, td {{ border: 1px solid #aaa; padding: 6px 10px; }}
     th {{ background-color: #e8f0f8; }}
   </style>
   </head>
   <body>
   {body_html}
   </body>
   </html>"""

   # Step 3: Write temp HTML and convert
   html_path = pdf_path.with_suffix('.html')
   html_path.write_text(full_html, encoding='utf-8')
   subprocess.run(["weasyprint", str(html_path), str(pdf_path)], timeout=60)
   html_path.unlink()
   ```

   **Alternative — Python markdown renderer (for large files):** When the merged markdown exceeds 500KB / 4000+ lines, pandoc may timeout. Use `scripts/convert_md_to_pdf.py` instead:
   ```bash
   uv run scripts/convert_md_to_pdf.py <input.md> <output.pdf>
   ```
   This script has its own markdown→HTML renderer that handles Chinese headings, pipe tables, blockquotes, lists, code blocks, and `---` horizontal rules without pandoc's YAML issue.

3. **Font Requirements:** Ensure a CJK font is installed (e.g., WenQuanYi Zen Hei, Noto Sans CJK). The CSS font-family MUST list an installed CJK font first. Do NOT use:
   - `Noto Sans CJK SC` (not installed)
   - `Source Han Sans SC` (not installed)
   - `SimSun` (not installed)
   - `Microsoft YaHei` (not installed)
   These fail silently and produce garbled output.

4. **Keep both .md and .pdf.** Delete the intermediate .html.

### Phase 5 — Verify PDF Output

```bash
pdftotext output.pdf - | head -20
# Expected: clean Chinese like "政策文件汇编 — 摘要"
# Bad: garbled like "æ”¿ç–æ–‡ä»¶æ±‡ç¼–" (font or CSS wrapping issue)
```

## Pitfalls

- **Chinese vs English `政策`/`policy` prefix mismatch** — the conversion script saves files as `policy-<name>.md` but the merge script may look for `政策-<name>.md`. The `policy-` prefix (English) is correct — align all keys with actual filenames.
- **.doc binary extraction is lossy** — olefile extracts raw text from the WordDocument stream, which may include metadata, lose formatting, or produce fragments. Always note in the merged doc: "从旧格式 .doc 提取，格式可能不完整".
- **Pandoc timeout** — large files (>500KB) can take >30s via stdin. Set timeout to at least 120s or use `scripts/convert_md_to_pdf.py`.
- **Markdown anchor links** — Chinese characters in TOC anchors may not work in all renderers. For pandoc compatibility, ASCII-only anchors are safer.
- **Memory pressure** — 16+ documents merged can exceed 500K chars. Keep the summary small; the full merged file is for reference.
- **`---` horizontal rule = YAML parse exception** — pandoc interprets `---` lines as YAML metadata block delimiters, even with `-f markdown`. Replace with `<hr>` or use the Python renderer script.
