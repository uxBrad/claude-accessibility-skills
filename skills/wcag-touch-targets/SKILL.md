---
name: wcag-touch-targets
description: 'Audit touch and click target sizes for WCAG 2.5.5 and 2.5.8. Use this skill whenever someone wants to check if buttons, links, or interactive elements are large enough to tap — especially on mobile. Generates a color-coded heatmap showing every interactive element: green for AAA pass (44x44px+), yellow for AA pass (24x24px+), red for elements that fail minimum size. Trigger when the user mentions tap targets, click targets, touch accessibility, small buttons, fat-finger errors, mobile accessibility, or WCAG 2.5.'
---

# WCAG Touch Target Size Audit (2.5.5 / 2.5.8)

You are auditing a webpage to check whether interactive elements are large enough to activate reliably — a critical issue for users with motor disabilities, tremors, or anyone using a touch screen.

**WCAG criteria:**
- **2.5.8 (AA, WCAG 2.2):** Target size at least 24x24 CSS pixels (or has 24px spacing offset around it)
- **2.5.5 (AAA):** Target size at least 44x44 CSS pixels

The skill directory containing this file is `SKILL_DIR`. Replace all occurrences of `<SKILL_DIR>` below with that path.

---

## Step 1: Capture full-page screenshots

Run `capture.py` for both viewports. Use the URL provided by the user.

```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport desktop --output "<WORKSPACE>/desktop_screenshot.png"
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport mobile  --output "<WORKSPACE>/mobile_screenshot.png"
```

---

## Step 2: Collect interactive elements via JavaScript

Navigate to the URL with the Chrome MCP. Execute the following JavaScript separately at each viewport (resize the browser window first using the Chrome MCP resize tool).

**Desktop — resize to 1280px wide, then run:**

```javascript
(function() {
  const sel = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])', '[role="button"]', '[role="link"]',
    '[role="checkbox"]', '[role="radio"]', '[role="menuitem"]',
    '[role="tab"]', '[role="switch"]', 'summary', '[onclick]'
  ].join(', ');

  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;

  return [...document.querySelectorAll(sel)].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' &&
           s.opacity !== '0' && el.offsetParent !== null;
  }).map((el, i) => {
    const r = el.getBoundingClientRect();
    const w = Math.round(r.width), h = Math.round(r.height);
    const passes_aaa = w >= 44 && h >= 44;
    const passes_aa  = w >= 24 && h >= 24;
    return {
      index: i,
      tag:   el.tagName.toLowerCase(),
      type:  el.getAttribute('type') || '',
      role:  el.getAttribute('role') || '',
      label: (el.getAttribute('aria-label') || el.textContent ||
              el.getAttribute('placeholder') || '').trim().replace(/\s+/g,' ').slice(0,50),
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: w, h: h,
      status: passes_aaa ? 'aaa' : passes_aa ? 'aa' : 'fail'
    };
  }).filter(e => e.w > 0 && e.h > 0);
})()
```

Save as `<WORKSPACE>/desktop_elements.json`.

**Mobile — resize to 390px wide, reload the page, then run the same script.**  
Save as `<WORKSPACE>/mobile_elements.json`.

---

## Step 3: Generate heatmaps

```bash
python "<SKILL_DIR>/scripts/target_heatmap.py" \
  --screenshot "<WORKSPACE>/desktop_screenshot.png" \
  --elements   "<WORKSPACE>/desktop_elements.json" \
  --output     "<WORKSPACE>/desktop_targets.png" \
  --label      "Desktop (1280px) — Touch Target Audit"

python "<SKILL_DIR>/scripts/target_heatmap.py" \
  --screenshot "<WORKSPACE>/mobile_screenshot.png" \
  --elements   "<WORKSPACE>/mobile_elements.json" \
  --output     "<WORKSPACE>/mobile_targets.png" \
  --label      "Mobile (390px) — Touch Target Audit"
```

---

## Step 4: Report to the user

Share both heatmap images, then provide:

**Summary table:**

| Viewport | Total | AAA (>=44x44) | AA (>=24x24) | Fail (<24px) |
|----------|-------|---------------|--------------|--------------|
| Desktop  | N     | N (%)         | N (%)        | N (%)        |
| Mobile   | N     | N (%)         | N (%)        | N (%)        |

**Failing elements** — list each with: element type, label/text, actual size, and how many pixels short it is of AA and AAA thresholds.

**Quick CSS fix** — suggest a minimal CSS rule to bring failing elements up to the 24x24 AA minimum (e.g., `min-height: 24px; min-width: 24px;` or padding adjustments).

Note: some elements intentionally small (e.g., inline text links in body copy) may have a WCAG 2.5.8 exception if they have adequate spacing around them — flag these for manual review rather than marking them as definitive failures.