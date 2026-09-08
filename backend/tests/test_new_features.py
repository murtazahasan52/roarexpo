"""Iteration 4 - New features: stall-map PDF upload, series, generate-from-series,
public stall endpoints, admin visitor/exhibitor/enquiry edit/delete, files serving.
Also verifies regressions: registration (with email now delivering) and public/stalls
without packageCode returning ALL stalls (behaviour changed from previous 400)."""
import io
import os
import time
import pytest
import requests
from dotenv import dotenv_values

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or dotenv_values("/app/frontend/.env").get("REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE}/api"


# Minimal 1-page PDF (valid, tiny)
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]/Resources<<>>/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 44>>stream\nBT /F1 24 Tf 50 150 Td (Hello Stall Map) Tj ET\nendstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000053 00000 n \n0000000099 00000 n \n0000000178 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n270\n%%EOF\n"
)

# 1x1 transparent PNG
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def token(s):
    r = s.post(f"{API}/admin/login", json={"email": "admin@roarexpo.com", "password": "Admin@12345"})
    assert r.status_code == 200, r.text
    body = r.json()
    tok = body.get("token")
    assert tok, f"Token not at top-level: {body}"
    return tok


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- ADMIN LOGIN ----------
def test_admin_login_token_top_level(s):
    r = s.post(f"{API}/admin/login", json={"email": "admin@roarexpo.com", "password": "Admin@12345"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert isinstance(body.get("token"), str) and len(body["token"]) > 20
    # ensure NOT nested under data
    assert not isinstance((body.get("data") or {}).get("token"), str) or body.get("token")


# ---------- STALL MAP PDF UPLOAD ----------
def test_upload_stall_map_pdf(s, auth):
    files = {"map": ("layout.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    r = s.post(f"{API}/admin/stalls/upload-map", headers=auth, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert "PDF layout converted and uploaded" in body["message"]
    url = body["data"]["url"]
    assert url.startswith("/api/files/") and url.endswith(".png"), url
    assert "stall-maps" in url
    # Fetch that URL
    full = f"{BASE}{url}"
    r2 = s.get(full)
    assert r2.status_code == 200, f"{r2.status_code} {full}"
    assert r2.headers.get("content-type", "").startswith("image/png"), r2.headers.get("content-type")
    assert body["data"]["sourceType"] == "pdf"


def test_upload_stall_map_png(s, auth):
    files = {"map": ("layout.png", io.BytesIO(PNG_1X1), "image/png")}
    r = s.post(f"{API}/admin/stalls/upload-map", headers=auth, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    url = body["data"]["url"]
    assert url.startswith("/api/files/")
    r2 = s.get(f"{BASE}{url}")
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("image/")
    assert body["data"]["sourceType"] == "image"


# ---------- STALL MAP SERIES ----------
def test_update_map_series_valid(s, auth):
    r = s.put(f"{API}/admin/stalls/map-series", headers=auth,
              json={"series": [{"prefix": "G", "packageCode": "gold", "separator": "-"},
                               {"prefix": "S", "packageCode": "silver", "separator": ""}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    series = body["data"]["series"]
    assert len(series) == 2
    codes = {(x["prefix"], x["packageCode"]) for x in series}
    assert ("G", "gold") in codes and ("S", "silver") in codes


def test_update_map_series_invalid_prefix(s, auth):
    r = s.put(f"{API}/admin/stalls/map-series", headers=auth,
              json={"series": [{"prefix": "g1", "packageCode": "gold"}]})
    assert r.status_code == 400
    msg = (r.json().get("message") or r.json().get("detail") or "").lower()
    assert "prefix" in msg, r.json()


def test_update_map_series_unknown_pkg(s, auth):
    r = s.put(f"{API}/admin/stalls/map-series", headers=auth,
              json={"series": [{"prefix": "X", "packageCode": "nonexistent"}]})
    assert r.status_code == 400
    msg = (r.json().get("message") or r.json().get("detail") or "").lower()
    assert "unknown" in msg or "category" in msg, r.json()


# ---------- GENERATE STALLS FROM SERIES ----------
def test_generate_stalls_from_series_and_idempotent(s, auth):
    # Use a small unique prefix to avoid mass-creation. Set count via override.
    s.put(f"{API}/admin/stalls/map-series", headers=auth,
          json={"series": [{"prefix": "TG", "packageCode": "gold", "separator": "-"}]})
    r = s.post(f"{API}/admin/stalls/generate-from-series", headers=auth,
               json={"counts": {"TG": 3}})
    assert r.status_code == 200, r.text
    body = r.json()
    created = body["data"]["created"]
    skipped = body["data"]["skipped"]
    # Either freshly created (3) or already existing from a previous run
    total = len(created) + len(skipped)
    assert total == 3, body
    # Run again — should be all skipped
    r2 = s.post(f"{API}/admin/stalls/generate-from-series", headers=auth,
                json={"counts": {"TG": 3}})
    body2 = r2.json()
    assert len(body2["data"]["created"]) == 0
    assert len(body2["data"]["skipped"]) == 3


# ---------- PUBLIC ENDPOINTS ----------
def test_public_stall_map(s):
    r = s.get(f"{API}/public/stall-map")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data and "url" in data and "sourceType" in data and "series" in data


def test_public_stalls_all(s):
    r = s.get(f"{API}/public/stalls")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert isinstance(data, list)
    # Should include TG-1
    numbers = {x["stallNumber"] for x in data}
    assert any(n.startswith("TG") for n in numbers), f"TG stalls not visible in ALL list; got {list(numbers)[:5]}"


def test_public_stalls_filter(s):
    r = s.get(f"{API}/public/stalls", params={"packageCode": "gold"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert all(x["packageCode"] == "gold" for x in data)


def test_public_stall_directory(s):
    r = s.get(f"{API}/public/stall-directory")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


# ---------- REGRESSION: visitor + exhibitor registration ----------
_created = {"visitor_id": None, "visitor_code": None, "exhibitor_id": None, "enquiry_id": None, "stall_number": None}


def test_visitor_register_no_email_error(s, auth):
    payload = {
        "fullName": "TEST NewFeatures Visitor",
        "email": f"test.newfeat.vis.{int(time.time())}@example.com",
        "phone": "9998887771",
        "city": "Mumbai",
        "numberOfGuests": 2,
        "source": "online",
    }
    r = s.post(f"{API}/visitors/register", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    code = body["data"]["registrationCode"]
    _created["visitor_code"] = code
    # Get id via admin list
    r2 = s.get(f"{API}/admin/visitors", headers=auth, params={"search": code})
    items = r2.json()["data"]
    assert items, "just-created visitor not found via admin list"
    v = items[0]
    _created["visitor_id"] = v["id"] if "id" in v else v.get("_id")
    # No emailError persisted
    assert not v.get("emailError"), f"emailError present: {v.get('emailError')}"


def test_exhibitor_register_no_email_error(s, auth):
    # find a free gold stall (we generated TG-1..3, use one)
    r = s.get(f"{API}/public/stalls", params={"packageCode": "gold"})
    stalls = r.json()["data"]
    avail = [x for x in stalls if x.get("status") == "available" and x["stallNumber"].startswith("TG")]
    if not avail:
        avail = [x for x in stalls if x.get("status") == "available"]
    if not avail:
        pytest.skip("No available gold stalls to test exhibitor register")
    stall_no = avail[0]["stallNumber"]
    _created["stall_number"] = stall_no

    files = {"logo": ("logo.png", io.BytesIO(PNG_1X1), "image/png")}
    ts = int(time.time())
    data = {
        "itsNumber": f"TES{ts % 100000}",
        "contactPerson": "TEST Exh NewFeat",
        "email": f"test.newfeat.exh.{ts}@example.com",
        "phone": "9998887779",
        "companyName": "TEST NewFeat Co",
        "businessAddress": "TEST rd",
        "category": "Food",
        "stallPackage": "gold",
        "stallNumber": stall_no,
        "fasciaName": "TEST FASCIA",
        "agreedToTerms": "true",
    }
    r = s.post(f"{API}/exhibitors/register", data=data, files=files)
    assert r.status_code == 200, r.text
    reg = r.json()["data"]["registrationCode"]
    # find id
    r2 = s.get(f"{API}/admin/exhibitors", headers=auth, params={"search": reg})
    items = r2.json()["data"]
    assert items
    ex = items[0]
    _created["exhibitor_id"] = ex.get("id") or ex.get("_id")
    assert not ex.get("emailError"), f"emailError present: {ex.get('emailError')}"
    # logo url is /api/files
    if ex.get("logoUrl"):
        assert ex["logoUrl"].startswith("/api/files/"), ex["logoUrl"]


# ---------- ADMIN VISITOR EDIT/DELETE ----------
def test_visitor_edit_valid(s, auth):
    vid = _created["visitor_id"]
    assert vid
    r = s.patch(f"{API}/admin/visitors/{vid}", headers=auth,
                json={"city": "Pune", "checkedIn": True, "numberOfGuests": 5})
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["city"] == "Pune"
    assert d["checkedIn"] is True
    assert d["numberOfGuests"] == 5


def test_visitor_edit_invalid_guests(s, auth):
    vid = _created["visitor_id"]
    r = s.patch(f"{API}/admin/visitors/{vid}", headers=auth, json={"numberOfGuests": 99})
    assert r.status_code == 400


def test_visitor_edit_invalid_source(s, auth):
    vid = _created["visitor_id"]
    r = s.patch(f"{API}/admin/visitors/{vid}", headers=auth, json={"source": "carrier-pigeon"})
    assert r.status_code == 400


# ---------- ADMIN ENQUIRY: create via public, then edit/delete ----------
def test_create_and_edit_enquiry(s, auth):
    # Create an enquiry via public endpoint
    payload = {"name": "TEST Enq", "email": f"test.enq.{int(time.time())}@example.com",
               "mobile": "9998887770", "details": "Testing enquiry flow"}
    r = s.post(f"{API}/enquiries", json=payload)
    assert r.status_code == 200, r.text

    # Find id via admin list
    r2 = s.get(f"{API}/admin/enquiries", headers=auth, params={"search": payload["email"]})
    items = r2.json()["data"]
    assert items, "enquiry not visible after create"
    eid = items[0].get("id") or items[0].get("_id")
    _created["enquiry_id"] = eid

    # Edit status to handled
    r3 = s.patch(f"{API}/admin/enquiries/{eid}", headers=auth, json={"status": "handled"})
    assert r3.status_code == 200
    assert r3.json()["data"]["status"] == "handled"

    # Edit invalid status
    r4 = s.patch(f"{API}/admin/enquiries/{eid}", headers=auth, json={"status": "nonsense"})
    assert r4.status_code == 400

    # Edit fields
    r5 = s.patch(f"{API}/admin/enquiries/{eid}", headers=auth, json={"details": "Updated details TEST"})
    assert r5.status_code == 200
    assert r5.json()["data"]["details"] == "Updated details TEST"


def test_delete_enquiry(s, auth):
    eid = _created["enquiry_id"]
    r = s.delete(f"{API}/admin/enquiries/{eid}", headers=auth)
    assert r.status_code == 200


# ---------- ADMIN EXHIBITOR DELETE (releases stall) ----------
def test_delete_exhibitor_releases_stall(s, auth):
    ex_id = _created["exhibitor_id"]
    stall_no = _created["stall_number"]
    if not ex_id or not stall_no:
        pytest.skip("Exhibitor not created")
    r = s.delete(f"{API}/admin/exhibitors/{ex_id}", headers=auth)
    assert r.status_code == 200
    # Verify stall released
    r2 = s.get(f"{API}/public/stalls", params={"packageCode": "gold"})
    st = next((x for x in r2.json()["data"] if x["stallNumber"] == stall_no), None)
    assert st and st["status"] == "available", st


# ---------- ADMIN VISITOR DELETE (cleanup) ----------
def test_delete_visitor(s, auth):
    vid = _created["visitor_id"]
    r = s.delete(f"{API}/admin/visitors/{vid}", headers=auth)
    assert r.status_code == 200


# ---------- Cleanup: delete generated TG stalls ----------
def test_cleanup_tg_stalls(s, auth):
    r = s.get(f"{API}/admin/stalls", headers=auth, params={"packageCode": "gold", "limit": 500})
    assert r.status_code == 200
    body = r.json()
    items = body.get("data") if isinstance(body.get("data"), list) else body.get("items") or []
    for st in items:
        if st.get("stallNumber", "").startswith("TG-"):
            sid = st.get("id") or st.get("_id")
            s.delete(f"{API}/admin/stalls/{sid}", headers=auth)
    # Also reset series to empty to keep app clean
    s.put(f"{API}/admin/stalls/map-series", headers=auth, json={"series": []})


# ---------- FILE ENDPOINT ----------
def test_files_404(s):
    r = s.get(f"{API}/files/does-not-exist-xyz.png")
    assert r.status_code in (404, 403)
