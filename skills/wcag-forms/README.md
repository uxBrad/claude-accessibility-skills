# wcag-forms

Audits every form field on a page for accessible labels, autocomplete attributes, and required indicators. Generates a contact sheet showing each field color-coded by label status.

## WCAG Coverage

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.3.1 Info and Relationships | A | Labels and instructions are programmatically determined |
| 1.3.5 Identify Input Purpose | AA | Input purpose can be programmatically determined (autocomplete tokens) |
| 3.3.2 Labels or Instructions | A | Labels or instructions are provided for user input |

## What it produces

- **Form field contact sheet** — grid of every `input`, `select`, and `textarea` with label status shown and color-coded by result
- Console output listing all fields with their label source, status, and autocomplete value

## Status classification

| Status | Border | Meaning |
|--------|--------|---------|
| `good` | Green | Has a proper programmatic label (aria-labelledby, aria-label, `<label for>`, wrapping label, or title) |
| `placeholder` | Amber | Only has placeholder text — no true accessible label |
| `missing` | Red | No label at all — WCAG 1.3.1 fail |

## Example prompts

- *"Check if all form fields have labels on https://example.com"*
- *"Find any inputs that only use placeholder text as a label"*
- *"Run a form accessibility audit"*
- *"Are there any inputs missing autocomplete attributes on this page?"*
- *"Check WCAG 1.3.5 on the checkout form"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/capture.py` | Playwright: full-page screenshot |
| `scripts/form_sheet.py` | PIL: contact sheet of form fields |

### form_sheet.py CLI

```bash
python scripts/form_sheet.py \
  --data   path/to/form_fields.json \
  --output path/to/output.png \
  --label  "Desktop (1280px) — Form Fields Audit"
```

### form_fields.json format

```json
[
  {
    "index": 0,
    "tag": "input",
    "type": "email",
    "label_text": "Email address",
    "label_source": "label[for]",
    "status": "good",
    "placeholder": "you@example.com",
    "autocomplete": "email",
    "required": true,
    "name": "email",
    "x": 200, "y": 400, "w": 320, "h": 40
  }
]
```

## Common fixes

| Issue | Fix |
|-------|-----|
| Placeholder-only label | Add `<label for="field-id">Label text</label>` or `aria-label="Label text"` on the input |
| Missing label entirely | Add a visible `<label>` — visible labels are preferred over aria-label for cognition |
| Missing autocomplete on personal fields | Add `autocomplete="name"`, `autocomplete="email"`, `autocomplete="tel"` etc. |
| Required not indicated | Add `required` attribute and ensure visible indicator (e.g. asterisk) with explanation |

## Example output — jecture.co/contact/

**Result:** ✓ 3 fields, all pass — Name, Email, and Message all have proper `<label for="">` associations and required indicators.

| Form fields contact sheet |
|--------------------------|
| ![Form fields audit](examples/jecture-co/desktop_form_sheet.png) |
