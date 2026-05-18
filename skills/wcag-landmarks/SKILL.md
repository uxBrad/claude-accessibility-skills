---
name: wcag-landmarks
description: 'Audit page landmark regions for WCAG 1.3.6 and 2.4.1. Use this skill when someone wants to check if a page has proper landmark structure, verify that screen reader users can navigate by landmarks, find missing or duplicate landmarks, or check that multiple nav elements have accessible names. Generates an annotated screenshot with color-coded landmark overlays. Trigger when the user mentions landmarks, page regions, skip navigation, banner, main content area, ARIA landmarks, navigation regions, or WCAG 2.4.1.'
---

# WCAG Landmark Regions Audit (1.3.6 / 2.4.1)

You are auditing a webpage for proper ARIA landmark structure. Landmarks are the primary way screen reader users jump between major sections of a page — missing, duplicate, or unlabelled landmarks create serious navigation barriers.

**WCAG criteria:**
- **1.3.6 (AAA):** The purpose of UI components, icons, and regions can be programmatically determined
- **2.4.1 (A):** A mechanism is available to bypass blocks of content that are repeated on multiple pages (landmarks + skip links satisfy this)

**Landmark roles and their HTML equivalents:**
| Role | Native element(s) |
|------|-------------------|
| `banner` | `<header>` (at page level) |
| `navigation` | `<nav>` |
| `main` | `<main>` |
| `complementary` | `<aside>` |
| `contentinfo` | `<footer>` (at page level) |
| `search` | `<search>` or `role="search"` |
| `form` | `<form>` (with accessible name) |
| `region` | `<section>` with accessible name |

**Issues to detect:**
- No `main` landmark → **FAIL** (critical — screen reader users have no way to jump to main content)
- Multiple `main` landmarks → **FAIL** (only one `main` is valid per page)
- No `navigation` landmark → **WARN** (acceptable on single-purpose pages, e.g. a form page)
- No `banner` landmark → **WARN**
- No `contentinfo` landmark → **WARN**
- Multiple `nav` / `navigation` landmarks without accessible names → **WARN** (users cannot distinguish them)

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture full-page screenshots

```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport desktop --output "<WORKSPACE>/desktop_screenshot.png"
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport mobile  --output "<WORKSPACE>/mobile_screenshot.png"
```

---

## Step 2: Collect landmarks via JavaScript

Navigate to the URL in the Chrome MCP at **desktop** viewport (1280px wide). Execute this JavaScript and save the result as `<WORKSPACE>/desktop_landmarks.json`:

```javascript
(function() {
  const ROLE_MAP = {
    header: 'banner', nav: 'navigation', main: 'main',
    aside: 'complementary', footer: 'contentinfo',
    form: 'form', section: 'region',
  };
  const ARIA_ROLES = ['banner','navigation','main','complementary','contentinfo','search','form','region','application'];

  function getAccessibleName(el) {
    return el.getAttribute('aria-label') ||
           (el.getAttribute('aria-labelledby') && document.getElementById(el.getAttribute('aria-labelledby'))?.textContent?.trim()) ||
           el.getAttribute('title') || '';
  }

  const scrollY = window.pageYOffset || 0;
  const results = [];

  // Native landmark elements
  document.querySelectorAll('header, nav, main, aside, footer, form, section[aria-label], section[aria-labelledby]').forEach((el, i) => {
    const s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role') || ROLE_MAP[tag] || 'region';
    results.push({
      index: results.length,
      tag,
      role,
      accessible_name: getAccessibleName(el),
      x: Math.round(r.left + window.pageXOffset),
      y: Math.round(r.top + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
    });
  });

  // ARIA role landmarks not already captured
  ARIA_ROLES.forEach(role => {
    document.querySelectorAll('[role="' + role + '"]').forEach(el => {
      const s = window.getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden') return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (results.some(res => res.x === Math.round(r.left) && res.y === Math.round(r.top + scrollY))) return;
      results.push({
        index: results.length,
        tag: el.tagName.toLowerCase(),
        role,
        accessible_name: getAccessibleName(el),
        x: Math.round(r.left + window.pageXOffset),
        y: Math.round(r.top + scrollY),
        w: Math.round(r.width),
        h: Math.round(r.height),
      });
    });
  });

  return results;
})()
```

Then resize the Chrome MCP to **mobile** viewport (390px wide), navigate to the same URL, run the same script, and save as `<WORKSPACE>/mobile_landmarks.json`.

---

## Step 3: Generate annotated screenshots

```bash
python "<SKILL_DIR>/scripts/landmark_overlay.py" \
  --screenshot "<WORKSPACE>/desktop_screenshot.png" \
  --landmarks  "<WORKSPACE>/desktop_landmarks.json" \
  --output     "<WORKSPACE>/desktop_landmarks.png" \
  --label      "Desktop (1280px) — Landmark Regions Audit"

python "<SKILL_DIR>/scripts/landmark_overlay.py" \
  --screenshot "<WORKSPACE>/mobile_screenshot.png" \
  --landmarks  "<WORKSPACE>/mobile_landmarks.json" \
  --output     "<WORKSPACE>/mobile_landmarks.png" \
  --label      "Mobile (390px) — Landmark Regions Audit"
```

---

## Step 4: Report to the user

Share **both** annotated screenshots, then provide:

**Landmarks found** (desktop):
| Role | Tag | Accessible Name | Dimensions |
|------|-----|-----------------|------------|
| `main` | `<main>` | — | 1280 × 2400 |
| `navigation` | `<nav>` | "Primary" | 1280 × 64 |
| … | | | |

**Issues found** (each with role, severity, and fix suggestion):
- No `main` landmark — **FAIL**: add `<main>` around the primary content
- Multiple `nav` elements with no accessible names — **WARN**: add `aria-label` to each
- No `banner` landmark — **WARN**: wrap the site header in `<header>`

**If no issues:** Confirm that the landmark structure is complete and well-labelled.

**Note on mobile:** Mobile layouts often drop or reorder landmarks (e.g. nav collapses into a drawer). Always check both viewports and flag any differences.

---

## Suggested fix patterns

**Missing `main` landmark:**
```html
<!-- Option A: semantic HTML -->
<main id="main-content">
  <!-- page-specific content -->
</main>

<!-- Option B: ARIA role on existing div -->
<div role="main" id="main-content">
  <!-- page-specific content -->
</div>
```

**Multiple `nav` elements without accessible names:**
```html
<!-- Before (ambiguous) -->
<nav>…</nav>
<nav>…</nav>

<!-- After (distinguishable) -->
<nav aria-label="Primary navigation">…</nav>
<nav aria-label="Breadcrumbs">…</nav>
<nav aria-label="Footer links">…</nav>
```

**Missing skip link (pairs with `main` landmark to satisfy WCAG 2.4.1):**
```html
<!-- In <head> or very start of <body> -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- CSS to show on focus only -->
<style>
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #000;
  color: #fff;
  padding: 8px 16px;
  z-index: 9999;
  text-decoration: none;
}
.skip-link:focus { top: 0; }
</style>

<!-- The target -->
<main id="main-content">…</main>
```

**Missing `banner` / `contentinfo`:**
```html
<!-- Banner -->
<header>
  <a href="/">Logo</a>
  <nav aria-label="Primary navigation">…</nav>
</header>

<!-- Content info -->
<footer>
  <p>© 2026 Company Name</p>
</footer>
```
