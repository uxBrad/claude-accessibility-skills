# wcag-images

Audits every image on a page for alternative text quality and generates a contact sheet showing each image with its alt text displayed below, color-coded by result.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.1.1 Non-text Content | A | All non-text content has a text alternative serving the equivalent purpose |

## What it produces

- **Desktop contact sheet** and **Mobile contact sheet**
- Grid of image thumbnails, one per cell, with alt text and status shown below
- Cell border color indicates result:
  - **Green** — good descriptive alt text (pass)
  - **Amber** — `alt=""` (decorative — needs manual verification)
  - **Red** — missing alt attribute entirely (WCAG 1.1.1 fail)
  - **Orange** — filename or generic-only alt text (needs improvement)

## Alt text classification

| Status | Meaning | Example |
|--------|---------|---------|
| `good` | Descriptive alt present | `alt="Team members at the 2024 conference"` |
| `decorative` | Empty alt set explicitly | `alt=""` |
| `missing` | No alt attribute at all | `<img src="hero.jpg">` |
| `filename` | Alt text is a filename | `alt="hero_image_v3.jpg"` |
| `generic` | Only generic words | `alt="Photo"`, `alt="Image"`, `alt="Icon"` |

## Example prompts

- *"Check the alt text on all images at https://example.com"*
- *"Find any images missing alt attributes on this page"*
- *"Run a WCAG 1.1.1 image audit on localhost:3000"*
- *"Show me a contact sheet of all images and their alt text"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture_images.py` | Playwright: collects image metadata and saves crops |
| `scripts/image_sheet.py` | Assembles crops into a contact sheet grid |

### capture_images.py CLI

```bash
python scripts/capture_images.py \
  --url        https://example.com \
  --output-dir path/to/crops/ \
  --viewport   desktop
```

Outputs: `img_000.png`, `img_001.png`, ..., `image_data.json`

### image_sheet.py CLI

```bash
python scripts/image_sheet.py \
  --crops-dir path/to/crops/ \
  --data      path/to/crops/image_data.json \
  --output    path/to/image_sheet.png \
  --label     "Desktop (1280px)"
```

### image_data.json format

```json
[
  {
    "index": 0,
    "tag": "img",
    "alt": null,
    "alt_missing": true,
    "src_short": "hero.jpg",
    "x": 0, "y": 80, "w": 1280, "h": 500,
    "status": "missing",
    "crop_file": "img_000.png"
  }
]
```

## Limitations

- CSS background images are not captured (use DevTools to audit separately)
- Lazy-loaded images that haven't entered the viewport may be missed — scroll the page before auditing or use `page.wait_for_timeout` after load
- SVG images inline in HTML are partially supported via `role="img"` detection
