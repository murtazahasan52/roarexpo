"""
Guided flows that write to the same collections as the website forms:

  * stall booking   — the full exhibitor registration in the chat (every
                      mandatory field of /register/exhibitor), submitted through
                      routers.exhibitors.register_exhibitor itself, so the
                      e-mail with payment details, the organiser alert, the
                      WhatsApp "exhibitor_registration" template and the admin
                      Exhibitors list behave exactly as for the website form.
  * enquiry         — the /enquiry form in the chat (routers.enquiries).
  * payment details — for an exhibitor found by mobile number.

Each step function returns (blocks, quickReplies, finished).
"""
from __future__ import annotations

import json
import re

from config.bot_config import BOT
from config.event_config import EVENT, find_stall_package
from utils.validators import is_valid_email


def text(t):
    return {"type": "text", "text": t}


def card(title, rows, tone="info"):
    return {"type": "card", "title": title, "rows": [[k, v] for k, v in rows if v not in (None, "")], "tone": tone}


def links(*items):
    return {"type": "links", "items": list(items)}


def qr(*pairs):
    return [{"label": p, "send": p} if isinstance(p, str) else {"label": p[0], "send": p[1]} for p in pairs]


def rupees(n):
    if n is None:
        return "On request"
    s = str(int(n))
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:]); head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts) + "," + tail


def _mobile(s):
    d = re.sub(r"\D", "", s or "")
    if len(d) >= 12 and d.startswith("91"):
        d = d[-10:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    return d if len(d) == 10 and d[0] in "6789" else None


def _natkey(code):
    m = re.match(r"([A-Z]+)(\d+)([A-Z]?)", code or "")
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (code, 0, "")


CANCEL = ("Cancel", "cancel")

# ===================================================================== payment details (verified exhibitor)

def payment_blocks(exhibitor: dict) -> tuple[list[dict], list[dict]]:
    from utils.email_templates import _PAYMENT
    rate = exhibitor.get("stallRate")
    n = exhibitor.get("numberOfStalls") or 1
    total = exhibitor.get("totalAmount")
    try:
        total = int(total) if total is not None else (int(rate) * int(n) if rate is not None else None)
    except (TypeError, ValueError):
        total = None
    paid = str(exhibitor.get("paymentStatus") or "").lower() == "paid"
    rows = [("Registration ID", exhibitor.get("registrationCode")),
            ("Stall", ", ".join(exhibitor.get("stallNumbers") or []) or exhibitor.get("stallNumber")),
            ("Amount payable", rupees(total) if total is not None else "As confirmed by the team"),
            ("Payment status", "Received ✅" if paid else "Pending"),
            ("Account name", _PAYMENT["accountName"]), ("Bank", _PAYMENT["bankName"]), ("Branch", _PAYMENT["branch"]),
            ("Account number", _PAYMENT["accountNumber"]), ("IFSC", _PAYMENT["ifsc"])]
    stalls_c = BOT["contacts"]["stalls"]
    blocks = [card("Stall payment", rows, "ok" if paid else "warn")]
    if paid:
        blocks.append(text("Your payment is already marked as received — thank you!"))
    else:
        blocks.append(text(f"Transfer the amount by NEFT / RTGS / IMPS and share the transaction reference or a screenshot with "
                           f"{stalls_c['name']} on WhatsApp {stalls_c['phone']}, so the team can mark it paid. The same details are in "
                           f"your registration e-mail."))
        blocks.append(links({"label": "Send payment proof on WhatsApp",
                             "href": "https://wa.me/" + re.sub(r"\D", "", stalls_c["phone"]) + "?text=" +
                             re.sub(r"\s", "%20", f"Payment proof for ROAR Expo registration {exhibitor.get('registrationCode')}")}))
    return blocks, qr(("E-mail my invoice", "email my invoice"), ("Resend my confirmation", "resend my confirmation"), ("Main menu", "menu"))


# ===================================================================== enquiry form in the chat

ENQ_PROMPTS = {
    "name": "Your name, please?",
    "mobile": "Your 10-digit mobile number?",
    "email": "Your e-mail address? (the team replies there)",
    "details": "What would you like to ask the organising team? Type your message.",
}


async def enquiry_flow(db, session, message: str):
    from routers.enquiries import submit_enquiry
    from models.enquiry import EnquiryRequest
    data = session.setdefault("data", {})
    step = session.get("step") or "name"
    m = (message or "").strip()
    if step == "name":
        if len(m) < 3 or not re.search(r"[A-Za-zऀ-ॿ]", m):
            return [text("Your name, please?")], qr(CANCEL), False
        data["name"] = m.title() if m.islower() or m.isupper() else m
        session["step"] = "mobile"
        return [text(ENQ_PROMPTS["mobile"])], qr(CANCEL), False
    if step == "mobile":
        mob = _mobile(m)
        if not mob:
            return [text("Please type a 10-digit Indian mobile number.")], qr(CANCEL), False
        data["mobile"] = "+91 " + mob[:5] + " " + mob[5:]
        session["step"] = "email"
        return [text(ENQ_PROMPTS["email"])], qr(CANCEL), False
    if step == "email":
        em = re.sub(r"\s+", "", m).lower()
        if not is_valid_email(em):
            return [text("Please type a valid e-mail address, e.g. name@example.com.")], qr(CANCEL), False
        data["email"] = em
        session["step"] = "details"
        prefill = data.get("topic")
        return [text(ENQ_PROMPTS["details"] + (f" (I'll note that it's about: {prefill})" if prefill else ""))], qr(CANCEL), False
    if step == "details":
        if len(m) < 5:
            return [text("A few more words, please — what is your question?")], qr(CANCEL), False
        details = m if not data.get("topic") else f"[{data['topic']}] {m}"
        try:
            payload = EnquiryRequest(name=data["name"], email=data["email"], mobile=data["mobile"], details=details + "\n\n— sent from Ask ROAR Anything (website chat)")
            await submit_enquiry(payload, db)
        except Exception as err:  # noqa: BLE001
            return [text(f"Sorry — the enquiry could not be sent ({getattr(err, 'detail', None) or err}). Please try again, or use the Enquiry page.")], \
                   qr(("Try again", "send an enquiry"), ("Enquiry page", "open enquiry page")), False
        session["flow"], session["step"], session["data"] = None, None, {}
        session["_tag"] = "enquiry"
        return ([text(f"Thanks, {data['name'].split()[0]} — your enquiry has reached the organising team. They'll reply to {data['email']} "
                      f"or call {data['mobile']}. A copy has been e-mailed to you."),
                 card("Enquiry sent", [("Name", data["name"]), ("Mobile", data["mobile"]), ("E-mail", data["email"]), ("Message", m[:200])], "ok")],
                qr(("Main menu", "menu"), ("Rate this chat", "rate this chat")), True)
    return None


# ===================================================================== stall booking in the chat

BOOK_STEPS = ["package", "stall", "contactPerson", "itsNumber", "phone", "email", "companyName", "businessAddress",
              "category", "fasciaName", "confirm"]
BOOK_PROMPTS = {
    "contactPerson": "Your full name (the person we should contact)?",
    "itsNumber": "Your ITS number (8 digits)?",
    "phone": "Your 10-digit mobile number?",
    "email": "Your e-mail address? (registration ID and payment details go there)",
    "companyName": "Your business / company name?",
    "businessAddress": "Your business address (with city and pincode)?",
    "category": "Which industry is your business in?",
    "fasciaName": "Name to print on your stall's fascia board?",
}
FIELD_LABELS = {"contactPerson": "Name", "itsNumber": "ITS number", "phone": "Mobile", "email": "E-mail", "companyName": "Company",
                "businessAddress": "Address", "category": "Industry", "fasciaName": "Fascia name", "stall": "Stall", "package": "Category"}
EDIT_MAP = {"name": "contactPerson", "its": "itsNumber", "mobile": "phone", "phone": "phone", "email": "email", "e-mail": "email",
            "company": "companyName", "address": "businessAddress", "industry": "category", "fascia": "fasciaName",
            "stall": "stall", "category": "package"}


def bookable_packages():
    return [p for p in EVENT["stallPackages"] if p.get("hasStallPicker") and not p.get("adminOnly")]


async def _free_in(db, code: str) -> list[dict]:
    from utils.stall_holds import release_expired_holds
    await release_expired_holds(db)
    rows = await db.stalls.find({"packageCode": code, "status": "available"},
                                {"stallNumber": 1, "mapX": 1, "mapY": 1, "adminOnly": 1, "rate": 1, "size": 1}).to_list(length=None)
    rows = [r for r in rows if not r.get("adminOnly")]
    rows.sort(key=lambda r: _natkey(r["stallNumber"]))
    return rows


def _pkg_from_text(low: str):
    low = low.strip().lower()
    for p in bookable_packages():
        if low in (p["code"], p["label"].lower(), p["label"].lower().replace(" stall", ""), "book " + p["code"]):
            return p
    # partial: "gold", "premium 15"
    hits = [p for p in bookable_packages() if re.search(r"\b" + re.escape(p["label"].lower().replace(" stall", "")) + r"\b", low)]
    if len(hits) == 1:
        return hits[0]
    if hits:  # most specific label wins ("premium ruby stall (standard)" over "premium")
        return sorted(hits, key=lambda p: -len(p["label"]))[0]
    return None


async def _package_prompt(db):
    rows, chips = [], []
    for p in bookable_packages():
        free = await _free_in(db, p["code"])
        if not free:
            continue
        rows.append({"code": p["code"], "label": p["label"], "rate": rupees(p.get("rate")), "count": p.get("size") or "",
                     "available": len(free), "note": p.get("inclusions", "")})
        chips.append((f"{p['label'].replace(' Stall', '')} · {rupees(p.get('rate'))}", f"category {p['code']}"))
    blocks = [text("Let's book your stall right here. First, pick a stall category (rate is per stall for all three days):"),
              {"type": "rates", "rows": rows}]
    return blocks, qr(*chips, ("Help me choose by budget", "which stall under 1 lakh"), CANCEL)


async def _stall_prompt(db, data):
    from utils.bot_engine import map_url
    p = find_stall_package(data["package"]) or {}
    free = await _free_in(db, data["package"])
    if not free:
        data.pop("package", None)
        b, q = await _package_prompt(db)
        return [text(f"Sorry — no {p.get('label', 'such')} stalls are free right now. Please pick another category.")] + b[1:], q
    pins = [{"n": r["stallNumber"], "x": round(float(r["mapX"]), 2), "y": round(float(r["mapY"]), 2), "c": data["package"]}
            for r in free if r.get("mapX") is not None]
    blocks = [text(f"{p.get('label')} — {rupees(p.get('rate'))}, {p.get('size', '')}. {len(free)} free. Tap a stall number below (or type it); "
                   "the green dots on the map are the free ones."),
              {"type": "map", "mapUrl": await map_url(db), "stalls": pins, "counts": [], "label": f"{len(free)} {p.get('label', '').replace(' Stall', '')} free"}]
    chips = [(r["stallNumber"], f"stall {r['stallNumber']}") for r in free[:12]]
    if len(free) > 12:
        blocks.append(text("All free numbers: " + ", ".join(r["stallNumber"] for r in free) + "."))
    return blocks, qr(*chips, ("Change category", "change category"), CANCEL)


def _summary_card(data):
    p = find_stall_package(data.get("package") or "") or {}
    labels = {c["key"]: c["label"] for c in EVENT["categories"]}
    return card("Stall booking — please check", [
        ("Stall", f"{data.get('stall')} · {p.get('label', '')}"), ("Rate", rupees(p.get("rate"))),
        ("Name", data.get("contactPerson")), ("ITS number", data.get("itsNumber")), ("Mobile", data.get("phone")),
        ("E-mail", data.get("email")), ("Company", data.get("companyName")), ("Address", data.get("businessAddress")),
        ("Industry", labels.get(data.get("category"), data.get("category"))), ("Fascia name", data.get("fasciaName")),
    ], "info")


CONFIRM_QR = [{"label": "I agree & submit", "send": "i agree and submit", "primary": True}] + qr(("Change name", "change name"), ("Change ITS", "change its"),
                ("Change mobile", "change mobile"), ("Change e-mail", "change email"), ("Change company", "change company"),
                ("Change address", "change address"), ("Change industry", "change industry"), ("Change fascia", "change fascia"),
                ("Change stall", "change stall"), CANCEL)


def _confirm(data):
    return [_summary_card(data),
            text("By submitting you agree to the exhibitor terms & conditions and confirm the details above are accurate. "
                 f"Your stall stays reserved until the organising team approves it.")], CONFIRM_QR


def _category_quick():
    return qr(*[(c["label"], f"industry {c['key']}") for c in EVENT["categories"]], CANCEL)


async def _hold(db, data, code):
    from utils.stall_holds import hold_stall, HOLD_MINUTES
    stall, token, expires = await hold_stall(db, code, data.get("holdToken"))
    if not stall:
        return None
    data["holdToken"] = token
    data["stall"] = code
    data["holdUntil"] = expires.isoformat()
    return HOLD_MINUTES


async def release(db, session):
    from utils.stall_holds import release_hold
    token = (session.get("data") or {}).get("holdToken")
    if token:
        await release_hold(db, token)


async def start_booking(db, session, low: str = ""):
    """Entry point. Keeps a stall already reserved in this chat (Reserve G3 → Book in chat)."""
    prev = session.get("data") or {}
    data = {}
    if prev.get("holdToken") and prev.get("holdStall"):
        s = await db.stalls.find_one({"stallNumber": prev["holdStall"]})
        if s and s.get("status") == "held" and s.get("tempHoldToken") == prev["holdToken"]:
            data = {"package": s["packageCode"], "stall": s["stallNumber"], "holdToken": prev["holdToken"]}
    session["flow"], session["data"] = "book", data
    if not data:
        p = _pkg_from_text(low) if low else None
        if p:
            data["package"] = p["code"]
    if data.get("stall"):
        session["step"] = "contactPerson"
        p = find_stall_package(data["package"]) or {}
        return [text(f"Great — let's complete the booking for {data['stall']} ({p.get('label')}, {rupees(p.get('rate'))}). "
                     "It stays reserved for you while we go. " + BOOK_PROMPTS["contactPerson"])], qr(CANCEL), False
    if data.get("package"):
        if data["package"] == "ruby":
            session["step"] = "ruby_ok"
            return _ruby_prompt(), qr(("Yes, I confirm", "yes i confirm"), ("No", "no"), CANCEL), False
        session["step"] = "stall"
        b, q = await _stall_prompt(db, data)
        return b, q, False
    session["step"] = "package"
    b, q = await _package_prompt(db)
    return b, q, False


def _ruby_prompt():
    ruby = find_stall_package("ruby") or {}
    return [text((ruby.get("eligibility") or BOT["ruby"]) + " Please confirm you are a woman entrepreneur of the Dawoodi Bohra community.")]


async def booking_flow(db, session, message: str):
    data = session.setdefault("data", {})
    step = session.get("step") or "package"
    m = (message or "").strip()
    low = m.lower()

    # ---- category
    if step == "package":
        p = _pkg_from_text(re.sub(r"^category\s+", "", low))
        if not p:
            b, q = await _package_prompt(db)
            return [text("Please pick one of the categories below.")] + b[1:], q, False
        data["package"] = p["code"]
        if p["code"] == "ruby":
            session["step"] = "ruby_ok"
            return _ruby_prompt(), qr(("Yes, I confirm", "yes i confirm"), ("No", "no"), CANCEL), False
        session["step"] = "stall"
        b, q = await _stall_prompt(db, data)
        return b, q, False

    if step == "ruby_ok":
        if re.match(r"^(yes|haan|ha|ji|confirm)", low):
            session["step"] = "stall"
            b, q = await _stall_prompt(db, data)
            return b, q, False
        data.pop("package", None)
        session["step"] = "package"
        b, q = await _package_prompt(db)
        return [text("No problem — Ruby stalls are reserved for women entrepreneurs. Please choose another category.")] + b[1:], q, False

    # ---- stall number
    if step == "stall":
        if low in ("change category", "category"):
            data.pop("package", None)
            session["step"] = "package"
            b, q = await _package_prompt(db)
            return b, q, False
        from utils.bot_features import stall_codes_in
        codes = stall_codes_in(m.upper())
        code = codes[0] if codes else None
        if not code:
            b, q = await _stall_prompt(db, data)
            return [text("Please tap or type a stall number from the list.")] + b, q, False
        s = await db.stalls.find_one({"stallNumber": code})
        if not s:
            return [text(f"There is no stall {code}. Pick one from the list.")], (await _stall_prompt(db, data))[1], False
        if s.get("packageCode") != data.get("package"):
            p2 = find_stall_package(s.get("packageCode") or "") or {}
            return [text(f"{code} is a {p2.get('label', 'different')} stall ({rupees(s.get('rate'))}). Pick a stall from your chosen category, "
                         "or tap “Change category”.")], (await _stall_prompt(db, data))[1], False
        if s.get("adminOnly"):
            return [text(f"{code} is allotted by the organising team and can't be booked online. Please pick another.")], (await _stall_prompt(db, data))[1], False
        minutes = await _hold(db, data, code)
        if not minutes:
            b, q = await _stall_prompt(db, data)
            return [text(f"Sorry — {code} was just taken. Please pick another free stall.")] + b, q, False
        nxt = "confirm" if session.pop("editing", False) and all(data.get(k) for k in BOOK_STEPS[2:-1]) else "contactPerson"
        session["step"] = nxt
        if nxt == "confirm":
            b, q = _confirm(data)
            return [text(f"Switched to {code}.")] + b, q, False
        return [text(f"✅ {code} is reserved for you for {minutes} minutes while we finish. " + BOOK_PROMPTS["contactPerson"])], qr(CANCEL), False

    # ---- confirm / edit
    if step == "confirm":
        if re.match(r"^(i agree|agree|yes|submit|confirm|haan|ha|ji)", low):
            return await _submit(db, session)
        e = re.match(r"^(change|edit)\s+(name|its|mobile|phone|e-?mail|company|address|industry|fascia|stall|category)", low)
        if e:
            field = EDIT_MAP[e.group(2).replace("e-mail", "email")]
            session["editing"] = True
            if field == "stall":
                session["step"] = "stall"
                b, q = await _stall_prompt(db, data)
                return b, q, False
            if field == "package":
                session["step"] = "package"
                b, q = await _package_prompt(db)
                return b, q, False
            session["step"] = field
            quick = _category_quick() if field == "category" else (qr(("Same as company name", "same as company name"), CANCEL) if field == "fasciaName" else qr(CANCEL))
            return [text(BOOK_PROMPTS[field])], quick, False
        b, q = _confirm(data)
        return b, q, False

    # ---- text fields
    if step == "contactPerson":
        if len(m) < 3 or not re.search(r"[A-Za-zऀ-ॿ]", m) or re.search(r"\d{4,}", m):
            return [text("Please type the full name (letters only).")], qr(CANCEL), False
        data["contactPerson"] = re.sub(r"\s+", " ", m).title() if (m.islower() or m.isupper()) else re.sub(r"\s+", " ", m)
    elif step == "itsNumber":
        d = re.sub(r"\D", "", m)
        if len(d) != 8:
            return [text("The ITS number must be exactly 8 digits — please type it again.")], qr(CANCEL), False
        data["itsNumber"] = d
    elif step == "phone":
        mob = _mobile(m)
        if not mob:
            return [text("That doesn't look like an Indian mobile number. Please type the 10 digits.")], qr(CANCEL), False
        data["phone"] = "+91 " + mob[:5] + " " + mob[5:]
        if not session.get("editing"):
            from utils.bot_engine import _phone_regex
            ex = await db.exhibitors.find_one({"$or": [{"phone": _phone_regex(mob)}, {"whatsapp": _phone_regex(mob)}],
                                               "status": {"$ne": "cancelled"}}, {"companyName": 1, "registrationCode": 1, "stallNumber": 1})
            if ex:
                session["step"] = "email"
                return [text(f"Note: this number already has a booking — {ex.get('companyName')} ({ex.get('registrationCode')}, stall "
                             f"{ex.get('stallNumber') or '—'}). I'll continue with this new stall booking."),
                        text(BOOK_PROMPTS["email"])], qr(CANCEL), False
    elif step == "email":
        em = re.sub(r"\s+", "", m).lower()
        if not is_valid_email(em):
            return [text("Please type a valid e-mail address, e.g. name@example.com.")], qr(CANCEL), False
        data["email"] = em
    elif step == "companyName":
        if len(m) < 2:
            return [text("Your business / company name?")], qr(CANCEL), False
        data["companyName"] = m
    elif step == "businessAddress":
        if len(m) < 10:
            return [text("Please type the full business address — street, area, city and pincode.")], qr(CANCEL), False
        data["businessAddress"] = m
    elif step == "category":
        key = re.sub(r"^industry\s+", "", low)
        cat = next((c for c in EVENT["categories"] if key in (c["key"], c["label"].lower())), None)
        if not cat:
            from utils.bot_features import industry_in
            cat = industry_in(low)
        if not cat:
            return [text("Please pick your industry from the list.")], _category_quick(), False
        data["category"] = cat["key"]
    elif step == "fasciaName":
        if low in ("same as company name", "same", "same as company"):
            data["fasciaName"] = data.get("companyName", "")
        elif len(m) < 2:
            return [text(BOOK_PROMPTS["fasciaName"])], qr(("Same as company name", "same as company name"), CANCEL), False
        else:
            data["fasciaName"] = m[:60]
    else:
        return None

    if session.pop("editing", False):
        session["step"] = "confirm"
        b, q = _confirm(data)
        return [text(f"{FIELD_LABELS.get(step, step)} updated.")] + b, q, False

    nxt = BOOK_STEPS[BOOK_STEPS.index(step) + 1]
    session["step"] = nxt
    if nxt == "confirm":
        b, q = _confirm(data)
        return b, q, False
    quick = _category_quick() if nxt == "category" else (qr(("Same as company name", "same as company name"), CANCEL) if nxt == "fasciaName" else qr(CANCEL))
    return [text(BOOK_PROMPTS[nxt])], quick, False


async def _submit(db, session):
    from routers.exhibitors import register_exhibitor
    from utils.bot_engine import _phone_regex  # noqa: F401  (kept for parity)
    data = session["data"]
    # refresh the hold so a slow chat never loses the stall at the last second
    minutes = await _hold(db, data, data["stall"])
    if not minutes:
        session["step"] = "stall"
        b, q = await _stall_prompt(db, data)
        return [text(f"Sorry — {data['stall']} was taken while we were chatting. Please pick another stall; your details are kept.")] + b, q, False
    try:
        res = await register_exhibitor(
            itsNumber=data["itsNumber"], contactPerson=data["contactPerson"], designation="", email=data["email"],
            phone=data["phone"], landline="", whatsapp="", companyName=data["companyName"],
            businessAddress=data["businessAddress"], businessEmail="", city="", state="", pincode="", website="",
            gstNumber="", linkedin="", instagram="", facebook="", category=data["category"],
            productsServices="", message="Booked through Ask ROAR Anything (website chat)", stallPackage=data["package"],
            numberOfStalls=1, stallNumber=data["stall"], holdToken=data["holdToken"], fasciaName=data["fasciaName"],
            agreedToTerms="true", logo=None, productImages=[], db=db,
        )
    except Exception as err:  # noqa: BLE001 — HTTPException carries the exact reason
        detail = getattr(err, "detail", None) or str(err)
        return [text(f"Sorry — the booking could not be saved: {detail}")], qr(("Try again", "i agree and submit"), ("Change stall", "change stall"), CANCEL), False
    if hasattr(res, "body"):  # JSONResponse → validation problem
        try:
            body = json.loads(res.body)
        except Exception:  # noqa: BLE001
            body = {"message": "Validation failed"}
        errs = body.get("errors") or []
        msgs = [e.get("msg") for e in errs if isinstance(e, dict)] if isinstance(errs, list) else list(errs.values()) if isinstance(errs, dict) else []
        return [text("Sorry — " + (body.get("message") or "the booking could not be saved") + (": " + "; ".join(msgs) if msgs else "") + ".")], CONFIRM_QR, False

    code = (res.get("data") or {}).get("registrationCode", "")
    p = find_stall_package(data["package"]) or {}
    ex = await db.exhibitors.find_one({"registrationCode": code}) if code else None
    session["flow"], session["step"] = "visitor_manage", None
    session["data"] = {"exhibitors": [{"id": str(ex["_id"]), "name": ex.get("companyName", ""), "code": code}] if ex else [],
                       "exhibitorId": str(ex["_id"]) if ex else None, "visitors": [], "visitorId": None}
    session["_tag"] = "stall-booked"
    blocks = [text(f"Done — {data['stall']} is booked for {data['companyName']}! 🎉 It's reserved and pending approval by the organising team."),
              card("Your stall registration", [("Registration ID", code), ("Stall", f"{data['stall']} · {p.get('label', '')}"),
                                               ("Amount", rupees(p.get("rate"))), ("Status", "Pending approval"),
                                               ("Name", data["contactPerson"]), ("Company", data["companyName"])], "ok"),
              text(f"The registration e-mail with the payment details is on its way to {data['email']}, and a WhatsApp message to "
                   f"{data['phone']}. You'll get a confirmation once the team approves. Want to add your logo, GST number or product "
                   "photos? Send them to the team on WhatsApp, or reply to the e-mail.")]
    if ex:
        pb, _ = payment_blocks(ex)
        blocks.append(text("Payment details:"))
        blocks += pb
    return blocks, qr(("Track my registration", "track my registration"), ("Set-up & documents", "setup and documents"),
                      ("Rate this chat", "rate this chat"), ("Main menu", "menu")), True
