"""
Full-page screenshot capture using Playwright.
Used by the wcag-keyboard skill to get full-page screenshots for heatmap generation.

Usage:
  python capture.py --url https://example.com --outdir ./output --viewport desktop
  python capture.py --url https://example.com --outdir ./output --viewport mobile

Requirements: pip install playwright && python -m playwright install chromium
"""
import argparse, asyncio
from pathlib import Path
from playwright.async_api import async_playwright

VIEWPORTS = {
    'desktop': {'width': 1280, 'height': 900},
    'mobile':  {'width': 390,  'height': 844},
}

async def capture(url, outdir, viewport_name):
    vp = VIEWPORTS[viewport_name]
    Path(outdir).mkdir(parents=True, exist_ok=True)
    out = str(Path(outdir) / f'{viewport_name}_screenshot.png')
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport=vp)
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)
        await page.screenshot(path=out, full_page=True)
        await browser.close()
    print(f'Screenshot saved: {out}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url',      required=True)
    ap.add_argument('--outdir',   required=True)
    ap.add_argument('--viewport', choices=['desktop','mobile'], default='desktop')
    args = ap.parse_args()
    asyncio.run(capture(args.url, args.outdir, args.viewport))

if __name__ == '__main__': main()