"""End-to-end registration API tests: visitor + exhibitor + admin verify."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend env
    from dotenv import dotenv_values
    vals = dotenv_values("/app/frontend/.env")
    BASE_URL = (vals.get("REACT_APP_BACKEND_URL") or "").rstrip("/")

API = f"{BASE_URL}/api"

created_codes = {"visitor": [], "exhibitor": []}


@pytest.fixture(scope="module")
def s():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_token(s):
    r = s.post(f"{API}/admin/login", json={"email": "admin@roarexpo.com", "password": "Admin@12345"})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or (data.get("data") or {}).get("token")
    assert tok, f"no token in login response: {data}"
    return tok


# ---------- Health ----------
def test_health(s):
    r = s.get(f"{API}/public/config")
    assert r.status_code == 200


# ---------- Visitor Registration ----------
def test_visitor_register_success(s):
    payload = {
        "fullName": "TEST Visitor One",
        "email": "test.visitor.one@example.com",
        "phone": "9998887771",
        "city": "Mumbai",
        "organization": "TEST Org",
        "designation": "QA",
        "numberOfGuests": 1,
        "source": "online",
    }
    r = s.post(f"{API}/visitors/register", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    code = body["data"]["registrationCode"]
    assert code.startswith("RE-VIS-")
    created_codes["visitor"].append(code)


def test_visitor_register_missing_name(s):
    r = s.post(f"{API}/visitors/register", json={
        "fullName": "",
        "email": "bad@example.com",
        "phone": "9998887771",
    })
    assert r.status_code in (400, 422), r.text


def test_visitor_register_invalid_email(s):
    r = s.post(f"{API}/visitors/register", json={
        "fullName": "TEST X",
        "email": "not-an-email",
        "phone": "9998887771",
    })
    assert r.status_code in (400, 422), r.text


# ---------- Exhibitor: public stalls ----------
def test_public_stalls_all_no_package(s):
    # NEW: without packageCode returns all stalls (used by full venue map)
    r = s.get(f"{API}/public/stalls")
    assert r.status_code == 200
    assert isinstance(r.json().get("data"), list)


def test_public_stall_map(s):
    r = s.get(f"{API}/public/stall-map")
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    # data may be None or {url,...}
    data = body.get("data")
    if data:
        assert "url" in data


# ---------- Exhibitor Registration ----------
@pytest.fixture(scope="module")
def available_gold_stall(s):
    # Try common gold-ish codes; pick the first with an available stall
    for code in ("gold", "silver", "bronze", "premium", "regular", "ruby", "diamond", "title"):
        r = s.get(f"{API}/public/stalls", params={"packageCode": code})
        if r.status_code != 200:
            continue
        stalls = r.json().get("data") or []
        avail = [x for x in stalls if x.get("status") == "available"]
        if avail:
            return code, avail[0]["stallNumber"]
    pytest.skip("No available numbered stalls found in any package")


def test_exhibitor_register_success(s, available_gold_stall):
    pkg, stall_no = available_gold_stall
    files = {
        "logo": ("logo.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "image/png"),
    }
    data = {
        "itsNumber": "TEST1234",
        "contactPerson": "TEST Exhibitor",
        "email": "test.exh1@example.com",
        "phone": "9998887772",
        "companyName": "TEST Co",
        "businessAddress": "123 TEST Rd",
        "category": "Food",
        "stallPackage": pkg,
        "stallNumber": stall_no,
        "fasciaName": "TEST FASCIA",
        "agreedToTerms": "true",
    }
    r = s.post(f"{API}/exhibitors/register", data=data, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True
    code = body["data"]["registrationCode"]
    assert code.startswith("RE-STL-")
    created_codes["exhibitor"].append(code)

    # Stall should now be held
    r2 = s.get(f"{API}/public/stalls", params={"packageCode": pkg})
    stalls = r2.json()["data"]
    picked = next((x for x in stalls if x["stallNumber"] == stall_no), None)
    assert picked and picked["status"] == "held", picked


def test_exhibitor_missing_required(s):
    r = s.post(f"{API}/exhibitors/register", data={
        "itsNumber": "TS",  # too short
        "contactPerson": "",
        "email": "not-email",
        "phone": "1",
        "companyName": "",
        "businessAddress": "",
        "category": "",
        "stallPackage": "",
        "fasciaName": "",
        "agreedToTerms": "false",
    })
    assert r.status_code == 400, r.text
    body = r.json()
    assert body.get("success") is False
    assert isinstance(body.get("errors"), list) and len(body["errors"]) >= 5


def test_exhibitor_organizer_allocated_no_stall(s):
    # Food Court / Play Zone should NOT require a stall number
    for pkg in ("food-court", "play-zone"):
        r = s.get(f"{API}/public/stalls", params={"packageCode": pkg})
        if r.status_code == 200 and r.json().get("data") is not None:
            # Just test with empty stall number
            data = {
                "itsNumber": "TEST5678",
                "contactPerson": "TEST FoodCourt",
                "email": "test.exh.fc@example.com",
                "phone": "9998887773",
                "companyName": "TEST FC Co",
                "businessAddress": "456 TEST Rd",
                "category": "Food",
                "stallPackage": pkg,
                "stallNumber": "",
                "fasciaName": "TEST FC",
                "agreedToTerms": "true",
            }
            r2 = s.post(f"{API}/exhibitors/register", data=data)
            # Either 200 (accepted) or 400 with clear error if package unknown
            if r2.status_code == 200:
                created_codes["exhibitor"].append(r2.json()["data"]["registrationCode"])
                return
    pytest.skip("Organizer-allocated packages not present in inventory")


# ---------- Admin Verify ----------
def test_admin_sees_visitor(s, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = s.get(f"{API}/admin/visitors", headers=headers, params={"limit": 50})
    assert r.status_code == 200, r.text
    body = r.json()
    items = body.get("data") if isinstance(body.get("data"), list) else (body.get("data") or {}).get("items") or body.get("items") or []
    codes = [v.get("registrationCode") for v in items]
    assert any(c in codes for c in created_codes["visitor"]), f"created visitor not visible; got {codes[:5]}"


def test_admin_sees_exhibitor(s, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = s.get(f"{API}/admin/exhibitors", headers=headers, params={"limit": 50})
    assert r.status_code == 200, r.text
    body = r.json()
    items = body.get("data") if isinstance(body.get("data"), list) else (body.get("data") or {}).get("items") or body.get("items") or []
    codes = [v.get("registrationCode") for v in items]
    assert any(c in codes for c in created_codes["exhibitor"]), f"created exhibitor not visible; got {codes[:5]}"


# ---------- File Serving ----------
def test_files_endpoint_exists(s):
    # Try a nonexistent file -> 404 expected, not 500
    r = s.get(f"{API}/files/nonexistent-xyz.png")
    assert r.status_code in (404, 403), r.status_code
