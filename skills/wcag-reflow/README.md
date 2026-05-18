# wcag-reflow

Tests whether page content reflows cleanly at 320px width (equivalent to viewing at 400% zoom on a 1280px screen) without requiring horizontal scrolling. Generates a side-by-side comparison of full-width vs. narrow viewport screenshots.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.4.10 Reflow | AA | Content can be presented without loss of information or functionality without scrolling in two dimensions — except for content that requires 2D layout (data tables, maps, toolbars) |

## What it produces

- **Reflow comparison** — side-by-side PNG showing desktop (1280px) and narrow (320px) views
- Column header turns green (pass) or red (fail — horizontal scroll detected)
- Footer lists any overflowing elements with how many pixels they extend beyond the viewport
- Console output with pass/fail verdict and element-level details

## Issues detected

- Horizontal scrollbar at 320px viewport width
- Elements whose right edge extends beyond the viewport boundary (with exact overflow amount in px)

## Acceptable exceptions (per WCAG)

Content that inherently requires two-dimensional layout is exempt: data tables, maps, diagrams, video players, toolbars with many buttons, and certain games or applications.

## Example prompts

- *"Test reflow on https://example.com"*
- *"Check if this page requires horizontal scrolling at 400% zoom"*
- *"Run a WCAG 1.4.10 audit"*
- *"Does this page work at 320px wide?"*
- *"Check narrow viewport compatibility"*

## Requirements

- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture_reflow.py` | Playwright: screenshots at both viewports + overflow detection |
| `scripts/reflow_compare.py` | PIL: side-by-side comparison with pass/fail indicator |

### capture_reflow.py CLI

```bash
python scripts/capture_reflow.py \
  --url          https://example.com \
  --output-dir   path/to/workspace/ \
  --wide-width   1280 \
  --narrow-width 320
```

Outputs: `wide_screenshot.png`, `narrow_screenshot.png`, `reflow_data.json`

### reflow_compare.py CLI

```bash
python scripts/reflow_compare.py \
  --wide   path/to/wide_screenshot.png \
  --narrow path/to/narrow_screenshot.png \
  --data   path/to/reflow_data.json \
  --output path/to/reflow_audit.png \
  --label  "Reflow Audit (WCAG 1.4.10) — https://example.com"
```

## Common fixes

| Root cause | Fix |
|------------|-----|
| Fixed pixel widths on containers | Replace `width: 800px` with `max-width: 100%` or `width: min(800px, 100%)` |
| Images or video overflowing | Add `max-width: 100%; height: auto` to `img`, `video`, `iframe` |
| Wide pre/code blocks | Add `overflow-x: auto` on the `<pre>` element |
| Wide data tables | Wrap table in `<div style="overflow-x: auto">` |
| Fixed-position elements causing overflow | Ensure fixed elements are sized relative to viewport (`width: 100vw` not wider) |

## Example output — jecture.co

**Result:** ✓ Pass — no horizontal scrolling at 320px, no overflowing elements. Page height increases from 2,913px to 5,129px as content stacks vertically (expected behavior).

| Reflow audit (desktop vs 320px) |
|---------------------------------|
| ![Reflow audit](examples/jecture-co/reflow_audit.png) |
