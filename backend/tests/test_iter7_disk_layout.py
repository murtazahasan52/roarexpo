"""Iteration 7 — ROAR Expo backend regression.

Verifies the DISK-served bundled 141-stall final layout, exhibitor stall
hold/release lifecycle, admin approve/reject/reopen, and generic
visitor/enquiry regression.

Run:
    pytest /app/backend/tests/test_iter7_disk_layout.py -v \
      --junitxml=/app/test_reports/pytest/iter7.xml
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


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    r = s.post(f"{BASE}/api/admin/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


# ---------- File serving (disk /uploads) ----------
class TestFileServing:
    def test_stall_map_url(self):
        r = requests.get(f"{BASE}/api/public/stall-map")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["url"] == "/uploads/stall-maps/final-layout.png", data

    def test_image_via_api_uploads(self):
        r = requests.get(f"{BASE}/api/uploads/stall-maps/final-layout.png")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert len(r.content) > 1000

    def test_stall_directory_141(self):
        r = requests.get(f"{BASE}/api/public/stall-directory")
        assert r.status_code == 200
        stalls = r.json()["data"]
        assert len(stalls) == 141, f"expected 141, got {len(stalls)}"
        for s in stalls:
            assert isinstance(s.get("mapX"), (int, float))
            assert isinstance(s.get("mapY"), (int, float))
            assert s.get("status") in {"available", "reserved", "booked", "held"}
        by = {}
        for s in stalls:
            by[s["packageCode"]] = by.get(s["packageCode"], 0) + 1
        assert by.get("premium") == 30, by
        assert by.get("ruby") == 69, by
        # Rate-card summary: Premium 30 + Ruby 69 == 99 (paid); Total 141


# ---------- Stall hold / release lifecycle ----------
class TestStallHoldLifecycle:
    def _first_available(self, package=None):
        stalls = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        for s in stalls:
            if s.get("status") == "available" and (package is None or s.get("packageCode") == package):
                return s["stallNumber"]
        return None

    def test_hold_then_release(self):
        stall = self._first_available("ruby")
        assert stall
        # Hold
        h = requests.post(f"{BASE}/api/public/stalls/{stall}/hold", json={})
        assert h.status_code in (200, 201), h.text
        token = (h.json().get("data") or {}).get("holdToken")
        assert token
        # Verify held
        stalls = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        item = next((x for x in stalls if x["stallNumber"] == stall), None)
        assert item and item["status"] in ("held", "reserved"), item

        # Release
        r = requests.post(f"{BASE}/api/public/stalls/release-hold",
                          json={"holdToken": token})
        assert r.status_code in (200, 204), r.text
        stalls = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        item = next((x for x in stalls if x["stallNumber"] == stall), None)
        assert item and item["status"] == "available", item


# ---------- Full admin approve / reject / reopen flow ----------
def _register_exhibitor(stall_number, its=None,
                        email=None, pkg="ruby", hold_token=""):
    import random
    its = its or str(random.randint(10000000, 99999999))
    email = email or f"TEST_exh_{int(time.time()*1000)}@example.com"
    buf = io.BytesIO()
    Image.new("RGB", (60, 60), (10, 100, 200)).save(buf, "PNG")
    form = {
        "itsNumber": its,
        "companyName": "TEST_Iter7 Co",
        "contactPerson": "Ivan Test",
        "email": email,
        "phone": "9998880011",
        "businessAddress": "1 Test Ave, Pune",
        "category": "products",
        "stallPackage": pkg,
        "stallNumber": stall_number,
        "holdToken": hold_token,
        "fasciaName": "TEST Iter7",
        "agreedToTerms": "true",
    }
    r = requests.post(f"{BASE}/api/exhibitors/register",
                      data=form,
                      files={"logo": ("l.png", buf.getvalue(), "image/png")})
    return r, email


class TestAdminApproveRejectReopen:
    def test_approve_and_reject_and_reopen(self, admin):
        # 1) Reserve a stall (hold) then register.
        stalls = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        stall = next(s["stallNumber"] for s in stalls
                     if s["status"] == "available" and s["packageCode"] == "ruby")
        h = requests.post(f"{BASE}/api/public/stalls/{stall}/hold", json={})
        assert h.status_code in (200, 201), h.text
        hold_token = (h.json().get("data") or {}).get("holdToken")
        assert hold_token

        r, email = _register_exhibitor(stall, pkg="ruby", hold_token=hold_token)
        assert r.status_code in (200, 201), r.text
        rcode = (r.json().get("data") or {}).get("registrationCode")
        assert rcode and rcode.startswith("RE-STL-"), rcode

        # 2) Find exhibitor id
        lst = admin.get(f"{BASE}/api/admin/exhibitors").json()
        items = lst.get("data") or lst.get("exhibitors") or []
        item = next((x for x in items if x.get("registrationCode") == rcode), None)
        assert item, f"no exhibitor with {rcode}"
        exid = item.get("_id") or item.get("id")

        # 3) Reject first (test path: reject → reopen → then approve)
        rej = admin.post(f"{BASE}/api/admin/exhibitors/{exid}/reject", json={})
        assert rej.status_code in (200, 204), rej.text
        after = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        assert next(s for s in after if s["stallNumber"] == stall)["status"] == "available"

        # 4) Reopen a rejected registration → back to pending; stall re-held
        reop = admin.post(f"{BASE}/api/admin/exhibitors/{exid}/reopen", json={})
        assert reop.status_code in (200, 204), reop.text
        after = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        st = next(s for s in after if s["stallNumber"] == stall)["status"]
        assert st in ("reserved", "held", "booked"), st

        # 5) Approve → stall booked
        appr = admin.post(f"{BASE}/api/admin/exhibitors/{exid}/approve", json={})
        assert appr.status_code in (200, 204), appr.text
        after = requests.get(f"{BASE}/api/public/stall-directory").json()["data"]
        assert next(s for s in after if s["stallNumber"] == stall)["status"] == "booked"

        # Cleanup
        admin.delete(f"{BASE}/api/admin/exhibitors/{exid}")


# ---------- Regression: visitor + enquiry + home APIs ----------
class TestRegression:
    def test_visitor(self, admin):
        v = requests.post(f"{BASE}/api/visitors/register", json={
            "fullName": "TEST_Iter7 V", "email": f"TEST_iter7v_{int(time.time())}@example.com",
            "phone": "9998880021", "organization": "T", "city": "Pune",
            "interests": ["general"],
        })
        assert v.status_code in (200, 201), v.text
        vd = v.json().get("data", v.json())
        assert not vd.get("emailError")
        vid = vd.get("_id") or vd.get("id")
        if vid:
            admin.delete(f"{BASE}/api/admin/visitors/{vid}")

    def test_enquiry(self, admin):
        e = requests.post(f"{BASE}/api/enquiries", json={
            "name": "TEST_Iter7 E",
            "email": f"TEST_iter7e_{int(time.time())}@example.com",
            "mobile": "9998880022",
            "details": "Iter7 automation test enquiry.",
        })
        assert e.status_code in (200, 201), e.text
        # Cleanup by email
        lst = admin.get(f"{BASE}/api/admin/enquiries").json()
        items = lst.get("data") or lst.get("enquiries") or []
        this = next((x for x in items if x.get("email", "").startswith("test_iter7e_")), None)
        if this:
            eid = this.get("_id") or this.get("id")
            admin.delete(f"{BASE}/api/admin/enquiries/{eid}")
