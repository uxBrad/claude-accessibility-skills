---
name: wcag-text-spacing
description: 'Audit text spacing reflow for WCAG 1.4.12. Use this skill when someone wants to test whether a page breaks when text spacing is increased, check if content clips or overflows when WCAG spacing overrides are applied, or verify 1.4.12 compliance. Generates a side-by-side before/after comparison screenshot. Trigger when the user mentions text spacing, letter spacing, line height, WCAG 1.4.12, or spacing overrides.'
---

# WCAG 1.4.12 Text Spacing Audit

You will produce **two side-by-side comparison images** (desktop + mobile) showing the page before and after WCAG 1.4.12 text-spacing overrides are applied, plus a written summary of any overflow or clipping issues detected.

**WCAG 1.4.12 (Text Spacing — AA)** requires that no loss of content or functionality occurs when all of the following CSS properties are overridden:
- `line-height: 1.5` (relative to font-size)
- `letter-spacing: 0.12em`
- `word-spacing: 0.16em`
- Spacing following paragraphs: `margin-bottom: 2em` (on `p`, `li`, `dt`, `dd`, `blockquote`, `label`, `legend`)

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture before/after screenshots

Run the capture script twice — once for desktop, once for mobile. Each run saves `before.png`, `after.png`, and `spacing_data.json` into the specified output directory.

```bash
python "<SKILL_DIR>/scripts/capture_spacing.py" \
  --url "<URL>" \
  --viewport desktop \
  --output-dir "<WORKSPACE>/desktop"

python "<SKILL_DIR>/scripts/capture_spacing.py" \
  --url "<URL>" \
  --viewport mobile \
  --output-dir "<WORKSPACE>/mobile"
```

---

## Step 2: Generate side-by-side comparison images

```bash
python "<SKILL_DIR>/scripts/spacing_compare.py" \
  --before  "<WORKSPACE>/desktop/before.png" \
  --after   "<WORKSPACE>/desktop/after.png" \
  --data    "<WORKSPACE>/desktop/spacing_data.json" \
  --output  "<WORKSPACE>/desktop_spacing_audit.png" \
  --label   "Desktop (1280px) — WCAG 1.4.12 Text Spacing"

python "<SKILL_DIR>/scripts/spacing_compare.py" \
  --before  "<WORKSPACE>/mobile/before.png" \
  --after   "<WORKSPACE>/mobile/after.png" \
  --data    "<WORKSPACE>/mobile/spacing_data.json" \
  --output  "<WORKSPACE>/mobile_spacing_audit.png" \
  --label   "Mobile (390px) — WCAG 1.4.12 Text Spacing"
```

---

## Step 3: Report to the user

Share both comparison images inline, then provide:

**Summary table:**

| Viewport | Result | Height increase | Overflow issues |
|----------|--------|-----------------|-----------------|
| Desktop (1280px) | Pass / Fail | +X% (Ypx → Zpx) | None / N element(s) |
| Mobile (390px)   | Pass / Fail | +X% (Ypx → Zpx) | None / N element(s) |

A viewport **passes** if:
- `has_horizontal_scroll` is `false`, AND
- `overflowing_elements` is empty

A viewport **fails** if horizontal scroll is introduced or elements clip/overflow their containers after the spacing overrides are applied.

**Overflowing elements** — if any are found in `spacing_data.json`, list each one with its tag, id, and class, along with the measured widths and a suggested fix:

| # | Element | scrollWidth | clientWidth | Suggested fix |
|---|---------|-------------|-------------|---------------|
| 1 | `<div class="hero-text">` | 1340px | 1280px | Add `overflow-wrap: break-word` or reduce fixed `width`/`padding` |

**Common root causes and fixes:**

- **Fixed `width` or `min-width` in px** — switch to `max-width` or use `%`/`ch` units so text can wrap
- **`white-space: nowrap`** — remove or scope it so it does not apply to user-visible text
- **`overflow: hidden` clipping text** — add `overflow: visible` or increase the container's height/padding
- **Inline or absolute-positioned elements** — ensure they do not escape their parent when text expands
- **CSS Grid / Flexbox with fixed track sizes** — use `minmax()` or `flex-wrap: wrap` to accommodate larger text

**WCAG 1.4.12 verdict:** Pass / Fail (per viewport)

If the page fails, remind the developer that WCAG 1.4.12 is a Level AA requirement and must be met for AA conformance. The page must not lose content or functionality when the specified spacing values are applied — the content may reflow and grow taller, but it must not clip or scroll horizontally.
