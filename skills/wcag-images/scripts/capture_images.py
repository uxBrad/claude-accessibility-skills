#!/usr/bin/env python3
"""
capture_images.py -- Capture every image element with its alt text metadata.

For each <img>, <picture>, and role="img" element:
  1. Collect metadata: src, alt attribute (present/missing/empty), dimensions
  2. Scroll element into view and take an element-level screenshot via Playwright
  3. Classify alt text quality

Status classification:
  good        -- descriptive alt text present
  decorative  -- alt="" (explicitly decorative, flag for manual verify)
  missing     -- no alt attribute at all (WCAG fail)
  filename    -- alt looks like a filename or path
  generic     -- alt contains only generic words (image, photo, icon, etc.)

Output:
  <output-dir>/img_NNN.png     -- cropped screenshot per image
  <output-dir>/image_data.json -- full metadata
"""

import argparse, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

GENERIC_WORDS = {
    "image", "img", "photo", "photograph", "picture", "graphic", "icon",
    "logo", "banner", "thumbnail", "illustration", "figure", "screenshot",
}
FILENAME_RE = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|bmp|avif|tiff?)$", re.IGNORECASE)
UNDERSCORED_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

COLLECT_JS = """
(function() {
  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  const results = [];
  const seen = new Set();

  function classify(alt, src) {
    if (alt === null || alt === undefined) return "missing";
    if (alt.trim() === "") return "decorative";
    const low = alt.trim().toLowerCase();
    if (/\\.(jpg|jpeg|png|gif|svg|webp|bmp|avif)$/i.test(low)) return "filename";
    const words = low.split(/[\\s_\\-]+/).filter(Boolean);
    const genericCount = words.filter(w =>
      ["image","img","photo","photograph","picture","graphic","icon","logo",
       "banner","thumbnail","illustration","figure","screenshot"].includes(w)
    ).length;
    if (words.length > 0 && genericCount === words.length) return "generic";
    return "good";
  }

  document.querySelectorAll('img, [role="img"]').forEach((el, i) => {
    const s = window.getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    const key = `${Math.round(r.left)},${Math.round(r.top)}`;
    if (seen.has(key)) return;
    seen.add(key);

    const altAttr = el.getAttribute("alt");
    const ariaLabel = el.getAttribute("aria-label") || "";
    const effectiveAlt = altAttr !== null ? altAttr : (ariaLabel || null);
    const src = el.src || el.getAttribute("src") || "";
    const srcShort = src.split("/").pop().split("?")[0].slice(0, 60);

    results.push({
      index: results.length,
      tag: el.tagName.toLowerCase(),
      role: el.getAttribute("role") || "",
      alt: effectiveAlt,
      alt_missing: altAttr === null && !ariaLabel,
      src_short: srcShort,
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
      status: classify(effectiveAlt, src),
    });
  });
  return results;
})()
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url",        required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--viewport",   default="desktop", choices=["desktop", "mobile"])
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    vw, vh = (1280, 900) if args.viewport == "desktop" else (390, 844)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": vw, "height": vh})
        page.goto(args.url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        images = page.evaluate(COLLECT_JS)
        print(f"Found {len(images)} images")

        # Full-page screenshot for cropping
        import io
        from PIL import Image
        full_bytes = page.screenshot(full_page=True)
        full_img = Image.open(io.BytesIO(full_bytes)).convert("RGB")
        full_w, full_h = full_img.size

        for img_meta in images:
            idx = img_meta["index"]
            x, y, w, h = img_meta["x"], img_meta["y"], img_meta["w"], img_meta["h"]
            crop_file = f"img_{idx:03d}.png"

            try:
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = min(full_w, x + w)
                y2 = min(full_h, y + h)
                if x2 > x1 and y2 > y1:
                    crop = full_img.crop((x1, y1, x2, y2))
                    crop.save(out / crop_file)
                    img_meta["crop_file"] = crop_file
                else:
                    img_meta["crop_file"] = None
            except Exception as e:
                img_meta["crop_file"] = None
                img_meta["error"] = str(e)

            status = img_meta["status"]
            alt_display = repr(img_meta["alt"]) if img_meta["alt"] is not None else "MISSING"
            print(f"  [{idx:3d}] {status.upper():<12} alt={alt_display[:50]}  ({img_meta['src_short']})")

        browser.close()

    with open(out / "image_data.json", "w") as f:
        json.dump(images, f, indent=2)

    counts = {}
    for img in images:
        counts[img["status"]] = counts.get(img["status"], 0) + 1
    print(f"\nDone: {counts}  -> {out / 'image_data.json'}")

if __name__ == "__main__": main()
