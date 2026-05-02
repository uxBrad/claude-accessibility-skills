---
name: wcag-keyboard
description: 'Generates a visual keyboard accessibility heatmap for any website (including localhost). Use this skill when the user wants to audit keyboard accessibility, visualize tab order, check which elements are keyboard-focusable, generate a tab order heatmap, see the keyboard flow through a page, check WCAG 2.1 keyboard criteria (2.1.1 / 2.1.2 / 2.1.4), test a site with the Tab key, find elements that should be interactive but are not, or audit a local dev server. Also trigger for phrases like keyboard through, tab order, focus flow, accessibility audit, can keyboard users navigate, check my UI is accessible, heatmap of focus, or desktop and mobile accessibility. Even if the user just says check accessibility - keyboard is the most commonly missed issue and this visual audit immediately shows the problems.'
---

# WCAG 2.1 Keyboard Accessibility Heatmap

You will produce **two annotated heatmap images** (desktop + mobile) of a webpage showing the full keyboard tab order, and a written summary of findings.

Each heatmap shows:
- **Numbered yellow circles** at each focusable element's center (in tab order)
- **Blue arrows** connecting tab stops to show the flow direction
- **Red outlined boxes** on elements that should be interactive but cannot be reached by keyboard

---

## Step 1: Set up Chrome and navigate

You need the Chrome MCP tools:
- `mcp__Claude_in_Chrome__tabs_context_mcp`
- `mcp__Claude_in_Chrome__navigate`
- `mcp__Claude_in_Chrome__javascript_tool`
- `mcp__Claude_in_Chrome__computer`
- `mcp__Claude_in_Chrome__resize_window`

Get or create a tab, then navigate to the user's URL. Accept any URL including `localhost:*` and `127.0.0.1:*`.

---

## Step 2: Desktop audit (1280px wide)

### 2a. Set viewport
```
resize_window(width=1280, height=900)
```
Then scroll to top: `window.scrollTo(0, 0)`

### 2b. Expand window to capture full page height

Run JS:
```javascript
({ pageH: document.documentElement.scrollHeight, viewH: window.innerHeight })
```
If pageH > viewH, resize height to min(pageH, 6000). Scroll to top again.

If the browser cannot resize that tall (screen too small), use Playwright for screenshots instead:
```bash
python scripts/capture.py --url <url> --outdir <outdir>
```

### 2c. Collect focusable elements (actual tab order)

```javascript
(function() {
  const sel = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])', '[contenteditable="true"]',
    'details > summary', 'audio[controls]', 'video[controls]'
  ].join(', ');
  const els = [...document.querySelectorAll(sel)].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0' && el.offsetParent !== null;
  });
  const scrollY = window.pageYOffset || 0, scrollX = window.pageXOffset || 0;
  const withPos = els.map((el, i) => {
    const r = el.getBoundingClientRect();
    return {
      index: i,
      tabindex: parseInt(el.getAttribute('tabindex') || '0', 10),
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      label: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('value') || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ').slice(0, 60),
      x: Math.round(r.left + scrollX + r.width / 2),
      y: Math.round(r.top + scrollY + r.height / 2),
      w: Math.round(r.width), h: Math.round(r.height),
      top: Math.round(r.top + scrollY), left: Math.round(r.left + scrollX)
    };
  });
  const positive = withPos.filter(e => e.tabindex > 0).sort((a, b) => a.tabindex - b.tabindex || a.index - b.index);
  const zeros = withPos.filter(e => e.tabindex <= 0).sort((a, b) => a.index - b.index);
  const ordered = [...positive, ...zeros];
  ordered.forEach((e, i) => { e.tabOrder = i + 1; });
  return ordered;
})()
```

Save result as JSON to `desktop_elements.json`.

### 2d. Collect missing-interactive elements

```javascript
(function() {
  const nonInteractive = new Set(['div','span','li','td','tr','th','p','section','article','header','footer','figure','img','h1','h2','h3','h4','h5','h6']);
  const interactiveRoles = new Set(['button','link','tab','menuitem','option','treeitem','checkbox','radio','switch']);
  const scrollY = window.pageYOffset || 0, scrollX = window.pageXOffset || 0;
  const results = [];
  document.querySelectorAll('*').forEach(el => {
    const tag = el.tagName.toLowerCase();
    if (!nonInteractive.has(tag)) return;
    const s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || el.offsetParent === null) return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const hasClick = el.onclick !== null || !!el.getAttribute('onclick');
    const hasRole = interactiveRoles.has(el.getAttribute('role'));
    const tabIdx = el.getAttribute('tabindex');
    const isReachable = tabIdx === '0' || (tabIdx !== null && parseInt(tabIdx) > 0);
    if ((hasClick || hasRole) && !isReachable) {
      results.push({ tag, role: el.getAttribute('role') || '', label: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60), hasOnClick: hasClick, hasRole, x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) });
    }
  });
  return results;
})()
```

Save as `desktop_missing.json`.

### 2e. Screenshot the full page
Use Playwright for reliable full-page capture:
```bash
python scripts/capture.py --url <url> --outdir <outdir> --viewport desktop
```
Or use `computer(action="screenshot")` if the window was expanded to full page height.
Save as `desktop_screenshot.png`.

---

## Step 3: Mobile audit (390px wide)

Run the capture script with mobile viewport:
```bash
python scripts/capture.py --url <url> --outdir <outdir> --viewport mobile
```

Also run the element collection JS in a 390px-wide browser context and save as `mobile_elements.json` and `mobile_missing.json`.

---

## Step 4: Generate heatmap images

Install if needed: `pip install Pillow`

```bash
python scripts/heatmap.py --screenshot desktop_screenshot.png --elements desktop_elements.json --missing desktop_missing.json --output desktop_heatmap.png --label "Desktop (1280px)"

python scripts/heatmap.py --screenshot mobile_screenshot.png --elements mobile_elements.json --missing mobile_missing.json --output mobile_heatmap.png --label "Mobile (390px)"
```

Tell the user the full paths to both output images.

---

## Step 5: Write audit report in conversation

# Keyboard Accessibility Audit

**URL:** [url]
**Date:** [today]

## At a Glance

| | Desktop (1280px) | Mobile (390px) |
|---|---|---|
| Focusable elements | N | N |
| Missing from tab order | N | N |
| Tab order logical? | Yes/No/Partial | Yes/No/Partial |

## Tab Order Observations

**Desktop:** Does the order follow reading flow (top to bottom, left to right)? Call out surprising jumps by element name and number.

**Mobile:** Does the mobile layout cause visual order to differ from tab order? CSS flex/grid reordering is a common source of mismatches.

## Elements Missing from Tab Order

| # | Tag | Label | Issue | Fix |
|---|-----|-------|-------|-----|
| 1 | div | "Save" | Has onclick, no tabindex | Replace with button, or add tabindex="0" + onKeyDown handler |

## WCAG 2.1 Assessment

| Criterion | Desktop | Mobile |
|-----------|---------|--------|
| 2.1.1 Keyboard | Pass/Fail | Pass/Fail |
| 2.1.2 No Keyboard Trap | Pass/Fail | Pass/Fail |
| 2.1.4 Character Key Shortcuts | Pass/Fail | Pass/Fail |

## Heatmap Files
- `desktop_heatmap.png` -- N tab stops marked
- `mobile_heatmap.png` -- N tab stops marked

Legend: Yellow numbered circle = tab stop | Arrow = flow | Red box = missing from tab order

---

## Edge case notes

- **Pages taller than 6000px**: heatmap captures first 6000px -- note the cutoff
- **Modals and dropdowns**: open each and re-run element collection separately for a supplemental heatmap
- **iframes**: not captured by main-frame JS -- audit each iframe document separately
- **SPAs with client-side routing**: audit each route separately
- **Lazy-loaded content**: scroll to bottom first, wait for content, then collect elements