#!/usr/bin/env python3
"""Full-page screenshot via Playwright.

Args:
  --url       Page URL to capture
  --viewport  desktop (1280px) or mobile (390px)  [default: desktop]
  --output    Output PNG path
"""
import argparse
from playwright.sync_api import sync_playwright


def capture(url: str, viewport: str, output: str) -> None:
    w, h = (1280, 900) if viewport == "desktop" else (390, 844)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(1500)
        page.screenshot(path=output, full_page=True)
        browser.close()
    print(f"Screenshot saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture a full-page screenshot.")
    parser.add_argument("--url",      required=True,  help="Page URL")
    parser.add_argument("--viewport", default="desktop", choices=["desktop", "mobile"])
    parser.add_argument("--output",   required=True,  help="Output PNG path")
    args = parser.parse_args()
    capture(args.url, args.viewport, args.output)
