"""
Keyboard accessibility heatmap generator.

Overlays on a page screenshot:
  - Numbered yellow circles at each tab stop (in tab order)
  - Blue arrows connecting tab stops showing flow direction
  - Red outlined boxes on elements that should be keyboard-accessible but are not

Usage:
  python heatmap.py --screenshot page.png --elements elements.json
                    --missing missing.json --output heatmap.png [--label "Desktop (1280px)"]

Requirements: pip install Pillow
"""
import argparse, json, math, sys
from PIL import Image, ImageDraw, ImageFont

CIRCLE_R=14; CIRCLE_FILL=(255,220,0,220); CIRCLE_OUTLINE=(160,120,0,255); NUMBER_COLOR=(20,20,20)
ARROW_COLOR=(60,80,220,170); ARROW_W=2; ARROWHEAD_LEN=11; ARROWHEAD_ANG=28
MISSING_OUTLINE=(210,30,30,240); MISSING_FILL=(210,30,30,30); MISSING_W=3
LABEL_BG=(20,20,20,210); LABEL_TEXT=(255,255,255); LEGEND_BG=(20,20,20,175); LEGEND_TEXT=(255,255,255)
MAX_H=8000; MAX_W=4000

def load_json(p):
    with open(p, encoding='utf-8') as f: return json.load(f)

def clamp(v, lo, hi): return max(lo, min(hi, v))

def get_font(size):
    for c in ['arial.ttf', 'Arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        try: return ImageFont.truetype(c, size)
        except: pass
    return ImageFont.load_default()

def text_size(draw, text, font):
    try:
        bb = draw.textbbox((0,0), text, font=font); return bb[2]-bb[0], bb[3]-bb[1]
    except: return len(text)*8, 14

def draw_arrow(draw, x1, y1, x2, y2, color, width):
    draw.line([(x1,y1),(x2,y2)], fill=color, width=width)
    angle = math.atan2(y2-y1, x2-x1)
    for sign in (+1, -1):
        tip = angle + sign * math.radians(ARROWHEAD_ANG)
        hx = x2 - ARROWHEAD_LEN * math.cos(tip); hy = y2 - ARROWHEAD_LEN * math.sin(tip)
        draw.line([(x2,y2),(int(hx),int(hy))], fill=color, width=width)

def shorten_end(x1, y1, x2, y2, amount):
    dx, dy = x2-x1, y2-y1; dist = math.hypot(dx, dy)
    if dist <= amount: return x2, y2
    r = (dist-amount)/dist; return x1+dx*r, y1+dy*r

def generate(screenshot_path, elements, missing, output_path, label=''):
    img = Image.open(screenshot_path).convert('RGBA'); iw, ih = img.size
    if iw > MAX_W or ih > MAX_H:
        scale = min(MAX_W/iw, MAX_H/ih)
        img = img.resize((int(iw*scale), int(ih*scale)), Image.LANCZOS); iw, ih = img.size
        for el in elements:
            for k in ('x','y','top','left'): el[k] = int(el[k]*scale)
            for k in ('w','h'): el[k] = int(el[k]*scale)
        for el in missing:
            for k in ('x','y'): el[k] = int(el[k]*scale)
            for k in ('w','h'): el[k] = int(el[k]*scale)
    overlay = Image.new('RGBA', (iw,ih), (0,0,0,0)); draw = ImageDraw.Draw(overlay)
    font_num = get_font(13); font_label = get_font(20); font_legend = get_font(13)
    for el in missing:
        x = clamp(el['x'],0,iw-1); y = clamp(el['y'],0,ih-1)
        x2 = clamp(el['x']+max(el['w'],20),0,iw-1); y2 = clamp(el['y']+max(el['h'],20),0,ih-1)
        if x2 > x and y2 > y:
            draw.rectangle([x,y,x2,y2], fill=MISSING_FILL, outline=MISSING_OUTLINE, width=MISSING_W)
    valid = [el for el in elements if 0 <= el['x'] < iw and 0 <= el['y'] < ih]
    for i in range(len(valid)-1):
        a, b = valid[i], valid[i+1]; ex, ey = shorten_end(a['x'],a['y'],b['x'],b['y'],CIRCLE_R+4)
        draw_arrow(draw, a['x'], a['y'], int(ex), int(ey), ARROW_COLOR, ARROW_W)
    for el in valid:
        cx, cy = el['x'], el['y']
        draw.ellipse([cx-CIRCLE_R,cy-CIRCLE_R,cx+CIRCLE_R,cy+CIRCLE_R], fill=CIRCLE_FILL, outline=CIRCLE_OUTLINE, width=2)
        num = str(el.get('tabOrder', el.get('index','?'))); tw, th = text_size(draw, num, font_num)
        draw.text((cx-tw//2, cy-th//2), num, fill=NUMBER_COLOR, font=font_num)
    if label:
        pad = 8; lw, lh = text_size(draw, label, font_label)
        draw.rectangle([10,10,10+lw+pad*2,10+lh+pad*2], fill=LABEL_BG)
        draw.text((10+pad,10+pad), label, fill=LABEL_TEXT, font=font_label)
    legend = [
        '  Numbered circle = keyboard tab stop (in order)',
        '  Arrow = tab flow direction',
        '  Red box = should be keyboard-accessible but is not',
    ]
    ly = ih - 20 - len(legend) * 24
    for line in legend:
        lw, lh = text_size(draw, line, font_legend)
        draw.rectangle([8,ly-3,14+lw+8,ly+lh+5], fill=LEGEND_BG)
        draw.text((12,ly), line, fill=LEGEND_TEXT, font=font_legend); ly += 24
    result = Image.alpha_composite(img, overlay).convert('RGB')
    result.save(output_path, 'PNG')
    print(f'Saved: {output_path}  ({iw}x{ih}px | {len(valid)} tab stops | {len(missing)} missing)')
    return len(valid), len(missing)

def main():
    p = argparse.ArgumentParser(description='WCAG keyboard accessibility heatmap')
    p.add_argument('--screenshot', required=True)
    p.add_argument('--elements',   required=True, help='JSON array of focusable elements with tabOrder')
    p.add_argument('--missing',    required=True, help='JSON array of elements missing from tab order')
    p.add_argument('--output',     required=True)
    p.add_argument('--label',      default='', help='Viewport label shown on image')
    args = p.parse_args()
    generate(args.screenshot, load_json(args.elements), load_json(args.missing), args.output, args.label)

if __name__ == '__main__': main()