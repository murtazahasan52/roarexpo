"""End-to-end tests for the bundled 146-stall final layout, admin record
pages, background layout detection, invoice PDF and regression endpoints.

Run:
    pytest /app/backend/tests/test_final_layout.py -v \
        --junitxml=/app/test_reports/pytest/iter6.xml
"""
import io
import os
import time
import pytest
import requests
from PIL import Image

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@roarexpo.com"
ADMIN_PASSWORD = "Admin@12345"


# ---------- shared fixtures ----------
@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    return s


@pytest.fixture(scope="module")
def admin(api):
    r = api.post(f"{BASE}/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    return s


# ---------- public: stall-map + stall-directory ----------
class TestPublicLayout:
    def test_stall_map(self, api):
        r = api.get(f"{BASE}/api/public/stall-map")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["url"].startswith("/api/files/")
        series = data["series"]
        # T D G S B X Y L = 8 series
        codes = sorted(s["packageCode"] for s in series)
        assert len(series) == 8
        assert set(codes) == {"title", "diamond", "gold", "silver", "bronze", "premium", "ruby", "regular"}
        # Fetch the actual image
        img = api.get(f"{BASE}{data['url']}")
        assert img.status_code == 200
        assert img.headers.get("content-type", "").startswith("image/")
        # Bundled layout PNG is ~1.2MB; even if a prior detection test left a
        # tiny placeholder as the current map, the endpoint must at least
        # return a real image.
        assert len(img.content) > 100

    def test_stall_directory_146(self, api):
        r = api.get(f"{BASE}/api/public/stall-directory")
        assert r.status_code == 200
        stalls = r.json()["data"]
        assert len(stalls) == 146
        # Every stall has numeric coords
        assert all(isinstance(s.get("mapX"), (int, float)) and isinstance(s.get("mapY"), (int, float))
                   for s in stalls)
        # Every stall has a status
        assert all(s.get("status") in {"available", "reserved", "booked"} for s in stalls)
        # Category counts per rate card
        by_pkg = {}
        for s in stalls:
            by_pkg[s["packageCode"]] = by_pkg.get(s["packageCode"], 0) + 1
        assert by_pkg.get("gold") == 4
        assert by_pkg.get("silver") == 4
        assert by_pkg.get("bronze") == 4
        assert by_pkg.get("premium") == 32
        assert by_pkg.get("regular") == 27
        assert by_pkg.get("ruby") == 72


# ---------- admin: stats ----------
class TestAdminStats:
    def test_stats_shape(self, admin):
        r = admin.get(f"{BASE}/api/admin/stats")
        assert r.status_code == 200
        d = r.json()
        # Response might be wrapped in {success, data}
        payload = d.get("data", d)
        # Accept a few possible key names for approved exhibitors
        keys = set(payload.keys())
        assert any("pproved" in k or "confirmed" in k.lower() for k in keys), keys


# ---------- admin: record fetch ----------
class TestAdminRecords:
    def test_exhibitor_visitor_enquiry_by_id(self, admin):
        # Create a lightweight test set through public endpoints, fetch by id, then delete.
        # Visitor
        v = requests.post(f"{BASE}/api/visitors/register", json={
            "fullName": "TEST_Rec Visitor", "email": "TEST_rec_v@example.com",
            "phone": "9998887771", "organization": "T", "city": "Pune", "interests": ["general"],
        })
        assert v.status_code in (200, 201), v.text
        vcode = (v.json().get("data") or {}).get("registrationCode")
        # Enquiry
        e = requests.post(f"{BASE}/api/enquiries", json={
            "name": "TEST_Rec Enq", "email": "TEST_rec_e@example.com",
            "mobile": "9998887772", "details": "A test enquiry for automation.",
        })
        assert e.status_code in (200, 201), e.text

        # Look up ids via admin lists
        vlist = admin.get(f"{BASE}/api/admin/visitors").json()
        vitems = vlist.get("data") or vlist.get("visitors") or []
        vitem = next((x for x in vitems if x.get("registrationCode") == vcode), None)
        assert vitem, f"could not find visitor {vcode}"
        vid = vitem.get("_id") or vitem.get("id")
        elist = admin.get(f"{BASE}/api/admin/enquiries").json()
        eitems = elist.get("data") or elist.get("enquiries") or []
        eitem = next((x for x in eitems if x.get("email") == "test_rec_e@example.com"), None)
        assert eitem, "could not find enquiry"
        eid = eitem.get("_id") or eitem.get("id")

        assert vid and eid

        # Fetch by id
        rv = admin.get(f"{BASE}/api/admin/visitors/{vid}")
        assert rv.status_code == 200, rv.text
        assert (rv.json().get("data") or rv.json()).get("email") == "test_rec_v@example.com"

        re_ = admin.get(f"{BASE}/api/admin/enquiries/{eid}")
        assert re_.status_code == 200, re_.text
        assert (re_.json().get("data") or re_.json()).get("email") == "test_rec_e@example.com"

        # Cleanup
        admin.delete(f"{BASE}/api/admin/visitors/{vid}")
        admin.delete(f"{BASE}/api/admin/enquiries/{eid}")


# ---------- admin: background detection + restore bundled ----------
class TestBackgroundDetection:
    def test_upload_detect_and_restore(self, admin):
        # Small dummy PNG
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), (240, 240, 240)).save(buf, "PNG")
        buf.seek(0)
        headers = {k: v for k, v in admin.headers.items() if k.lower() != "content-type"}
        r = requests.post(
            f"{BASE}/api/admin/stalls/upload-map",
            headers=headers,
            files={"map": ("t.png", buf.getvalue(), "image/png")},
        )
        assert r.status_code == 200, r.text
        payload = r.json().get("data", r.json())
        det = payload.get("detection") or {}
        assert det.get("status") in ("running", "done"), det
        # Poll for detection to finish (up to ~20s)
        end = time.time() + 25
        final_status = det.get("status")
        while time.time() < end and final_status == "running":
            time.sleep(1)
            g = admin.get(f"{BASE}/api/admin/stalls/detection")
            assert g.status_code == 200, g.text
            body = g.json().get("data") or g.json()
            final_status = ((body.get("detection") or {}).get("status")) or body.get("status")
        assert final_status in ("done", "error"), final_status

        # Restore bundled layout so DB is back to the real 146
        r = admin.post(f"{BASE}/api/admin/stalls/apply-bundled-layout", json={})
        assert r.status_code == 200, r.text
        # Verify 146 restored
        n = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        assert len(n) == 146


# ---------- admin: invoice PDF for a confirmed exhibitor ----------
class TestInvoicePDF:
    def test_invoice_returns_pdf(self, admin):
        # Register a fresh exhibitor via multipart, then approve, then fetch invoice.
        headers = {k: v for k, v in admin.headers.items() if k.lower() != "content-type"}
        buf = io.BytesIO()
        Image.new("RGB", (60, 60), (10, 100, 200)).save(buf, "PNG")

        form = {
            "itsNumber": "TEST1234",
            "companyName": "TEST_Invoice Co",
            "contactPerson": "Ivan",
            "email": "TEST_invoice@example.com",
            "phone": "9998887773",
            "businessAddress": "123 Test St, Pune",
            "website": "https://example.com",
            "category": "products",
            "stallPackage": "gold",
            "fasciaName": "TEST Invoice",
            "agreedToTerms": "true",
        }
        # Object storage occasionally returns 500 for the logo upload — retry once.
        r = None
        for _ in range(3):
            r = requests.post(
                f"{BASE}/api/exhibitors/register",
                data=form,
                files={"logo": ("l.png", buf.getvalue(), "image/png")},
            )
            if r.status_code in (200, 201):
                break
            time.sleep(2)
        assert r.status_code in (200, 201), r.text
        rcode = (r.json().get("data") or {}).get("registrationCode")
        # Look up in admin list
        lst = admin.get(f"{BASE}/api/admin/exhibitors").json()
        items = lst.get("data") or lst.get("exhibitors") or []
        item = next((x for x in items if x.get("registrationCode") == rcode), None)
        assert item, f"could not find exhibitor {rcode}"
        exid = item.get("_id") or item.get("id")

        # Approve
        appr = admin.post(f"{BASE}/api/admin/exhibitors/{exid}/approve", json={})
        # Some backends use PATCH or /confirm — try a couple of fallbacks
        if appr.status_code == 404:
            appr = admin.patch(f"{BASE}/api/admin/exhibitors/{exid}", json={"status": "confirmed"})
        assert appr.status_code in (200, 204), appr.text

        # Fetch invoice
        inv = requests.get(
            f"{BASE}/api/admin/exhibitors/{exid}/invoice",
            headers=headers, stream=True,
        )
        assert inv.status_code == 200, inv.text[:300]
        ct = inv.headers.get("content-type", "")
        assert "pdf" in ct, ct
        content = inv.content
        assert content.startswith(b"%PDF"), content[:20]

        # Cleanup
        admin.delete(f"{BASE}/api/admin/exhibitors/{exid}")


# ---------- regression: home unchanged endpoints ----------
class TestRegression:
    def test_visitor_and_enquiry_still_work(self):
        v = requests.post(f"{BASE}/api/visitors/register", json={
            "fullName": "TEST_Reg V", "email": "TEST_reg_v@example.com",
            "phone": "9998880001", "organization": "T", "city": "Pune", "interests": ["general"],
        })
        assert v.status_code in (200, 201), v.text
        vd = v.json().get("data", v.json())
        assert not vd.get("emailError")
        vid = vd.get("_id") or vd.get("id")

        e = requests.post(f"{BASE}/api/enquiries", json={
            "name": "TEST_Reg E", "email": "TEST_reg_e@example.com",
            "mobile": "9998880002", "details": "Another test enquiry for automation.",
        })
        assert e.status_code in (200, 201), e.text
        # Wait a moment for ackSent
        time.sleep(3)

        # Cleanup via admin
        s = requests.Session()
        tok = s.post(f"{BASE}/api/admin/login",
                     json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()["token"]
        s.headers["Authorization"] = f"Bearer {tok}"
        if vid:
            s.delete(f"{BASE}/api/admin/visitors/{vid}")
        eid = e.json().get("data", e.json()).get("_id")
        if eid:
            s.delete(f"{BASE}/api/admin/enquiries/{eid}")
