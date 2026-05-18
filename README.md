# Claude Accessibility Skills

A collection of Claude skills for automated web accessibility auditing. Each skill gives Claude the ability to perform a specific type of accessibility check — producing visual heatmaps, annotated screenshots, and structured reports.

## What are Claude Skills?

Skills are instructions bundled with helper scripts that extend what Claude can do. Once installed, you invoke them through natural language in any Claude conversation. No commands to memorize — just describe what you want.

## Available Skills

| Skill | WCAG Coverage | What It Produces |
|-------|--------------|-----------------|
| [wcag-keyboard](skills/wcag-keyboard/) | 2.1.1 · 2.1.2 · 2.1.4 | Tab-order heatmap (desktop + mobile), keyboard flow diagram, summary report |
| [wcag-touch-targets](skills/wcag-touch-targets/) | 2.5.5 · 2.5.8 | Color-coded size heatmap showing every interactive element (green/yellow/red) |
| [wcag-focus-indicators](skills/wcag-focus-indicators/) | 2.4.7 · 2.4.11 | Contact sheet of every focusable element in its focused state |
| [wcag-color-contrast](skills/wcag-color-contrast/) | 1.4.3 · 1.4.6 | Annotated screenshot with contrast ratio badges on failing text |

---

## wcag-keyboard

Maps the full keyboard tab order and generates a heatmap showing tab stops, flow arrows, and elements missing from the tab order.

**Example output — [jecture.co](https://jecture.co) homepage:**

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop keyboard heatmap](examples/jecture-co/desktop_heatmap.png) | ![Mobile keyboard heatmap](examples/jecture-co/mobile_heatmap.png) |

**Example prompts:**
- *"Audit the keyboard accessibility of https://example.com"*
- *"Check WCAG 2.1 keyboard access on localhost:3000 and show me the tab order"*

---

## wcag-touch-targets

Checks whether interactive elements meet WCAG minimum tap target sizes. Critical for mobile usability and users with motor disabilities.

**Color coding:** Green = AAA pass (>=44x44px) · Yellow = AA pass (>=24x24px) · Red = fails minimum size

**Example output — [jecture.co](https://jecture.co) homepage:**

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop touch target heatmap](examples/jecture-co/touch-targets/desktop_targets.png) | ![Mobile touch target heatmap](examples/jecture-co/touch-targets/mobile_targets.png) |

**Example prompts:**
- *"Check if the buttons on this page are large enough to tap on mobile"*
- *"Run a WCAG 2.5 touch target audit on https://example.com"*

---

## wcag-focus-indicators

Photographs every focusable element in its focused state using pixel-diff detection, then assembles a contact sheet for visual review.

**Color coding:** Green border = focus visible · Red border = no focus indicator detected

**Example output — [jecture.co](https://jecture.co) homepage:**

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop focus contact sheet](examples/jecture-co/focus-indicators/desktop_focus_sheet.png) | ![Mobile focus contact sheet](examples/jecture-co/focus-indicators/mobile_focus_sheet.png) |

**Example prompts:**
- *"Check if all interactive elements have visible focus rings on https://example.com"*
- *"Find elements where outline:none removed the focus indicator"*

---

## wcag-color-contrast

Scans all visible text, calculates WCAG contrast ratios against computed backgrounds, and marks failures with ratio badges on the screenshot.

**Example output — [jecture.co](https://jecture.co) homepage:**

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop contrast audit](examples/jecture-co/color-contrast/desktop_contrast.png) | ![Mobile contrast audit](examples/jecture-co/color-contrast/mobile_contrast.png) |

**Example prompts:**
- *"Check the color contrast on https://example.com"*
- *"Find all text that fails WCAG 1.4.3 on this page"*

---

## Requirements

Before using any skill in this collection you need:

1. **Claude desktop app** — [claude.ai/download](https://claude.ai/download)
2. **Claude in Chrome extension** — Required for browser automation. Install from the Chrome Web Store, then connect it to Claude via Settings → Extensions.
3. **Python 3.9+** with these packages:
   ```bash
   pip install pillow playwright
   python -m playwright install chromium
   ```

---

## Installing a Skill

### Option 1 — Clone this repo and point Claude at it

```bash
git clone https://github.com/uxBrad/claude-accessibility-skills.git
```

Then in Claude settings (Settings → Skills → Add skill folder), add the `skills/` directory from this repo. Claude will automatically detect all skills inside.

### Option 2 — Copy an individual skill

Copy any skill folder (e.g. `skills/wcag-keyboard/`) anywhere on your machine, then add that folder path to Claude's skill settings.

---

## Using a Skill

Once installed, just describe what you want in a Claude conversation:

> *"Can you audit the keyboard accessibility of https://mysite.com?"*

> *"Check touch target sizes on localhost:8080 — desktop and mobile"*

> *"Find any text with low contrast on this page"*

> *"Are there any missing focus indicators on this site?"*

Claude picks up the relevant skill, navigates to the URL using the Chrome extension, runs the analysis, generates the visual report, and shares everything in your conversation.

---

## Repository Structure

```
claude-accessibility-skills/
├── skills/
│   ├── wcag-keyboard/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── scripts/
│   │       ├── heatmap.py
│   │       └── capture.py
│   ├── wcag-touch-targets/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── scripts/
│   │       ├── capture.py
│   │       └── target_heatmap.py
│   ├── wcag-focus-indicators/
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   └── scripts/
│   │       ├── capture_focus.py
│   │       └── contact_sheet.py
│   └── wcag-color-contrast/
│       ├── SKILL.md
│       ├── README.md
│       └── scripts/
│           ├── capture.py
│           └── contrast_overlay.py
├── examples/
│   └── jecture-co/
│       ├── desktop_heatmap.png
│       ├── mobile_heatmap.png
│       ├── touch-targets/
│       │   ├── desktop_targets.png
│       │   └── mobile_targets.png
│       ├── focus-indicators/
│       │   ├── desktop_focus_sheet.png
│       │   └── mobile_focus_sheet.png
│       └── color-contrast/
│           ├── desktop_contrast.png
│           └── mobile_contrast.png
└── README.md
```

---

## Contributing

Contributions are welcome — new skills, improvements to existing ones, bug fixes, or additional examples.

**To add a new skill:**

1. Fork this repo and create a branch
2. Create a folder under `skills/your-skill-name/`
3. Write a `SKILL.md` with YAML frontmatter (`name` and `description` fields) followed by instructions for Claude
4. Add a `README.md` explaining what the skill does, example output, and any requirements
5. Include example output in `examples/your-skill-name/` if possible
6. Open a pull request

**SKILL.md frontmatter format:**
```yaml
---
name: your-skill-name
description: 'One or two sentences. When to use this skill and what it produces.'
---
```

The `description` field is what Claude reads to decide when to activate the skill — make it specific about the contexts and user phrases that should trigger it.

---

## License

MIT