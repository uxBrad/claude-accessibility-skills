# wcag-touch-targets

Audits interactive element sizes against WCAG touch target requirements and generates an annotated heatmap.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 2.5.8 Target Size (Minimum) | AA (WCAG 2.2) | At least 24x24 CSS pixels |
| 2.5.5 Target Size | AAA | At least 44x44 CSS pixels |

## Example output — jecture.co homepage

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop touch target heatmap](../../examples/jecture-co/touch-targets/desktop_targets.png) | ![Mobile touch target heatmap](../../examples/jecture-co/touch-targets/mobile_targets.png) |

**What this revealed on jecture.co:**
- 12/22 elements pass AAA (>=44x44px) — primary CTAs and article thumbnails are well-sized
- 5/22 pass AA only — nav links at 30px height need 14px more to reach AAA
- 5/22 fail — footer social links (Mastodon, Bluesky, Threads, Instagram) and "Let's Find Out." inline link are only 20-22px tall, below the 24px AA minimum

## What it produces

- **Desktop heatmap** (1280px) and **Mobile heatmap** (390px)
- Color-coded boxes over every interactive element:
  - **Green** — passes AAA (44x44px or larger)
  - **Yellow** — passes AA (24x24px or larger)
  - **Red** — fails AA minimum size
- Size label on each box showing actual pixel dimensions
- Summary report listing failing elements and CSS fix recommendations

## Example prompts

- *"Audit the touch target sizes on https://example.com"*
- *"Check if the buttons on localhost:3000 are large enough to tap on mobile"*
- *"Run a WCAG 2.5 target size check on this page"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture.py` | Full-page screenshot at desktop or mobile viewport |
| `scripts/target_heatmap.py` | Draws color-coded size overlay on screenshot |

### target_heatmap.py CLI

```bash
python scripts/target_heatmap.py \
  --screenshot path/to/screenshot.png \
  --elements   path/to/elements.json \
  --output     path/to/output.png \
  --label      "Mobile (390px)"
```

### elements.json format

Array of objects with these fields:

```json
[
  {
    "index":  0,
    "tag":    "button",
    "label":  "Submit",
    "x":      120,
    "y":      340,
    "w":      80,
    "h":      20,
    "status": "fail"
  }
]
```

`status` must be one of `"aaa"`, `"aa"`, or `"fail"`.

## Notes on WCAG 2.5.8 exceptions

WCAG 2.5.8 allows small targets if they have a 24px offset spacing around them — inline text links inside a paragraph, for example, are often exempt. Claude will flag small elements for review rather than marking them as definitive failures when context suggests an exception may apply.