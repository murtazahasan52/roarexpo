"""OPTIONAL fallback renderer. The bundled map (seed/assets/final-layout.png) is
now the designer's artwork itself, so this script is NOT used to produce it —
keep it only if you ever need a generated drawing again (it would overwrite
the artwork). It renders a map from the stall list: a clean, branded version of the organizers' drawing — no running-track
lines, red-carpet walkways with direction chevrons, tinted Food Court / Play
Zone, entry/exit, legend. Every stall is drawn exactly where
final_layout.json says it is (percent of the image), so the positions the
app uses stay valid.

The walkways, hall outline and zones are derived from the stall rows
themselves, so re-running this after the drawing changes needs no manual
tuning. Run from backend_fastapi/:  python seed/render_final_layout.py
"""
import json
import pathlib

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
FONT_DIR = HERE.parent / "assets" / "fonts"
BOLD = str(FONT_DIR / "DejaVuSans-Bold.ttf")
REG = str(FONT_DIR / "DejaVuSans.ttf")
SERIF = str(FONT_DIR / "DejaVuSerif-Bold.ttf")

lay = json.load(open(HERE / "final_layout.json"))
boxes = json.load(open(HERE / "final_layout_boxes.json"))  # x, y, w, h (percent), text
W, H = lay["imageWidth"], lay["imageHeight"]
S = W / 2160.0  # stroke/font scale relative to the design size

COLORS = {  # border, fill
    "title": ("#b45309", "#fde9d4"), "diamond": ("#c99700", "#fff4c2"), "gold": ("#9a3412", "#fbe2d2"),
    "silver": ("#0e8fb3", "#d9f2fb"), "bronze": ("#0369a1", "#dbeafe"), "premium": ("#c81e1e", "#fde2e2"),
    "ruby": ("#c2258f", "#fbe0f2"), "regular": ("#6d28d9", "#ebe3fb"), "food": ("#15803d", "#dcfce7"),
}
INK, CARPET, CARPET_DARK, GOLD, WALL = "#101c33", "#b3121d", "#7f0a12", "#e0a828", "#9aa3b2"
PREMIUM = {"T1", "D1", "D2"}

img = Image.new("RGB", (W, H), "#ffffff")
d = ImageDraw.Draw(img)


def P(x, y):
    return (x / 100 * W, y / 100 * H)


def font(path, px):
    return ImageFont.truetype(path, max(8, int(px)))


def rrect(x1, y1, x2, y2, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=int(width))


def text_center(cx, cy, s, f, fill=INK):
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], cy - (bb[3] - bb[1]) / 2 - bb[1]), s, font=f, fill=fill)


def mid(t):
    return (t[0] + t[1]) / 2


# ---------------- geometry from the stalls ----------------
by_num = {b["text"]: b for b in boxes}
stall_boxes = [by_num[s["stallNumber"]] for s in lay["stalls"]]
food_boxes = [b for b in boxes if b["text"] == "44"]


def top(b):
    return b["y"] - b["h"] / 2


def bottom(b):
    return b["y"] + b["h"] / 2


def left(b):
    return b["x"] - b["w"] / 2


def right(b):
    return b["x"] + b["w"] / 2


col_x = max(b["x"] for b in stall_boxes)                     # the right-hand column of stalls
column = [b for b in stall_boxes if b["x"] > col_x - 1.5]
body = [b for b in stall_boxes if b["x"] <= col_x - 1.5]      # everything else, in rows
rows = []
for b in sorted(body, key=lambda b: b["y"]):
    for r in rows:
        if abs(r["y"] - b["y"]) < max(b["h"], r["h"]) * 0.6:
            r["boxes"].append(b)
            break
    else:
        rows.append({"y": b["y"], "h": b["h"], "boxes": [b]})
rows.sort(key=lambda r: r["y"])


def row_top(r):
    return min(top(b) for b in r["boxes"])


def row_bottom(r):
    return max(bottom(b) for b in r["boxes"])


def row_left(r):
    return min(left(b) for b in r["boxes"])


# rows: 0 top Y row (with D1/D2), 1 S/X (T1 spans 1-2), 2 B/X, 3 G/Y, 4 G/Y, 5 L
r_top, r_sx, r_bx, r_gy1, r_gy2, r_l = rows[0], rows[1], rows[2], rows[3], rows[4], rows[5]
gap = 0.6  # percent breathing room around carpets
band1 = (row_bottom(r_top) + gap, row_top(r_sx) - gap)       # between top row and S/X row
band2 = (row_bottom(r_bx) + gap, row_top(r_gy1) - gap)       # between B/X row and G/Y rows
band3 = (row_bottom(r_gy2) + gap, row_top(r_l) - gap)        # between bottom Y row and L row
aisle_right = min(left(b) for b in column) - gap             # carpets stop before the column
hall_left = min(row_left(r) for r in rows) - 5.5
aisle_left = (hall_left + 1.4, min(row_left(r) for r in rows) - gap)
l_sorted = sorted(r_l["boxes"], key=lambda b: b["x"])        # the gap in the L row leads to the food court
gaps = [(right(a), left(b)) for a, b in zip(l_sorted, l_sorted[1:]) if left(b) - right(a) > 2.5]
branch = max(gaps, key=lambda g: g[1] - g[0])
branch = (branch[0] + gap, branch[1] - gap)
band_h = band3[1] - band3[0]
band4 = (row_bottom(r_l) + gap, row_bottom(r_l) + gap + band_h)   # under the left L row, joins the left aisle and the branch
zone_top_play = band4[1] + 1.0
zone_top_food = row_bottom(r_l) + 1.0
zone_bottom = max(bottom(b) for b in food_boxes) + 14
hall_right = max(right(b) for b in column) + 1.6
hall_top = row_top(r_top) - 2.2
hall_bottom = zone_bottom + 1.6
landing = (max(bottom(b) for b in food_boxes) + 1.2, max(bottom(b) for b in food_boxes) + 1.2 + band_h)

# ---------------- draw ----------------
rrect(*P(hall_left, hall_top), *P(hall_right, hall_bottom), 28 * S, fill="#fbf9f4", outline=WALL, width=3 * S)


def zone(x1, y1, x2, y2, fill, outline, label):
    a, b = P(x1, y1)
    c, e = P(x2, y2)
    rrect(a, b, c, e, 18 * S, fill=fill, outline=outline, width=2 * S)
    text_center((a + c) / 2, e - 30 * S, label, font(BOLD, 34 * S), fill=outline)


zone(hall_left + 1.4, zone_top_play, branch[0] - 0.9, zone_bottom - 1.2, "#e8f4ff", "#3b82c4", "PLAY ZONE")
zone(branch[1] + 0.9, zone_top_food, hall_right - 1.4, zone_bottom - 1.2, "#fff3e0", "#d97706", "FOOD COURT")


def carpet(x1, y1, x2, y2):
    a, b = P(x1, y1)
    c, e = P(x2, y2)
    rrect(a, b, c, e, 10 * S, fill=CARPET_DARK)
    rrect(a + 5 * S, b + 5 * S, c - 5 * S, e - 5 * S, 8 * S, fill=CARPET)
    d.rounded_rectangle([a + 2 * S, b + 2 * S, c - 2 * S, e - 2 * S], radius=9 * S, outline=GOLD, width=int(1.6 * S))


carpet(aisle_left[0], band1[0], aisle_right, band1[1])
carpet(aisle_left[0], band2[0], aisle_right, band2[1])
carpet(aisle_left[0], band3[0], aisle_right, band3[1])
carpet(aisle_left[0], band4[0], branch[1], band4[1])
carpet(aisle_left[0], band1[0], aisle_left[1], band4[1])
carpet(branch[0], band3[0], branch[1], landing[1])
carpet(branch[0], landing[0], branch[1] + 14, landing[1])


def chevron(cx, cy, dirn, size=9 * S):
    x, y = P(cx, cy)
    dx, dy = dirn
    w = int(3 * S)
    if dx:
        d.line([(x - dx * size, y - size), (x, y), (x - dx * size, y + size)], fill=GOLD, width=w, joint="curve")
    else:
        d.line([(x - size, y - dy * size), (x, y), (x + size, y - dy * size)], fill=GOLD, width=w, joint="curve")


# entry / exit through the left wall
fe = font(BOLD, 26 * S)


def arrow(x1, y, x2, color, head=14 * S):
    a, b = P(x1, y)
    c, _ = P(x2, y)
    d.line([(a, b), (c, b)], fill=color, width=int(4 * S))
    dirn = 1 if c > a else -1
    d.polygon([(c, b), (c - dirn * head, b - head * 0.6), (c - dirn * head, b + head * 0.6)], fill=color)


wx = P(hall_left, 0)[0]
for band in (band1, band3):
    d.rectangle([wx - 4 * S, P(0, band[0] + 0.6)[1], wx + 4 * S, P(0, band[1] - 0.6)[1]], fill="#fbf9f4")
text_center(*P(hall_left - 3.4, band1[0] + 0.2), "ENTRY", fe, fill=CARPET)
arrow(hall_left - 5.2, mid(band1), hall_left + 1.2, CARPET)
text_center(*P(hall_left - 3.4, band3[0] + 0.2), "EXIT", fe, fill=CARPET)
arrow(hall_left + 1.2, mid(band3), hall_left - 5.2, CARPET)

# stalls
code_of = {s["stallNumber"]: s["packageCode"] for s in lay["stalls"]}


def stall_box(b, code, label):
    a, bb = P(left(b), top(b))
    c, e = P(right(b), bottom(b))
    border, fill = COLORS[code]
    premium = label in PREMIUM
    if premium:
        border, fill = "#b8740f", "#ffe08a"
    rrect(a, bb, c, e, 6 * S, fill=fill, outline=border, width=(3.2 if premium else 2.4) * S)
    if premium:
        rrect(a + 4 * S, bb + 4 * S, c - 4 * S, e - 4 * S, 4 * S, outline=GOLD, width=1.5 * S)
    big = b["w"] > 4 or b["h"] > 9
    fh = min((e - bb) * 0.42, (c - a) * 0.28 * (1.35 if big else 1.0))
    text_center((a + c) / 2, (bb + e) / 2 + (2 * S if premium else 0), ("★ " + label) if premium else label, font(BOLD, max(16 * S, fh)))
    if premium:
        text_center((a + c) / 2, bb + 9 * S, "PREMIUM", font(BOLD, 8.5 * S), fill="#7a5200")


for b in stall_boxes:
    stall_box(b, code_of[b["text"]], b["text"])
for b in food_boxes:
    stall_box(b, "food", "4 × 4")

# legend
lx, ly = P(hall_right + 1.6, hall_top + 2.5)
fl, fs = font(BOLD, 21 * S), font(REG, 19 * S)
d.text((lx, ly), "STALL SIZES", font=font(BOLD, 24 * S), fill=INK)
rows_legend = [
    ("title", "★ T1 · premium", "6m × 6m"), ("diamond", "★ D1 – D2 · premium", "6m × 3m"), ("gold", "G1 – G4", "6m × 3m"),
    ("premium", "XY1, XY2", "7m × 3m"), ("silver", "S1 – S4", "4m × 3m"), ("bronze", "B1 – B4", "4m × 3m"),
    ("premium", "X1 – X28", "4m × 3m"), ("ruby", "Y1 – Y72", "3m × 3m"), ("regular", "L1 – L27", "3m × 3m"),
    ("food", "Food Court", "4m × 4m"),
]
y = ly + 46 * S
for code, name, size in rows_legend:
    border, fill = COLORS[code]
    rrect(lx, y + 3 * S, lx + 26 * S, y + 25 * S, 5 * S, fill=fill, outline=border, width=2 * S)
    d.text((lx + 36 * S, y), name, font=fl, fill=INK)
    d.text((lx + 36 * S, y + 25 * S), size, font=fs, fill="#5b6478")
    y += 56 * S
rrect(lx, y + 6 * S, lx + 26 * S, y + 20 * S, 4 * S, fill=CARPET, outline=GOLD, width=1.5 * S)
d.text((lx + 36 * S, y), "Red carpet walkway", font=fs, fill="#5b6478")

d.text((P(hall_left, 0)[0], P(0, 0.9)[1]), "ROAR — BUSINESS EXPO NAGPUR  ·  VENUE LAYOUT", font=font(SERIF, 26 * S), fill=INK)

img.save(HERE / "assets" / "final-layout.png", optimize=True)
print("written", HERE / "assets" / "final-layout.png", img.size)
