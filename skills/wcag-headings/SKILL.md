---
name: wcag-headings
description: 'Audit heading structure and document outline for WCAG 1.3.1 and 2.4.6. Use this skill when someone wants to check if headings are in logical order, find skipped heading levels, verify a single H1, or visualize the page outline. Produces two outputs: an annotated screenshot with each heading labeled by level, and a standalone outline diagram showing the full heading tree. Trigger when the user mentions headings, heading hierarchy, H1, H2, H3, document structure, page outline, or WCAG 1.3 or 2.4.6.'
---

# WCAG Heading Structure Audit (1.3.1 / 2.4.6)

You are auditing a webpage for proper heading structure. Headings are the primary navigation mechanism for screen reader users — a logical, non-skipping hierarchy is essential for accessibility.

**WCAG criteria:**
- **1.3.1 (A):** Information and structure conveyed through presentation can be programmatically determined
- **2.4.6 (AA):** Headings describe the topic or purpose of the content

**Common issues to detect:**
- Skipped heading levels (H1 → H3 with no H2)
- Multiple H1 elements on one page
- Empty or whitespace-only headings
- Headings used purely for visual styling (bold text as H3, etc.)
- Missing H1 entirely

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture full-page screenshots

```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport desktop --output "<WORKSPACE>/desktop_screenshot.png"
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport mobile  --output "<WORKSPACE>/mobile_screenshot.png"
```

---

## Step 2: Collect headings via JavaScript

Navigate to the URL with the Chrome MCP. Execute this JavaScript:

```javascript
(function() {
  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  return [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden';
  }).map((el, i) => {
    const r = el.getBoundingClientRect();
    return {
      index: i,
      level: parseInt(el.tagName[1]),
      text:  el.textContent.trim().replace(/\s+/g, ' ').slice(0, 120),
      tag:   el.tagName.toLowerCase(),
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
    };
  });
})()
```

Save as `<WORKSPACE>/headings.json`. You only need to collect once — the outline is the same at any viewport.

---

## Step 3: Generate annotated screenshot and outline diagram

```bash
python "<SKILL_DIR>/scripts/heading_overlay.py" \
  --screenshot "<WORKSPACE>/desktop_screenshot.png" \
  --headings   "<WORKSPACE>/headings.json" \
  --output     "<WORKSPACE>/desktop_headings.png" \
  --label      "Desktop (1280px) — Heading Structure Audit"

python "<SKILL_DIR>/scripts/heading_tree.py" \
  --headings "<WORKSPACE>/headings.json" \
  --output   "<WORKSPACE>/heading_outline.png" \
  --url      "<URL>"
```

---

## Step 4: Report to the user

Share the annotated screenshot AND the outline diagram, then provide:

**Heading inventory:**
| Level | Count | Example text |
|-------|-------|-------------|
| H1    | N     | "Page title" |
| H2    | N     | "Section name" |
| ...   |       |              |

**Issues found** (each with heading text, level, and fix suggestion):
- Skipped level: H1 "Title" → H3 "Subsection" — add an H2 between them
- Multiple H1s: "Home" and "Featured" both marked H1 — one should be H2 or lower
- Empty heading: H2 with no text found at position Y=340 — remove or add content

**If no issues:** Confirm the heading hierarchy is logical and well-structured.

**Note on mobile:** The heading structure is typically identical at mobile — run the overlay on the mobile screenshot too if the mobile layout differs significantly (e.g. sections reordered).
