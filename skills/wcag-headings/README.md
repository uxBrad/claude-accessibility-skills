# wcag-headings

Audits heading structure and generates two visual outputs: an annotated screenshot with every heading labeled by level, and a standalone outline diagram showing the full heading tree.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.3.1 Info and Relationships | A | Structure conveyed through presentation is programmatically determined |
| 2.4.6 Headings and Labels | AA | Headings describe the topic or purpose of content |

## What it produces

- **Annotated screenshot** — colored level badge (H1–H6) beside each heading, red underline on structural issues
- **Outline diagram** — standalone dark-background PNG showing the indented heading tree with issue markers

**Color scheme:**
- H1 = purple · H2 = blue · H3 = teal · H4 = green · H5 = amber · H6 = orange
- Red highlights = structural issues (skipped level, multiple H1s, empty heading)

## Issues detected

- Skipped heading levels (H1 → H3 with no H2 in between)
- Multiple H1 elements on a single page
- Empty or whitespace-only headings
- Missing H1 entirely

## Example prompts

- *"Audit the heading structure of https://example.com"*
- *"Check if the headings are in the right order on this page"*
- *"Find any skipped heading levels on localhost:3000"*
- *"Show me the page outline for this site"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture.py` | Full-page screenshot via Playwright |
| `scripts/heading_overlay.py` | Annotates screenshot with heading level badges |
| `scripts/heading_tree.py` | Renders standalone heading outline diagram |

### heading_overlay.py CLI

```bash
python scripts/heading_overlay.py \
  --screenshot path/to/screenshot.png \
  --headings   path/to/headings.json \
  --output     path/to/output.png \
  --label      "Desktop (1280px)"
```

### heading_tree.py CLI

```bash
python scripts/heading_tree.py \
  --headings path/to/headings.json \
  --output   path/to/outline.png \
  --url      https://example.com
```

### headings.json format

```json
[
  { "index": 0, "level": 1, "text": "Page Title", "tag": "h1", "x": 40, "y": 120, "w": 800, "h": 60 },
  { "index": 1, "level": 3, "text": "Subsection", "tag": "h3", "x": 40, "y": 340, "w": 600, "h": 40 }
]
```

The second entry above would be flagged — H1 jumping directly to H3 skips a level.
