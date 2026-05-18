#!/usr/bin/env python3
"""
capture_reflow.py -- Capture screenshots at desktop and narrow viewports for WCAG 1.4.10 reflow audit.

Saves:
  wide_screenshot.png   -- full-page at --wide-width (default 1280)
  narrow_screenshot.png -- full-page at --narrow-width (default 320)
  reflow_data.json      -- metadata + horizontal scroll + overflowing elements
"""

import argparse
import json
import os
import sys
from playwright.sync_api import sync_playwright


OVERFLOW_JS = """
[...document.querySelectorAll('*')].filter(el => {
    if (!el.offsetParent && el.tagName !== 'BODY' && el.tagName !== 'HTML') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.right > window.innerWidth + 4;
}).slice(0, 15).map(el => ({
    tag: el.tagName.toLowerCase(),
    id: el.id || '',
    class: el.className.toString().trim().split(/\\s+/).slice(0,2).join(' '),
    right: Math.round(el.getBoundingClientRect().right),
    overflowBy: Math.round(el.getBoundingClientRect().right - window.innerWidth),
}))
"""

HAS_SCROLL_JS = (
    "document.documentElement.scrollWidth > document.documentElement.clientWidth + 4"
)


def capture(url, output_dir, wide_width, narrow_width):
    os.makedirs(output_dir, exist_ok=True)

    wide_path   = os.path.join(output_dir, "wide_screenshot.png")
    narrow_path = os.path.join(output_dir, "narrow_screenshot.png")
    data_path   = os.path.join(output_dir, "reflow_data.json")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- Wide viewport ---
        print(f"Capturing wide viewport ({wide_width}px)…")
        page = browser.new_page(viewport={"width": wide_width, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)
        page.screenshot(path=wide_path, full_page=True)
        wide_height = page.evaluate("document.documentElement.scrollHeight")
        print(f"  Saved: {wide_path}  (height: {wide_height}px)")

        # --- Narrow viewport ---
        print(f"Capturing narrow viewport ({narrow_width}px)…")
        page2 = browser.new_page(viewport={"width": narrow_width, "height": 900})
        page2.goto(url, wait_until="networkidle", timeout=30000)
        page2.wait_for_timeout(1500)
        page2.screenshot(path=narrow_path, full_page=True)
        narrow_height = page2.evaluate("document.documentElement.scrollHeight")
        print(f"  Saved: {narrow_path}  (height: {narrow_height}px)")

        # --- Reflow checks ---
        has_horizontal_scroll = page2.evaluate(HAS_SCROLL_JS)
        overflow_elements = page2.evaluate(OVERFLOW_JS)

        browser.close()

    data = {
        "url":                   url,
        "wide_width":            wide_width,
        "narrow_width":          narrow_width,
        "wide_height":           wide_height,
        "narrow_height":         narrow_height,
        "has_horizontal_scroll": has_horizontal_scroll,
        "overflow_elements":     overflow_elements,
    }

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # --- Summary ---
    status = "FAIL — horizontal scroll detected" if has_horizontal_scroll else "PASS — no horizontal scroll"
    print()
    print(f"Result:   {status}")
    print(f"URL:      {url}")
    print(f"Wide:     {wide_width}px × {wide_height}px")
    print(f"Narrow:   {narrow_width}px × {narrow_height}px")
    print(f"Overflow: {len(overflow_elements)} element(s) detected")
    for el in overflow_elements:
        ident = f"#{el['id']}" if el["id"] else (f".{el['class'].split()[0]}" if el["class"] else "")
        print(f"  <{el['tag']}{ident}>  right={el['right']}px  overflow by {el['overflowBy']}px")
    print(f"Data:     {data_path}")

    return data


def main():
    ap = argparse.ArgumentParser(
        description="Capture reflow screenshots for WCAG 1.4.10 audit"
    )
    ap.add_argument("--url",          required=True,     help="Page URL to audit")
    ap.add_argument("--output-dir",   required=True,     help="Directory for output files")
    ap.add_argument("--wide-width",   type=int, default=1280, help="Desktop viewport width (default 1280)")
    ap.add_argument("--narrow-width", type=int, default=320,  help="Narrow viewport width (default 320)")
    args = ap.parse_args()

    capture(args.url, args.output_dir, args.wide_width, args.narrow_width)


if __name__ == "__main__":
    main()
