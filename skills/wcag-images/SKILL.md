---
name: wcag-images
description: 'Audit image alternative text for WCAG 1.1.1. Use this skill when someone wants to check if images have proper alt text, find images missing alt attributes, or review whether alt descriptions are meaningful. Generates a contact sheet of every image with its alt text shown below, color-coded by quality — green for good descriptions, red for missing alt, amber for decorative, orange for filename or generic alt. Trigger when the user mentions alt text, alternative text, image descriptions, missing alt, decorative images, or WCAG 1.1.'
---

# WCAG Image Alternative Text Audit (1.1.1)

You are auditing a webpage to ensure all images have meaningful alternative text — a fundamental requirement for users who are blind or have low vision.

**WCAG criterion:**
- **1.1.1 (A):** All non-text content has a text alternative that serves the equivalent purpose. Purely decorative images must have `alt=""` (empty, not absent).

**Alt text quality classification:**
- **good** — descriptive alt text present (passes, shown in green)
- **decorative** — `alt=""` explicitly set (flag for manual verify — is it truly decorative?)
- **missing** — no `alt` attribute at all (WCAG 1.1.1 failure, shown in red)
- **filename** — alt text looks like a filename or path (e.g. `hero_banner_v2.jpg`)
- **generic** — alt contains only generic words (`image`, `photo`, `icon`, `logo`)

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references below with that path.

---

## Step 1: Capture images and metadata

`capture_images.py` navigates to the page, finds every visible image, takes a crop of each, and classifies the alt text automatically.

```bash
python "<SKILL_DIR>/scripts/capture_images.py" \
  --url        "<URL>" \
  --output-dir "<WORKSPACE>/desktop_images" \
  --viewport   desktop

python "<SKILL_DIR>/scripts/capture_images.py" \
  --url        "<URL>" \
  --output-dir "<WORKSPACE>/mobile_images" \
  --viewport   mobile
```

Each run produces:
- `img_NNN.png` — cropped image screenshots
- `image_data.json` — metadata including alt text and status classification

---

## Step 2: Build contact sheets

```bash
python "<SKILL_DIR>/scripts/image_sheet.py" \
  --crops-dir "<WORKSPACE>/desktop_images" \
  --data      "<WORKSPACE>/desktop_images/image_data.json" \
  --output    "<WORKSPACE>/desktop_image_sheet.png" \
  --label     "Desktop (1280px) — Image Alt Text Audit"

python "<SKILL_DIR>/scripts/image_sheet.py" \
  --crops-dir "<WORKSPACE>/mobile_images" \
  --data      "<WORKSPACE>/mobile_images/image_data.json" \
  --output    "<WORKSPACE>/mobile_image_sheet.png" \
  --label     "Mobile (390px) — Image Alt Text Audit"
```

---

## Step 3: Report to the user

Share both contact sheet images, then provide:

**Summary table:**

| Viewport | Total | Good | Decorative | Missing | Filename/Generic |
|----------|-------|------|------------|---------|-----------------|
| Desktop  | N     | N    | N          | N       | N               |
| Mobile   | N     | N    | N          | N       | N               |

**Missing alt text** (WCAG failures — list each):
- Image N: `<img src="hero.jpg">` — no alt attribute. Suggested fix: add descriptive `alt="..."` or `alt=""` if purely decorative.

**Filename/generic alt** (needs improvement):
- Image N: `alt="header_image_final.png"` — replace with a description of what the image shows.
- Image N: `alt="Photo"` — too generic, describe the subject of the photo.

**Decorative images to verify manually:**
- Image N: `alt=""` — confirm this image truly adds no information to the page.

**Note:** Background images set via CSS (`background-image`) are not captured by this audit — check those separately.
