"""
generate_report.py — WCAG Full Audit Report Generator

Reads audit_results.json from a workspace directory and generates:
  - A PDF report (via Playwright HTML→PDF)
  - A CSV of all issues

Usage:
  python generate_report.py \
    --workspace DIR \
    --output-pdf PATH \
    --output-csv PATH
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLORS = {
    "bg":           "#141414",
    "card":         "#1e1e1e",
    "border":       "#2a2a2a",
    "text":         "#e8e8e8",
    "text_sec":     "#999",
    "red":          "#c0392b",
    "red_light":    "#e74c3c",
    "amber":        "#d4870a",
    "amber_light":  "#f39c12",
    "green":        "#27ae60",
    "blue":         "#2980b9",
    "purple":       "#8e44ad",
}

LEVEL_COLORS = {
    "A":   COLORS["green"],
    "AA":  COLORS["blue"],
    "AAA": COLORS["purple"],
}

FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
GLOBAL_CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: {COLORS['bg']};
  color: {COLORS['text']};
  font-family: {FONT_STACK};
  font-size: 13px;
  line-height: 1.5;
}}
.page-break {{ page-break-after: always; }}
.page-break-before {{ page-break-before: always; }}

/* Cover */
.cover {{
  width: 100%;
  min-height: 100vh;
  padding: 48px 56px;
  display: flex;
  flex-direction: column;
  gap: 32px;
}}
.cover-eyebrow {{
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: {COLORS['text_sec']};
}}
.cover-url {{
  font-size: 32px;
  font-weight: 700;
  color: {COLORS['text']};
  word-break: break-all;
  margin-top: 4px;
}}
.cover-date {{
  font-size: 14px;
  color: {COLORS['text_sec']};
  margin-top: 6px;
}}
.stat-row {{
  display: flex;
  gap: 24px;
  margin-top: 8px;
}}
.stat-box {{
  flex: 1;
  border-radius: 10px;
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.stat-box.fail {{ background: {COLORS['red']}; }}
.stat-box.review {{ background: {COLORS['amber']}; }}
.stat-number {{
  font-size: 72px;
  font-weight: 900;
  line-height: 1;
  color: #fff;
}}
.stat-label {{
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.85);
}}

/* Summary table */
.summary-table {{
  width: 100%;
  border-collapse: collapse;
  margin-top: 8px;
  font-size: 12px;
}}
.summary-table th {{
  text-align: left;
  padding: 8px 12px;
  background: {COLORS['card']};
  color: {COLORS['text_sec']};
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 11px;
  border-bottom: 1px solid {COLORS['border']};
}}
.summary-table td {{
  padding: 8px 12px;
  border-bottom: 1px solid {COLORS['border']};
}}
.summary-table tr:last-child td {{ border-bottom: none; }}
.summary-table tr:nth-child(even) td {{ background: rgba(255,255,255,0.02); }}
.pass-indicator {{
  color: {COLORS['green']};
  font-weight: 600;
}}

/* Footer */
.cover-footer {{
  margin-top: auto;
  font-size: 11px;
  color: {COLORS['text_sec']};
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid {COLORS['border']};
}}

/* Criterion section */
.criterion-section {{
  padding: 32px 40px;
}}
.criterion-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: {COLORS['card']};
  border-radius: 8px 8px 0 0;
  padding: 16px 20px;
  border-bottom: 1px solid {COLORS['border']};
  gap: 16px;
}}
.criterion-name {{
  font-size: 18px;
  font-weight: 700;
  color: {COLORS['text']};
  flex: 1;
}}
.badge-group {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}}
.wcag-badge {{
  display: inline-block;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.04em;
}}
.level-badge {{
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.04em;
}}
.criterion-body {{
  background: {COLORS['card']};
  border-radius: 0 0 8px 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}}
.criterion-description {{
  color: {COLORS['text_sec']};
  font-size: 13px;
  line-height: 1.6;
}}

/* Screenshots */
.screenshot-row {{
  display: flex;
  gap: 12px;
  align-items: flex-start;
}}
.screenshot-single img {{
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid {COLORS['border']};
  display: block;
}}
.screenshot-desktop {{
  flex: 0 0 60%;
}}
.screenshot-mobile {{
  flex: 0 0 38%;
}}
.screenshot-desktop img,
.screenshot-mobile img {{
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid {COLORS['border']};
  display: block;
}}
.extra-images {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 4px;
}}
.extra-images img {{
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid {COLORS['border']};
}}

/* Issues table */
.issues-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}}
.issues-table th {{
  text-align: left;
  padding: 8px 12px;
  background: rgba(0,0,0,0.3);
  color: {COLORS['text_sec']};
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-size: 11px;
  border-bottom: 1px solid {COLORS['border']};
}}
.issues-table td {{
  padding: 9px 12px;
  border-bottom: 1px solid {COLORS['border']};
  vertical-align: top;
}}
.issues-table tr:nth-child(even) td {{ background: rgba(255,255,255,0.025); }}
.issues-table tr:last-child td {{ border-bottom: none; }}
.verdict-badge {{
  display: inline-block;
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: #fff;
  white-space: nowrap;
}}
.verdict-fail {{ background: {COLORS['red']}; }}
.verdict-needs-review {{ background: {COLORS['amber']}; }}
.element-code {{
  font-family: 'Courier New', Courier, monospace;
  font-size: 11px;
  background: rgba(0,0,0,0.3);
  padding: 2px 5px;
  border-radius: 3px;
  word-break: break-all;
}}
.no-issues-banner {{
  background: rgba(39,174,96,0.15);
  border: 1px solid {COLORS['green']};
  border-radius: 6px;
  padding: 14px 20px;
  color: {COLORS['green']};
  font-weight: 600;
  font-size: 14px;
}}

/* Passed section */
.passed-section {{
  padding: 32px 40px;
}}
.passed-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
.passed-table th {{
  text-align: left;
  padding: 8px 12px;
  background: {COLORS['card']};
  color: {COLORS['text_sec']};
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 11px;
  border-bottom: 1px solid {COLORS['border']};
}}
.passed-table td {{
  padding: 9px 12px;
  border-bottom: 1px solid {COLORS['border']};
}}
.passed-table tr:last-child td {{ border-bottom: none; }}
.passed-table tr:nth-child(even) td {{ background: rgba(255,255,255,0.02); }}
"""


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def esc(text: str) -> str:
    """HTML-escape a string."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def image_tag(path_str: str, style: str = "") -> str:
    """Return an <img> tag for a file path, using file:/// URI with forward slashes.
    Returns empty string if the file does not exist."""
    p = Path(path_str)
    if not p.exists():
        return ""
    uri = "file:///" + p.as_posix().lstrip("/")
    style_attr = f' style="{style}"' if style else ""
    return f'<img src="{uri}" alt=""{style_attr}>'


def level_color(level: str) -> str:
    return LEVEL_COLORS.get(level.upper(), COLORS["blue"])


def wcag_badge(wcag_id: str) -> str:
    return f'<span class="wcag-badge" style="background:{COLORS["blue"]}">WCAG {esc(wcag_id)}</span>'


def level_badge_html(level: str) -> str:
    color = level_color(level)
    return f'<span class="level-badge" style="background:{color}">Level {esc(level)}</span>'


def verdict_badge(verdict: str) -> str:
    if verdict.lower() == "fail":
        return '<span class="verdict-badge verdict-fail">FAIL</span>'
    return '<span class="verdict-badge verdict-needs-review">NEEDS REVIEW</span>'


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------

def build_cover(data: dict) -> str:
    url = esc(data.get("url", "Unknown URL"))
    audit_date_raw = data.get("audit_date", "")
    try:
        dt = datetime.fromisoformat(audit_date_raw)
        audit_date = dt.strftime("%B %d, %Y at %H:%M")
    except Exception:
        audit_date = esc(audit_date_raw)

    summary = data.get("summary", {})
    fail_count = summary.get("fail_count", 0)
    needs_review_count = summary.get("needs_review_count", 0)

    criteria = data.get("criteria", {})

    # Build summary table rows
    table_rows = []
    for key, crit in criteria.items():
        name = esc(crit.get("criterion", key))
        wcag_ids = crit.get("wcag_ids", [])
        wcag_str = esc(" / ".join(wcag_ids))
        level = esc(crit.get("level", ""))
        fails = crit.get("fail_count", 0)
        reviews = crit.get("needs_review_count", 0)

        if fails == 0 and reviews == 0:
            fail_cell = '<span class="pass-indicator">&#10003; Pass</span>'
            review_cell = "—"
        else:
            fail_cell = f'<span style="color:{COLORS["red"]};font-weight:600;">{fails}</span>' if fails else "0"
            review_cell = f'<span style="color:{COLORS["amber"]};font-weight:600;">{reviews}</span>' if reviews else "0"

        level_color_css = level_color(level)
        table_rows.append(
            f"<tr>"
            f"<td>{name}</td>"
            f"<td>{wcag_str}</td>"
            f'<td><span style="color:{level_color_css};font-weight:700;">{level}</span></td>'
            f"<td>{fail_cell}</td>"
            f"<td>{review_cell}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(table_rows)

    return f"""
<div class="cover page-break">
  <div>
    <div class="cover-eyebrow">Web Accessibility Audit</div>
    <div class="cover-url">{url}</div>
    <div class="cover-date">Audited {audit_date}</div>
  </div>

  <div class="stat-row">
    <div class="stat-box fail">
      <div class="stat-number">{fail_count}</div>
      <div class="stat-label">Failures</div>
    </div>
    <div class="stat-box review">
      <div class="stat-number">{needs_review_count}</div>
      <div class="stat-label">Need Review</div>
    </div>
  </div>

  <div>
    <table class="summary-table">
      <thead>
        <tr>
          <th>Criterion</th>
          <th>WCAG IDs</th>
          <th>Level</th>
          <th>Failures</th>
          <th>Needs Review</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </div>

  <div class="cover-footer">Generated by Claude &middot; claude.ai</div>
</div>
"""


# ---------------------------------------------------------------------------
# Per-criterion section
# ---------------------------------------------------------------------------

def build_criterion_section(key: str, crit: dict, workspace: Path, is_first: bool) -> str:
    name = esc(crit.get("criterion", key))
    description = esc(crit.get("description", ""))
    wcag_ids = crit.get("wcag_ids", [])
    level = crit.get("level", "")
    issues = crit.get("issues", [])

    # Page break
    pb_class = "criterion-section" if is_first else "criterion-section page-break-before"

    # WCAG badges
    badges_html = " ".join(wcag_badge(wid) for wid in wcag_ids)
    if level:
        badges_html += " " + level_badge_html(level)

    # Screenshots
    desktop_img_rel = crit.get("desktop_image", "")
    mobile_img_rel = crit.get("mobile_image", "")
    extra_imgs_rel = crit.get("extra_images", []) or []

    def resolve(rel: str) -> Path:
        p = Path(rel)
        if not p.is_absolute():
            p = workspace / rel
        return p

    desktop_img_path = resolve(desktop_img_rel) if desktop_img_rel else None
    mobile_img_path = resolve(mobile_img_rel) if mobile_img_rel else None
    extra_img_paths = [resolve(r) for r in extra_imgs_rel if r]

    desktop_exists = desktop_img_path and desktop_img_path.exists()
    mobile_exists = mobile_img_path and mobile_img_path.exists()

    screenshots_html = ""
    if desktop_exists and mobile_exists:
        d_tag = image_tag(str(desktop_img_path))
        m_tag = image_tag(str(mobile_img_path))
        if d_tag or m_tag:
            screenshots_html = f"""
<div class="screenshot-row">
  <div class="screenshot-desktop">{d_tag}</div>
  <div class="screenshot-mobile">{m_tag}</div>
</div>"""
    elif desktop_exists:
        d_tag = image_tag(str(desktop_img_path))
        if d_tag:
            screenshots_html = f'<div class="screenshot-single">{d_tag}</div>'
    elif mobile_exists:
        m_tag = image_tag(str(mobile_img_path))
        if m_tag:
            screenshots_html = f'<div class="screenshot-single">{m_tag}</div>'

    # Extra images
    extra_tags = [image_tag(str(p)) for p in extra_img_paths if p.exists()]
    extra_tags = [t for t in extra_tags if t]
    if extra_tags:
        screenshots_html += f'<div class="extra-images">{"".join(extra_tags)}</div>'

    # Issues table
    if issues:
        rows = []
        for issue in issues:
            v = issue.get("verdict", "needs_review")
            element = esc(issue.get("element", ""))
            desc = esc(issue.get("description", ""))
            location = esc(issue.get("location", ""))
            fix = esc(issue.get("suggested_fix", ""))
            badge = verdict_badge(v)
            rows.append(
                f"<tr>"
                f"<td>{badge}</td>"
                f'<td><span class="element-code">{element}</span></td>'
                f"<td>{desc}</td>"
                f"<td>{location}</td>"
                f"<td>{fix}</td>"
                f"</tr>"
            )
        issues_html = f"""
<table class="issues-table">
  <thead>
    <tr>
      <th>Verdict</th>
      <th>Element</th>
      <th>Description</th>
      <th>Location</th>
      <th>Fix</th>
    </tr>
  </thead>
  <tbody>
    {"".join(rows)}
  </tbody>
</table>"""
    else:
        issues_html = '<div class="no-issues-banner">&#10003; No issues found</div>'

    # Compose section
    screenshots_block = f"\n{screenshots_html}" if screenshots_html else ""

    return f"""
<div class="{pb_class}">
  <div class="criterion-header" style="border-radius: 8px 8px 0 0; background:{COLORS['card']}; border-bottom: 1px solid {COLORS['border']}; padding: 16px 20px; display:flex; align-items:center; justify-content:space-between; gap:16px;">
    <div class="criterion-name">{name}</div>
    <div class="badge-group">{badges_html}</div>
  </div>
  <div class="criterion-body">
    <p class="criterion-description">{description}</p>
    {screenshots_block}
    {issues_html}
  </div>
</div>
"""


# ---------------------------------------------------------------------------
# Passed criteria page
# ---------------------------------------------------------------------------

def build_passed_section(passed: list) -> str:
    if not passed:
        return ""

    rows = []
    for crit in passed:
        name = esc(crit.get("criterion", ""))
        wcag_ids = crit.get("wcag_ids", [])
        wcag_str = esc(" / ".join(wcag_ids))
        level = esc(crit.get("level", ""))
        level_color_css = level_color(level)
        rows.append(
            f"<tr>"
            f'<td><span class="pass-indicator">&#10003; Pass</span></td>'
            f"<td>{name}</td>"
            f"<td>{wcag_str}</td>"
            f'<td><span style="color:{level_color_css};font-weight:700;">{level}</span></td>'
            f"</tr>"
        )

    return f"""
<div class="passed-section page-break-before">
  <h2 style="color:{COLORS['text']};font-size:20px;margin-bottom:16px;">&#10003; Passed Criteria</h2>
  <table class="passed-table">
    <thead>
      <tr>
        <th>Status</th>
        <th>Criterion</th>
        <th>WCAG IDs</th>
        <th>Level</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
</div>
"""


# ---------------------------------------------------------------------------
# Full HTML assembly
# ---------------------------------------------------------------------------

def build_html(data: dict, workspace: Path) -> str:
    criteria = data.get("criteria", {})

    # Separate criteria with issues vs fully passed
    with_issues = {k: v for k, v in criteria.items()
                   if v.get("fail_count", 0) > 0 or v.get("needs_review_count", 0) > 0}
    passed = [v for v in criteria.values()
              if v.get("fail_count", 0) == 0 and v.get("needs_review_count", 0) == 0]

    cover_html = build_cover(data)

    criterion_sections = []
    for i, (key, crit) in enumerate(with_issues.items()):
        criterion_sections.append(
            build_criterion_section(key, crit, workspace, is_first=(i == 0))
        )

    passed_html = build_passed_section(passed)

    body_content = cover_html + "\n".join(criterion_sections) + passed_html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WCAG Accessibility Audit Report</title>
  <style>
{GLOBAL_CSS}
  </style>
</head>
<body>
{body_content}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Playwright PDF export
# ---------------------------------------------------------------------------

async def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.async_api import async_playwright

    uri = "file:///" + html_path.as_posix().lstrip("/")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(uri, wait_until="networkidle")
        await page.pdf(
            path=str(pdf_path),
            format="A4",
            landscape=True,
            print_background=True,
            margin={"top": "0.5cm", "bottom": "0.5cm", "left": "0.5cm", "right": "0.5cm"},
        )
        await browser.close()


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def write_csv(data: dict, output_csv: Path) -> int:
    """Write one row per issue. Returns total row count."""
    url = data.get("url", "")
    audit_date = data.get("audit_date", "")
    criteria = data.get("criteria", {})

    columns = [
        "url", "audit_date", "criterion", "wcag_id", "wcag_level",
        "verdict", "element", "description", "location", "suggested_fix",
    ]

    row_count = 0
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for key, crit in criteria.items():
            criterion_name = crit.get("criterion", key)
            wcag_ids = crit.get("wcag_ids", [])
            wcag_id_str = " / ".join(wcag_ids)
            wcag_level = crit.get("level", "")
            issues = crit.get("issues", [])

            for issue in issues:
                writer.writerow({
                    "url": url,
                    "audit_date": audit_date,
                    "criterion": criterion_name,
                    "wcag_id": wcag_id_str,
                    "wcag_level": wcag_level,
                    "verdict": issue.get("verdict", ""),
                    "element": issue.get("element", ""),
                    "description": issue.get("description", ""),
                    "location": issue.get("location", ""),
                    "suggested_fix": issue.get("suggested_fix", ""),
                })
                row_count += 1

    return row_count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a PDF report and CSV from a WCAG audit workspace."
    )
    parser.add_argument("--workspace", required=True,
                        help="Path to the audit workspace directory containing audit_results.json")
    parser.add_argument("--output-pdf", required=True,
                        help="Path for the output PDF file")
    parser.add_argument("--output-csv", required=True,
                        help="Path for the output CSV file")
    return parser.parse_args()


def main():
    args = parse_args()

    workspace = Path(args.workspace).resolve()
    output_pdf = Path(args.output_pdf).resolve()
    output_csv = Path(args.output_csv).resolve()

    # Validate workspace
    results_path = workspace / "audit_results.json"
    if not results_path.exists():
        print(f"ERROR: audit_results.json not found in {workspace}", file=sys.stderr)
        sys.exit(1)

    print(f"[1/5] Reading audit results from {results_path} ...")
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    url = data.get("url", "unknown")
    summary = data.get("summary", {})
    fail_count = summary.get("fail_count", 0)
    needs_review_count = summary.get("needs_review_count", 0)
    criteria = data.get("criteria", {})
    print(f"    URL: {url}")
    print(f"    Criteria: {len(criteria)}")
    print(f"    Failures: {fail_count}  |  Needs review: {needs_review_count}")

    # CSV
    print(f"[2/5] Writing CSV to {output_csv} ...")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    row_count = write_csv(data, output_csv)
    print(f"    Wrote {row_count} issue rows.")

    # Build HTML
    print(f"[3/5] Building HTML report ...")
    html_str = build_html(data, workspace)

    # Save temp HTML
    temp_html = workspace / "audit_report.html"
    print(f"[4/5] Saving temporary HTML to {temp_html} ...")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_str)

    # Convert to PDF
    print(f"[5/5] Rendering PDF with Playwright -> {output_pdf} ...")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(html_to_pdf(temp_html, output_pdf))
    finally:
        # Remove temp HTML
        try:
            os.remove(temp_html)
        except OSError:
            pass

    print()
    print("Done.")
    print(f"  PDF: {output_pdf}")
    print(f"  CSV: {output_csv}")
    print(f"  Summary: {fail_count} failures | {needs_review_count} need review")


if __name__ == "__main__":
    main()
