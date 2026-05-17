#!/usr/bin/env python3
"""
capture.py -- Full-page screenshot via Playwright.
Usage:
  python capture.py --url <url> --viewport desktop|mobile --output <path.png>
"""
import argparse
from playwright.sync_api import sync_playwright

def capture(url, viewport, output):
    w, h = (1280, 900) if viewport == "desktop" else (390, 844)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)
        page.screenshot(path=output, full_page=True)
        browser.close()
    print(f"Screenshot saved: {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--viewport", default="desktop", choices=["desktop", "mobile"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    capture(args.url, args.viewport, args.output)