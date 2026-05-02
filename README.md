# Claude Accessibility Skills

A collection of Claude skills for automated web accessibility auditing. Each skill gives Claude the ability to perform a specific type of accessibility check — producing visual reports, annotated screenshots, and structured summaries.

## What are Claude Skills?

Skills are instructions bundled with helper scripts that extend what Claude can do. Once installed, you invoke them through natural language in any Claude conversation. No commands to memorize — just describe what you want.

## Available Skills

| Skill | WCAG Coverage | What It Produces |
|-------|--------------|-----------------|
| [wcag-keyboard](skills/wcag-keyboard/) | 2.1.1 · 2.1.2 · 2.1.4 | Tab-order heatmap images (desktop + mobile), keyboard flow diagram, summary report |

---

## wcag-keyboard

Audits keyboard accessibility by mapping the full tab order of any webpage and generating annotated heatmap images.

**Example output — [jecture.co](https://jecture.co) homepage:**

| Desktop (1280px) | Mobile (390px) |
|-----------------|----------------|
| ![Desktop heatmap](examples/jecture-co/desktop_heatmap.png) | ![Mobile heatmap](examples/jecture-co/mobile_heatmap.png) |

**Reading the heatmap:**
- **Yellow circles with numbers** — focusable elements in tab order
- **Blue arrows** — keyboard flow direction between tab stops
- **Red boxes** — elements that should be keyboard-accessible but aren't reachable via Tab

**Example prompts:**
- *"Audit the keyboard accessibility of https://example.com"*
- *"Check WCAG 2.1 keyboard access on localhost:3000 and show me the tab order"*
- *"Run a keyboard accessibility heatmap on the mobile view of this page"*

See [skills/wcag-keyboard/README.md](skills/wcag-keyboard/README.md) for full details.

---

## Requirements

Before using any skill in this collection you need:

1. **Claude desktop app** — [claude.ai/download](https://claude.ai/download)
2. **Claude in Chrome extension** — Required for browser automation. Install from the Chrome Web Store, then connect it to Claude via Settings → Extensions.
3. **Python 3.9+** with these packages:
   ```
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

Copy the skill folder (e.g. `skills/wcag-keyboard/`) anywhere on your machine, then add that folder path to Claude's skill settings.

---

## Using a Skill

Once installed, just describe what you want in a Claude conversation. Examples:

> *"Can you audit the keyboard accessibility of https://mysite.com?"*

> *"I want to see the tab order on localhost:8080 — desktop and mobile views"*

> *"Check if there are any keyboard traps on this page"*

Claude will pick up the relevant skill, navigate to the URL using the Chrome extension, run the analysis, generate the visual report, and share the results in your conversation.

---

## Repository Structure

```
claude-accessibility-skills/
├── skills/
│   └── wcag-keyboard/
│       ├── SKILL.md          # Skill instructions (loaded by Claude)
│       ├── README.md         # Human-readable documentation
│       └── scripts/
│           ├── heatmap.py    # Annotated image generator
│           └── capture.py    # Full-page screenshot via Playwright
├── examples/
│   └── jecture-co/
│       ├── desktop_heatmap.png
│       └── mobile_heatmap.png
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