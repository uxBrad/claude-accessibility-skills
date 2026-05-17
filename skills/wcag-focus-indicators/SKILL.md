---
name: wcag-focus-indicators
description: 'Audit keyboard focus indicator visibility for WCAG 2.4.7 and 2.4.11. Use this skill when someone wants to check if focused elements are visually distinguishable, find elements with missing or invisible focus rings, audit outline:none usage, or verify focus styles. Generates a contact sheet showing every focusable element in its focused state with green (visible) or red (missing) borders. Trigger when the user mentions focus rings, focus styles, focus visible, outline:none, keyboard focus, focus indicators, or WCAG 2.4.'
---

# WCAG Focus Indicator Audit (2.4.7 / 2.4.11)

You are auditing a webpage to verify that every keyboard-focusable element has a clearly visible focus indicator — critical for keyboard-only users and anyone who cannot use a mouse.

**WCAG criteria:**
- **2.4.7 (AA):** Every keyboard-operable interface has a visible focus indicator
- **2.4.11 (AA, WCAG 2.2):** Focus indicator meets minimum size and contrast requirements

The skill directory containing this file is `SKILL_DIR`. Replace all occurrences of `<SKILL_DIR>` below with that path.

---

## How detection works

`capture_focus.py` uses Playwright to focus each element programmatically, then compares pixel values in the element region before and after focus. If the max per-channel pixel delta exceeds the threshold (default 6), the focus indicator is considered **visible**. This catches browser-default focus styles, custom outlines, box-shadows, and background-color changes that pure CSS inspection would miss.

---

## Step 1: Capture focus states (both viewports)

```bash
python "<SKILL_DIR>/scripts/capture_focus.py" \
  --url "<URL>" \
  --output-dir "<WORKSPACE>/desktop_crops" \
  --viewport desktop

python "<SKILL_DIR>/scripts/capture_focus.py" \
  --url "<URL>" \
  --output-dir "<WORKSPACE>/mobile_crops" \
  --viewport mobile
```

Each run produces:
- `focus_NNN.png` files — cropped screenshots of each element in focused state
- `focus_data.json` — metadata including `focus_visible`, `diff_score`, `tag`, `label`

---

## Step 2: Build contact sheets

```bash
python "<SKILL_DIR>/scripts/contact_sheet.py" \
  --crops-dir "<WORKSPACE>/desktop_crops" \
  --data      "<WORKSPACE>/desktop_crops/focus_data.json" \
  --output    "<WORKSPACE>/desktop_focus_sheet.png" \
  --label     "Desktop (1280px) — Focus Indicator Audit"

python "<SKILL_DIR>/scripts/contact_sheet.py" \
  --crops-dir "<WORKSPACE>/mobile_crops" \
  --data      "<WORKSPACE>/mobile_crops/focus_data.json" \
  --output    "<WORKSPACE>/mobile_focus_sheet.png" \
  --label     "Mobile (390px) — Focus Indicator Audit"
```

---

## Step 3: Report to the user

Share both contact sheet images, then provide:

**Summary table:**

| Viewport | Total elements | Focus visible | No indicator | Errors |
|----------|---------------|---------------|--------------|--------|
| Desktop  | N             | N (%)         | N (%)        | N      |
| Mobile   | N             | N (%)         | N (%)        | N      |

**Elements missing focus indicators** — list each: index, tag, label/text, and a suggested fix (e.g., remove `outline: none` without a replacement, or add `outline: 2px solid #005fcc`).

**Common causes to check:**
- `outline: none` or `outline: 0` in CSS without a replacement focus style
- `:focus` styles overridden by `:hover` styles
- Focus styles on a parent element rather than the focused element itself (the diff detector will still catch these, but they're worth noting)
- Elements using `tabindex="0"` without any focus styling

**WCAG 2.4.11 note:** For AA compliance under WCAG 2.2, the focus indicator must also meet minimum contrast and size requirements. Flag low-diff-score passes (diff_score between 6-20) for manual review — they may have technically detectable but visually weak indicators.