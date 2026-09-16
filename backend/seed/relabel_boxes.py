"""One-off: relabel the 12 S/B/G boxes printed on the venue artwork.

Final layout: top row = Gold (G4 G3 G2 G1, left->right), second row = Silver
(S1 S2 S3 S4), pink block = Bronze (B1..B4). Regenerates from the pristine
original so it is safe to re-run."""
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

# (center%x, center%y, new label)
boxes = [
    # top row -> gold, numbered right to left
    (31.11, 21.82, "G4"), (35.01, 21.82, "G3"), (39.18, 21.82, "G2"), (43.21, 21.82, "G1"),
    # second row -> silver
    (31.11, 29.17, "S1"), (35.01, 29.17, "S2"), (39.15, 29.11, "S3"), (43.21, 29.11, "S4"),
    # pink block -> bronze
    (30.33, 41.72, "B1"), (25.96, 41.72, "B2"), (25.94, 49.38, "B3"), (30.33, 49.38, "B4"),
]


def median_color(points):
    r = sorted(p[0] for p in points)[len(points) // 2]
    g = sorted(p[1] for p in points)[len(points) // 2]
    b = sorted(p[2] for p in points)[len(points) // 2]
    return (r, g, b)


for xp, yp, label in boxes:
    cx, cy = int(xp / 100 * W), int(yp / 100 * H)
    bg_pts = [px[cx - 46, cy], px[cx + 46, cy], px[cx - 46, cy - 24], px[cx + 46, cy - 24],
              px[cx - 46, cy + 24], px[cx + 46, cy + 24]]
    fill = median_color(bg_pts)
    dark = (60, 60, 70)
    best = 10 ** 9
    for dx in range(-40, 41, 2):
        for dy in range(-26, 27, 2):
            r, g, b = px[cx + dx, cy + dy]
            s = r + g + b
            if s < best:
                best = s
                dark = (r, g, b)
    draw.rectangle([cx - 46, cy - 28, cx + 46, cy + 28], fill=fill)
    draw.text((cx, cy), label, font=FONT, fill=dark, anchor="mm")

im.save(DST)
print("relabelled 12 boxes ->", DST)
