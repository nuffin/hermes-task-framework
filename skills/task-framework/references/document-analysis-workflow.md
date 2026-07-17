# Document Analysis Workflow (PPT / PDF)

When a project task involves analyzing a document (PPTX, PDF, DOCX), follow this pattern to extract content and produce structured docs.

## Prerequisites

Create a project venv if one doesn't exist:

```bash
cd <project-root>
uv venv
source .venv/bin/activate
uv pip install python-pptx  # for PPTX files
# or for PDF: uv pip install pymupdf  (marker-pdf for complex PDFs)
```

## Step 1 — Write an extraction script

Do NOT use inline heredocs for Python scripts — shell quoting issues (nested quotes, `\n`, f-strings) are guaranteed to fail. Write a `.py` file under the task's `scripts/` dir instead.

Example (`scripts/extract_ppt.py`):

```python
#!/usr/bin/env python3
"""Extract all text and structure from a PPT."""

from pptx import Presentation
import os

# Resolve the PPT path relative to the script
pptx_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "S-filename.pptx"
)

prs = Presentation(pptx_path)
print(f"Total slides: {len(prs.slides)}")

for i, slide in enumerate(prs.slides, 1):
    print(f"\n{'='*80}")
    print(f"SLIDE {i}")
    print(f"{'='*80}")

    for shape in slide.shapes:
        text = ""
        has_image = False

        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                t = para.text.strip()
                if t:
                    text += t + "\n"

        if shape.shape_type == 13:  # Picture
            has_image = True

        if text.strip() or has_image:
            tag = " [IMAGE]" if has_image else ""
            print(f"\n  [{shape.name}]{tag}")
            if text.strip():
                for line in text.strip().split("\n"):
                    print(f"    {line}")
```

## Step 2 — Save raw output to logs/

```bash
cd <project-root>
source .venv/bin/activate
ts=$(date '+%Y%m%d-%H%M%S')
python3 tasks/*.<task-name>/scripts/extract_ppt.py \
  > "tasks/*.<task-name>/logs/output.${ts}.log" 2>&1
```

## Step 3 — Analyze and write structured docs to docs/

Organize findings into focused markdown files under `docs/`. Each file covers one domain:

| File | Content |
|------|---------|
| `docs/01-project-background.md` | Background, policy, market analysis |
| `docs/02-project-plan.md` | Architecture, technical solution, product design |
| `docs/03-cost-and-roadmap.md` | Budget, timeline, investment analysis |
| `docs/04-cooperation-resources.md` | Partners, team, training resources |
| `docs/05-benefits-and-outlook.md` | Economic/social benefits, forecasts |
| `docs/06-product-requirements-summary.md` | PRD-style consolidated summary |

Number prefix (`01-`, `02-`...) ensures chronological ordering in `ls` and file explorers. Use meaningful topic names, not `slide-notes.md`.

## Pitfalls

- **Heredoc quoting fails** — Python f-strings with `\n`, nested quotes, and shell variable expansion in heredoc bodies all break. Always write extraction scripts to a `.py` file.
- **python-pptx cannot extract embedded images' text content** — charts in image-only slides yield `[IMAGE]` with no text. Note these in docs as "diagram — see PPT directly."
- **Chinese text truncation** — `sed -n '3p'` on README.md with Chinese characters may truncate mid-character if `head -c` cuts at the wrong byte boundary. Use `head -c 60 | head -n 1` to avoid splitting multi-byte chars.
- **Blank lines after `## Status`** — TASK.md format has `## Status` → blank line → status value. `grep -A1` picks up the blank line; use `grep -A2` + `tail -1` to get the actual status. Both code snippets and pitfall text must use `-A2`.
