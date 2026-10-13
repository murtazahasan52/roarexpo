"""
"Ask ROAR Anything" — the conversation engine behind POST /api/bot/chat.

Design: a small, deterministic assistant. Every visitor message is matched to
an intent (keywords + a few regexes); guided flows (visitor registration,
status tracking) keep their step in a per-session document in MongoDB
(`bot_sessions`, auto-expiring). Replies are a list of typed "blocks" the
React widget knows how to draw:

    {"type": "text",  "text": "..."}
    {"type": "card",  "title": "...", "rows": [[label, value], ...], "tone": "ok|warn|info|muted"}
    {"type": "links", "items": [{"label": "...", "to": "/register/visitor"} | {"label": "...", "href": "https://..."}]}
    {"type": "rates", "rows": [{"label", "rate", "count", "available", "note"}]}
    {"type": "map",   "mapUrl": "...", "stalls": [{"n","x","y","c"}], "counts": [{"code","label","available","total"}]}

plus `quickReplies` ([{label, send}]) — chips the widget shows under the
reply; tapping one sends its `send` text back through this same engine.

Only the facts in config/event_config.py + config/bot_config.py and the
public stall/registration data are used. Free-text questions that match no
intent go to utils/bot_llm.ai_answer when an API key is configured.
"""
from __future__ import annotations

import re
from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.bot_config import BOT, llm_settings
from config.event_config import EVENT, find_stall_package
from models.common import utcnow
from models.visitor import VisitorRegisterRequest
from utils.bot_llm import ai_answer
from utils import bot_features as F
from utils import bot_flows as FL
from utils import bot_kb as KB
from utils.validators import is_valid_email

SESSION_TTL = timedelta(hours=6)
HISTORY_KEEP = 12

# ------------------------------------------------------------------ helpers

def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _mobile(s: str) -> str | None:
    """Indian 10-digit mobile anywhere in the text (with or without +91)."""
    d = _digits(s)
    if len(d) >= 12 and d.startswith("91"):
        d = d[-10:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if len(d) == 10 and d[0] in "6789":
        return d
    return None


def _phone_regex(mobile: str) -> dict:
    """Matches a stored phone string ending in these 10 digits whatever the
    separators ("+91 99228 02852", "9922802852", "099228-02852")."""
    return {"$regex": r"\D*".join(mobile) + r"\D*$"}


def _mask_email(e: str) -> str:
    if not e or "@" not in e:
        return e or "—"
    user, dom = e.split("@", 1)
    keep = user[:2] if len(user) > 2 else user[:1]
    return f"{keep}{'•' * max(2, len(user) - len(keep))}@{dom}"


def _rupees(rate) -> str:
    if rate is None:
        return "On request"
    rate = int(rate)
    # Indian grouping: 21,00,000
    s = str(rate)
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts) + "," + tail


def _when(dt) -> str:
    try:
        return dt.strftime("%d %b %Y")
    except Exception:  # noqa: BLE001
        return "—"


def text(t: str) -> dict:
    return {"type": "text", "text": t}


def card(title: str, rows: list, tone: str = "info") -> dict:
    return {"type": "card", "title": title, "rows": [[k, v] for k, v in rows if v not in (None, "")], "tone": tone}


def links(*items) -> dict:
    return {"type": "links", "items": list(items)}


def qr(*pairs) -> list[dict]:
    """quick replies: qr(("Label", "text to send"), "Same as label", ...)"""
    out = []
    for p in pairs:
        if isinstance(p, str):
            out.append({"label": p, "send": p})
        else:
            out.append({"label": p[0], "send": p[1]})
    return out


MENU = qr(
    ("Register as visitor", "register as visitor"),
    ("Book a stall", "book a stall in chat"),
    ("Track my registration", "track my registration"),
    ("Empty stalls map", "empty stalls"),
    ("Stall rates", "stall rates"),
    ("Dates & venue", "dates and venue"),
    ("Contact", "contact"),
)

# ------------------------------------------------------------------ intents

INTENTS: list[tuple[str, list[str]]] = [
    # order matters — first match wins
    ("cancel", [r"^\s*(cancel|stop|exit|quit|start over|restart|main menu|menu|home)\s*[.!]?\s*$"]),
    ("greeting", [r"^\s*(hi|hii+|hello|hey|salaam|salam|assalam|namaste|namaskar|good (morning|afternoon|evening)|start)\b[\s!.]*$"]),
    ("thanks", [r"\b(thank|thanks|thank you|shukriya|dhanyavad|great|ok(ay)?|nice|perfect)\b[\s!.]*$"]),
    ("book_chat", [r"\b(book|reserve|register|booking|take)\b.*\bstall\b.*\b(in|on|via|through|here in|in this)\s*(the\s+)?(chat|bot)\b",
                   r"^\s*(book a stall in chat|book in chat|book a stall here|book stall here|continue booking in chat|book it here in chat|book a stall|book stall|i want to book a stall|book my stall)\b"]),
    ("enquiry", [r"\b(send (an |a )?(enquiry|inquiry|message|query)|make an enquiry|enquiry form|i have a (question|query) for the team|write to (the )?team|ask the (team|organi[sz]ers))\b"]),
    ("payment", [r"^\s*(payment details|show payment details|bank details)\s*$"]),
    ("reserve", [r"^\s*(reserve|hold|block)\s+(stall\s+)?([a-z]{1,3}\s?-?\s?\d{1,3})\b"]),
    ("release", [r"^\s*(release|unreserve|cancel (the )?(reservation|hold))\b"]),
    ("callback", [r"\b(call ?back|call me|ring me|phone me|speak to (someone|a person|the team)|talk to (a |the )?(team|person|human|someone))\b"]),
    ("feedback", [r"\b(feedback|rate (this|the) chat|rating|review (this|the) chat|rate this)\b"]),
    ("qr_pass", [r"\b(show|see|view|open|display|get)\b.*\b(qr|id card|my pass|entry pass|ticket)\b|\b(my )?(qr code|id card)\b"]),
    ("calendar", [r"\b(calendar|remind(er)?|save the date|\.?ics)\b"]),
    ("share", [r"\b(share|invite|forward|send (this|it|details) to)\b"]),
    ("invoice", [r"\binvoice\b"]),
    ("directory", [r"\b(who (is|are|all are) exhibiting|exhibitors? (in|for|from|list|list of)|list of exhibitors|which (companies|firms|brands)|stall of |which stall (is|does) .* (have|in)|find (the )?(company|exhibitor|firm|brand)|participating (companies|firms|brands)|exhibitor directory)\b"]),
    ("suggest", [r"\b(budget|within|under|up ?to|around|afford(able)?|cheap(est|er)?|lowest|which stall (should|for|suits|is best|is good)|suggest|recommend|best stall|good stall|suitable|value for money)\b"]),
    ("resend", [r"\b(re-?send|send (me )?(my |the )?(pass|id card|invitation|e-?mail|mail|qr)( again)?|not received|(did ?n[o']?t|do ?n[o']?t|never|have ?n[o']?t|has ?n[o']?t) (get|got|receive|received|come|arrive)|lost my (pass|id card|qr)|mail nahi (aaya|mila))\b"]),
    ("edit_details", [r"\b(edit|change|update)\b.*\b(my |the )?(detail|name|e-?mail|mail id|city|number|mobile|phone|guest|people|registration)s?\b"]),
    ("status", [r"\b(track|status|tracking|my (registration|booking|stall|pass|ticket|id card|invitation)|registered\??|check my|confirm(ed|ation)\b.*\bmy|where is my|did i register|registration (code|id|number))\b"]),
    ("visitor_register", [r"\b(register|registration|sign ?up|book|get|want|need)\b.*\b(visitor|visit|pass|entry|ticket|invitation|attend)\b",
                          r"\b(visitor|visit|attend)\b.*\b(register|registration|sign ?up)\b",
                          r"\b(visitor registration|register me|i want to visit|get (my|a) (visitor )?pass|book (a |my )?(visitor )?pass)\b"]),
    ("exhibitor_register", [r"\b(exhibit|exhibitor|stall booking|book (a )?stall|book stall|take (a )?stall|participate|put up (a )?stall|want (a )?stall|stall registration|register (my )?(company|business|firm))\b"]),
    ("ruby", [r"\b(ruby|women|woman|ladies|lady|female|mahila)\b"]),
    ("sponsor", [r"\b(sponsor|sponsorship|partnership|partner|title sponsor|silver sponsor)\b"]),
    ("stalls_available", [r"\b(empty|available|availability|vacant|free stalls|remaining|left|open stalls|which stalls|stall map|layout|floor ?plan|venue map|map)\b"]),
    ("rates", [r"\b(rate|rates|price|prices|pricing|cost|costs|charge|charges|fee|fees|rent|rupees|rs\.?|₹|package|packages|how much|kitna|kitne)\b"]),
    ("dates", [r"\b(date|dates|when|kab|day|days|timing|timings|time|hours|schedule|january|jan|2027|hijri|shaban)\b"]),
    ("venue", [r"\b(venue|where is (the )?(expo|event|venue)|location|address|ground|msb|directions|kaha|kahan)\b"]),
    ("deadline", [r"\b(deadline|last date|closing date|till when|until when)\b"]),
    ("categories", [r"\b(categor|industr|sector|what kind of (business|stall|product)|which business)\w*"]),
    ("instructions", [r"\b(set ?up|move[- ]?in|move[- ]?out|dismantl|fabrication|guideline|rules|documents|gst|agreement|cancellation|refund|height|electric|power)\b"]),
    ("about", [r"\b(about|what is roar|roar means|roar expo|roar stand|organi[sz]er|who (is|are) (organi|behind|managing)|managed by|dbohra|jamiyat|expected visitors|footfall|how many (stalls|visitors|industries))\b"]),
    ("contact", [r"\b(contact|whatsapp|call|phone|number|email|mail|helpline|helpdesk|reach you|talk to|speak to|human|person|team)\b"]),
    ("website", [r"\b(website|site|link|url)\b"]),
]


def detect_intent(message: str) -> str | None:
    m = (message or "").strip().lower()
    if not m:
        return "greeting"
    for name, patterns in INTENTS:
        for p in patterns:
            if re.search(p, m):
                return name
    return None


# ------------------------------------------------------------------ data lookups

async def available_stalls(db: AsyncIOMotorDatabase) -> tuple[list[dict], list[dict], int]:
    """Available stalls that sit on the map + per-category counts."""
    from utils.stall_holds import release_expired_holds
    await release_expired_holds(db)
    projection = {"stallNumber": 1, "packageCode": 1, "status": 1, "mapX": 1, "mapY": 1, "rate": 1}
    stalls = await db.stalls.find({}, projection).sort("stallNumber", 1).to_list(length=None)
    counts: dict[str, dict] = {}
    for p in EVENT["stallPackages"]:
        if p.get("hasStallPicker"):
            counts[p["code"]] = {"code": p["code"], "label": p["label"], "available": 0, "total": 0, "rate": p.get("rate"), "numbers": []}
    free = []
    for s in stalls:
        c = counts.get(s.get("packageCode"))
        if c is None:
            continue
        c["total"] += 1
        if s.get("status") == "available":
            c["available"] += 1
            c["numbers"].append(s["stallNumber"])
            if s.get("mapX") is not None and s.get("mapY") is not None:
                free.append({"n": s["stallNumber"], "x": round(float(s["mapX"]), 2), "y": round(float(s["mapY"]), 2), "c": s["packageCode"]})
    total_free = sum(c["available"] for c in counts.values())
    return free, [c for c in counts.values() if c["total"]], total_free


async def map_url(db: AsyncIOMotorDatabase) -> str:
    doc = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    return (doc or {}).get("url") or ""


EXHIBITOR_STATUS = {
    "pending": ("Pending confirmation", "warn", "Your registration has reached the organising team and is being verified. You will get a confirmation e-mail once it is approved."),
    "confirmed": ("Confirmed", "ok", "Your stall is confirmed. The confirmation e-mail has the exhibitor instructions, set-up timings and documents required."),
    "cancelled": ("Cancelled", "muted", "This registration was cancelled. Contact the team if you think this is a mistake."),
}


async def lookup_by_mobile(db: AsyncIOMotorDatabase, mobile: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Returns (reply blocks, matching visitor documents, matching exhibitor documents)."""
    rx = _phone_regex(mobile)
    blocks: list[dict] = []
    exhibitors = await db.exhibitors.find({"$or": [{"phone": rx}, {"whatsapp": rx}]}).sort("createdAt", -1).to_list(length=10)
    visitors = await db.visitors.find({"phone": rx}).sort("createdAt", -1).to_list(length=10)
    for e in exhibitors:
        label, tone, note = EXHIBITOR_STATUS.get(e.get("status"), (e.get("status", "—").title(), "info", ""))
        pkg = find_stall_package(e.get("stallPackage") or "")
        rows = [
            ("Status", label),
            ("Registration ID", e.get("registrationCode")),
            ("Company", e.get("companyName")),
            ("Contact person", e.get("contactPerson")),
            ("Stall" + ("s" if len(e.get("stallNumbers") or []) > 1 else ""), (", ".join(e.get("stallNumbers") or []) or e.get("stallNumber") or "To be allotted") + (f" · {pkg['label']}" if pkg else "")),
            ("Amount", _rupees(e.get("totalAmount") or e.get("stallRate")) if (e.get("totalAmount") or e.get("stallRate")) else None),
            ("Payment", {"paid": "Paid ✅", "unpaid": "Pending"}.get(str(e.get("paymentStatus") or "").lower()) if e.get("status") == "confirmed" else None),
            ("E-mail", _mask_email(e.get("email", ""))),
            ("Registered on", _when(e.get("createdAt"))),
        ]
        blocks.append(card("Exhibitor registration", rows, tone))
        if note:
            blocks.append(text(note))
    for v in visitors:
        rows = [
            ("Status", "Checked in at the expo" if v.get("checkedIn") else "Registered — show your QR ID card at the entrance"),
            ("Registration ID", v.get("registrationCode")),
            ("Name", v.get("fullName")),
            ("Guests", str(v.get("numberOfGuests") or 1)),
            ("City", v.get("city")),
            ("E-mail", _mask_email(v.get("email", ""))),
            ("ID card e-mail", "Sent" if v.get("emailSent") else "Not delivered yet — contact us if it doesn't arrive"),
            ("Registered on", _when(v.get("createdAt"))),
        ]
        blocks.append(card("Visitor registration", rows, "ok" if v.get("emailSent") else "warn"))
    return blocks, visitors, exhibitors


# ------------------------------------------------------------------ static answers

def contact_blocks() -> list[dict]:
    c = BOT["contacts"]
    return [
        text("Here's how to reach the ROAR Expo team:"),
        card("Stalls · partnerships · sponsorship", [("Name", c["stalls"]["name"]), ("Phone / WhatsApp", c["stalls"]["phone"])], "info"),
        card("Ruby stalls (women entrepreneurs)", [("Name", c["ruby"]["name"]), ("Phone / WhatsApp", c["ruby"]["phone"])], "info"),
        card("General enquiries", [("WhatsApp", c["enquiries"]["phone"] + " (message only)"), ("E-mail", ", ".join(c["emails"]))], "muted"),
        links({"label": "WhatsApp " + c["stalls"]["name"].split()[0], "href": "https://wa.me/" + _digits(c["stalls"]["phone"])},
              {"label": "Send an enquiry", "to": "/enquiry"}),
    ]


def dates_blocks() -> list[dict]:
    return [
        card("ROAR Business Expo Nagpur 2027", [
            ("Dates", EVENT["eventDatesLabel"]),
            ("Hijri", EVENT.get("eventDatesHijri", "1st – 3rd Shaban ul Karim 1448H")),
            ("Timings", BOT["showTimings"]),
            ("Venue", EVENT["venueName"]),
        ], "info"),
        links({"label": "Open venue in Google Maps", "href": EVENT["venueMapUrl"]},
              {"label": "Why Nagpur?", "to": "/why-nagpur"}),
    ]


def rates_blocks(highlight: str | None = None, counts: list[dict] | None = None) -> list[dict]:
    avail = {c["code"]: c["available"] for c in (counts or [])}
    rows = []
    for p in EVENT["stallPackages"]:
        if highlight and p["code"] != highlight:
            continue
        rows.append({
            "code": p["code"], "label": p["label"], "rate": _rupees(p.get("rate")),
            "count": p.get("stallCount") or p.get("sizeLabel") or "",
            "available": avail.get(p["code"]) if p.get("hasStallPicker") else None,
            "note": p.get("inclusions", ""),
        })
    out = [{"type": "rates", "rows": rows}]
    if not highlight:
        out.insert(0, text("Stall rate card (per stall, for all three days):"))
        out.append(text("Ruby stalls are reserved for women entrepreneurs. Food Court and Play Zone spaces are priced directly with the team."))
    out.append(links({"label": "Book a stall online", "to": "/register/exhibitor"}, {"label": "See the live stall map", "to": "/stalls"}))
    return out


def exhibitor_blocks() -> list[dict]:
    c = BOT["contacts"]["stalls"]
    d = EVENT["registrationDeadlines"]["stall"]
    return [
        text("Exhibitor registration is online — pick your category, click the stall you want on the live map and fill the form. "
             f"Stall bookings close on {d}."),
        links({"label": "Register as an exhibitor", "to": "/register/exhibitor", "primary": True},
              {"label": "Live stall map", "to": "/stalls"},
              {"label": "WhatsApp " + c["name"].split()[0] + " for help", "href": "https://wa.me/" + _digits(c["phone"])}),
        text(f"For partnerships or sponsorship, {c['name']} — {c['phone']}."),
    ]


def about_blocks() -> list[dict]:
    h = BOT["headline"]
    s = BOT["sponsors"]
    return [
        text(BOT["about"]),
        card("At a glance", [
            ("Stalls", h["stalls"]), ("Industries", h["industries"]), ("Expected visitors", h["visitors"]), ("Days", h["days"]),
            ("Managed by", EVENT["organizers"][0]["name"] + ", " + EVENT["organizers"][0]["tagline"]),
            ("In collaboration with", s["collaboration"]),
            ("Title sponsors", " · ".join(s["title"])),
            ("Silver sponsor", " · ".join(s["silver"])),
        ], "info"),
    ]


def greeting_blocks() -> list[dict]:
    return [text(f"Hello! I'm the {BOT['name']} for ROAR Business Expo Nagpur, {EVENT['eventDatesLabel']} at {EVENT['venueName']}. "
                 "Ask me anything about the expo — I can also register you as a visitor, book your stall right here, track a registration "
                 "by mobile number, and show empty stalls, rates and dates. What would you like?")]


# ------------------------------------------------------------------ visitor registration flow

VISITOR_STEPS = ["fullName", "phone", "email", "city", "numberOfGuests", "confirm"]
PROMPTS = {
    "fullName": "Great — let's register you as a visitor (it's free). What's your full name?",
    "phone": "Your 10-digit mobile number? (Your entry ID card will be linked to it.)",
    "email": "Your e-mail address? We'll send the ID card with your entrance QR code there.",
    "city": "Are you coming from Nagpur or another city?",
    "numberOfGuests": "How many people will attend including you? (1 – 10)",
}


def _confirm_blocks(data: dict) -> list[dict]:
    return [
        text("Please check your details:"),
        card("Visitor registration", [
            ("Name", data.get("fullName")), ("Mobile", data.get("phone")), ("E-mail", data.get("email")),
            ("City", data.get("city")), ("People", str(data.get("numberOfGuests", 1))),
        ], "info"),
        text("Shall I submit this?"),
    ]


CONFIRM_QR = [{"label": "Yes, register me", "send": "yes", "primary": True}] + qr(("Change name", "edit name"), ("Change mobile", "edit mobile"),
                ("Change e-mail", "edit email"), ("Change city", "edit city"), ("Change people", "edit guests"), ("Cancel", "cancel"))


async def visitor_flow(db, session: dict, message: str) -> tuple[list[dict], list[dict], bool]:
    """Returns (blocks, quickReplies, finished)."""
    data = session.setdefault("data", {})
    step = session.get("step") or "fullName"
    m = (message or "").strip()
    low = m.lower()

    if step == "confirm":
        if re.match(r"^(yes|y|ok|okay|submit|confirm|haan|ha|ji|register me|yes, register me)\b", low):
            return await _submit_visitor(db, session)
        edit = re.match(r"^(edit|change)\s+(name|mobile|phone|number|e-?mail|city|guests|people)", low)
        if edit:
            field = {"name": "fullName", "mobile": "phone", "phone": "phone", "number": "phone", "email": "email", "e-mail": "email",
                     "city": "city", "guests": "numberOfGuests", "people": "numberOfGuests"}[edit.group(2)]
            session["step"] = field
            session["editing"] = True
            return [text(PROMPTS[field])], (qr(("Nagpur", "Nagpur"), ("Other city", "other city")) if field == "city" else qr(("Cancel", "cancel"))), False
        if re.match(r"^(no|nah|nahi|wrong)\b", low):
            return [text("No problem — what would you like to change?")], CONFIRM_QR, False
        return _confirm_blocks(data), CONFIRM_QR, False

    # collecting a field
    if step == "fullName":
        if len(m) < 3 or not re.search(r"[A-Za-z]", m) or re.search(r"\d{5,}", m):
            return [text("Please type your full name (letters only), e.g. Mustafa Kanchwala.")], qr(("Cancel", "cancel")), False
        data["fullName"] = re.sub(r"\s+", " ", m).title() if m.islower() or m.isupper() else re.sub(r"\s+", " ", m)
    elif step == "phone":
        mob = _mobile(m)
        if not mob:
            return [text("That doesn't look like an Indian mobile number. Please type the 10 digits, e.g. 98765 43210.")], qr(("Cancel", "cancel")), False
        data["phone"] = "+91 " + mob[:5] + " " + mob[5:]
        if not session.get("editing"):
            existing = await db.visitors.find_one({"phone": _phone_regex(mob)}, {"fullName": 1, "registrationCode": 1})
            if existing:
                session["step"] = "email"
                session["editing"] = False
                return ([text(f"This number is already registered for {existing.get('fullName')} (ID {existing.get('registrationCode')}). "
                              "I'll continue with a new registration — or type 'track' to see the existing one."),
                         text(PROMPTS["email"])], qr(("Track existing", "track my registration"), ("Cancel", "cancel")), False)
    elif step == "email":
        em = re.sub(r"\s+", "", m).lower()
        if not is_valid_email(em):
            return [text("Please type a valid e-mail address, e.g. name@example.com.")], qr(("Cancel", "cancel")), False
        data["email"] = em
    elif step == "city":
        if re.match(r"^(other|other city|another city|outside nagpur|not nagpur|bahar)\b", low):
            return [text("Please type the name of your city.")], [], False
        if len(m) < 2 or len(m) > 60 or re.search(r"\d{3,}", m):
            return [text("Please type your city name, e.g. Mumbai, Indore, Surat.")], qr(("Nagpur", "Nagpur"), ("Other city", "other city")), False
        data["city"] = m.strip().title() if m.islower() else m.strip()
    elif step == "numberOfGuests":
        n = re.search(r"\d+", m)
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5}
        val = int(n.group()) if n else words.get(low.split()[0] if low else "", None)
        if not val or val < 1 or val > 10:
            return [text("How many people, between 1 and 10?")], qr(("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("Cancel", "cancel")), False
        data["numberOfGuests"] = val

    if session.get("editing"):
        session["editing"] = False
        session["step"] = "confirm"
        return _confirm_blocks(data), CONFIRM_QR, False

    # group registration: name is enough — mobile, e-mail and city are copied from the first person
    if data.get("group") and step == "fullName":
        data.setdefault("numberOfGuests", 1)
        session["step"] = "confirm"
        return [text(f"Adding {data['fullName']} with the same mobile, e-mail and city.")] + _confirm_blocks(data), CONFIRM_QR, False

    # next step
    nxt = VISITOR_STEPS[VISITOR_STEPS.index(step) + 1]
    session["step"] = nxt
    if nxt == "confirm":
        return _confirm_blocks(data), CONFIRM_QR, False
    quick = qr(("Cancel", "cancel"))
    if nxt == "city":
        quick = qr(("Nagpur", "Nagpur"), ("Other city", "other city"))
    if nxt == "numberOfGuests":
        quick = qr(("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("Cancel", "cancel"))
    return [text(PROMPTS[nxt])], quick, False


async def _submit_visitor(db, session) -> tuple[list[dict], list[dict], bool]:
    from routers.visitors import register_visitor  # same code path as the website form
    data = session.get("data", {})
    try:
        payload = VisitorRegisterRequest(
            fullName=data["fullName"], email=data["email"], phone=data["phone"], city=data.get("city", ""),
            numberOfGuests=int(data.get("numberOfGuests", 1)), interests=[], organization="", designation="",
            howDidYouHear="Ask ROAR Anything (website chat)", source="online",
        )
        res = await register_visitor(payload, db)
        code = (res.get("data") or {}).get("registrationCode", "")
    except Exception as err:  # noqa: BLE001
        detail = getattr(err, "detail", None) or str(err)
        return ([text(f"Sorry — the registration could not be saved: {detail}"),
                 text("You can try again, or register on the website form.")],
                qr(("Try again", "yes"), ("Open visitor form", "open visitor form"), ("Cancel", "cancel")), False)
    new_doc = await db.visitors.find_one({"registrationCode": code}) if code else None
    session["_tag"] = "registered"
    session["flow"], session["step"] = "visitor_manage", None
    session["data"] = {"visitorId": str(new_doc["_id"]) if new_doc else None,
                       "visitors": [{"id": str(new_doc["_id"]), "name": new_doc.get("fullName", ""), "code": code}] if new_doc else [],
                       "last": {"phone": data["phone"], "email": data["email"], "city": data.get("city", "")}}
    blocks = [
        text(f"Done — you're registered, {data['fullName'].split()[0]}! 🎉"),
        card("Your visitor registration", [
            ("Registration ID", code), ("Name", data["fullName"]), ("Mobile", data["phone"]),
            ("People", str(data.get("numberOfGuests", 1))), ("Dates", EVENT["eventDatesLabel"]), ("Venue", EVENT["venueName"]),
        ], "ok"),
        text(f"Your ID card with the entrance QR code is on its way to {data['email']}. Show it on your phone at the gate. "
             "You can check it any time here with 'Track my registration' and your mobile number."),
    ] + F.calendar_blocks()
    return blocks, qr(("Show my QR pass", "show my qr pass"), ("Register another person", "register another person"),
                      ("Edit my details", "edit my details"), ("Main menu", "menu")), False


# ------------------------------------------------------------------ main entry

async def handle(db: AsyncIOMotorDatabase, session_id: str, message: str, action: str | None = None) -> dict:
    now = utcnow()
    session = await db.bot_sessions.find_one({"sessionId": session_id}) or {"sessionId": session_id, "flow": None, "step": None, "data": {}, "history": [], "createdAt": now}
    session.setdefault("history", [])
    message = (message or "").strip()[:1000]

    if action == "open":
        blocks, quick = greeting_blocks(), MENU
        session["flow"], session["step"], session["data"] = None, None, {}
        return await _finish(db, session, "", blocks, quick, now)

    low = message.lower()
    blocks: list[dict] = []
    quick: list[dict] = MENU
    tags: list[str] = []

    # language follows the visitor (chips are English, so a tapped chip never switches it)
    if message and message not in (session.get("lastQuick") or []):
        session["lang"] = F.detect_lang(message, session.get("lang"))

    # ---- an active guided flow gets the message first (except cancel / clear intent switches)
    intent = detect_intent(F.normalize_for_intent(message))
    if session.get("flow") in ("book", "visitor", "enquiry", "callback") and intent != "cancel" and _is_question(message):
        kbq = KB.best(F.normalize_for_intent(message))
        if kbq and kbq[0][0] >= KB.WEAK:
            qb, _ = KB.blocks_for(kbq[0][1])
            resume = _resume_prompt(session)
            return await _finish(db, session, message, qb + [text("Now, back to where we were — " + resume)],
                                 qr(("Cancel", "cancel")) if session.get("step") != "confirm" else _confirm_quick(session), now, tags=["kb:" + kbq[0][1]["id"]])

    if session.get("flow") == "book":
        if intent == "cancel":
            await FL.release(db, session)
            session["flow"], session["step"], session["data"] = None, None, {}
            return await _finish(db, session, message, [text("Okay — booking cancelled and the stall released. Anything else?")], MENU, now)
        r = await FL.booking_flow(db, session, message)
        if r:
            fb, fq, done = r
            return await _finish(db, session, message, fb, fq or MENU, now)
    if session.get("flow") == "enquiry" and intent != "cancel":
        r = await FL.enquiry_flow(db, session, message)
        if r:
            fb, fq, done = r
            return await _finish(db, session, message, fb, fq or MENU, now)
    if session.get("flow") == "callback" and intent != "cancel":
        r = await F.callback_flow(db, session, message)
        if r:
            fb, fq, done = r
            return await _finish(db, session, message, fb, fq or MENU, now)
    if session.get("flow") == "feedback" and intent != "cancel":
        r = await F.feedback_flow(db, session, message)
        if r:
            fb, fq, done = r
            return await _finish(db, session, message, fb, fq or MENU, now)
    if session.get("flow") == "visitor" and intent not in ("cancel",):
        # Let obvious topic switches through (e.g. "stall rates") unless we're mid-field and the text fits the field.
        if intent in ("rates", "dates", "venue", "contact", "stalls_available", "exhibitor_register", "status") and session.get("step") in ("confirm",):
            session["flow"], session["step"] = None, None
        else:
            fblocks, fquick, finished = await visitor_flow(db, session, message)
            if finished:
                session["flow"], session["step"], session["data"] = None, None, {}
            return await _finish(db, session, message, fblocks, fquick, now)

    if session.get("flow") == "visitor_manage":
        handled = await manage_flow(db, session, message, intent)
        if handled is not None:
            mblocks, mquick = handled
            return await _finish(db, session, message, mblocks, mquick, now)
        # anything else: leave the manage flow and answer the question normally
        session["flow"], session["step"] = None, None

    if session.get("flow") == "status":
        mob = _mobile(message)
        if mob:
            return await _status_with(db, session, message, mob, now)
        if intent in (None, "status"):
            return await _finish(db, session, message, [text("Please type the 10-digit mobile number you registered with.")], qr(("Cancel", "cancel")), now)
        session["flow"], session["step"] = None, None  # a different question — answer it instead

    # ---- a bare mobile number anywhere = status lookup
    mob = _mobile(message)
    if mob and (intent is None or intent in ("status", "greeting", "contact")) and len(_digits(message)) <= 13:
        return await _status_with(db, session, message, mob, now)

    # ---- "is G2 free?" — a stall number in the message
    if intent in (None, "stalls_available", "rates", "exhibitor_register", "status", "venue") and len(message) <= 80:
        codes = F.stall_codes_in(message)
        if codes:
            r = await F.stall_check(db, codes, low)
            if r:
                return await _finish(db, session, message, r[0], r[1], now)

    # ---- group registration: another person on the same mobile / e-mail / city
    if low in ("register another person", "register another visitor", "add another person"):
        last = (session.get("data") or {}).get("last")
        if last:
            session["flow"], session["step"] = "visitor", "fullName"
            session["data"] = {"group": True, "last": last, **last}
            return await _finish(db, session, message, [text("Sure — what's the next person's full name?")], qr(("Cancel", "cancel")), now)
        intent = "visitor_register"

    # ---- website knowledge: a clearly specific question beats a generic intent ("how to reach Nagpur by train" → Getting there)
    kb = KB.best(F.normalize_for_intent(message))
    if kb and kb[0][0] >= KB.STRONG and (intent in (None, "venue", "dates", "about", "website", "categories", "contact", "instructions", "deadline", "ruby")
                                         or (intent in ("exhibitor_register", "visitor_register", "rates") and _is_question(message))):
        kb_blocks, kb_quick = KB.blocks_for(kb[0][1])
        return await _finish(db, session, message, kb_blocks, kb_quick, now, tags=["kb:" + kb[0][1]["id"]])

    # ---- intents
    if intent in ("greeting", "cancel"):
        session["flow"], session["step"], session["data"] = None, None, {}
        blocks = greeting_blocks() if intent == "greeting" else [text("Okay, cancelled. What else can I help with?")]
    elif intent == "thanks":
        blocks = [text("You're welcome! Anything else — stalls, rates, dates, or your registration?")]
        quick = qr(("Rate this chat", "rate this chat"), ("Add to calendar", "add to calendar"), ("Invite a friend", "invite a friend"), ("Main menu", "menu"))
    elif intent == "reserve":
        code = (F.stall_codes_in(message) or [""])[0]
        blocks, quick = await F.reserve_stall(db, session, code)
        tags.append("reserved")
    elif intent == "release":
        blocks, quick = await F.release_reserved(db, session, (F.stall_codes_in(message) or [None])[0])
    elif intent == "callback":
        session["flow"], session["step"], session["data"] = "callback", "name", {}
        blocks = [text("Sure — the team will call you back. Your name, please?")]
        quick = qr(("Cancel", "cancel"))
    elif intent == "feedback":
        session["flow"], session["step"], session["data"] = "feedback", "rating", {}
        blocks = [text("How would you rate this chat, 1 to 5?")]
        quick = F.RATING_QR
    elif intent == "qr_pass":
        session["flow"], session["step"] = "status", "mobile"
        session["data"] = {"pending": "qr"}
        blocks = [text("Type the 10-digit mobile number you registered with and I'll show your entrance QR pass here.")]
        quick = qr(("Cancel", "cancel"))
    elif intent == "invoice":
        session["flow"], session["step"] = "status", "mobile"
        session["data"] = {"pending": "invoice"}
        blocks = [text("Type the mobile number used for the stall registration and I'll e-mail the invoice.")]
        quick = qr(("Cancel", "cancel"))
    elif intent in ("calendar", "share"):
        blocks = F.calendar_blocks()
        quick = qr(("Register as visitor", "register as visitor"), ("Dates & venue", "dates and venue"), ("Main menu", "menu"))
    elif intent == "directory":
        blocks, quick = await F.directory_search(db, low)
    elif intent == "suggest":
        blocks, quick = await F.suggest_stalls(db, low)
    elif intent == "visitor_register" or low == "open visitor form":
        if low == "open visitor form":
            blocks = [links({"label": "Open the visitor registration form", "to": "/register/visitor", "primary": True})]
        else:
            session["flow"], session["step"], session["data"] = "visitor", "fullName", {}
            blocks = [text("Visitor entry is free. I can register you right here in a minute, or you can use the website form."),
                      text(PROMPTS["fullName"])]
            quick = qr(("Use the website form", "open visitor form"), ("Cancel", "cancel"))
    elif intent == "book_chat":
        fb, fq, _ = await FL.start_booking(db, session, low)
        return await _finish(db, session, message, fb, fq, now, tags=["booking-started"])
    elif intent == "enquiry" or low in ("send an enquiry", "send enquiry"):
        session["flow"], session["step"], session["data"] = "enquiry", "name", {}
        blocks = [text("Sure — I'll send your question to the organising team (same as the Enquiry page). " + FL.ENQ_PROMPTS["name"])]
        quick = qr(("Cancel", "cancel"))
    elif low == "open enquiry page":
        blocks = [links({"label": "Open the Enquiry page", "to": "/enquiry", "primary": True})]
    elif intent == "payment":
        session["flow"], session["step"] = "status", "mobile"
        session["data"] = {"pending": "payment"}
        blocks = [text("Type the mobile number used for your stall registration and I'll show the amount and bank details.")]
        quick = qr(("Cancel", "cancel"))
    elif intent == "exhibitor_register":
        blocks = [text("You can book your stall right here in the chat — I'll ask the same details as the website form (about 2 minutes), "
                       "or use the online form with the live map. Stall bookings close on " + EVENT["registrationDeadlines"]["stall"] + "."),
                  links({"label": "Use the website form", "to": "/register/exhibitor"}, {"label": "Live stall map", "to": "/stalls"})]
        quick = [{"label": "Book in chat now", "send": "book a stall in chat", "primary": True}] + qr(("Stall rates", "stall rates"), ("Empty stalls map", "empty stalls"), ("Contact", "contact"))
    elif intent == "status":
        session["flow"], session["step"] = "status", "mobile"
        session["data"] = {}
        blocks = [text("Sure — type the 10-digit mobile number you registered with and I'll pull up your exhibitor or visitor registration.")]
        quick = qr(("Cancel", "cancel"))
    elif intent in ("resend", "edit_details"):
        session["flow"], session["step"] = "status", "mobile"
        session["data"] = {"pending": "resend" if intent == "resend" else "edit"}
        blocks = [text("Type the 10-digit mobile number you registered with" + (" and I'll send your entry pass again." if intent == "resend" else " and I'll open your registration for editing."))]
        quick = qr(("Cancel", "cancel"))
    elif intent == "stalls_available":
        free, counts, total_free = await available_stalls(db)
        url = await map_url(db)
        pkg = _package_in(low)
        if pkg:
            c = next((x for x in counts if x["code"] == pkg["code"]), None)
            if c:
                nums = ", ".join(c["numbers"]) if c["numbers"] else "none left"
                blocks = [text(f"{pkg['label']}: {c['available']} of {c['total']} stalls available ({_rupees(pkg.get('rate'))} each)."),
                          text(f"Available numbers: {nums}.")]
            else:
                blocks = [text(f"{pkg['label']} is priced and allotted directly by the team — no online picker.")]
        else:
            blocks = [text(f"{total_free} stalls are still available right now (green on the map). Tap a category below the map to see the stall numbers.")]
        blocks.append({"type": "map", "mapUrl": url, "stalls": free,
                       "counts": [{"code": c["code"], "label": c["label"], "available": c["available"], "total": c["total"], "numbers": c["numbers"]} for c in counts]})
        blocks.append(links({"label": "Book a stall", "to": "/register/exhibitor", "primary": True}, {"label": "Full-screen map", "to": "/stalls"}))
        quick = qr(("Stall rates", "stall rates"), ("Exhibitor registration", "exhibitor registration"), ("Ruby stalls", "ruby stalls"), ("Contact", "contact"))
    elif intent == "rates":
        _, counts, _ = await available_stalls(db)
        pkg = _package_in(low)
        if pkg:
            blocks = [text(f"{pkg['label']}: {_rupees(pkg.get('rate'))}" + (f" per stall, {pkg['stallCount']} stalls in this category." if pkg.get("stallCount") else "."))]
            blocks += rates_blocks(pkg["code"], counts)
        else:
            blocks = rates_blocks(None, counts)
        quick = qr(("Empty stalls map", "empty stalls"), ("Exhibitor registration", "exhibitor registration"), ("Ruby stalls", "ruby stalls"), ("Contact", "contact"))
    elif intent == "ruby":
        c = BOT["contacts"]["ruby"]
        p = find_stall_package("ruby") or {}
        _, counts, _ = await available_stalls(db)
        rc = next((x for x in counts if x["code"] == "ruby"), None)
        blocks = [text((p.get("eligibility") or BOT["ruby"]) + f" Rate {_rupees(p.get('rate'))} per stall" + (f"; {rc['available']} of {rc['total']} still available." if rc else ".")),
                  card("Ruby stall bookings", [("Contact", c["name"]), ("Phone / WhatsApp", c["phone"])], "info"),
                  links({"label": "WhatsApp " + c["name"].split()[0], "href": "https://wa.me/" + _digits(c["phone"])},
                        {"label": "Ruby stalls on the map", "to": "/stalls"}, {"label": "Book online (RU1–RU13)", "to": "/register/exhibitor"})]
        quick = qr(("Empty stalls map", "empty stalls"), ("Stall rates", "stall rates"), ("Main menu", "menu"))
    elif intent == "sponsor":
        c = BOT["contacts"]["stalls"]
        s = BOT["sponsors"]
        blocks = [card("Sponsors", [("Title sponsors", " · ".join(s["title"])), ("Silver sponsor", " · ".join(s["silver"])), ("In collaboration with", s["collaboration"])], "info"),
                  text(f"For sponsorship and partnership packages, speak to {c['name']} — {c['phone']}."),
                  links({"label": "WhatsApp " + c["name"].split()[0], "href": "https://wa.me/" + _digits(c["phone"])}, {"label": "Send an enquiry", "to": "/enquiry"})]
    elif intent == "dates":
        blocks = dates_blocks()
        quick = qr(("Register as visitor", "register as visitor"), ("Exhibitor registration", "exhibitor registration"), ("Where is the venue?", "venue"), ("Main menu", "menu"))
    elif intent == "venue":
        blocks = [card("Venue", [("Venue", EVENT["venueName"]), ("Address", EVENT["venueAddress"]), ("Dates", EVENT["eventDatesLabel"]), ("Timings", BOT["showTimings"])], "info"),
                  text("Nagpur sits at the centre of India — well connected by air, rail and highway from every region."),
                  links({"label": "Open in Google Maps", "href": EVENT["venueMapUrl"]}, {"label": "Getting there — Why Nagpur", "to": "/why-nagpur"})]
    elif intent == "deadline":
        d = EVENT["registrationDeadlines"]
        blocks = [card("Registration deadlines", [("Stall booking", d["stall"]), ("Visitor registration", d["visitor"])], "warn"),
                  text("Stalls are allotted on a first-come basis — book early to get the location you want.")]
        quick = qr(("Exhibitor registration", "exhibitor registration"), ("Register as visitor", "register as visitor"), ("Main menu", "menu"))
    elif intent == "categories":
        blocks = [text("Industries at the expo: " + ", ".join(c["label"] for c in EVENT["categories"]) + ".")]
        quick = qr(("Stall rates", "stall rates"), ("Exhibitor registration", "exhibitor registration"), ("Main menu", "menu"))
    elif intent == "instructions":
        ins = EVENT["exhibitorInstructions"]
        blocks = [card("Exhibitor information", [("Set-up", ins["setupWindow"]), ("Move-out", ins["moveOutWindow"]), ("Daily timing", ins["dailyShowTiming"]),
                                                 ("Documents", "; ".join(ins["documentsRequired"]))], "info"),
                  text(" ".join(ins["guidelines"])), text("Cancellation: " + ins["cancellationPolicy"])]
    elif intent == "about":
        blocks = about_blocks()
        quick = qr(("Register as visitor", "register as visitor"), ("Exhibitor registration", "exhibitor registration"), ("Dates & venue", "dates and venue"), ("Contact", "contact"))
    elif intent == "contact":
        blocks = contact_blocks()
    elif intent == "website":
        blocks = [text("You're on it — www.roarexpo.com."), links({"label": "Visitor registration", "to": "/register/visitor"}, {"label": "Exhibitor registration", "to": "/register/exhibitor"}, {"label": "Stall map", "to": "/stalls"})]
    else:
        # free text → website knowledge → AI (when configured) → closest topics
        if kb and kb[0][0] >= KB.WEAK:
            blocks, quick = KB.blocks_for(kb[0][1])
            tags.append("kb:" + kb[0][1]["id"])
        else:
            answer = await ai_answer(message, session.get("history"))
            if answer:
                blocks = [text(answer)]
                tags.append("ai")
            else:
                session["_unanswered"] = message
                blocks = [text("I'm not sure I understood that. I can help with visitor registration, exhibitor registration, tracking a registration by mobile number, empty stalls, stall rates, dates and venue, or contacting the team — pick one below, or message the team on WhatsApp "
                               + BOT["contacts"]["enquiries"]["phone"] + "."),
                          text("Or send your question to the organising team and they'll reply by e-mail.")]
                quick = qr(("Send an enquiry", "send an enquiry"), ("Request a callback", "call me back"), ("Main menu", "menu"))
    return await _finish(db, session, message, blocks, quick, now, tags=tags)


_QUESTION_RE = re.compile(r"^\s*(what|what's|how|when|where|why|who|which|is|are|can|could|do|does|will|would|should|kya|kab|kaha|kahan|kitna|kitne|kaise)\b", re.I)


def _is_question(message: str) -> bool:
    m = (message or "").strip()
    return len(m) > 6 and (m.endswith("?") or bool(_QUESTION_RE.match(m)))


def _resume_prompt(session) -> str:
    flow, step = session.get("flow"), session.get("step")
    if flow == "visitor":
        return PROMPTS.get(step) or "please confirm your details above."
    if flow == "book":
        return FL.BOOK_PROMPTS.get(step) or {"package": "pick a stall category from the list above.", "stall": "tap a stall number above.",
                                            "ruby_ok": "please confirm the Ruby eligibility above.", "confirm": "tap “I agree & submit” when the details look right."}.get(step, "please answer the last question above.")
    if flow == "enquiry":
        return FL.ENQ_PROMPTS.get(step, "please answer the last question above.")
    return "please answer the last question above."


def _confirm_quick(session):
    return FL.CONFIRM_QR if session.get("flow") == "book" else CONFIRM_QR


async def _status_with(db, session, message, mob, now):
    pending = (session.get("data") or {}).get("pending")
    session["flow"], session["step"], session["data"] = None, None, {}
    found, visitors, exhibitors = await lookup_by_mobile(db, mob)
    if not found:
        blocks = [text(f"No registration found for {mob[:5]} {mob[5:]}. Check the number, or register now."),
                  links({"label": "Register as visitor", "to": "/register/visitor"}, {"label": "Register as exhibitor", "to": "/register/exhibitor"})]
        quick = qr(("Register as visitor", "register as visitor"), ("Try another number", "track my registration"), ("Contact", "contact"))
        return await _finish(db, session, message, blocks, quick, now)
    blocks = [text(f"Here's what I found for {mob[:5]} {mob[5:]}:")] + found
    quick = qr(("Register as visitor", "register as visitor"), ("Exhibitor registration", "exhibitor registration"), ("Contact", "contact"), ("Main menu", "menu"))
    session["flow"] = "visitor_manage"
    session["data"] = {"visitors": [{"id": str(v["_id"]), "name": v.get("fullName", ""), "code": v.get("registrationCode", "")} for v in visitors],
                       "visitorId": str(visitors[0]["_id"]) if len(visitors) == 1 else None,
                       "exhibitors": [{"id": str(e["_id"]), "name": e.get("companyName", ""), "code": e.get("registrationCode", "")} for e in exhibitors],
                       "exhibitorId": str(exhibitors[0]["_id"]) if exhibitors else None}
    chips = []
    if visitors:
        chips += [("Show my QR pass", "show my qr pass"), ("Resend my pass", "resend my pass"), ("Edit my details", "edit my details")]
    if exhibitors:
        chips += [("Payment details", "payment details"), ("Resend my confirmation", "resend my confirmation"), ("E-mail my invoice", "email my invoice"), ("Set-up & documents", "setup and documents")]
    chips += [("Main menu", "menu")]
    auto = {"resend": "resend my pass" if visitors else "resend my confirmation", "edit": "edit my details" if visitors else None,
            "qr": "show my qr pass" if visitors else None, "invoice": "email my invoice" if exhibitors else None,
            "payment": "payment details" if exhibitors else None}.get(pending)
    if auto and (len(visitors) <= 1):
        mres = await manage_flow(db, session, auto, None)
        if mres:
            mblocks, mquick = mres
            return await _finish(db, session, message, blocks + mblocks, mquick, now)
    blocks.append(text("Need the pass again, or want to correct something? Use the buttons below." if visitors else "Need anything for your stall? Use the buttons below."))
    return await _finish(db, session, message, blocks, qr(*chips), now)


# ------------------------------------------------------------------ existing visitor: resend pass / edit details

EDIT_FIELDS = {"name": "fullName", "mobile": "phone", "email": "email", "e-mail": "email", "city": "city", "people": "numberOfGuests", "guests": "numberOfGuests"}
EDIT_PROMPTS = {
    "fullName": "Type the correct full name.",
    "phone": "Type the new 10-digit mobile number.",
    "email": "Type the correct e-mail address (the pass will go there).",
    "city": "Which city? Nagpur or another city?",
    "numberOfGuests": "How many people will attend including you? (1 – 10)",
}
EDIT_PICK_QR = qr(("Name", "edit name"), ("Mobile", "edit mobile"), ("E-mail", "edit email"), ("City", "edit city"), ("People", "edit people"), ("Done", "done"))
MANAGE_QR = qr(("Resend my pass", "resend my pass"), ("Edit my details", "edit my details"), ("Main menu", "menu"))


def _visitor_card(v: dict, tone="ok") -> dict:
    return card("Visitor registration", [
        ("Registration ID", v.get("registrationCode")), ("Name", v.get("fullName")), ("Mobile", v.get("phone")),
        ("E-mail", v.get("email")), ("City", v.get("city")), ("People", str(v.get("numberOfGuests") or 1)),
    ], tone)


async def _manage_target(db, session):
    data = session.setdefault("data", {})
    vid = data.get("visitorId")
    if not vid:
        return None
    from models.common import to_object_id
    return await db.visitors.find_one({"_id": to_object_id(vid)})


async def manage_flow(db, session, message, intent):
    """Handles 'resend my pass' / 'edit my details' for a visitor found by
    mobile number. Returns (blocks, quick) or None when the message is not
    for this flow (the caller then answers it as a normal question)."""
    from utils.visitor_pass import send_visitor_pass
    data = session.setdefault("data", {})
    low = (message or "").strip().lower()
    step = session.get("step")

    # several registrations on one number: pick one first
    if not data.get("visitorId") and data.get("visitors"):
        if step == "pick_visitor":
            chosen = next((v for v in data["visitors"] if low in (v["name"].lower(), v["code"].lower()) or v["code"].lower() in low), None)
            if not chosen:
                return [text("Which registration? Tap one of the names.")], qr(*[(v["name"], v["name"]) for v in data["visitors"]])
            data["visitorId"] = chosen["id"]
            session["step"] = None
            message, low = data.pop("after", "edit my details"), data.get("after", "edit my details")
        elif low in ("resend my pass", "edit my details"):
            data["after"] = low
            session["step"] = "pick_visitor"
            return [text("This number has more than one visitor registration — which one?")], qr(*[(v["name"], v["name"]) for v in data["visitors"]])

    if low in ("done", "finish", "ok done", "no", "nothing else", "bas"):
        session["flow"], session["step"], session["data"] = None, None, {}
        return [text("Done. Anything else I can help with?")], qr(("Rate this chat", "rate this chat"), ("Main menu", "menu"))

    # ---- visitor: QR pass in the chat
    if low in ("show my qr pass", "show my pass", "my qr", "qr pass", "show qr") or intent == "qr_pass":
        v = await _manage_target(db, session)
        if not v:
            return None
        return await F.qr_pass_blocks(db, v)

    # ---- exhibitor self-service
    ex_id = data.get("exhibitorId")
    if ex_id and (low in ("payment details", "payment", "how to pay", "bank details") or intent == "payment"):
        from models.common import to_object_id
        e = await db.exhibitors.find_one({"_id": to_object_id(ex_id)})
        if e:
            return FL.payment_blocks(e)
    if ex_id and (low in ("resend my confirmation", "email my invoice", "e-mail my invoice", "my invoice") or intent == "invoice"):
        from models.common import to_object_id
        e = await db.exhibitors.find_one({"_id": to_object_id(ex_id)})
        if e:
            r = await F.exhibitor_action(db, e, "invoice" if ("invoice" in low) else "resend_confirmation")
            if r:
                return r

    # ---- resend
    if low in ("resend my pass", "resend", "send again", "resend pass") or intent == "resend":
        v = await _manage_target(db, session)
        if not v:
            return None
        result = await send_visitor_pass(db, v, resend=True)
        session["step"] = None
        if result["emailSent"]:
            msg = f"Done — your entry pass (ID card with QR + invitation) has been e-mailed again to {v.get('email')}."
            if result["whatsappSent"]:
                msg += f" The ID card was also sent on WhatsApp to {v.get('phone')}."
            msg += " Please check your spam/promotions folder if you don't see it in a few minutes."
            return [text(msg)], qr(("E-mail is wrong — change it", "edit email"), ("Edit my details", "edit my details"), ("Main menu", "menu"))
        return [text(f"Sorry — the e-mail could not be sent right now ({result['emailError'] or 'mail server error'}). "
                     f"Please try again in a few minutes, or message the team on WhatsApp {BOT['contacts']['enquiries']['phone']} with your registration ID {v.get('registrationCode')}.")], \
               qr(("Try again", "resend my pass"), ("Edit my details", "edit my details"), ("Main menu", "menu"))

    # ---- edit: pick a field
    if low in ("edit my details", "edit", "change my details", "edit details", "change something else"):
        v = await _manage_target(db, session)
        if not v:
            return None
        session["step"] = "edit_pick"
        return [_visitor_card(v, "info"), text("What would you like to change?")], EDIT_PICK_QR

    m = re.match(r"^(edit|change)\s+(name|mobile|phone|number|e-?mail|city|people|guests)$", low)
    if m or (step == "edit_pick" and low in EDIT_FIELDS):
        key = (m.group(2) if m else low).replace("phone", "mobile").replace("number", "mobile")
        field = EDIT_FIELDS.get(key) or EDIT_FIELDS.get(key.replace("-", ""))
        if field:
            session["step"] = "edit_" + field
            quick = qr(("Nagpur", "Nagpur"), ("Other city", "other city")) if field == "city" else (qr(("1", "1"), ("2", "2"), ("3", "3"), ("4", "4")) if field == "numberOfGuests" else qr(("Back", "edit my details")))
            return [text(EDIT_PROMPTS[field])], quick

    # ---- edit: receive the new value
    if step and step.startswith("edit_") and step != "edit_pick":
        field = step[5:]
        v = await _manage_target(db, session)
        if not v:
            return None
        m_ = (message or "").strip()
        value = None
        if field == "fullName":
            if len(m_) < 3 or not re.search(r"[A-Za-z]", m_) or re.search(r"\d{5,}", m_):
                return [text("Please type the full name (letters only).")], qr(("Back", "edit my details"))
            value = re.sub(r"\s+", " ", m_).title() if m_.islower() or m_.isupper() else re.sub(r"\s+", " ", m_)
        elif field == "phone":
            mob = _mobile(m_)
            if not mob:
                return [text("That doesn't look like an Indian mobile number. Please type the 10 digits.")], qr(("Back", "edit my details"))
            value = "+91 " + mob[:5] + " " + mob[5:]
        elif field == "email":
            em = re.sub(r"\s+", "", m_).lower()
            if not is_valid_email(em):
                return [text("Please type a valid e-mail address, e.g. name@example.com.")], qr(("Back", "edit my details"))
            value = em
        elif field == "city":
            if re.match(r"^(other|other city|another city|outside nagpur|not nagpur)\b", low):
                return [text("Please type the name of your city.")], []
            if len(m_) < 2 or len(m_) > 60 or re.search(r"\d{3,}", m_):
                return [text("Please type your city name.")], qr(("Nagpur", "Nagpur"), ("Other city", "other city"))
            value = m_.title() if m_.islower() else m_
        elif field == "numberOfGuests":
            n = re.search(r"\d+", m_)
            val = int(n.group()) if n else None
            if not val or val < 1 or val > 10:
                return [text("How many people, between 1 and 10?")], qr(("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"))
            value = val
        await db.visitors.update_one({"_id": v["_id"]}, {"$set": {field: value, "updatedAt": utcnow(), "editedViaBotAt": utcnow()}})
        v[field] = value
        session["step"] = "edit_pick"
        label = {"fullName": "Name", "phone": "Mobile number", "email": "E-mail", "city": "City", "numberOfGuests": "Number of people"}[field]
        blocks = [text(f"{label} updated."), _visitor_card(v, "ok")]
        if field in ("email", "fullName", "numberOfGuests", "phone"):
            blocks.append(text("Your pass carries these details — shall I send it again?"))
            return blocks, qr(("Yes, resend my pass", "resend my pass"), ("Change something else", "edit my details"), ("Done", "done"))
        return blocks, qr(("Change something else", "edit my details"), ("Resend my pass", "resend my pass"), ("Done", "done"))

    if low in ("yes, resend my pass", "yes"):
        return await manage_flow(db, session, "resend my pass", None)
    return None


def _package_in(low: str) -> dict | None:
    for p in EVENT["stallPackages"]:
        key = p["label"].lower().replace(" stall", "")
        if re.search(r"\b" + re.escape(key) + r"\b", low):
            return p
    return None


async def _finish(db, session, message, blocks, quick, now, tags: list | None = None, unanswered: str | None = None) -> dict:
    blocks = F.translate_blocks(blocks, session.get("lang", "en"))
    session["lastQuick"] = [q.get("send") for q in (quick or [])]
    tags = list(tags or [])
    if session.get("_tag"):
        tags.append(session.pop("_tag"))
    unanswered = unanswered or session.pop("_unanswered", None)
    await F.log_turn(db, session, message, blocks, tags=tags, unanswered=unanswered)
    hist = session.get("history", [])
    if message:
        hist.append({"role": "user", "text": message})
    summary = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text")[:600]
    if summary:
        hist.append({"role": "assistant", "text": summary})
    session["history"] = hist[-HISTORY_KEEP:]
    session["updatedAt"] = now
    session["expiresAt"] = now + SESSION_TTL
    await db.bot_sessions.update_one({"sessionId": session["sessionId"]}, {"$set": {k: v for k, v in session.items() if k != "_id"}}, upsert=True)
    return {"messages": blocks, "quickReplies": quick, "flow": session.get("flow"), "step": session.get("step"),
            "ai": bool(llm_settings()["enabled"] and any(llm_settings()[k] for k in ("emergent_key", "openai_key", "anthropic_key")))}
