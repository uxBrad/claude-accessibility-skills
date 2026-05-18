# wcag-color-contrast

Audits text color contrast ratios across a webpage and generates annotated screenshots highlighting elements that fail WCAG requirements.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.4.3 Contrast (Minimum) | AA | Normal text 4.5:1 / Large text 3:1 |
| 1.4.6 Contrast (Enhanced) | AAA | Normal text 7:1 / Large text 4.5:1 |

**Large text** is defined as 18pt (24px) or larger, or 14pt (18.67px) bold or heavier.

## Example output — jecture.co homepage

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop contrast audit](../../examples/jecture-co/color-contrast/desktop_contrast.png) | ![Mobile contrast audit](../../examples/jecture-co/color-contrast/mobile_contrast.png) |

**What this revealed on jecture.co:**
- 41 text elements scanned — 0 failures, strong overall contrast
- 33/41 pass AAA (7:1 or 4.5:1 large) — excellent result
- 8/41 pass AA only — these are the grey body text elements (rgb 75,85,99 on white = ~4.6:1) and blue badge text, just clearing the AA bar but not AAA
- The dark section (white on navy #111827) scores very high contrast

## What it produces

- **Desktop annotated screenshot** and **Mobile annotated screenshot**
- Red outlined badge on every failing text element showing its actual contrast ratio
- Optional: subtle colored borders on passing elements (`--show-passes` flag)
- Console output listing the worst failures sorted by ratio
- Summary report with totals and recommended color fixes

## Example prompts

- *"Check the color contrast on https://example.com"*
- *"Find all text that fails WCAG contrast requirements on this page"*
- *"Run a contrast audit on localhost:3000 — desktop and mobile"*
- *"Is the text readable? Check WCAG 1.4.3"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture.py` | Full-page screenshot at desktop or mobile viewport |
| `scripts/contrast_overlay.py` | Calculates WCAG contrast ratios and draws annotated overlay |

### contrast_overlay.py CLI

```bash
python scripts/contrast_overlay.py \
  --screenshot path/to/screenshot.png \
  --elements   path/to/text_elements.json \
  --output     path/to/contrast_result.png \
  --label      "Desktop (1280px)"

# Also show passing elements (for full picture):
python scripts/contrast_overlay.py ... --show-passes
```

## Limitations

- **Background images / gradients** — the script traverses the DOM to find solid background colors. Elements over images or gradients will show the nearest solid parent background, which may not be accurate. These should be flagged for manual review.
- **Dynamic states** — contrast in hover, focus, or active states requires a separate pass.
- **Translucent/alpha text** — alpha channel in text color is not factored into the contrast calculation.
- **Canvas and SVG text** — not captured by the DOM walker; check these separately.