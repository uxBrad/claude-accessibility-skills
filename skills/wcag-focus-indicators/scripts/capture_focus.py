#!/usr/bin/env python3
"""
capture_focus.py -- Capture focused state of every keyboard-focusable element.

For each element:
  1. Scroll it into view
  2. Screenshot viewport before focus (unfocused baseline)
  3. Focus the element
  4. Screenshot viewport after focus
  5. Pixel-diff the element region -- if changed, focus indicator is visible
  6. Save a cropped image of the focused state + metadata

Output:
  <output-dir>/focus_NNN.png  -- cropped focused screenshot per element
  <output-dir>/focus_data.json -- metadata including focus_visible flag

Requirements: pip install pillow playwright && python -m playwright install chromium
"""

import argparse, json, io
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

PAD = 16   # px padding around element in crop
DIFF_THRESHOLD = 6  # max pixel channel delta to consider "no change"

FOCUSABLE_JS = """
(function() {
  const sel = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])', '[contenteditable="true"]',
    'details > summary', 'audio[controls]', 'video[controls]'
  ].join(', ');

  const els = [...document.querySelectorAll(sel)].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' &&
           s.opacity !== '0' && el.offsetParent !== null;
  });

  return els.map((el, i) => {
    const r = el.getBoundingClientRect();
    const scrollY = window.pageYOffset || 0;
    const scrollX = window.pageXOffset || 0;
    return {
      index: i,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      label: (el.getAttribute('aria-label') || el.textContent ||
              el.getAttribute('placeholder') || '').trim().replace(/\s+/g,' ').slice(0,60),
      abs_x: Math.round(r.left + scrollX),
      abs_y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
    };
  }).filter(e => e.w > 0 && e.h > 0);
})()
"""

def screenshot_to_pil(page):
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")

def pixel_diff_score(before: Image.Image, after: Image.Image) -> float:
    """Return the max channel change across any pixel (0-255)."""
    diff = ImageChops.difference(before, after)
    stat = ImageStat.Stat(diff)
    return max(band[1] for band in stat.extrema)  # max of extrema highs

def crop_element(img: Image.Image, vx: int, vy: int, w: int, h: int, pad: int) -> Image.Image:
    iw, ih = img.size
    x1 = max(0, vx - pad)
    y1 = max(0, vy - pad)
    x2 = min(iw, vx + w + pad)
    y2 = min(ih, vy + h + pad)
    return img.crop((x1, y1, x2, y2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url",        required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--viewport",   default="desktop", choices=["desktop","mobile"])
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    vw, vh = (1280, 900) if args.viewport == "desktop" else (390, 844)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": vw, "height": vh})
        page.goto(args.url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        elements = page.evaluate(FOCUSABLE_JS)
        print(f"Found {len(elements)} focusable elements")

        focus_js = """
        (function(idx) {
          const sel = [
            'a[href]','button:not([disabled])','input:not([disabled])',
            'select:not([disabled])','textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])','[contenteditable="true"]',
            'details > summary','audio[controls]','video[controls]'
          ].join(', ');
          const els = [...document.querySelectorAll(sel)].filter(el => {
            const s = window.getComputedStyle(el);
            return s.display!=='none' && s.visibility!=='hidden' &&
                   s.opacity!=='0' && el.offsetParent!==null;
          });
          if (els[idx]) {
            els[idx].scrollIntoView({block:'center', inline:'center'});
            return true;
          }
          return false;
        })
        """

        for el in elements:
            idx = el["index"]
            crop_file = f"focus_{idx:03d}.png"
            try:
                # Scroll element into view
                page.evaluate(f"({focus_js})({idx})")
                page.wait_for_timeout(120)

                # Get fresh viewport coords after scroll
                coords = page.evaluate(f"""
                  (function() {{
                    const sel = ['a[href]','button:not([disabled])','input:not([disabled])',
                      'select:not([disabled])','textarea:not([disabled])',
                      '[tabindex]:not([tabindex="-1"])','[contenteditable]',
                      'details > summary','audio[controls]','video[controls]'].join(',');
                    const els = [...document.querySelectorAll(sel)].filter(el => {{
                      const s=window.getComputedStyle(el);
                      return s.display!=='none'&&s.visibility!=='hidden'&&
                             s.opacity!=='0'&&el.offsetParent!==null;
                    }});
                    const el = els[{idx}];
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return {{vx: Math.round(r.left), vy: Math.round(r.top),
                             w: Math.round(r.width), h: Math.round(r.height)}};
                  }})()
                """)
                if not coords:
                    raise ValueError("Could not locate element after scroll")

                vx, vy, w, h = coords["vx"], coords["vy"], coords["w"], coords["h"]

                # Unfocused screenshot
                before = screenshot_to_pil(page)

                # Focus
                page.evaluate(f"""
                  (function() {{
                    const sel = ['a[href]','button:not([disabled])','input:not([disabled])',
                      'select:not([disabled])','textarea:not([disabled])',
                      '[tabindex]:not([tabindex="-1"])','[contenteditable]',
                      'details > summary','audio[controls]','video[controls]'].join(',');
                    const els = [...document.querySelectorAll(sel)].filter(el => {{
                      const s=window.getComputedStyle(el);
                      return s.display!=='none'&&s.visibility!=='hidden'&&
                             s.opacity!=='0'&&el.offsetParent!==null;
                    }});
                    if (els[{idx}]) els[{idx}].focus();
                  }})()
                """)
                page.wait_for_timeout(150)

                # Focused screenshot
                after = screenshot_to_pil(page)

                # Diff
                score = pixel_diff_score(
                    before.crop((max(0,vx-PAD), max(0,vy-PAD), min(vw,vx+w+PAD), min(vh,vy+h+PAD))),
                    after.crop( (max(0,vx-PAD), max(0,vy-PAD), min(vw,vx+w+PAD), min(vh,vy+h+PAD)))
                )
                focus_visible = score > DIFF_THRESHOLD

                # Save crop of focused state
                crop = crop_element(after, vx, vy, w, h, PAD)
                crop.save(out / crop_file)

                # Blur
                page.evaluate("document.activeElement && document.activeElement.blur()")
                page.wait_for_timeout(60)

                results.append({
                    **el, "status": "pass" if focus_visible else "fail",
                    "focus_visible": focus_visible, "diff_score": round(score,1),
                    "crop_file": crop_file,
                })
                flag = "PASS" if focus_visible else "FAIL"
                print(f"  [{idx:3d}] {flag} diff={score:.0f}  <{el['tag']}> {el['label'][:40]}")

            except Exception as e:
                results.append({
                    **el, "status": "error", "focus_visible": None,
                    "diff_score": 0, "crop_file": None, "error": str(e)
                })
                print(f"  [{idx:3d}] ERROR  <{el['tag']}> {el['label'][:40]}  -- {e}")

        browser.close()

    with open(out / "focus_data.json", "w") as f:
        json.dump(results, f, indent=2)

    passed = sum(1 for r in results if r["status"]=="pass")
    failed = sum(1 for r in results if r["status"]=="fail")
    errors = sum(1 for r in results if r["status"]=="error")
    print(f"\nDone: {passed} pass / {failed} fail / {errors} error  -> {out/'focus_data.json'}")

if __name__ == "__main__": main()