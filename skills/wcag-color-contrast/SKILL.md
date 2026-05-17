---
name: wcag-color-contrast
description: 'Audit color contrast ratios for WCAG 1.4.3 (AA) and 1.4.6 (AAA). Use this skill when someone wants to check if text is readable, find low-contrast text, verify color accessibility, or audit a site for contrast failures. Generates an annotated screenshot with red badges on failing elements showing their contrast ratio, plus a full summary report. Trigger when the user mentions contrast, readability, color accessibility, low contrast, text visibility, or WCAG 1.4.'
---

# WCAG Color Contrast Audit (1.4.3 / 1.4.6)

You are auditing a webpage for text color contrast accessibility. Low contrast text is one of the most common WCAG failures and affects users with low vision, color blindness, and anyone in a bright environment.

**WCAG thresholds:**
- **1.4.3 (AA):** Normal text 4.5:1 | Large text 3:1 (>=18pt or >=14pt bold)
- **1.4.6 (AAA):** Normal text 7:1 | Large text 4.5:1

The skill directory containing this file is `SKILL_DIR`. Replace all occurrences of `<SKILL_DIR>` below with that path.

---

## Step 1: Capture full-page screenshots

```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport desktop --output "<WORKSPACE>/desktop_screenshot.png"
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport mobile  --output "<WORKSPACE>/mobile_screenshot.png"
```

---

## Step 2: Collect text elements with color data via JavaScript

Navigate to the URL with the Chrome MCP. Execute this JavaScript to collect all visible text elements with their computed foreground and background colors:

```javascript
(function() {
  function getEffectiveBg(el) {
    let node = el;
    while (node && node !== document.documentElement) {
      const bg = window.getComputedStyle(node).backgroundColor;
      if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') return bg;
      node = node.parentElement;
    }
    return 'rgb(255, 255, 255)';
  }

  function parseRgb(str) {
    const m = str.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    return m ? [+m[1], +m[2], +m[3]] : null;
  }

  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  const results = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;

  while (node = walker.nextNode()) {
    const el = node;
    const s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') continue;
    if (!el.offsetParent && el.tagName !== 'BODY') continue;

    const hasDirectText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!hasDirectText) continue;

    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;

    const fg = parseRgb(s.color);
    const bg = parseRgb(getEffectiveBg(el));
    if (!fg || !bg) continue;

    const fontSize   = parseFloat(s.fontSize);
    const fontWeight = s.fontWeight;
    const isLarge    = fontSize >= 24 || (fontSize >= 18.67 && (+fontWeight >= 700 || fontWeight === 'bold'));

    results.push({
      tag:      el.tagName.toLowerCase(),
      text:     el.textContent.trim().replace(/\s+/g,' ').slice(0,50),
      fg:       fg,
      bg:       bg,
      fg_str:   s.color,
      bg_str:   getEffectiveBg(el),
      fontSize: Math.round(fontSize),
      isLarge:  isLarge,
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height)
    });
  }
  return results;
})()
```

Save as `<WORKSPACE>/desktop_text_elements.json`. Repeat after resizing to 390px and save as `<WORKSPACE>/mobile_text_elements.json`.

---

## Step 3: Generate annotated screenshots

```bash
python "<SKILL_DIR>/scripts/contrast_overlay.py" \
  --screenshot "<WORKSPACE>/desktop_screenshot.png" \
  --elements   "<WORKSPACE>/desktop_text_elements.json" \
  --output     "<WORKSPACE>/desktop_contrast.png" \
  --label      "Desktop (1280px) — Color Contrast Audit"

python "<SKILL_DIR>/scripts/contrast_overlay.py" \
  --screenshot "<WORKSPACE>/mobile_screenshot.png" \
  --elements   "<WORKSPACE>/mobile_text_elements.json" \
  --output     "<WORKSPACE>/mobile_contrast.png" \
  --label      "Mobile (390px) — Color Contrast Audit"
```

Add `--show-passes` to also highlight passing elements (useful when everything fails, for context).

---

## Step 4: Report to the user

Share both annotated screenshots, then provide:

**Summary table:**

| Viewport | Text elements | AAA pass | AA pass only | Fail |
|----------|--------------|----------|--------------|------|
| Desktop  | N            | N (%)    | N (%)        | N (%) |
| Mobile   | N            | N (%)    | N (%)        | N (%) |

**Failing elements** — list the worst offenders (sorted by ratio, lowest first):
- Include ratio, element type, sample text, and fg/bg color pair
- Note whether it is normal text or large text (different threshold)

**Recommendations:**
- For each unique color pair that fails, suggest a specific corrected color value that would pass AA
- Note any elements where the background might be an image or gradient (these show as assumed white — flag for manual check)
- Point out any text on brand colors that commonly fail (dark text on yellow, white text on orange, etc.)

**Important limitations:**
- Background images and CSS gradients are approximated as solid colors — flag those elements for manual verification
- Overlapping elements or translucent layers may report incorrect background colors
- Dynamic state contrast (hover, focus, active) requires a separate pass