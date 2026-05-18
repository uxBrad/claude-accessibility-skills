# wcag-text-spacing

Tests whether page content remains readable and unclipped when WCAG 1.4.12 text-spacing overrides are applied. Generates a side-by-side before/after comparison screenshot at desktop and mobile viewports.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.4.12 Text Spacing | AA | No loss of content or functionality when line height, letter spacing, word spacing, and paragraph spacing are overridden |

## What the overrides test

| Property | Override value |
|----------|---------------|
| `line-height` | 1.5× font-size |
| `letter-spacing` | 0.12em |
| `word-spacing` | 0.16em |
| Paragraph spacing (`margin-bottom`) | 2em on `p`, `li`, `dt`, `dd`, `blockquote` |

## What it produces

- **Desktop comparison** and **Mobile comparison** — dark-themed side-by-side PNG showing before (left) and after (right)
- Footer bar: green pass or red fail with overflow details and page height increase
- Console output listing any overflowing elements

## Issues detected

- Horizontal scrollbar appearing after overrides
- Elements where `scrollWidth > clientWidth` (content clipped or pushed out of container)
- Page height increase reported as a percentage (expected — more space is normal; clipping is the problem)

## Example prompts

- *"Test text spacing on https://example.com"*
- *"Check WCAG 1.4.12 on this page"*
- *"Does the layout break when spacing is increased?"*
- *"Run a text spacing audit"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture_spacing.py` | Playwright: before/after screenshots + overflow detection |
| `scripts/spacing_compare.py` | PIL: side-by-side comparison image with pass/fail footer |

### capture_spacing.py CLI

```bash
python scripts/capture_spacing.py \
  --url      https://example.com \
  --viewport desktop \
  --output-dir path/to/workspace/
```

Outputs: `before.png`, `after.png`, `spacing_data.json`

### spacing_compare.py CLI

```bash
python scripts/spacing_compare.py \
  --before path/to/before.png \
  --after  path/to/after.png \
  --data   path/to/spacing_data.json \
  --output path/to/output.png \
  --label  "Desktop (1280px) — Text Spacing Audit (WCAG 1.4.12)"
```

## Common fixes

| Issue | Fix |
|-------|-----|
| Text clipped in fixed-height container | Replace `height: Npx` with `min-height: Npx` |
| Text overflows its box | Remove `overflow: hidden` or use `overflow: auto` |
| Navigation items wrap and break layout | Use `flex-wrap: wrap` or increase container flexibility |
| Content disappears | Check `white-space: nowrap` — remove or scope it narrowly |

## Example output — jecture.co

**Result:** ✓ Pass on both viewports — no overflow, no clipping. Page height increased 8.4% on desktop (expected — extra spacing pushes content down).

| Desktop comparison | Mobile comparison |
|-------------------|------------------|
| ![Desktop text spacing audit](examples/jecture-co/desktop_spacing_audit.png) | ![Mobile text spacing audit](examples/jecture-co/mobile_spacing_audit.png) |
