"""Iteration 5 - room-alerts features: layout detection (OpenCV+OCR),
apply-layout with mapX/mapY, organizer email alerts (non-blocking),
enquiry auto-reply (ackSent/ackError), admin stats approvedExhibitorCount,
regression on registration + files serving from object storage."""
import io
import os
import time
import struct
import zlib
import pytest
import requests
from dotenv import dotenv_values

BASE = (
    os.environ.get("REACT_APP_BACKEND_URL")
    or dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL")
    or ""
).rstrip("/")
API = f"{BASE}/api"


def _make_png(w: int = 32, h: int = 32, color=(255, 255, 255)) -> bytes:
    """Minimal RGB PNG of a solid colour (no external deps)."""
    def chunk(t, d):
        return (
            struct.pack(">I", len(d)) + t + d
            + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        )
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    r, g, b = color
    raw = b"".join(b"\x00" + bytes((r, g, b)) * w for _ in range(h))
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _make_layout_png(w=800, h=600, cols=4, rows=3):
    """A white background with dark-bordered light rectangles (fake stalls)."""
    import numpy as np, cv2  # noqa
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    margin_x, margin_y = 60, 60
    gap = 20
    bw = (w - 2 * margin_x - (cols - 1) * gap) // cols
    bh = (h - 2 * margin_y - (rows - 1) * gap) // rows
    for r in range(rows):
        for c in range(cols):
            x = margin_x + c * (bw + gap)
            y = margin_y + r * (bh + gap)
            cv2.rectangle(img, (x, y), (x + bw, y + bh), (255, 255, 255), -1)
            cv2.rectangle(img, (x, y), (x + bw, y + bh), (30, 30, 30), 3)
            label = f"G{r * cols + c + 1}"
            cv2.putText(img, label, (x + 15, y + bh // 2 + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


PNG_1X1 = _make_png(1, 1)


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def token(s):
    r = s.post(f"{API}/admin/login",
               json={"email": "admin@roarexpo.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- ADMIN STATS: approvedExhibitorCount / pendingExhibitorCount ----------
def test_admin_stats_has_approved_pending_fields(s, auth):
    r = s.get(f"{API}/admin/stats", headers=auth)
    assert r.status_code == 200
    d = r.json()["data"]
    assert "approvedExhibitorCount" in d
    assert "pendingExhibitorCount" in d
    assert isinstance(d["approvedExhibitorCount"], int)
    assert isinstance(d["pendingExhibitorCount"], int)


# ---------- UPLOAD MAP → returns detection object + /api/files url ----------
def test_upload_map_plain_png_returns_detection(s, auth):
    files = {"map": ("plain.png", io.BytesIO(PNG_1X1), "image/png")}
    r = s.post(f"{API}/admin/stalls/upload-map", headers=auth, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]
    url = data["url"]
    assert url.startswith("/api/files/") and "stall-maps" in url
    # file fetches OK
    r2 = s.get(f"{BASE}{url}")
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("image/")
    det = data.get("detection")
    assert isinstance(det, dict), f"no detection object: {data}"
    for k in ("ok", "boxes", "rows", "prefixes", "ocrEngine"):
        assert k in det, f"detection missing key {k}: {det}"
    assert isinstance(det["boxes"], list)
    assert isinstance(det["rows"], list)
    assert isinstance(det["prefixes"], list)


def test_upload_map_synthetic_layout_detects_boxes(s, auth):
    """A synthetic layout with 12 dark-bordered light rectangles should yield
    a non-zero box count (independent of OCR accuracy)."""
    try:
        img_bytes = _make_layout_png()
    except Exception:
        pytest.skip("cv2/numpy not available")
    files = {"map": ("layout.png", io.BytesIO(img_bytes), "image/png")}
    r = s.post(f"{API}/admin/stalls/upload-map", headers=auth, files=files)
    assert r.status_code == 200, r.text
    det = r.json()["data"]["detection"]
    assert det["ok"] is True
    assert len(det["boxes"]) >= 6, f"expected >=6 boxes, got {len(det['boxes'])}"


# ---------- DETECT-LAYOUT reads from object storage (no 404/500) ----------
def test_detect_layout_reads_from_object_storage(s, auth):
    # First ensure a map exists — upload one
    files = {"map": ("plain2.png", io.BytesIO(PNG_1X1), "image/png")}
    up = s.post(f"{API}/admin/stalls/upload-map", headers=auth, files=files)
    assert up.status_code == 200

    r = s.post(f"{API}/admin/stalls/detect-layout", headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    det = body["data"]["detection"]
    assert "boxes" in det and "rows" in det and "prefixes" in det and "ocrEngine" in det
    assert det["ok"] is True


# ---------- APPLY-LAYOUT: creates stalls with mapX/mapY, idempotent ----------
def test_apply_layout_creates_stalls_with_positions(s, auth):
    # Ensure a map exists
    files = {"map": ("plain3.png", io.BytesIO(PNG_1X1), "image/png")}
    up = s.post(f"{API}/admin/stalls/upload-map", headers=auth, files=files)
    assert up.status_code == 200

    stalls_payload = [
        {"stallNumber": "TAG-1", "packageCode": "gold", "mapX": 10, "mapY": 20},
        {"stallNumber": "TAG-2", "packageCode": "gold", "mapX": 30, "mapY": 20},
        {"stallNumber": "TAG-3", "packageCode": "gold", "mapX": 50, "mapY": 20},
    ]
    series = [{"prefix": "TAG", "packageCode": "gold", "separator": "-"}]
    r = s.post(f"{API}/admin/stalls/apply-layout", headers=auth,
               json={"stalls": stalls_payload, "series": series})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    created_or_updated = set(data.get("created", []) + data.get("updated", []))
    assert {"TAG-1", "TAG-2", "TAG-3"}.issubset(created_or_updated)

    # Verify stall-directory shows them with coords
    d = s.get(f"{API}/public/stall-directory").json()["data"]
    by_no = {x["stallNumber"]: x for x in d}
    for n in ("TAG-1", "TAG-2", "TAG-3"):
        assert n in by_no, f"{n} not in directory"
        assert by_no[n]["mapX"] is not None and by_no[n]["mapY"] is not None

    # Verify stall-map series
    sm = s.get(f"{API}/public/stall-map").json()["data"]
    assert any(x["prefix"] == "TAG" for x in (sm.get("series") or []))

    # Idempotency: re-apply
    r2 = s.post(f"{API}/admin/stalls/apply-layout", headers=auth,
                json={"stalls": stalls_payload, "series": series})
    assert r2.status_code == 200, r2.text


# ---------- ORGANIZER ALERTS: non-blocking on visitor/exhibitor/enquiry ----------
def test_visitor_register_non_blocking(s, auth):
    ts = int(time.time())
    payload = {
        "fullName": "TEST RA Visitor",
        "email": f"test.ra.vis.{ts}@example.com",
        "phone": "9998887111",
        "city": "Pune",
        "numberOfGuests": 1,
        "source": "online",
    }
    r = s.post(f"{API}/visitors/register", json=payload)
    assert r.status_code == 200, r.text
    code = r.json()["data"]["registrationCode"]
    assert code.startswith("RE-VIS-"), code

    # Confirm the record is stored (organizer alert must not have blocked it)
    r2 = s.get(f"{API}/admin/visitors", headers=auth, params={"search": code})
    items = r2.json()["data"]
    assert items, "visitor not found"
    v = items[0]
    # emailError may or may not be present — must not be set (organizer alert failure shouldn't leak here)
    assert not v.get("emailError"), f"unexpected emailError: {v.get('emailError')}"


def test_exhibitor_register_non_blocking(s, auth):
    r = s.get(f"{API}/public/stalls", params={"packageCode": "gold"})
    stalls = r.json()["data"]
    avail = [x for x in stalls if x.get("status") == "available"]
    if not avail:
        pytest.skip("no available gold stalls")
    stall_no = avail[0]["stallNumber"]

    files = {"logo": ("logo.png", io.BytesIO(PNG_1X1), "image/png")}
    ts = int(time.time())
    data = {
        "itsNumber": f"TES{ts % 100000}",
        "contactPerson": "TEST RA Exh",
        "email": f"test.ra.exh.{ts}@example.com",
        "phone": "9998887222",
        "companyName": "TEST RA Co",
        "businessAddress": "TEST rd",
        "category": "Food",
        "stallPackage": "gold",
        "stallNumber": stall_no,
        "fasciaName": "TEST FASCIA RA",
        "agreedToTerms": "true",
    }
    r = s.post(f"{API}/exhibitors/register", data=data, files=files)
    assert r.status_code == 200, r.text
    reg = r.json()["data"]["registrationCode"]
    assert reg.startswith("RE-STL-"), reg

    r2 = s.get(f"{API}/admin/exhibitors", headers=auth, params={"search": reg})
    items = r2.json()["data"]
    assert items
    ex = items[0]
    assert not ex.get("emailError"), f"emailError: {ex.get('emailError')}"
    # logo persists to object storage
    if ex.get("logoUrl"):
        assert ex["logoUrl"].startswith("/api/files/"), ex["logoUrl"]
        rf = s.get(f"{BASE}{ex['logoUrl']}")
        assert rf.status_code == 200

    # Cleanup
    ex_id = ex.get("id") or ex.get("_id")
    if ex_id:
        s.delete(f"{API}/admin/exhibitors/{ex_id}", headers=auth)


def test_enquiry_auto_reply(s, auth):
    ts = int(time.time())
    payload = {
        "name": "TEST RA Enq",
        "email": f"test.ra.enq.{ts}@example.com",
        "mobile": "9998887333",
        "details": "Testing enquiry auto-reply flow",
    }
    r = s.post(f"{API}/enquiries", json=payload)
    assert r.status_code == 200, r.text
    time.sleep(2)  # give the auto-reply mail a moment to update the doc

    r2 = s.get(f"{API}/admin/enquiries", headers=auth, params={"search": payload["email"]})
    items = r2.json()["data"]
    assert items, "enquiry not found"
    e = items[0]
    # ackSent should be True and ackError should be None/absent
    assert e.get("ackSent") is True, f"ackSent not True: {e.get('ackSent')} ackError={e.get('ackError')}"
    assert not e.get("ackError"), f"ackError present: {e.get('ackError')}"

    eid = e.get("id") or e.get("_id")
    if eid:
        s.delete(f"{API}/admin/enquiries/{eid}", headers=auth)


# ---------- CLEANUP: delete visitor + TAG stalls ----------
def test_cleanup_ra(s, auth):
    r = s.get(f"{API}/admin/visitors", headers=auth, params={"search": "test.ra.vis"})
    for v in r.json().get("data", []) or []:
        vid = v.get("id") or v.get("_id")
        if vid:
            s.delete(f"{API}/admin/visitors/{vid}", headers=auth)

    r = s.get(f"{API}/admin/stalls", headers=auth)
    body = r.json()
    items = body.get("data") if isinstance(body.get("data"), list) else []
    for st in items:
        if st.get("stallNumber", "").startswith("TAG-"):
            sid = st.get("id") or st.get("_id")
            if sid:
                s.delete(f"{API}/admin/stalls/{sid}", headers=auth)
