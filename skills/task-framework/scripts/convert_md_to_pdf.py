#!/usr/bin/env python3
"""
Convert a large Chinese markdown file to PDF without pandoc.

Pandoc fails on markdown files with --- horizontal rules (YAML parse exception)
and times out on files >500KB of Chinese text. This script uses a custom
markdown-to-HTML renderer + weasyprint as a drop-in replacement.

Usage:
    uv run scripts/convert_md_to_pdf.py input.md output.pdf
    uv run scripts/convert_md_to_pdf.py input.md output.pdf --title "文档标题"
"""

import re
import subprocess
import sys
from pathlib import Path


def md_to_html(md_text: str) -> str:
    """Convert markdown to HTML with Chinese-friendly rendering."""
    lines = md_text.split('\n')
    html_parts = []
    in_code_block = False
    in_table = False
    table_rows = []
    in_list = False
    list_type = None
    list_items = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        html_parts.append('<table>\n')
        for i, row in enumerate(table_rows):
            tag = 'th' if i == 0 else 'td'
            html_parts.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in row) + '</tr>\n')
        html_parts.append('</table>\n')
        table_rows = []
        in_table = False

    def flush_list():
        nonlocal in_list, list_type, list_items
        if not list_items:
            return
        html_parts.append(f'<{list_type}>\n')
        for item in list_items:
            html_parts.append(f'<li>{item}</li>\n')
        html_parts.append(f'</{list_type}>\n')
        list_items = []
        in_list = False
        list_type = None

    def fmt(text):
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.strip().startswith('```'):
            flush_table()
            flush_list()
            if in_code_block:
                in_code_block = False
                html_parts.append('</code></pre>\n')
            else:
                in_code_block = True
                html_parts.append(f'<pre><code class="language-{line.strip()[3:]}">\n')
            i += 1
            continue

        if in_code_block:
            html_parts.append(line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '\n')
            i += 1
            continue

        if line.strip() == '---' and not in_table:
            flush_table()
            flush_list()
            html_parts.append('<hr>\n')
            i += 1
            continue

        h_match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if h_match:
            flush_table()
            flush_list()
            level = len(h_match.group(1))
            text = h_match.group(2)
            html_parts.append(f'<h{level}>{text}</h{level}>\n')
            i += 1
            continue

        if line.startswith('> '):
            flush_table()
            flush_list()
            html_parts.append(f'<blockquote><p>{line[2:]}</p></blockquote>\n')
            i += 1
            continue

        if '|' in line and line.strip().startswith('|'):
            flush_list()
            in_table = True
            if re.match(r'^\|[\s\-:]+\|', line):
                i += 1
                continue
            cells = [fmt(c.strip()) for c in line.strip().split('|')[1:-1]]
            table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        ul_match = re.match(r'^[\s]*[-*]\s+(.+)$', line)
        if ul_match:
            flush_table()
            if list_type != 'ul':
                flush_list()
                in_list, list_type = True, 'ul'
            list_items.append(fmt(ul_match.group(1)))
            i += 1
            continue

        ol_match = re.match(r'^[\s]*(\d+)\.\s+(.+)$', line)
        if ol_match:
            flush_table()
            if list_type != 'ol':
                flush_list()
                in_list, list_type = True, 'ol'
            list_items.append(fmt(ol_match.group(2)))
            i += 1
            continue

        if line.strip() == '' and in_list:
            i += 1
            continue

        if in_list and line.strip() and not re.match(r'^[\s*\-*\d]', line) and not line.startswith('|'):
            flush_list()

        if line.strip():
            flush_list()
            flush_table()
            html_parts.append(f'<p>{fmt(line)}</p>\n')
        i += 1

    flush_table()
    flush_list()
    if in_code_block:
        html_parts.append('</code></pre>\n')

    return ''.join(html_parts)


def build_html(md_content: str, title: str = "Document") -> str:
    """Wrap markdown HTML in a full document with print CSS."""
    body = md_to_html(md_content)
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 1.8cm; }}
  body {{ font-family: 'WenQuanYi Zen Hei', 'Noto Sans CJK SC', sans-serif;
         font-size: 10pt; line-height: 1.7; color: #1a1a1a; }}
  h1 {{ font-size: 20pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 6px; }}
  h2 {{ font-size: 15pt; color: #2a5a8c; margin-top: 28px; border-bottom: 1px solid #ccc; padding-bottom: 4px; page-break-after: avoid; }}
  h3 {{ font-size: 12pt; color: #3a7abc; margin-top: 18px; page-break-after: avoid; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; page-break-inside: avoid; }}
  th, td {{ border: 1px solid #bbb; padding: 4px 8px; text-align: left; }}
  th {{ background-color: #e8f0f8; }}
  code {{ background: #f4f4f4; padding: 1px 4px; border-radius: 2px; font-size: 9pt; }}
  pre {{ background: #f8f8f8; border: 1px solid #ddd; padding: 10px; font-size: 9pt; overflow-x: auto; }}
  blockquote {{ border-left: 4px solid #1a3a5c; margin: 10px 0; padding: 5px 14px; background: #f8faff; }}
  hr {{ border: none; border-top: 2px solid #1a3a5c; margin: 24px 0; }}
  ul, ol {{ margin: 6px 0; padding-left: 24px; }}
  p {{ margin: 6px 0; }}
</style>
</head>
<body>
{body}
</body>
</html>'''


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.pdf> [--title \"...\"]", file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    pdf_path = Path(sys.argv[2])
    title = "Document"

    if '--title' in sys.argv:
        idx = sys.argv.index('--title')
        if idx + 1 < len(sys.argv):
            title = sys.argv[idx + 1]

    if not md_path.exists():
        print(f"Error: input file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading: {md_path}")
    content = md_path.read_text(encoding='utf-8')

    print(f"Converting markdown to HTML ({len(content):,} chars)...")
    html = build_html(content, title)

    html_path = pdf_path.with_suffix('.html')
    html_path.write_text(html, encoding='utf-8')

    print(f"Converting HTML to PDF with weasyprint...")
    result = subprocess.run(
        ["weasyprint", str(html_path), str(pdf_path)],
        capture_output=True, text=True, timeout=300
    )

    html_path.unlink()

    if result.returncode != 0:
        print(f"weasyprint failed: {result.stderr[:500]}", file=sys.stderr)
        sys.exit(1)

    print(f"PDF written: {pdf_path} ({pdf_path.stat().st_size:,} bytes)")


if __name__ == '__main__':
    main()
