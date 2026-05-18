# wcag-full-audit

Runs all 11 WCAG audit skills in a single automated pass and produces a PDF report with annotated screenshots for every criterion, plus a CSV of every issue for tracking and remediation.

## What it produces

- **PDF report** — cover page with summary counts, per-criterion sections with annotated screenshots and issue tables, passed criteria listed at the end
- **CSV** — one row per issue across all criteria, ready to open in Excel or import into a project tracker

## Verdict tiers

| Verdict | Meaning |
|---------|---------|
| **Fail** | Automation can confirm the violation with confidence |
| **Needs Review** | Automation flagged something that requires human judgment |

Most items default to Needs Review — the screenshots and issue descriptions are there to make that manual check as fast as possible.

## Criteria covered

| Skill | WCAG | Level |
|-------|------|-------|
| Link Purpose | 2.4.4 / 2.4.9 | AA |
| Non-text Content | 1.1.1 | A |
| Heading Structure | 1.3.1 / 2.4.6 | A/AA |
| Form Labels | 1.3.1 / 1.3.5 / 3.3.2 | A/AA |
| Landmark Regions | 1.3.6 / 2.4.1 | AAA/A |
| Reflow | 1.4.10 | AA |
| Text Spacing | 1.4.12 | AA |
| Color Contrast | 1.4.3 / 1.4.6 | AA/AAA |
| Touch Target Size | 2.5.5 / 2.5.8 | AAA/AA |
| Focus Indicators | 2.4.7 / 2.4.11 | AA |
| Keyboard Accessibility | 2.1.1 / 2.4.3 | A/AA |

## Example prompts

- *"Run a full accessibility audit on https://example.com"*
- *"Give me a complete WCAG report for this site"*
- *"Audit everything and give me a PDF"*
- *"Full accessibility check on localhost:3000"*

## Requirements

- Claude desktop app with Chrome extension connected
- Python 3.9+ with `pip install pillow playwright`
- `python -m playwright install chromium`
- All 11 sub-skills installed in the same `skills/` directory

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_audit.py` | Orchestrates all captures, overlays, and verdict computation |
| `scripts/generate_report.py` | Generates PDF and CSV from audit results |

### run_audit.py CLI

```bash
python scripts/run_audit.py \
  --url https://example.com \
  --workspace path/to/output/
```

Takes 2–5 minutes. Runs Playwright DOM collection, 5 parallel capture subprocesses, 15 parallel overlay scripts, then computes verdicts. Outputs `audit_results.json` and all annotated screenshots.

### generate_report.py CLI

```bash
python scripts/generate_report.py \
  --workspace  path/to/output/ \
  --output-pdf path/to/report.pdf \
  --output-csv path/to/issues.csv
```

## CSV format

| Column | Description |
|--------|-------------|
| `url` | Page audited |
| `audit_date` | ISO 8601 timestamp |
| `criterion` | Human-readable criterion name |
| `wcag_id` | WCAG success criterion ID(s) |
| `wcag_level` | A / AA / AAA |
| `verdict` | `fail` or `needs_review` |
| `element` | Element description |
| `description` | What was found |
| `location` | x/y coordinates on page |
| `suggested_fix` | Recommended remediation |

## Example output — jecture.co

**Result:** 12 failures · 50 need review across 11 criteria

| | |
|--|--|
| PDF report cover (4.6MB, 11 criteria) | CSV with 62 issue rows |

The 12 failures were: 3 empty blog card links (WCAG 2.4.4), several touch targets below 24×24px, and focus indicator issues where no visible change was detected on focus.
