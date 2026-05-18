---
name: wcag-reflow
description: 'Audit page reflow for WCAG 1.4.10. Use this skill when someone wants to check if a page requires horizontal scrolling at 320px wide, test 400% zoom compatibility, verify that content reflows without loss of information, or find elements that overflow at narrow viewports. Generates a side-by-side screenshot comparison of desktop vs 320px width. Trigger when the user mentions reflow, 400% zoom, horizontal scrolling, narrow viewport, WCAG 1.4.10, or mobile zoom.'
---

# WCAG Reflow Audit (1.4.10)

You are auditing a webpage for WCAG 1.4.10 Reflow compliance. Content must be presentable at 320px wide (equivalent to 400% zoom on a 1280px screen) without requiring horizontal scrolling to read a line of text.

**WCAG criterion:**
- **1.4.10 (AA):** Content can be presented without loss of information or functionality, and without requiring scrolling in two dimensions for vertical-scrolling content at a width equivalent to 320 CSS pixels

**Acceptable exceptions (2D layout is inherently required):**
- Data tables with many columns
- Maps and geographic images
- Toolbars with many controls
- Complex diagrams or charts where spatial relationships matter

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture both viewports

```bash
python "<SKILL_DIR>/scripts/capture_reflow.py" \
  --url "<URL>" \
  --output-dir "<WORKSPACE>"
```

This single script captures full-page screenshots at both the wide (1280px) and narrow (320px) viewports, runs the overflow detection JavaScript, and saves `wide_screenshot.png`, `narrow_screenshot.png`, and `reflow_data.json` into `<WORKSPACE>`.

---

## Step 2: Generate comparison image

```bash
python "<SKILL_DIR>/scripts/reflow_compare.py" \
  --wide   "<WORKSPACE>/wide_screenshot.png" \
  --narrow "<WORKSPACE>/narrow_screenshot.png" \
  --data   "<WORKSPACE>/reflow_data.json" \
  --output "<WORKSPACE>/reflow_audit.png" \
  --label  "Reflow Audit (WCAG 1.4.10) — <URL>"
```

The output is a side-by-side image showing the desktop layout on the left and the 320px layout on the right at their actual pixel widths — the width difference is intentional and demonstrates how the layout adapts (or fails to adapt) at narrow viewports.

---

## Step 3: Report to the user

Display `<WORKSPACE>/reflow_audit.png`, then provide:

**Result: PASS or FAIL**

If **FAIL**, list each overflowing element with:
- Element tag and identifier (id or class)
- How many pixels it overflows the viewport by
- A targeted fix suggestion

**Fix patterns by root cause:**

| Cause | Symptom | Fix |
|-------|---------|-----|
| Fixed pixel width | `width: 800px` on a container | Replace with `max-width: 100%` or `width: min(800px, 100%)` |
| Images/videos | Media wider than viewport | Add `max-width: 100%; height: auto` |
| Wide data tables | Table overflows container | Wrap table in `overflow-x: auto` container, or use responsive table techniques (stacked rows, horizontal scroll region) |
| Sticky/fixed elements | Fixed-position bar overflows | Ensure fixed elements use `max-width: 100vw` and `overflow: hidden` |
| Long words / URLs | Unbreakable text strings overflow | Add `overflow-wrap: break-word` or `word-break: break-all` to text containers |
| Flexbox/Grid min-width | Child refuses to shrink | Add `min-width: 0` to the flex/grid child, or `overflow: hidden` |

**If no issues:** Confirm the page passes WCAG 1.4.10 and note any intentional 2D-layout content that is exempt under the criterion.

**Note on exceptions:** If overflowing elements are data tables, maps, toolbars, or complex diagrams, these are acceptable under WCAG 1.4.10 — document them as intentional exceptions rather than failures.
