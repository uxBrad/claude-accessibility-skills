# wcag-focus-indicators

Audits keyboard focus indicator visibility by photographing every focusable element in its focused state, then assembles a contact sheet for easy review.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 2.4.7 Focus Visible | AA | Every keyboard-operable UI has a visible focus indicator |
| 2.4.11 Focus Appearance | AA (WCAG 2.2) | Focus indicator meets minimum size and contrast |

## What it produces

- **Desktop contact sheet** and **Mobile contact sheet**
- Grid of cropped screenshots — one cell per focusable element in its focused state
- Cell border color indicates result:
  - **Green border** — focus indicator detected (pass)
  - **Red border** — no visible focus indicator (fail)
  - **Grey border** — capture error
- Diff score shown on each cell (higher = more visible change on focus)
- Summary report listing elements with missing focus indicators and fix suggestions

## How detection works

The skill uses pixel-diff comparison: it screenshots the element before and after programmatic focus, then measures the maximum per-channel pixel change in the element region. A change greater than the threshold (default: 6 units) means a focus indicator is present. This catches:

- CSS `outline` and `box-shadow` focus styles
- Background color changes on focus
- Browser default focus rings
- Custom animated focus styles

Elements with diff scores between 6-20 should be reviewed manually — they may have technically detectable but visually weak indicators.

## Example prompts

- *"Check if all interactive elements have visible focus indicators on https://example.com"*
- *"Audit keyboard focus styles on localhost:8080"*
- *"Find elements with outline:none that have no replacement focus style"*
- *"Run a WCAG 2.4.7 focus visibility audit"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture_focus.py` | Playwright-based per-element focus capture with pixel-diff detection |
| `scripts/contact_sheet.py` | Assembles crop images into a contact sheet grid |

### capture_focus.py CLI

```bash
python scripts/capture_focus.py \
  --url        https://example.com \
  --output-dir path/to/crops/ \
  --viewport   desktop
```

Outputs: `focus_000.png`, `focus_001.png`, ..., `focus_data.json`

### contact_sheet.py CLI

```bash
python scripts/contact_sheet.py \
  --crops-dir path/to/crops/ \
  --data      path/to/crops/focus_data.json \
  --output    path/to/contact_sheet.png \
  --label     "Desktop (1280px)"
```

### focus_data.json format

```json
[
  {
    "index":         0,
    "tag":           "a",
    "label":         "Skip to main content",
    "abs_x":         20,
    "abs_y":         10,
    "w":             180,
    "h":             24,
    "status":        "pass",
    "focus_visible": true,
    "diff_score":    42.0,
    "crop_file":     "focus_000.png"
  }
]
```

## Common issues

- **`outline: none` without replacement** — the most common cause of WCAG 2.4.7 failures. Check for this in CSS resets and component library overrides.
- **Focus on parent, not child** — some components apply focus styles to a wrapper element. The diff detector catches this, but the element shown in the crop will look unstyled.
- **Very short animations** — fast transitions may not be captured if they complete before the screenshot. Diff scores will be lower than expected.