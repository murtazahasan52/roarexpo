"""One-off: relabel + recolour the S/B/G boxes printed on the venue artwork.

Final layout: top row = Gold (G4 G3 G2 G1, left->right) painted a warm gold,
second row = Silver (S1 S2 S3 S4) painted a metallic silver-grey, pink block =
Bronze (B1..B4). Recolouring is done by replacing the orange/green box pixels in
the S/G region row-by-row (top->gold, bottom->silver), which cleanly covers the
old box frames while keeping the dark grid dividers. Regenerates from the
pristine original so it is safe to re-run."""
from PIL import Image, ImageDraw, ImageFont
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "assets" / "final-layout.orig.png"
DST = HERE / "assets" / "final-layout.png"

im = Image.open(SRC).convert("RGB")
W, H = im.size
px = im.load()
draw = ImageDraw.Draw(im)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 46)

GOLD = (240, 190, 74)      # warm gold
SILVER = (196, 203, 212)   # metallic silver-grey
TEXT = (54, 54, 62)

# S/G region on the artwork. Purple T1 (left) and blue X boxes (right) are
# protected by the colour classifier below, so the box can be generous.
X0, X1 = 840, 1330
Y0, Y1 = 210, 406
ROW_SPLIT = 310

gold_boxes = [(31.11, 21.82, "G4"), (35.01, 21.82, "G3"), (39.18, 21.82, "G2"), (43.21, 21.82, "G1")]
silver_boxes = [(31.11, 29.17, "S1"), (35.01, 29.17, "S2"), (39.15, 29.11, "S3"), (43.21, 29.11, "S4")]
bronze_boxes = [(30.33, 41.72, "B1"), (25.96, 41.72, "B2"), (25.94, 49.38, "B3"), (30.33, 49.38, "B4")]


def is_box_color(r, g, b):
    """True for the orange / green box fills and their frames (saturated), but
    False for beige background, dark grid dividers, text, and the purple/blue/
    pink/yellow of neighbouring blocks."""
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 38:            # beige, dividers, text (low saturation)
        return False
    if g == mx and g >= r + 10:  # green fill / frame
        return True
    if r == mx and b == mn and g < r:  # orange fill / frame
        return True
    return False


def median_color(points):
    return tuple(sorted(p[i] for p in points)[len(points) // 2] for i in range(3))


# 1) Recolour box fills + frames by row (keeps dark dividers, text and background).
for y in range(Y0, Y1):
    target = GOLD if y < ROW_SPLIT else SILVER
    for x in range(X0, X1):
        r, g, b = px[x, y]
        if is_box_color(r, g, b):
            px[x, y] = target

# 2) Erase the old printed labels and draw the new ones.
for xp, yp, label in gold_boxes:
    cx, cy = int(xp / 100 * W), int(yp / 100 * H)
    draw.rectangle([cx - 42, cy - 27, cx + 42, cy + 27], fill=GOLD)
    draw.text((cx, cy), label, font=FONT, fill=TEXT, anchor="mm")
for xp, yp, label in silver_boxes:
    cx, cy = int(xp / 100 * W), int(yp / 100 * H)
    draw.rectangle([cx - 42, cy - 27, cx + 42, cy + 27], fill=SILVER)
    draw.text((cx, cy), label, font=FONT, fill=TEXT, anchor="mm")

# 3) Pink bronze boxes: only relabel, keep original colour.
for xp, yp, label in bronze_boxes:
    cx, cy = int(xp / 100 * W), int(yp / 100 * H)
    bg = [px[cx - 46, cy], px[cx + 46, cy], px[cx - 46, cy - 24], px[cx + 46, cy - 24],
          px[cx - 46, cy + 24], px[cx + 46, cy + 24]]
    fill = median_color(bg)
    draw.rectangle([cx - 46, cy - 28, cx + 46, cy + 28], fill=fill)
    draw.text((cx, cy), label, font=FONT, fill=(60, 60, 70), anchor="mm")

im.save(DST)
print("relabelled + recoloured ->", DST)
