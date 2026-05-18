---
name: wcag-links
description: 'Audit link text quality for WCAG 2.4.4 and 2.4.9. Use this skill when someone wants to find vague links like click here or read more, check for icon-only links without accessible labels, or verify that link text makes sense out of context. Generates an annotated screenshot with red badges on failing links and orange badges on ambiguous ones. Trigger when the user mentions link text, click here, read more, ambiguous links, icon-only links, accessible link names, or WCAG 2.4.4.'
---

# WCAG Link Purpose Audit (2.4.4 / 2.4.9)

You are auditing a webpage for descriptive, meaningful link text. Screen reader users often navigate by tabbing through links or pulling up a list of all links — every link must make sense in isolation.

**WCAG criteria:**
- **2.4.4 (AA):** Purpose of each link can be determined from the link text alone, or from the link text and its programmatic context
- **2.4.9 (AAA):** Purpose of each link can be determined from the link text alone

**Flag categories:**
- **vague** — well-known non-descriptive phrases: "click here", "here", "read more", "learn more", "more info", "this", "link", "go", "continue" → FAIL
- **empty** — link has no text and no aria-label (icon-only, invisible to screen readers) → FAIL
- **url** — link text is a raw URL (screen readers read every character) → FAIL
- **short** — 1-3 character text that isn't meaningful (">", "»", lone letters) → FAIL
- **generic** — contextually ambiguous but shorter list: "more", "view", "see", "details" → WARN

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture full-page screenshots

```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport desktop --output "<WORKSPACE>/desktop_screenshot.png"
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport mobile  --output "<WORKSPACE>/mobile_screenshot.png"
```

---

## Step 2: Collect all links via JavaScript

Navigate to the URL with the Chrome MCP. Execute this JavaScript:

```javascript
(function() {
  const VAGUE = new Set([
    "click here","here","read more","more info","more information","learn more",
    "see more","view more","find out more","this","this link","link","button",
    "click","press","tap","go","continue","next","previous","prev",
    "details","detail","info","information","see details","view details"
  ]);
  const GENERIC = new Set(["more","view","see","get","open","show","check","visit"]);
  const URL_RE = /^https?:\/\/|^www\./i;

  function classify(text, ariaLabel, href) {
    const effective = (ariaLabel || text || "").trim();
    if (!effective) return "empty";
    const low = effective.toLowerCase().replace(/[.,!?;:\s]+$/,"").trim();
    if (VAGUE.has(low)) return "vague";
    if (URL_RE.test(low) && !low.includes(" ")) return "url";
    const words = low.split(/\s+/);
    if (words.length <= 2 && words.every(w => GENERIC.has(w))) return "generic";
    if (effective.length <= 3) return "short";
    return "ok";
  }

  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  return [...document.querySelectorAll("a[href]")].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== "none" && s.visibility !== "hidden" && el.offsetParent !== null;
  }).map((el, i) => {
    const r = el.getBoundingClientRect();
    const text = el.textContent.trim().replace(/\s+/g," ");
    const ariaLabel = el.getAttribute("aria-label") || "";
    const href = el.getAttribute("href") || "";
    const flag = classify(text, ariaLabel, href);
    return {
      index: i,
      tag: el.tagName.toLowerCase(),
      text: text.slice(0, 80),
      aria_label: ariaLabel.slice(0, 80),
      href: href.slice(0, 100),
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
      flag: flag,
    };
  }).filter(l => l.w > 0 && l.h > 0);
})()
```

Save as `<WORKSPACE>/desktop_links.json`. Repeat at mobile viewport (resize, reload, re-run) and save as `<WORKSPACE>/mobile_links.json`.

---

## Step 3: Generate annotated screenshots

```bash
python "<SKILL_DIR>/scripts/link_overlay.py" \
  --screenshot "<WORKSPACE>/desktop_screenshot.png" \
  --links      "<WORKSPACE>/desktop_links.json" \
  --output     "<WORKSPACE>/desktop_links_audit.png" \
  --label      "Desktop (1280px) — Link Purpose Audit"

python "<SKILL_DIR>/scripts/link_overlay.py" \
  --screenshot "<WORKSPACE>/mobile_screenshot.png" \
  --links      "<WORKSPACE>/mobile_links.json" \
  --output     "<WORKSPACE>/mobile_links_audit.png" \
  --label      "Mobile (390px) — Link Purpose Audit"
```

---

## Step 4: Report to the user

Share both annotated screenshots, then provide:

**Summary table:**

| Viewport | Total links | Fail (vague/empty) | Warn (generic) | Pass |
|----------|-------------|-------------------|----------------|------|
| Desktop  | N           | N                 | N              | N    |
| Mobile   | N           | N                 | N              | N    |

**Failing links** — list each with: flag type, link text (or "no text"), suggested fix:
- VAGUE: "Read more" → Replace with "Read more about [topic]" or use `aria-label`
- EMPTY: `<a href="/cart"><svg>...</svg></a>` → Add `aria-label="Shopping cart"` to the link
- URL: "https://example.com/very/long/path" → Replace with "Visit our partner site"

**Fix patterns:**
- For "read more" links: add `aria-label="Read more about [article title]"` on the `<a>` element
- For icon-only links: add `aria-label` describing the destination or action
- For "click here": rewrite the surrounding sentence so the link text is naturally descriptive
