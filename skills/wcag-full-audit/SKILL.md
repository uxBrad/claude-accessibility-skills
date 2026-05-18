---
name: wcag-full-audit
description: 'Run a complete WCAG accessibility audit covering all 11 criteria and generate a PDF report with annotated screenshots and a CSV of issues. Use this skill when someone wants a full accessibility audit, complete WCAG check, comprehensive accessibility report, or to audit all criteria at once. Outputs a PDF report and a CSV issue list. Trigger on: full audit, complete audit, full accessibility check, accessibility report, audit everything, run all checks, WCAG report.'
---

# Full WCAG Accessibility Audit

Runs all 11 accessibility checks in a single automated pass and produces:
- **PDF report** — cover page with summary counts, annotated screenshots for every criterion, full issue tables
- **CSV** — one row per issue for tracking and remediation

The skill directory containing this file is `SKILL_DIR`. Replace all `<SKILL_DIR>` references with that path.

---

## Step 1: Run the audit

```bash
python "<SKILL_DIR>/scripts/run_audit.py" \
  --url "<URL>" \
  --workspace "<WORKSPACE>"
```

This takes 2–5 minutes. It runs Playwright captures, all overlay scripts, and computes verdicts. Progress is printed to the console.

---

## Step 2: Generate the report

```bash
python "<SKILL_DIR>/scripts/generate_report.py" \
  --workspace "<WORKSPACE>" \
  --output-pdf "<WORKSPACE>/accessibility_report.pdf" \
  --output-csv "<WORKSPACE>/accessibility_issues.csv"
```

---

## Step 3: Present to the user

Tell the user:
- The PDF path and CSV path
- The summary: "{fail_count} failures · {needs_review_count} need review"
- Top issues: list the first 3–5 FAIL items across all criteria
- Note that "Needs Review" items require human judgment — the report includes annotated screenshots to aid manual review
