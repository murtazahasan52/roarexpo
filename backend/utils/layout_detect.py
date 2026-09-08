"""
Automatic stall detection for an uploaded venue layout.

Given the layout image (PNG/JPG bytes — a PDF has already been rendered to
PNG by the time this runs), finds every drawn stall box and reads the label
printed inside it (G1, R12, RU3 …), so the admin only has to confirm the
series → category mapping once and every stall is created *with* its map
position — no click-per-stall placement needed.

How it works (no ML for the geometry, just image processing):

1. Box detection — a stall on a layout drawing is a light rectangle fully
   enclosed by a dark border. We threshold the image to "light" pixels and
   run connected-component labelling: every enclosed light region becomes
   one component. Filters drop the page background (touches the image
   edge), the big hall interior (too large), letter holes and noise (too
   small), and anything that isn't box-shaped (low fill ratio / extreme
   aspect ratio). Dashed zones (Food Court, Play Zone) leak into the hall
   region through their gaps and are therefore ignored automatically.

2. Label OCR — each box's interior is cropped and read. Engines are tried
   in order: pytesseract (needs the `tesseract` binary), then
   rapidocr-onnxruntime (pure pip, bundled models). If neither is
   installed the boxes still come back, just unlabelled — the admin then
   assigns a series per row in the confirmation dialog and the numbers are
   filled in left-to-right automatically.

3. Row grouping — boxes are clustered by vertical position and ordered
   left→right within each row, which is what makes that row-based
   auto-numbering fallback work and keeps the confirmation dialog tidy.

4. Sequence check — stalls in a row are numbered consecutively, so a box
   whose label was unreadable or misread (R45 between R14 and R16) is
   corrected from its neighbours, one series at a time. Boxes that still
   have no number afterwards (pillars, trees, the food court) come back
   `ignored` so the dialog leaves them unticked.

Returns plain dicts (percent coordinates, like Stall.mapX/mapY) so the
router can hand them straight to the frontend.
"""
from __future__ import annotations

import re
import shutil

LABEL_RE = re.compile(r"^([A-Z]{1,4})[\s\-_.]?(\d{1,3})$")

# Detection tuning (fractions of the full image unless stated otherwise)
LIGHT_THRESHOLD = 190         # gray value above which a pixel counts as "light" (box interior)
MAX_BOX_AREA_FRACTION = 0.20  # anything bigger is the hall floor, not a stall
MIN_BOX_AREA_FRACTION = 0.0003
MIN_BOX_SIDE_PX = 12
MIN_FILL_RATIO = 0.72         # component area / bounding-box area — rectangles are ~1
MIN_ASPECT, MAX_ASPECT = 0.18, 7.0
MIN_SIDE_VS_MEDIAN = 0.4      # drop slivers thinner than 40% of the typical box side
OCR_TARGET_HEIGHT = 110.0     # crops are upscaled to this height before OCR (small text reads badly)
OCR_WORKERS = 4               # parallel tesseract processes while reading labels
ROW_TOLERANCE = 0.6           # rows: |Δy| < tolerance × box height
# Sequence inference only trusts a neighbour that is actually adjacent
# (edge gap < this × neighbour width) and of comparable size.
ADJACENT_GAP_RATIO = 0.6
SIMILAR_AREA_RANGE = (0.5, 2.2)


def _load_gray(image_bytes: bytes):
    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode the layout image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img, gray


def _components_to_boxes(mask, w, h) -> list[dict]:
    import cv2

    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=4)
    total = w * h
    boxes = []
    for i in range(1, count):
        x, y, bw, bh, area = stats[i]
        if bw < MIN_BOX_SIDE_PX or bh < MIN_BOX_SIDE_PX:
            continue
        if area < MIN_BOX_AREA_FRACTION * total or area > MAX_BOX_AREA_FRACTION * total:
            continue
        if x <= 0 or y <= 0 or x + bw >= w or y + bh >= h:
            continue  # touches the image edge → page background
        if area / float(bw * bh) < MIN_FILL_RATIO:
            continue
        aspect = bw / float(bh)
        if aspect < MIN_ASPECT or aspect > MAX_ASPECT:
            continue
        boxes.append({"px": int(x), "py": int(y), "pw": int(bw), "ph": int(bh)})
    return boxes


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a["px"], a["py"], a["px"] + a["pw"], a["py"] + a["ph"]
    bx1, by1, bx2, by2 = b["px"], b["py"], b["px"] + b["pw"], b["py"] + b["ph"]
    iw = max(0, min(ax2, bx2) - max(ax1, bx1))
    ih = max(0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    if not inter:
        return 0.0
    return inter / float(a["pw"] * a["ph"] + b["pw"] * b["ph"] - inter)


def _find_boxes(img, gray) -> list[dict]:
    """Two complementary passes, merged:
    • light-interior boxes (a white rectangle inside a dark outline — CAD /
      line drawings), and
    • solid-fill boxes (a uniformly coloured or grey rectangle — designed
      plans like a coloured "expo layout"). A 3×3 opening breaks the thin
      light gap lines between neighbouring stalls so a grid doesn't merge
      into one block; trees/plants/cars are irregular and fail the fill-ratio
      test."""
    import cv2
    import numpy as np

    h, w = gray.shape
    light = (gray > LIGHT_THRESHOLD).astype("uint8")
    boxes = _components_to_boxes(light, w, h)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1].astype(int)
    val = hsv[:, :, 2].astype(int)
    # Saturated fills and neutral-grey fills are labelled SEPARATELY: a
    # coloured stall drawn on a grey platform (the title stall on a stage)
    # would otherwise merge with the platform into one big non-box blob.
    kernel = np.ones((3, 3), np.uint8)
    saturated = (sat > 70).astype("uint8")
    greyfill = ((sat < 45) & (val > 100) & (val < 205)).astype("uint8")
    for mask in (saturated, greyfill):
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        for b in _components_to_boxes(mask, w, h):
            if all(_iou(b, o) < 0.5 for o in boxes):
                boxes.append(b)

    # Drop boxes nested inside another detected box (e.g. an inner frame drawn
    # inside a stall) — keep the outer one.
    kept = []
    for b in boxes:
        inside = any(
            o is not b
            and o["px"] <= b["px"] and o["py"] <= b["py"]
            and o["px"] + o["pw"] >= b["px"] + b["pw"] and o["py"] + o["ph"] >= b["py"] + b["ph"]
            for o in boxes
        )
        if not inside:
            kept.append(b)

    # Stalls on one drawing are all roughly the same size. Slivers far
    # thinner than the typical box (legend swatches, banner poles, a strip of
    # walkway) are not stalls — drop them so they never get numbered.
    if len(kept) >= 6:
        sides = sorted(min(b["pw"], b["ph"]) for b in kept)
        median_side = sides[len(sides) // 2]
        kept = [b for b in kept if min(b["pw"], b["ph"]) >= MIN_SIDE_VS_MEDIAN * median_side]
    return kept


# ---------- OCR engines ----------

def _prep_variants(crop_bgr):
    """Several binarisations of a crop — coloured fills, grey fills and plain
    white boxes each read best with a different one. Yields grayscale images
    with dark text on a white background."""
    import cv2
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    scale = max(1.0, OCR_TARGET_HEIGHT / max(1, gray.shape[0]))
    if scale > 1.0:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if (otsu < 128).mean() > 0.5:
        otsu = 255 - otsu
    variants = [otsu, gray]
    if gray.mean() < 170:  # dark/saturated fill — a plain inversion often helps too
        variants.append(255 - gray)
    for v in variants:
        yield cv2.copyMakeBorder(v, 14, 14, 14, 14, cv2.BORDER_CONSTANT, value=255)


def _ocr_pytesseract():
    if not shutil.which("tesseract"):
        return None
    try:
        import pytesseract
    except ImportError:
        return None

    # psm 7 = "single text line". (psm 8 "single word" was measured on real
    # plans and never beat it, so it's not tried — halves the OCR time.)
    cfg = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"

    def run(crop_bgr):
        for v in _prep_variants(crop_bgr):
            try:
                yield pytesseract.image_to_string(v, config=cfg)
            except Exception:  # noqa: BLE001
                continue

    return run


def _ocr_rapidocr():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    engine = RapidOCR()

    def run(crop_bgr):
        for v in _prep_variants(crop_bgr):
            result, _ = engine(v)
            if result:
                yield " ".join(item[1] for item in result)

    return run


def _get_ocr():
    for factory in (_ocr_pytesseract, _ocr_rapidocr):
        try:
            fn = factory()
        except Exception:  # noqa: BLE001 — an engine that fails to init just isn't used
            fn = None
        if fn:
            return fn, factory.__name__.replace("_ocr_", "")
    return None, None


def parse_label(text: str) -> tuple[str, str, int] | None:
    """'g-12' → ('G12', 'G', 12). Returns None if the text isn't a stall label."""
    cleaned = re.sub(r"[^A-Za-z0-9\-]", "", (text or "").upper())
    m = LABEL_RE.match(cleaned)
    if not m:
        return None
    prefix, num = m.group(1), int(m.group(2))
    return f"{prefix}{num}", prefix, num


MULTI_LABEL_RE = re.compile(r"([A-Z]{1,4})[\-_.]?(\d{1,3})")


def _split_merged(text: str) -> list[tuple[str, str, int]]:
    """On a small or heavily compressed drawing the hairline between two
    neighbouring stalls can vanish, so one detected box reads as
    'RU-5 RU-6'. Returns the individual labels when the text holds two or
    more, so the box can be split into that many equal parts."""
    cleaned = re.sub(r"[^A-Z0-9\-_. ]", "", (text or "").upper())
    found = [(f"{p}{int(n)}", p, int(n)) for p, n in MULTI_LABEL_RE.findall(cleaned)]
    return found if len(found) >= 2 else []


def _group_rows(boxes: list[dict]) -> list[list[int]]:
    order = sorted(range(len(boxes)), key=lambda i: (boxes[i]["y"], boxes[i]["x"]))
    rows: list[list[int]] = []
    for i in order:
        b = boxes[i]
        placed = False
        for row in rows:
            ref = boxes[row[0]]
            if abs(b["y"] - ref["y"]) < ROW_TOLERANCE * max(b["h"], ref["h"]):
                row.append(i)
                placed = True
                break
        if not placed:
            rows.append([i])
    for row in rows:
        row.sort(key=lambda i: boxes[i]["x"])
    rows.sort(key=lambda row: boxes[row[0]]["y"])
    return rows


def _read_label(ocr, crop) -> tuple[str, tuple | None, list[str]]:
    """Runs the OCR variants lazily (best-first) and votes: stops as soon as
    two readings agree on a stall label, otherwise takes the first parse.
    Returns (text, parsed, candidates) — `candidates` lists every distinct
    label any variant produced, so the row-sequence pass can pick the one
    that fits its neighbours when the variants disagreed (S1 vs S11)."""
    votes: dict[str, int] = {}
    order: list[str] = []
    first_text: dict[str, str] = {}
    fallback_text = ""
    try:
        for raw in ocr(crop):
            t = (raw or "").strip()
            if not t:
                continue
            p = parse_label(t)
            if p:
                votes[p[0]] = votes.get(p[0], 0) + 1
                if p[0] not in order:
                    order.append(p[0])
                first_text.setdefault(p[0], t)
                if votes[p[0]] >= 2:
                    break
            elif not fallback_text:
                fallback_text = t
    except Exception:  # noqa: BLE001
        pass
    if votes:
        best = max(order, key=lambda k: (votes[k], -order.index(k)))
        return first_text[best], parse_label(best), order
    return fallback_text, None, []


def _adjacent(a: dict, b: dict) -> bool:
    """True when two boxes in a row sit side by side (only a thin line or
    gap between them) and are of comparable size — i.e. they plausibly
    belong to the same run of stalls."""
    gap = abs(a["x"] - b["x"]) - (a["w"] + b["w"]) / 2
    if gap > ADJACENT_GAP_RATIO * min(a["w"], b["w"]):
        return False
    ratio = (a["w"] * a["h"]) / max(1e-6, b["w"] * b["h"])
    return SIMILAR_AREA_RANGE[0] <= ratio <= SIMILAR_AREA_RANGE[1]


def _infer_from_sequence(boxes: list[dict], rows: list[list[int]]) -> None:
    """Stalls in a row are almost always numbered consecutively left→right.
    Use that to (a) fill in a box whose label couldn't be read, and (b)
    correct a misread that breaks the sequence (R45 sitting before R16 and
    R17 is R15). Works one series at a time — a row that holds both R and
    RU stalls is two separate sequences — and only trusts neighbours that
    are physically adjacent and similar in size, so a pillar or a walkway
    strip next to R7 never becomes "R8"."""
    for row in rows:
        if len(row) < 2:
            continue
        counts: dict[str, int] = {}
        for i in row:
            p = boxes[i]["prefix"]
            if p:
                counts[p] = counts.get(p, 0) + 1
        for prefix in sorted(counts, key=lambda p: -counts[p]):
            # The sub-sequence for this series: its own boxes plus anything
            # still unlabelled (which might be one of its stalls misread).
            seq = [i for i in row if boxes[i]["prefix"] == prefix or (not boxes[i]["label"] and not boxes[i]["ignored"])]
            nums = [boxes[i]["number"] if boxes[i]["prefix"] == prefix else None for i in seq]

            def support(k):
                """(expected number, strength) from this box's adjacent
                same-series neighbours. Strength 2 = both sides agree, or one
                side has two consecutive labels in step; 1 = one neighbour."""
                cands = []
                for step in (-1, 1):
                    j = k + step
                    if 0 <= j < len(seq) and nums[j] is not None and _adjacent(boxes[seq[k]], boxes[seq[j]]):
                        exp = nums[j] - step
                        jj = j + step
                        strong = 0 <= jj < len(seq) and nums[jj] is not None and nums[jj] - 2 * step == exp
                        cands.append((exp, 2 if strong else 1))
                if not cands:
                    return None, 0
                if len(cands) == 2:
                    if cands[0][0] != cands[1][0]:
                        return None, 0
                    return cands[0][0], 2
                return cands[0]

            for k, i in enumerate(seq):
                b = boxes[i]
                exp, strength = support(k)
                if exp is None or exp < 1:
                    continue
                if nums[k] is None:
                    if not b["label"]:
                        b.update({"label": f"{prefix}{exp}", "prefix": prefix, "number": exp, "inferred": True})
                        nums[k] = exp
                elif nums[k] != exp:
                    # A misread that breaks the sequence. Override when the
                    # neighbours are convincing, or when OCR itself offered
                    # the expected label as an alternative reading.
                    alt = f"{prefix}{exp}" in b.get("candidates", [])
                    if strength >= 2 or alt:
                        b.update({"label": f"{prefix}{exp}", "number": exp, "inferred": not alt})
                        nums[k] = exp


def _resolve_duplicates(boxes: list[dict]) -> None:
    """Two boxes with the same label: an inferred one loses to one OCR read
    directly; otherwise both are kept and the dialog flags the clash."""
    seen: dict[str, int] = {}
    for i, b in enumerate(boxes):
        if not b["label"] or b["ignored"]:
            continue
        j = seen.get(b["label"])
        if j is None:
            seen[b["label"]] = i
            continue
        loser = i if b["inferred"] and not boxes[j]["inferred"] else (j if boxes[j]["inferred"] and not b["inferred"] else None)
        if loser is not None:
            boxes[loser].update({"label": "", "prefix": "", "number": None, "inferred": False})
            if loser == j:
                seen[b["label"]] = i


def detect_layout(image_bytes: bytes) -> dict:
    img, gray = _load_gray(image_bytes)
    h, w = gray.shape
    raw_boxes = _find_boxes(img, gray)

    ocr, engine = _get_ocr()

    def read_one(rb):
        if not ocr:
            return "", None, []
        m = max(2, int(min(rb["pw"], rb["ph"]) * 0.08))  # stay clear of the border stroke
        crop = img[rb["py"] + m: rb["py"] + rb["ph"] - m, rb["px"] + m: rb["px"] + rb["pw"] - m]
        if not crop.size:
            return "", None, []
        return _read_label(ocr, crop)

    # OCR is the slow part (a tesseract process per crop); a hundred stalls
    # read one after another take ~40 s, so run them on a small thread pool
    # (tesseract is an external process, so threads really do run in
    # parallel here). rapidocr is in-process and not thread-safe → serial.
    if ocr and engine == "pytesseract" and len(raw_boxes) > 8:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=OCR_WORKERS) as pool:
            readings = list(pool.map(read_one, raw_boxes))
    else:
        readings = [read_one(rb) for rb in raw_boxes]

    boxes = []
    for rb, (text, parsed, candidates) in zip(raw_boxes, readings):

        def add_box(px, py, pw, ph, text, parsed, candidates):
            letters_only = re.sub(r"[^A-Z]", "", text.upper())
            ignored = bool(text) and parsed is None and len(letters_only) >= 4 and not re.search(r"\d", text)
            boxes.append({
                "x": round((px + pw / 2) / w * 100, 2),
                "y": round((py + ph / 2) / h * 100, 2),
                "w": round(pw / w * 100, 2),
                "h": round(ph / h * 100, 2),
                "text": text,
                "label": parsed[0] if parsed else "",
                "prefix": parsed[1] if parsed else "",
                "number": parsed[2] if parsed else None,
                "candidates": candidates,
                # A box whose text is a plain word (ENTRANCE, STAGE, EXIT …) is
                # not a stall — pre-flagged so the dialog leaves it unticked.
                "ignored": ignored,
                "inferred": False,
            })

        merged = _split_merged(text) if parsed is None else []
        if merged and rb["pw"] > rb["ph"]:
            # Neighbouring stalls whose dividing line was lost — split the
            # box into equal parts, one per label read, left to right.
            n = len(merged)
            part = rb["pw"] / n
            for k, lab in enumerate(merged):
                add_box(rb["px"] + int(k * part), rb["py"], int(part), rb["ph"], lab[0], lab, [lab[0]])
        else:
            add_box(rb["px"], rb["py"], rb["pw"], rb["ph"], text, parsed, candidates)

    rows = _group_rows(boxes)
    _infer_from_sequence(boxes, rows)
    _resolve_duplicates(boxes)

    # Anything still without a stall number after all that (a pillar, a
    # tree, the food court…) is left unticked in the dialog: the admin can
    # tick it and type a number if it really is a stall, but Save & Apply
    # must not be blocked by a dozen bits of scenery.
    for b in boxes:
        if not b["label"]:
            b["ignored"] = True
        b.pop("candidates", None)

    # Series suggestions: one per prefix seen, with how many boxes carry it.
    prefixes: dict[str, int] = {}
    for b in boxes:
        if b["prefix"] and not b["ignored"]:
            prefixes[b["prefix"]] = prefixes.get(b["prefix"], 0) + 1

    return {
        "imageWidth": int(w),
        "imageHeight": int(h),
        "ocrEngine": engine,
        "boxes": boxes,
        "rows": rows,
        "prefixes": [{"prefix": p, "count": n} for p, n in sorted(prefixes.items(), key=lambda kv: -kv[1])],
    }


def suggest_package_for_prefix(prefix: str, packages: list[dict]) -> str | None:
    """Best-effort default for the series → category dropdown: exact code
    initials first (RU → ruby, G → gold), then first letter."""
    p = prefix.upper()
    for pkg in packages:
        if not pkg.get("hasStallPicker"):
            continue
        code = pkg["code"].upper()
        if code.startswith(p) and len(p) >= 2:
            return pkg["code"]
    for pkg in packages:
        if pkg.get("hasStallPicker") and pkg["code"].upper().startswith(p[:1]):
            return pkg["code"]
    return None
