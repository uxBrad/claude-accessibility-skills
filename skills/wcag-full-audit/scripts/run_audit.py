#!/usr/bin/env python3
"""
run_audit.py -- Full WCAG accessibility audit orchestrator.

Runs all 11 sub-skill checks against a URL in a single automated pass.
Produces structured audit_results.json plus all annotated screenshots.

Usage:
    python run_audit.py --url URL --workspace DIR [--skills-dir DIR]
"""

import argparse
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# JavaScript collectors (inline from each skill's SKILL.md)
# ---------------------------------------------------------------------------

HEADINGS_JS = """
(function() {
  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  return [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden';
  }).map((el, i) => {
    const r = el.getBoundingClientRect();
    return {
      index: i,
      level: parseInt(el.tagName[1]),
      text:  el.textContent.trim().replace(/\\s+/g, ' ').slice(0, 120),
      tag:   el.tagName.toLowerCase(),
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
    };
  });
})()
"""

LINKS_JS = """
(function() {
  const VAGUE = new Set([
    "click here","here","read more","more info","more information","learn more",
    "see more","view more","find out more","this","this link","link","button",
    "click","press","tap","go","continue","next","previous","prev",
    "details","detail","info","information","see details","view details"
  ]);
  const GENERIC = new Set(["more","view","see","get","open","show","check","visit"]);
  const URL_RE = /^https?:\\/\\/|^www\\./i;

  function classify(text, ariaLabel, href) {
    const effective = (ariaLabel || text || "").trim();
    if (!effective) return "empty";
    const low = effective.toLowerCase().replace(/[.,!?;:\\s]+$/,"").trim();
    if (VAGUE.has(low)) return "vague";
    if (URL_RE.test(low) && !low.includes(" ")) return "url";
    const words = low.split(/\\s+/);
    if (words.length <= 2 && words.every(w => GENERIC.has(w))) return "generic";
    if (effective.length <= 3) return "short";
    return "ok";
  }

  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  return [...document.querySelectorAll("a[href]")].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== "none" && s.visibility !== "hidden" && el.offsetParent !== null;
  }).map((el, i) => {
    const r = el.getBoundingClientRect();
    const text = el.textContent.trim().replace(/\\s+/g," ");
    const ariaLabel = el.getAttribute("aria-label") || "";
    const href = el.getAttribute("href") || "";
    const flag = classify(text, ariaLabel, href);
    return {
      index: i,
      tag: el.tagName.toLowerCase(),
      text: text.slice(0, 80),
      aria_label: ariaLabel.slice(0, 80),
      href: href.slice(0, 100),
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
      flag: flag,
    };
  }).filter(l => l.w > 0 && l.h > 0);
})()
"""

TOUCH_TARGETS_JS = """
(function() {
  const sel = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])', '[role="button"]', '[role="link"]',
    '[role="checkbox"]', '[role="radio"]', '[role="menuitem"]',
    '[role="tab"]', '[role="switch"]', 'summary', '[onclick]'
  ].join(', ');

  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;

  return [...document.querySelectorAll(sel)].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' &&
           s.opacity !== '0' && el.offsetParent !== null;
  }).map((el, i) => {
    const r = el.getBoundingClientRect();
    const w = Math.round(r.width), h = Math.round(r.height);
    const passes_aaa = w >= 44 && h >= 44;
    const passes_aa  = w >= 24 && h >= 24;
    return {
      index: i,
      tag:   el.tagName.toLowerCase(),
      type:  el.getAttribute('type') || '',
      role:  el.getAttribute('role') || '',
      label: (el.getAttribute('aria-label') || el.textContent ||
              el.getAttribute('placeholder') || '').trim().replace(/\\s+/g,' ').slice(0,50),
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: w, h: h,
      status: passes_aaa ? 'aaa' : passes_aa ? 'aa' : 'fail'
    };
  }).filter(e => e.w > 0 && e.h > 0);
})()
"""

LANDMARKS_JS = """
(function() {
  const ROLE_MAP = {
    header: 'banner', nav: 'navigation', main: 'main',
    aside: 'complementary', footer: 'contentinfo',
    form: 'form', section: 'region',
  };
  const ARIA_ROLES = ['banner','navigation','main','complementary','contentinfo','search','form','region','application'];

  function getAccessibleName(el) {
    return el.getAttribute('aria-label') ||
           (el.getAttribute('aria-labelledby') && document.getElementById(el.getAttribute('aria-labelledby'))?.textContent?.trim()) ||
           el.getAttribute('title') || '';
  }

  const scrollY = window.pageYOffset || 0;
  const results = [];

  document.querySelectorAll('header, nav, main, aside, footer, form, section[aria-label], section[aria-labelledby]').forEach((el, i) => {
    const s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return;
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role') || ROLE_MAP[tag] || 'region';
    results.push({
      index: results.length,
      tag,
      role,
      accessible_name: getAccessibleName(el),
      x: Math.round(r.left + window.pageXOffset),
      y: Math.round(r.top + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height),
    });
  });

  ARIA_ROLES.forEach(role => {
    document.querySelectorAll('[role="' + role + '"]').forEach(el => {
      const s = window.getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden') return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (results.some(res => res.x === Math.round(r.left) && res.y === Math.round(r.top + scrollY))) return;
      results.push({
        index: results.length,
        tag: el.tagName.toLowerCase(),
        role,
        accessible_name: getAccessibleName(el),
        x: Math.round(r.left + window.pageXOffset),
        y: Math.round(r.top + scrollY),
        w: Math.round(r.width),
        h: Math.round(r.height),
      });
    });
  });

  return results;
})()
"""

FORMS_JS = """
(function() {
  function getLabel(el) {
    const lbId = el.getAttribute('aria-labelledby');
    if (lbId) {
      const text = lbId.split(' ').map(id => document.getElementById(id)?.textContent?.trim()).filter(Boolean).join(' ');
      if (text) return { text, source: 'aria-labelledby' };
    }
    const al = el.getAttribute('aria-label');
    if (al?.trim()) return { text: al.trim(), source: 'aria-label' };
    if (el.id) {
      const lbl = document.querySelector('label[for="' + el.id + '"]');
      if (lbl?.textContent?.trim()) return { text: lbl.textContent.trim(), source: 'label[for]' };
    }
    const parent = el.closest('label');
    if (parent) {
      const clone = parent.cloneNode(true);
      clone.querySelectorAll('input,select,textarea').forEach(n => n.remove());
      const text = clone.textContent.trim();
      if (text) return { text, source: 'label-wrap' };
    }
    const title = el.getAttribute('title');
    if (title?.trim()) return { text: title.trim(), source: 'title' };
    const ph = el.getAttribute('placeholder');
    if (ph?.trim()) return { text: ph.trim(), source: 'placeholder' };
    return { text: '', source: 'none' };
  }

  function classify(el, labelSource) {
    if (labelSource === 'none') return 'missing';
    if (labelSource === 'placeholder') return 'placeholder';
    return 'good';
  }

  const scrollY = window.pageYOffset || 0;
  return [...document.querySelectorAll('input:not([type="hidden"]), select, textarea')]
    .filter(el => {
      const s = window.getComputedStyle(el);
      return s.display !== 'none' && s.visibility !== 'hidden' && el.offsetParent !== null;
    })
    .map((el, i) => {
      const r = el.getBoundingClientRect();
      const { text: labelText, source: labelSource } = getLabel(el);
      return {
        index: i,
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || el.tagName.toLowerCase(),
        label_text: labelText,
        label_source: labelSource,
        status: classify(el, labelSource),
        placeholder: el.getAttribute('placeholder') || '',
        autocomplete: el.getAttribute('autocomplete') || '',
        required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
        name: el.getAttribute('name') || '',
        x: Math.round(r.left + window.pageXOffset),
        y: Math.round(r.top + scrollY),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    });
})()
"""

CONTRAST_JS = """
(function() {
  function getEffectiveBg(el) {
    let node = el;
    while (node && node !== document.documentElement) {
      const bg = window.getComputedStyle(node).backgroundColor;
      if (bg && bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') return bg;
      node = node.parentElement;
    }
    return 'rgb(255, 255, 255)';
  }

  function parseRgb(str) {
    const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    return m ? [+m[1], +m[2], +m[3]] : null;
  }

  const scrollY = window.pageYOffset || 0;
  const scrollX = window.pageXOffset || 0;
  const results = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;

  while (node = walker.nextNode()) {
    const el = node;
    const s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') continue;
    if (!el.offsetParent && el.tagName !== 'BODY') continue;

    const hasDirectText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!hasDirectText) continue;

    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;

    const fg = parseRgb(s.color);
    const bg = parseRgb(getEffectiveBg(el));
    if (!fg || !bg) continue;

    const fontSize   = parseFloat(s.fontSize);
    const fontWeight = s.fontWeight;
    const isLarge    = fontSize >= 24 || (fontSize >= 18.67 && (+fontWeight >= 700 || fontWeight === 'bold'));

    results.push({
      tag:      el.tagName.toLowerCase(),
      text:     el.textContent.trim().replace(/\\s+/g,' ').slice(0,50),
      fg:       fg,
      bg:       bg,
      fg_str:   s.color,
      bg_str:   getEffectiveBg(el),
      fontSize: Math.round(fontSize),
      isLarge:  isLarge,
      x: Math.round(r.left + scrollX),
      y: Math.round(r.top  + scrollY),
      w: Math.round(r.width),
      h: Math.round(r.height)
    });
  }
  return results;
})()
"""

KEYBOARD_JS = """
(function() {
  const sel = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])', '[contenteditable="true"]',
    'details > summary', 'audio[controls]', 'video[controls]'
  ].join(', ');
  const els = [...document.querySelectorAll(sel)].filter(el => {
    const s = window.getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0' && el.offsetParent !== null;
  });
  const scrollY = window.pageYOffset || 0, scrollX = window.pageXOffset || 0;
  const withPos = els.map((el, i) => {
    const r = el.getBoundingClientRect();
    return {
      index: i,
      tabindex: parseInt(el.getAttribute('tabindex') || '0', 10),
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      role: el.getAttribute('role') || '',
      label: (el.getAttribute('aria-label') || el.textContent || el.getAttribute('value') || el.getAttribute('placeholder') || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
      href: el.getAttribute('href') || '',
      x: Math.round(r.left + scrollX + r.width / 2),
      y: Math.round(r.top + scrollY + r.height / 2),
      w: Math.round(r.width), h: Math.round(r.height),
      top: Math.round(r.top + scrollY), left: Math.round(r.left + scrollX)
    };
  });
  const positive = withPos.filter(e => e.tabindex > 0).sort((a, b) => a.tabindex - b.tabindex || a.index - b.index);
  const zeros = withPos.filter(e => e.tabindex <= 0).sort((a, b) => a.index - b.index);
  const ordered = [...positive, ...zeros];
  ordered.forEach((e, i) => { e.tabOrder = i + 1; });
  return ordered;
})()
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_json(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [warn] Could not read {path}: {e}")
        return None


def run_subprocess(cmd: list, label: str) -> bool:
    """Run a subprocess, return True on success."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"  [warn] {label} exited with code {result.returncode}")
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines()[-5:]:
                    print(f"         {line}")
            return False
        return True
    except FileNotFoundError:
        print(f"  [skip] {label}: script not found")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [warn] {label}: timed out after 300s")
        return False
    except Exception as e:
        print(f"  [warn] {label}: {e}")
        return False


# ---------------------------------------------------------------------------
# Contrast math (mirroring contrast_overlay.py so we can compute thresholds)
# ---------------------------------------------------------------------------

def _linearize(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(r, g, b):
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(fg, bg):
    l1 = relative_luminance(*fg)
    l2 = relative_luminance(*bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Step 1: Playwright DOM collection
# ---------------------------------------------------------------------------

def playwright_collect(url: str, ws: Path):
    print("\n[Step 1] Playwright DOM collection...")

    desktop_ss = ws / "desktop_screenshot.png"
    mobile_ss  = ws / "mobile_screenshot.png"

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── Desktop pass (1280px) ──────────────────────────────────────────
        print("  [desktop] navigating...")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        print("  [desktop] taking screenshot...")
        page.screenshot(path=str(desktop_ss), full_page=True)

        print("  [desktop] collecting headings...")
        save_json(page.evaluate(HEADINGS_JS), ws / "headings.json")

        print("  [desktop] collecting links...")
        save_json(page.evaluate(LINKS_JS), ws / "desktop_links.json")

        print("  [desktop] collecting touch targets...")
        save_json(page.evaluate(TOUCH_TARGETS_JS), ws / "desktop_targets.json")

        print("  [desktop] collecting landmarks...")
        save_json(page.evaluate(LANDMARKS_JS), ws / "desktop_landmarks.json")

        print("  [desktop] collecting form fields...")
        save_json(page.evaluate(FORMS_JS), ws / "desktop_fields.json")

        print("  [desktop] collecting contrast data...")
        save_json(page.evaluate(CONTRAST_JS), ws / "desktop_contrast.json")

        print("  [desktop] collecting keyboard/focusable elements...")
        save_json(page.evaluate(KEYBOARD_JS), ws / "desktop_keyboard.json")

        page.close()

        # ── Mobile pass (390px) ───────────────────────────────────────────
        print("  [mobile] navigating...")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        print("  [mobile] taking screenshot...")
        page.screenshot(path=str(mobile_ss), full_page=True)

        print("  [mobile] collecting links...")
        save_json(page.evaluate(LINKS_JS), ws / "mobile_links.json")

        print("  [mobile] collecting touch targets...")
        save_json(page.evaluate(TOUCH_TARGETS_JS), ws / "mobile_targets.json")

        print("  [mobile] collecting landmarks...")
        save_json(page.evaluate(LANDMARKS_JS), ws / "mobile_landmarks.json")

        page.close()
        browser.close()

    print("  [Step 1] Done.")


# ---------------------------------------------------------------------------
# Step 2: Subprocess captures (concurrent)
# ---------------------------------------------------------------------------

def subprocess_captures(url: str, ws: Path, skills_dir: Path):
    print("\n[Step 2] Running capture subprocesses concurrently...")

    reflow_dir        = ws / "reflow"
    spacing_desk_dir  = ws / "text-spacing" / "desktop"
    spacing_mob_dir   = ws / "text-spacing" / "mobile"
    images_dir        = ws / "images" / "desktop_crops"
    focus_dir         = ws / "focus"

    python = sys.executable

    def _script(skill: str, name: str) -> Path:
        return skills_dir / skill / "scripts" / name

    tasks = [
        (
            "reflow",
            [python, str(_script("wcag-reflow", "capture_reflow.py")),
             "--url", url, "--output-dir", str(reflow_dir)],
        ),
        (
            "text-spacing desktop",
            [python, str(_script("wcag-text-spacing", "capture_spacing.py")),
             "--url", url, "--viewport", "desktop", "--output-dir", str(spacing_desk_dir)],
        ),
        (
            "text-spacing mobile",
            [python, str(_script("wcag-text-spacing", "capture_spacing.py")),
             "--url", url, "--viewport", "mobile", "--output-dir", str(spacing_mob_dir)],
        ),
        (
            "images",
            [python, str(_script("wcag-images", "capture_images.py")),
             "--url", url, "--output-dir", str(images_dir), "--viewport", "desktop"],
        ),
        (
            "focus indicators",
            [python, str(_script("wcag-focus-indicators", "capture_focus.py")),
             "--url", url, "--output-dir", str(focus_dir)],
        ),
    ]

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(run_subprocess, cmd, label): label for label, cmd in tasks}
        for fut in as_completed(futures):
            label = futures[fut]
            ok = fut.result()
            status = "done" if ok else "failed/skipped"
            print(f"  [Step 2] {label}: {status}")

    print("  [Step 2] Done.")


# ---------------------------------------------------------------------------
# Step 3: Overlay / sheet scripts (concurrent)
# ---------------------------------------------------------------------------

def run_overlays(url: str, ws: Path, skills_dir: Path):
    print("\n[Step 3] Running overlay/sheet scripts concurrently...")

    out      = ws / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    python   = sys.executable

    def _script(skill: str, name: str) -> str:
        return str(skills_dir / skill / "scripts" / name)

    def _exists(*paths) -> bool:
        return all(Path(p).exists() for p in paths)

    tasks = []

    # heading_overlay.py
    if _exists(ws / "desktop_screenshot.png", ws / "headings.json"):
        tasks.append(("heading overlay", [
            python, _script("wcag-headings", "heading_overlay.py"),
            "--screenshot", str(ws / "desktop_screenshot.png"),
            "--headings",   str(ws / "headings.json"),
            "--output",     str(out / "desktop_headings.png"),
            "--label",      "Heading Structure (1.3.1 / 2.4.6)",
        ]))
    else:
        print("  [skip] heading overlay: missing inputs")

    # heading_tree.py
    if _exists(ws / "headings.json"):
        tasks.append(("heading tree", [
            python, _script("wcag-headings", "heading_tree.py"),
            "--headings", str(ws / "headings.json"),
            "--output",   str(out / "heading_outline.png"),
            "--url",      url,
        ]))
    else:
        print("  [skip] heading tree: missing inputs")

    # link_overlay.py desktop
    if _exists(ws / "desktop_screenshot.png", ws / "desktop_links.json"):
        tasks.append(("link overlay desktop", [
            python, _script("wcag-links", "link_overlay.py"),
            "--screenshot", str(ws / "desktop_screenshot.png"),
            "--links",      str(ws / "desktop_links.json"),
            "--output",     str(out / "desktop_links_audit.png"),
            "--label",      "Link Purpose (2.4.4 / 2.4.9) — Desktop",
        ]))
    else:
        print("  [skip] link overlay desktop: missing inputs")

    # link_overlay.py mobile
    if _exists(ws / "mobile_screenshot.png", ws / "mobile_links.json"):
        tasks.append(("link overlay mobile", [
            python, _script("wcag-links", "link_overlay.py"),
            "--screenshot", str(ws / "mobile_screenshot.png"),
            "--links",      str(ws / "mobile_links.json"),
            "--output",     str(out / "mobile_links_audit.png"),
            "--label",      "Link Purpose (2.4.4 / 2.4.9) — Mobile",
        ]))
    else:
        print("  [skip] link overlay mobile: missing inputs")

    # image_sheet.py
    crops_dir  = ws / "images" / "desktop_crops"
    image_data = crops_dir / "image_data.json"
    if _exists(image_data):
        tasks.append(("image sheet", [
            python, _script("wcag-images", "image_sheet.py"),
            "--crops-dir", str(crops_dir),
            "--data",      str(image_data),
            "--output",    str(out / "desktop_image_sheet.png"),
            "--label",     "Image Alt Text (1.1.1)",
        ]))
    else:
        print("  [skip] image sheet: missing inputs")

    # form_sheet.py
    if _exists(ws / "desktop_fields.json"):
        tasks.append(("form sheet", [
            python, _script("wcag-forms", "form_sheet.py"),
            "--data",   str(ws / "desktop_fields.json"),
            "--output", str(out / "desktop_form_sheet.png"),
            "--label",  "Form Fields (1.3.1 / 1.3.5)",
        ]))
    else:
        print("  [skip] form sheet: missing inputs")

    # landmark_overlay.py desktop
    if _exists(ws / "desktop_screenshot.png", ws / "desktop_landmarks.json"):
        tasks.append(("landmark overlay desktop", [
            python, _script("wcag-landmarks", "landmark_overlay.py"),
            "--screenshot", str(ws / "desktop_screenshot.png"),
            "--landmarks",  str(ws / "desktop_landmarks.json"),
            "--output",     str(out / "desktop_landmarks_audit.png"),
            "--label",      "Desktop (1280px) — Landmark Regions Audit",
        ]))
    else:
        print("  [skip] landmark overlay desktop: missing inputs")

    # landmark_overlay.py mobile
    if _exists(ws / "mobile_screenshot.png", ws / "mobile_landmarks.json"):
        tasks.append(("landmark overlay mobile", [
            python, _script("wcag-landmarks", "landmark_overlay.py"),
            "--screenshot", str(ws / "mobile_screenshot.png"),
            "--landmarks",  str(ws / "mobile_landmarks.json"),
            "--output",     str(out / "mobile_landmarks_audit.png"),
            "--label",      "Mobile (390px) — Landmark Regions Audit",
        ]))
    else:
        print("  [skip] landmark overlay mobile: missing inputs")

    # target_heatmap.py desktop
    if _exists(ws / "desktop_screenshot.png", ws / "desktop_targets.json"):
        tasks.append(("target heatmap desktop", [
            python, _script("wcag-touch-targets", "target_heatmap.py"),
            "--screenshot", str(ws / "desktop_screenshot.png"),
            "--elements",   str(ws / "desktop_targets.json"),
            "--output",     str(out / "desktop_targets.png"),
            "--label",      "Desktop (1280px) — Touch Target Audit",
        ]))
    else:
        print("  [skip] target heatmap desktop: missing inputs")

    # target_heatmap.py mobile
    if _exists(ws / "mobile_screenshot.png", ws / "mobile_targets.json"):
        tasks.append(("target heatmap mobile", [
            python, _script("wcag-touch-targets", "target_heatmap.py"),
            "--screenshot", str(ws / "mobile_screenshot.png"),
            "--elements",   str(ws / "mobile_targets.json"),
            "--output",     str(out / "mobile_targets.png"),
            "--label",      "Mobile (390px) — Touch Target Audit",
        ]))
    else:
        print("  [skip] target heatmap mobile: missing inputs")

    # contact_sheet.py (focus)
    focus_data = ws / "focus" / "focus_data.json"
    if _exists(focus_data):
        tasks.append(("focus contact sheet", [
            python, _script("wcag-focus-indicators", "contact_sheet.py"),
            "--crops-dir", str(ws / "focus"),
            "--data",      str(focus_data),
            "--output",    str(out / "desktop_focus_sheet.png"),
            "--label",     "Focus Indicators (2.4.7 / 2.4.11)",
        ]))
    else:
        print("  [skip] focus contact sheet: missing inputs")

    # reflow_compare.py
    reflow_wide   = ws / "reflow" / "wide_screenshot.png"
    reflow_narrow = ws / "reflow" / "narrow_screenshot.png"
    reflow_data   = ws / "reflow" / "reflow_data.json"
    if _exists(reflow_wide, reflow_narrow, reflow_data):
        tasks.append(("reflow compare", [
            python, _script("wcag-reflow", "reflow_compare.py"),
            "--wide",   str(reflow_wide),
            "--narrow", str(reflow_narrow),
            "--data",   str(reflow_data),
            "--output", str(out / "reflow_audit.png"),
            "--label",  "Reflow Audit (WCAG 1.4.10)",
        ]))
    else:
        print("  [skip] reflow compare: missing inputs")

    # spacing_compare.py desktop
    sp_desk_before = ws / "text-spacing" / "desktop" / "before.png"
    sp_desk_after  = ws / "text-spacing" / "desktop" / "after.png"
    sp_desk_data   = ws / "text-spacing" / "desktop" / "spacing_data.json"
    if _exists(sp_desk_before, sp_desk_after, sp_desk_data):
        tasks.append(("spacing compare desktop", [
            python, _script("wcag-text-spacing", "spacing_compare.py"),
            "--before", str(sp_desk_before),
            "--after",  str(sp_desk_after),
            "--data",   str(sp_desk_data),
            "--output", str(out / "desktop_spacing_audit.png"),
            "--label",  "Desktop — WCAG 1.4.12 Text Spacing Audit",
        ]))
    else:
        print("  [skip] spacing compare desktop: missing inputs")

    # spacing_compare.py mobile
    sp_mob_before = ws / "text-spacing" / "mobile" / "before.png"
    sp_mob_after  = ws / "text-spacing" / "mobile" / "after.png"
    sp_mob_data   = ws / "text-spacing" / "mobile" / "spacing_data.json"
    if _exists(sp_mob_before, sp_mob_after, sp_mob_data):
        tasks.append(("spacing compare mobile", [
            python, _script("wcag-text-spacing", "spacing_compare.py"),
            "--before", str(sp_mob_before),
            "--after",  str(sp_mob_after),
            "--data",   str(sp_mob_data),
            "--output", str(out / "mobile_spacing_audit.png"),
            "--label",  "Mobile — WCAG 1.4.12 Text Spacing Audit",
        ]))
    else:
        print("  [skip] spacing compare mobile: missing inputs")

    # contrast_overlay.py desktop
    if _exists(ws / "desktop_screenshot.png", ws / "desktop_contrast.json"):
        tasks.append(("contrast overlay desktop", [
            python, _script("wcag-color-contrast", "contrast_overlay.py"),
            "--screenshot", str(ws / "desktop_screenshot.png"),
            "--elements",   str(ws / "desktop_contrast.json"),
            "--output",     str(out / "desktop_contrast.png"),
            "--label",      "Desktop (1280px) — Color Contrast Audit",
        ]))
    else:
        print("  [skip] contrast overlay desktop: missing inputs")

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(run_subprocess, cmd, label): label for label, cmd in tasks}
        for fut in as_completed(futures):
            label = futures[fut]
            ok = fut.result()
            status = "done" if ok else "failed/skipped"
            print(f"  [Step 3] {label}: {status}")

    print("  [Step 3] Done.")


# ---------------------------------------------------------------------------
# Step 4: Compute verdicts
# ---------------------------------------------------------------------------

def _loc(el: dict) -> str:
    return f"x:{el.get('x',0)} y:{el.get('y',0)} w:{el.get('w',0)} h:{el.get('h',0)}"


def verdict_links(data) -> list:
    issues = []
    if not data:
        return issues
    for el in data:
        flag = el.get("flag", "ok")
        if flag in ("empty", "vague", "url", "short"):
            issues.append({
                "verdict": "fail",
                "element": f"<{el.get('tag','a')}> {repr(el.get('text','') or '(no text)')}",
                "description": "Empty/vague link — no accessible text",
                "location": _loc(el),
                "href": el.get("href", ""),
                "suggested_fix": (
                    "Add aria-label describing the destination"
                    if flag == "empty"
                    else "Replace with descriptive text, e.g. 'Read article: [title]'"
                ),
            })
        elif flag == "generic":
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','a')}> {repr(el.get('text',''))}",
                "description": "Generic link text — verify it's meaningful in context",
                "location": _loc(el),
                "href": el.get("href", ""),
                "suggested_fix": "Replace with descriptive text, e.g. 'Read article: [title]'",
            })
    return issues


def verdict_images(data) -> list:
    issues = []
    if not data:
        return issues
    for el in data:
        if el.get("alt_missing"):
            issues.append({
                "verdict": "fail",
                "element": f"<{el.get('tag','img')}> {el.get('src_short','')}",
                "description": "Missing alt attribute",
                "location": _loc(el),
                "suggested_fix": "Add an alt attribute describing the image content",
            })
        elif el.get("status") == "decorative":
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','img')}> {el.get('src_short','')}",
                "description": "Empty alt (decorative) — verify image conveys no information",
                "location": _loc(el),
                "suggested_fix": "Confirm the image is purely decorative; if not, add descriptive alt text",
            })
        elif el.get("status") == "filename":
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','img')}> {el.get('src_short','')}",
                "description": "Alt text is a filename — write a description",
                "location": _loc(el),
                "suggested_fix": "Replace the filename with a human-readable description",
            })
        elif el.get("status") == "generic":
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','img')}> {el.get('src_short','')}",
                "description": "Generic alt text (e.g. 'image', 'photo') — write a description",
                "location": _loc(el),
                "suggested_fix": "Replace generic alt with specific image content description",
            })
    return issues


def verdict_headings(data) -> list:
    issues = []
    if not data:
        return issues
    prev_level = 0
    h1_count = 0
    for el in data:
        level = el.get("level", 1)
        text  = el.get("text", "").strip()

        if text == "":
            issues.append({
                "verdict": "fail",
                "element": f"<h{level}>",
                "description": "Empty heading",
                "location": _loc(el),
                "suggested_fix": "Add descriptive text to the heading or remove it",
            })
        if level == 1:
            h1_count += 1
            if h1_count > 1:
                issues.append({
                    "verdict": "fail",
                    "element": f"<h1> {repr(text[:60])}",
                    "description": "Multiple H1 elements",
                    "location": _loc(el),
                    "suggested_fix": "Use only one H1 per page; demote additional H1s to H2 or lower",
                })
        if prev_level > 0 and level > prev_level + 1:
            issues.append({
                "verdict": "fail",
                "element": f"<h{level}> {repr(text[:60])}",
                "description": f"Skipped heading level (H{prev_level} → H{level})",
                "location": _loc(el),
                "suggested_fix": f"Insert an H{prev_level + 1} between the H{prev_level} and this H{level}",
            })
        prev_level = level
    return issues


def verdict_forms(data) -> list:
    issues = []
    if not data:
        return issues
    AUTOCOMPLETE_TYPES = {"text", "email", "tel", "url", "search"}
    for el in data:
        status = el.get("status", "good")
        if status == "missing":
            issues.append({
                "verdict": "fail",
                "element": f"<{el.get('tag','input')}[{el.get('type','')}]> name={el.get('name','')}",
                "description": "Input has no label",
                "location": _loc(el),
                "suggested_fix": f"Add <label for=\"{el.get('name','id')}\">Label text</label> or aria-label",
            })
        elif status == "placeholder":
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','input')}[{el.get('type','')}]> name={el.get('name','')}",
                "description": "Input labelled by placeholder only — placeholder disappears on input",
                "location": _loc(el),
                "suggested_fix": "Add a visible <label> or aria-label; do not rely solely on placeholder",
            })
        if el.get("type", "") in AUTOCOMPLETE_TYPES and not el.get("autocomplete", ""):
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','input')}[{el.get('type','')}]> name={el.get('name','')}",
                "description": "Consider adding autocomplete attribute",
                "location": _loc(el),
                "suggested_fix": "Add appropriate autocomplete token (e.g. autocomplete=\"email\")",
            })
    return issues


def verdict_landmarks(landmark_data, keyboard_data) -> list:
    issues = []
    if not landmark_data:
        issues.append({
            "verdict": "fail",
            "element": "<page>",
            "description": "No <main> landmark",
            "location": "",
            "suggested_fix": "Wrap the primary content in <main id=\"main-content\">",
        })
        return issues

    main_landmarks = [lm for lm in landmark_data if lm.get("role") == "main"]
    if len(main_landmarks) == 0:
        issues.append({
            "verdict": "fail",
            "element": "<page>",
            "description": "No <main> landmark",
            "location": "",
            "suggested_fix": "Wrap the primary content in <main id=\"main-content\">",
        })
    elif len(main_landmarks) > 1:
        for extra in main_landmarks[1:]:
            issues.append({
                "verdict": "fail",
                "element": f"<{extra.get('tag','main')}>",
                "description": "Duplicate <main> landmark",
                "location": _loc(extra),
                "suggested_fix": "Only one <main> landmark is valid per page; remove or change the duplicates",
            })

    nav_landmarks = [lm for lm in landmark_data if lm.get("role") == "navigation"]
    if len(nav_landmarks) > 1:
        unnamed = [lm for lm in nav_landmarks if not lm.get("accessible_name", "").strip()]
        if unnamed:
            for lm in unnamed[1:]:
                issues.append({
                    "verdict": "needs_review",
                    "element": f"<{lm.get('tag','nav')}>",
                    "description": "Navigation landmark has no accessible name — add aria-label to distinguish it",
                    "location": _loc(lm),
                    "suggested_fix": "Add aria-label=\"Primary navigation\" (or similar) to each <nav>",
                })

    # Skip link detection from keyboard data
    has_skip_link = False
    if keyboard_data:
        for el in keyboard_data[:20]:  # only check near start of DOM
            if el.get("tag") == "a" and el.get("href", "").startswith("#"):
                has_skip_link = True
                break
    if not has_skip_link:
        issues.append({
            "verdict": "needs_review",
            "element": "<page>",
            "description": "No skip link detected — add <a href='#main'>Skip to main content</a>",
            "location": "",
            "suggested_fix": "Add a visually-hidden skip link as the first focusable element on the page",
        })

    return issues


def verdict_reflow(data) -> list:
    issues = []
    if not data:
        return issues
    if data.get("has_horizontal_scroll"):
        issues.append({
            "verdict": "fail",
            "element": "<page>",
            "description": "Page requires horizontal scrolling at 320px",
            "location": "",
            "suggested_fix": "Ensure all content reflows to a single column at 320px viewport width",
        })
    for el in data.get("overflow_elements", []):
        ident = f"#{el['id']}" if el.get("id") else (f".{el.get('class','').split()[0]}" if el.get("class","").strip() else "")
        issues.append({
            "verdict": "fail",
            "element": f"<{el.get('tag','?')}{ident}>",
            "description": f"Element overflows viewport at 320px by {el.get('overflowBy', '?')}px",
            "location": f"right:{el.get('right', '?')}",
            "suggested_fix": "Use max-width: 100%, overflow: hidden, or responsive layout to contain the element",
        })
    return issues


def verdict_text_spacing(data) -> list:
    issues = []
    if not data:
        return issues
    if data.get("has_horizontal_scroll"):
        issues.append({
            "verdict": "fail",
            "element": "<page>",
            "description": "Horizontal scroll appears after spacing overrides",
            "location": "",
            "suggested_fix": "Ensure layout does not break when line-height, letter-spacing, and word-spacing are increased",
        })
    for el in data.get("overflowing_elements", []):
        tag = el.get("tag", "?")
        cls = el.get("className", "") or el.get("class", "")
        ident = f".{cls.split()[0]}" if cls.strip() else ""
        issues.append({
            "verdict": "fail",
            "element": f"<{tag}{ident}>",
            "description": "Element clips or overflows after spacing overrides",
            "location": f"scrollWidth:{el.get('scrollWidth','?')} clientWidth:{el.get('clientWidth','?')}",
            "suggested_fix": "Avoid fixed heights and overflow: hidden on text containers",
        })
    return issues


def verdict_contrast(data) -> list:
    issues = []
    if not data:
        return issues
    for el in data:
        if "fg" not in el or "bg" not in el:
            continue
        try:
            ratio = contrast_ratio(el["fg"], el["bg"])
        except Exception:
            continue
        is_large = el.get("isLarge", False)
        threshold = 3.0 if is_large else 4.5
        if ratio < threshold:
            issues.append({
                "verdict": "fail",
                "element": f"<{el.get('tag','?')}> {repr(el.get('text','')[:40])}",
                "description": f"Contrast ratio {ratio:.2f}:1 — minimum is {threshold}:1",
                "location": _loc(el),
                "suggested_fix": "Increase color contrast between foreground and background",
            })
    return issues


def verdict_touch_targets(data) -> list:
    issues = []
    if not data:
        return issues
    for el in data:
        status = el.get("status", "aaa")
        w, h = el.get("w", 0), el.get("h", 0)
        if status == "fail":
            issues.append({
                "verdict": "fail",
                "element": f"<{el.get('tag','?')}> {el.get('label','')[:40]}",
                "description": f"Touch target too small ({w}×{h}px) — minimum 24×24px",
                "location": _loc(el),
                "suggested_fix": "Add min-width: 24px; min-height: 24px (or use padding to increase hit area)",
            })
        elif status == "aa":
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','?')}> {el.get('label','')[:40]}",
                "description": f"Touch target below recommended size ({w}×{h}px) — 44×44px recommended",
                "location": _loc(el),
                "suggested_fix": "Increase to at least 44×44px for AAA compliance and better usability",
            })
    return issues


def verdict_focus_indicators(data) -> list:
    issues = []
    if not data:
        return issues
    for el in data:
        if el.get("focus_visible") is False:
            issues.append({
                "verdict": "fail",
                "element": f"<{el.get('tag','?')}> {el.get('label','')[:40]}",
                "description": "No visible focus indicator detected",
                "location": f"x:{el.get('abs_x',0)} y:{el.get('abs_y',0)} w:{el.get('w',0)} h:{el.get('h',0)}",
                "suggested_fix": "Add :focus { outline: 2px solid #005FCC; } or equivalent visible focus style",
            })
        elif el.get("focus_visible") is True:
            issues.append({
                "verdict": "needs_review",
                "element": f"<{el.get('tag','?')}> {el.get('label','')[:40]}",
                "description": "Focus indicator detected — verify it meets size and contrast requirements",
                "location": f"x:{el.get('abs_x',0)} y:{el.get('abs_y',0)} w:{el.get('w',0)} h:{el.get('h',0)}",
                "suggested_fix": "Ensure focus outline has at least 3:1 contrast and is visually prominent",
            })
    return issues


def verdict_keyboard(data) -> list:
    issues = []
    if not data:
        return issues
    capped = data[:15]
    for el in capped:
        issues.append({
            "verdict": "needs_review",
            "element": f"<{el.get('tag','?')}> {el.get('label','')[:50]}",
            "description": "Verify keyboard operation and focus order",
            "location": f"x:{el.get('left',0)} y:{el.get('top',0)} w:{el.get('w',0)} h:{el.get('h',0)}",
            "suggested_fix": "Manually tab through this element and verify it behaves as expected",
        })
    if len(data) > 15:
        extra = len(data) - 15
        issues.append({
            "verdict": "needs_review",
            "element": "<page>",
            "description": f"...and {extra} more focusable elements — verify all are keyboard accessible",
            "location": "",
            "suggested_fix": "Review all focusable elements for correct keyboard interaction",
        })
    return issues


# ---------------------------------------------------------------------------
# Assemble audit_results.json
# ---------------------------------------------------------------------------

def _rel(ws: Path, path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        return str(path.relative_to(ws)).replace("\\", "/")
    except ValueError:
        return str(path)


def compute_results(url: str, ws: Path) -> dict:
    print("\n[Step 4] Computing verdicts...")

    out = ws / "outputs"

    # Load all JSON data (None if missing)
    headings_data        = load_json(ws / "headings.json")
    desktop_links_data   = load_json(ws / "desktop_links.json")
    mobile_links_data    = load_json(ws / "mobile_links.json")
    image_data           = load_json(ws / "images" / "desktop_crops" / "image_data.json")
    fields_data          = load_json(ws / "desktop_fields.json")
    desktop_lm_data      = load_json(ws / "desktop_landmarks.json")
    keyboard_data        = load_json(ws / "desktop_keyboard.json")
    reflow_data          = load_json(ws / "reflow" / "reflow_data.json")
    spacing_desk_data    = load_json(ws / "text-spacing" / "desktop" / "spacing_data.json")
    contrast_data        = load_json(ws / "desktop_contrast.json")
    desktop_target_data  = load_json(ws / "desktop_targets.json")
    mobile_target_data   = load_json(ws / "mobile_targets.json")
    focus_data           = load_json(ws / "focus" / "focus_data.json")

    # Compute all issues
    link_issues_desk = verdict_links(desktop_links_data)
    link_issues_mob  = verdict_links(mobile_links_data)
    # Merge link issues (dedup by href + flag from mobile)
    all_link_issues = link_issues_desk[:]
    desk_hrefs = {i.get("href") for i in link_issues_desk}
    for issue in link_issues_mob:
        if issue.get("href") not in desk_hrefs:
            all_link_issues.append(issue)

    image_issues     = verdict_images(image_data)
    heading_issues   = verdict_headings(headings_data)
    form_issues      = verdict_forms(fields_data)
    landmark_issues  = verdict_landmarks(desktop_lm_data, keyboard_data)
    reflow_issues    = verdict_reflow(reflow_data)
    spacing_issues   = verdict_text_spacing(spacing_desk_data)
    contrast_issues  = verdict_contrast(contrast_data)
    target_d_issues  = verdict_touch_targets(desktop_target_data)
    target_m_issues  = verdict_touch_targets(mobile_target_data)
    # Merge touch target issues
    all_target_issues = target_d_issues[:]
    for issue in target_m_issues:
        if issue not in all_target_issues:
            all_target_issues.append(issue)
    focus_issues     = verdict_focus_indicators(focus_data)
    keyboard_issues  = verdict_keyboard(keyboard_data)

    def _counts(issues):
        fails   = sum(1 for i in issues if i.get("verdict") == "fail")
        reviews = sum(1 for i in issues if i.get("verdict") == "needs_review")
        return fails, reviews

    def _img(p: Path) -> str | None:
        return _rel(ws, p) if p.exists() else None

    criteria = {
        "wcag-links": {
            "criterion":          "Link Purpose",
            "wcag_ids":           ["2.4.4", "2.4.9"],
            "level":              "AA",
            "description":        "Every link's purpose must be determinable from its text alone.",
            "fail_count":         sum(1 for i in all_link_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in all_link_issues if i["verdict"] == "needs_review"),
            "issues":             all_link_issues,
            "desktop_image":      _img(out / "desktop_links_audit.png"),
            "mobile_image":       _img(out / "mobile_links_audit.png"),
            "extra_images":       [],
        },
        "wcag-images": {
            "criterion":          "Non-text Content",
            "wcag_ids":           ["1.1.1"],
            "level":              "A",
            "description":        "All non-text content must have a text alternative.",
            "fail_count":         sum(1 for i in image_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in image_issues if i["verdict"] == "needs_review"),
            "issues":             image_issues,
            "desktop_image":      _img(out / "desktop_image_sheet.png"),
            "mobile_image":       None,
            "extra_images":       [],
        },
        "wcag-headings": {
            "criterion":          "Heading Structure",
            "wcag_ids":           ["1.3.1", "2.4.6"],
            "level":              "AA",
            "description":        "Headings must be properly structured and describe their content.",
            "fail_count":         sum(1 for i in heading_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in heading_issues if i["verdict"] == "needs_review"),
            "issues":             heading_issues,
            "desktop_image":      _img(out / "desktop_headings.png"),
            "mobile_image":       None,
            "extra_images":       [r for r in [_img(out / "heading_outline.png")] if r],
        },
        "wcag-forms": {
            "criterion":          "Form Labels & Input Purpose",
            "wcag_ids":           ["1.3.1", "1.3.5"],
            "level":              "AA",
            "description":        "Form inputs must have programmatic labels and appropriate autocomplete attributes.",
            "fail_count":         sum(1 for i in form_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in form_issues if i["verdict"] == "needs_review"),
            "issues":             form_issues,
            "desktop_image":      _img(out / "desktop_form_sheet.png"),
            "mobile_image":       None,
            "extra_images":       [],
        },
        "wcag-landmarks": {
            "criterion":          "Landmark Regions",
            "wcag_ids":           ["1.3.6", "2.4.1"],
            "level":              "A",
            "description":        "Pages must have proper landmark structure for screen reader navigation.",
            "fail_count":         sum(1 for i in landmark_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in landmark_issues if i["verdict"] == "needs_review"),
            "issues":             landmark_issues,
            "desktop_image":      _img(out / "desktop_landmarks_audit.png"),
            "mobile_image":       _img(out / "mobile_landmarks_audit.png"),
            "extra_images":       [],
        },
        "wcag-reflow": {
            "criterion":          "Reflow",
            "wcag_ids":           ["1.4.10"],
            "level":              "AA",
            "description":        "Content must reflow to a single column at 320px without horizontal scrolling.",
            "fail_count":         sum(1 for i in reflow_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in reflow_issues if i["verdict"] == "needs_review"),
            "issues":             reflow_issues,
            "desktop_image":      _img(out / "reflow_audit.png"),
            "mobile_image":       None,
            "extra_images":       [],
        },
        "wcag-text-spacing": {
            "criterion":          "Text Spacing",
            "wcag_ids":           ["1.4.12"],
            "level":              "AA",
            "description":        "No loss of content when text spacing is overridden per WCAG 1.4.12.",
            "fail_count":         sum(1 for i in spacing_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in spacing_issues if i["verdict"] == "needs_review"),
            "issues":             spacing_issues,
            "desktop_image":      _img(out / "desktop_spacing_audit.png"),
            "mobile_image":       _img(out / "mobile_spacing_audit.png"),
            "extra_images":       [],
        },
        "wcag-color-contrast": {
            "criterion":          "Color Contrast",
            "wcag_ids":           ["1.4.3", "1.4.6"],
            "level":              "AA",
            "description":        "Text must meet minimum contrast ratios against its background.",
            "fail_count":         sum(1 for i in contrast_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in contrast_issues if i["verdict"] == "needs_review"),
            "issues":             contrast_issues,
            "desktop_image":      _img(out / "desktop_contrast.png"),
            "mobile_image":       None,
            "extra_images":       [],
        },
        "wcag-touch-targets": {
            "criterion":          "Target Size",
            "wcag_ids":           ["2.5.5", "2.5.8"],
            "level":              "AA",
            "description":        "Interactive elements must meet minimum touch target size requirements.",
            "fail_count":         sum(1 for i in all_target_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in all_target_issues if i["verdict"] == "needs_review"),
            "issues":             all_target_issues,
            "desktop_image":      _img(out / "desktop_targets.png"),
            "mobile_image":       _img(out / "mobile_targets.png"),
            "extra_images":       [],
        },
        "wcag-focus-indicators": {
            "criterion":          "Focus Visible",
            "wcag_ids":           ["2.4.7", "2.4.11"],
            "level":              "AA",
            "description":        "All keyboard-focusable elements must have a visible focus indicator.",
            "fail_count":         sum(1 for i in focus_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in focus_issues if i["verdict"] == "needs_review"),
            "issues":             focus_issues,
            "desktop_image":      _img(out / "desktop_focus_sheet.png"),
            "mobile_image":       None,
            "extra_images":       [],
        },
        "wcag-keyboard": {
            "criterion":          "Keyboard Accessible",
            "wcag_ids":           ["2.1.1", "2.4.3"],
            "level":              "A",
            "description":        "All functionality must be operable by keyboard alone.",
            "fail_count":         sum(1 for i in keyboard_issues if i["verdict"] == "fail"),
            "needs_review_count": sum(1 for i in keyboard_issues if i["verdict"] == "needs_review"),
            "issues":             keyboard_issues,
            "desktop_image":      _rel(ws, ws / "desktop_screenshot.png"),
            "mobile_image":       None,
            "extra_images":       [],
        },
    }

    total_fail   = sum(c["fail_count"]   for c in criteria.values())
    total_review = sum(c["needs_review_count"] for c in criteria.values())

    result = {
        "url":          url,
        "audit_date":   datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "fail_count":         total_fail,
            "needs_review_count": total_review,
        },
        "criteria": criteria,
    }

    out_path = ws / "audit_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"  [Step 4] audit_results.json saved to {out_path}")
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Full WCAG accessibility audit — runs all 11 sub-skill checks."
    )
    ap.add_argument("--url",        required=True, help="URL to audit")
    ap.add_argument("--workspace",  required=True, help="Output workspace directory")
    ap.add_argument(
        "--skills-dir",
        default=None,
        help="Root skills/ directory (default: auto-detected from script location)",
    )
    args = ap.parse_args()

    url = args.url

    ws = Path(args.workspace)
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "outputs").mkdir(parents=True, exist_ok=True)

    if args.skills_dir:
        skills_dir = Path(args.skills_dir)
    else:
        # scripts/ → wcag-full-audit/ → skills/
        skills_dir = Path(__file__).parent.parent.parent
    skills_dir = skills_dir.resolve()

    print("=" * 70)
    print(f"WCAG Full Audit")
    print(f"  URL:        {url}")
    print(f"  Workspace:  {ws.resolve()}")
    print(f"  Skills dir: {skills_dir}")
    print("=" * 70)

    # Step 1: Playwright DOM collection
    playwright_collect(url, ws)

    # Step 2: Subprocess captures
    subprocess_captures(url, ws, skills_dir)

    # Step 3: Overlay scripts
    run_overlays(url, ws, skills_dir)

    # Step 4: Compute verdicts and write audit_results.json
    results = compute_results(url, ws)

    fail   = results["summary"]["fail_count"]
    review = results["summary"]["needs_review_count"]

    print("\n" + "=" * 70)
    print(f"Audit complete: {fail} failures, {review} need review")
    print(f"Results: {(ws / 'audit_results.json').resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()
