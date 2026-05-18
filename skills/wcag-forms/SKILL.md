---
name: wcag-forms
description: 'Audit form fields for accessible labels, autocomplete attributes, and required indicators. Use this skill when someone wants to check if form inputs have proper labels, find inputs that rely only on placeholder text as a label, check for missing autocomplete attributes, or verify WCAG 1.3.1 and 1.3.5 compliance. Generates a contact sheet of every form field color-coded by label status. Trigger when the user mentions form labels, input accessibility, autocomplete, required fields, WCAG 1.3.5, or placeholder text.'
---

# WCAG Forms Accessibility Audit (1.3.1 / 1.3.5 / 3.3.2)

You are auditing a webpage for accessible form fields. Every visible input, select, and textarea must have a proper programmatic label, appropriate autocomplete attributes on personal-data fields, and clearly communicated required-field status.

**WCAG criteria:**
- **1.3.1 (A):** Info and Relationships — labels and instructions are programmatically determinable
- **1.3.5 (AA):** Identify Input Purpose — inputs that collect personal data expose an `autocomplete` token
- **3.3.2 (A):** Labels or Instructions — labels or instructions are provided when content requires user input

**Status classification:**
- **good** — has a proper programmatic label (aria-labelledby, aria-label, `<label for="">`, wrapping `<label>`, or title) → green border, **PASS**
- **placeholder** — only placeholder text serves as a label, no true label → amber border, **WARN — placeholder only**
- **missing** — no label of any kind → red border, **FAIL — no label**

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture a full-page screenshot

```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport desktop --output "<WORKSPACE>/desktop_screenshot.png"
```

For mobile as well (optional but recommended):
```bash
python "<SKILL_DIR>/scripts/capture.py" --url "<URL>" --viewport mobile --output "<WORKSPACE>/mobile_screenshot.png"
```

Install Playwright if needed: `pip install playwright && playwright install chromium`

---

## Step 2: Collect all form fields via JavaScript (Chrome MCP)

Navigate to the URL with the Chrome MCP (`mcp__Claude_in_Chrome__navigate`), then execute the following JavaScript using `mcp__Claude_in_Chrome__javascript_tool`. Save the result as `<WORKSPACE>/desktop_fields.json`.

```javascript
(function() {
  function getLabel(el) {
    // aria-labelledby
    const lbId = el.getAttribute('aria-labelledby');
    if (lbId) {
      const text = lbId.split(' ').map(id => document.getElementById(id)?.textContent?.trim()).filter(Boolean).join(' ');
      if (text) return { text, source: 'aria-labelledby' };
    }
    // aria-label
    const al = el.getAttribute('aria-label');
    if (al?.trim()) return { text: al.trim(), source: 'aria-label' };
    // <label for="">
    if (el.id) {
      const lbl = document.querySelector('label[for="' + el.id + '"]');
      if (lbl?.textContent?.trim()) return { text: lbl.textContent.trim(), source: 'label[for]' };
    }
    // wrapping label
    const parent = el.closest('label');
    if (parent) {
      const clone = parent.cloneNode(true);
      clone.querySelectorAll('input,select,textarea').forEach(n => n.remove());
      const text = clone.textContent.trim();
      if (text) return { text, source: 'label-wrap' };
    }
    // title
    const title = el.getAttribute('title');
    if (title?.trim()) return { text: title.trim(), source: 'title' };
    // placeholder only
    const ph = el.getAttribute('placeholder');
    if (ph?.trim()) return { text: ph.trim(), source: 'placeholder' };
    return { text: '', source: 'none' };
  }

  function classify(el, labelSource) {
    if (labelSource === 'none') return 'missing';
    if (labelSource === 'placeholder') return 'placeholder';
    return 'good';
  }

  const scrollY = window.pageYOffset || 0;
  return [...document.querySelectorAll('input:not([type="hidden"]), select, textarea')]
    .filter(el => {
      const s = window.getComputedStyle(el);
      return s.display !== 'none' && s.visibility !== 'hidden' && el.offsetParent !== null;
    })
    .map((el, i) => {
      const r = el.getBoundingClientRect();
      const { text: labelText, source: labelSource } = getLabel(el);
      return {
        index: i,
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || el.tagName.toLowerCase(),
        label_text: labelText,
        label_source: labelSource,
        status: classify(el, labelSource),
        placeholder: el.getAttribute('placeholder') || '',
        autocomplete: el.getAttribute('autocomplete') || '',
        required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
        name: el.getAttribute('name') || '',
        x: Math.round(r.left + window.pageXOffset),
        y: Math.round(r.top + scrollY),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    });
})()
```

For a mobile viewport audit, resize the browser to 390 px wide, reload, and re-run the script — save the result as `<WORKSPACE>/mobile_fields.json`.

---

## Step 3: Generate the contact sheet

```bash
python "<SKILL_DIR>/scripts/form_sheet.py" \
  --data   "<WORKSPACE>/desktop_fields.json" \
  --output "<WORKSPACE>/desktop_form_sheet.png" \
  --label  "Desktop (1280px) — Form Fields Audit"
```

For mobile:
```bash
python "<SKILL_DIR>/scripts/form_sheet.py" \
  --data   "<WORKSPACE>/mobile_fields.json" \
  --output "<WORKSPACE>/mobile_form_sheet.png" \
  --label  "Mobile (390px) — Form Fields Audit"
```

Install Pillow if needed: `pip install Pillow`

---

## Step 4: Report to the user

Display the contact sheet image(s), then provide:

### Summary table

| Viewport | Total fields | PASS (good label) | WARN (placeholder only) | FAIL (no label) |
|----------|-------------|-------------------|-------------------------|-----------------|
| Desktop  | N           | N                 | N                       | N               |
| Mobile   | N           | N                 | N                       | N               |

### Failing and warning fields

List every field with status `missing` or `placeholder` using this format:

| # | Tag/Type | Name | Status | Issue | Suggested fix |
|---|----------|------|--------|-------|---------------|
| 3 | input[email] | email | FAIL — no label | No label of any kind | Add `<label for="email">Email address</label>` or `aria-label="Email address"` |
| 7 | input[text] | search | WARN — placeholder only | Only placeholder="Search…" as label | Add a visible `<label>` — placeholder disappears on input and is not announced by all screen readers |

### Fix patterns

**Placeholder-only fields** — placeholder text disappears on input and has poor screen-reader support as a sole label:
```html
<!-- Before -->
<input type="text" placeholder="First name">

<!-- After: explicit label -->
<label for="fname">First name</label>
<input type="text" id="fname" placeholder="First name">

<!-- Or: aria-label if a visible label is not possible -->
<input type="text" aria-label="First name" placeholder="First name">
```

**Missing labels** — add a visible or programmatic label:
```html
<label for="email">Email address</label>
<input type="email" id="email">
```

**Missing autocomplete on personal data fields** — add the appropriate token (WCAG 1.3.5):
```html
<input type="text"     autocomplete="given-name">
<input type="text"     autocomplete="family-name">
<input type="email"    autocomplete="email">
<input type="tel"      autocomplete="tel">
<input type="text"     autocomplete="street-address">
<input type="password" autocomplete="current-password">
```
Full token list: https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill

**Required fields** — clearly indicate required status both visually and programmatically:
```html
<label for="email">Email address <span aria-hidden="true">*</span></label>
<input type="email" id="email" required aria-required="true">
<!-- And note near the form: "Fields marked * are required" -->
```
