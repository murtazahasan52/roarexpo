"""
Extra "Ask ROAR Anything" features (see utils/bot_engine.py for the core):

  exhibitors — check a stall ("is G2 free?") and reserve it for the form,
               stall suggestion by budget / industry, resend the confirmation
               e-mail, e-mail the invoice, set-up & documents, request a callback
  visitors   — QR pass shown in the chat, exhibitor directory search,
               group registration, add-to-calendar + WhatsApp share
  general    — Hindi / Hinglish replies, rating & feedback, chat logs for admins

Every handler returns (blocks, quickReplies) or None when it doesn't apply.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from config.bot_config import BOT
from config.event_config import EVENT, find_stall_package
from models.common import utcnow

# ------------------------------------------------------------------ small helpers (same shapes as bot_engine)

def text(t):
    return {"type": "text", "text": t}


def card(title, rows, tone="info"):
    return {"type": "card", "title": title, "rows": [[k, v] for k, v in rows if v not in (None, "")], "tone": tone}


def links(*items):
    return {"type": "links", "items": list(items)}


def qr(*pairs):
    return [{"label": p, "send": p} if isinstance(p, str) else {"label": p[0], "send": p[1]} for p in pairs]


def digits(s):
    return re.sub(r"\D", "", s or "")


def rupees(rate):
    if rate is None:
        return "On request"
    s = str(int(rate))
    if len(s) <= 3:
        return "₹" + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:]); head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts) + "," + tail


def wa(phone):
    return "https://wa.me/" + digits(phone)


# ------------------------------------------------------------------ language

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
HINGLISH_WORDS = re.compile(r"\b(kya|kaise|kab|kahan|kaha|kitna|kitne|hai|hain|chahiye|karna|karo|mujhe|mera|meri|mere|batao|bataiye|bhai|ji|nahi|nahin|haan|acha|accha|theek|kripya|dhanyavad|shukriya|stall ka|ke liye|kar do|bhejo|milega|hoga)\b")


def detect_lang(message: str, current: str | None) -> str:
    m = (message or "").strip()
    if not m:
        return current or "en"
    if DEVANAGARI.search(m):
        return "hi"
    if HINGLISH_WORDS.search(m.lower()):
        return "hin"
    # an English sentence switches back; a bare number / chip keeps the current language
    if re.search(r"[a-zA-Z]{3,}", m) and len(m.split()) >= 3:
        return "en"
    return current or "en"


# English text (exact match) → Hinglish / Hindi. Static sentences only; dynamic
# ones (with names, numbers) stay English — the cards are bilingual enough.
TR = {
    "hin": {
        "What would you like?": "Aap kya karna chahenge?",
        "Visitor entry is free. I can register you right here in a minute, or you can use the website form.": "Visitor entry free hai. Main aapko yahin ek minute mein register kar sakta hoon, ya aap website form use kar sakte hain.",
        "Great — let's register you as a visitor (it's free). What's your full name?": "Chaliye, aapko visitor register karte hain (free hai). Aapka poora naam?",
        "Your 10-digit mobile number? (Your entry ID card will be linked to it.)": "Aapka 10-digit mobile number? (Entry ID card isi se link hoga.)",
        "Your e-mail address? We'll send the ID card with your entrance QR code there.": "Aapka e-mail address? QR code wala ID card wahin bhejenge.",
        "Are you coming from Nagpur or another city?": "Aap Nagpur se aa rahe hain ya kisi aur city se?",
        "Please type the name of your city.": "Apni city ka naam type kijiye.",
        "How many people will attend including you? (1 – 10)": "Aapko milakar kitne log aayenge? (1 – 10)",
        "Please check your details:": "Apni details check kar lijiye:",
        "Shall I submit this?": "Submit kar doon?",
        "Okay, cancelled. What else can I help with?": "Theek hai, cancel kar diya. Aur kya madad karoon?",
        "You're welcome! Anything else — stalls, rates, dates, or your registration?": "Shukriya! Aur kuch — stalls, rates, dates ya aapka registration?",
        "Sure — type the 10-digit mobile number you registered with and I'll pull up your exhibitor or visitor registration.": "Zaroor — jis 10-digit mobile number se register kiya tha woh type kijiye, main aapka exhibitor/visitor registration dikhata hoon.",
        "Please type the 10-digit mobile number you registered with.": "Jis 10-digit mobile number se register kiya tha woh type kijiye.",
        "Here's how to reach the ROAR Expo team:": "ROAR Expo team se aise sampark karein:",
        "Stall rate card (per stall, for all three days):": "Stall rate card (per stall, teen dino ke liye):",
        "Need the pass again, or want to correct something? Use the buttons below.": "Pass dobara chahiye ya kuch sahi karna hai? Neeche ke buttons use kijiye.",
        "Done. Anything else I can help with?": "Ho gaya. Aur kuch madad chahiye?",
        "What would you like to change?": "Kya badalna chahenge?",
    },
    "hi": {
        "What would you like?": "आप क्या करना चाहेंगे?",
        "Visitor entry is free. I can register you right here in a minute, or you can use the website form.": "विज़िटर एंट्री निःशुल्क है। मैं आपको यहीं एक मिनट में रजिस्टर कर सकता हूँ, या आप वेबसाइट फ़ॉर्म इस्तेमाल कर सकते हैं।",
        "Great — let's register you as a visitor (it's free). What's your full name?": "चलिए, आपको विज़िटर रजिस्टर करते हैं (निःशुल्क)। आपका पूरा नाम?",
        "Your 10-digit mobile number? (Your entry ID card will be linked to it.)": "आपका 10 अंकों का मोबाइल नंबर? (एंट्री ID कार्ड इसी से जुड़ेगा।)",
        "Your e-mail address? We'll send the ID card with your entrance QR code there.": "आपका ई-मेल पता? QR कोड वाला ID कार्ड वहीं भेजेंगे।",
        "Are you coming from Nagpur or another city?": "आप नागपुर से आ रहे हैं या किसी और शहर से?",
        "Please type the name of your city.": "अपने शहर का नाम लिखिए।",
        "How many people will attend including you? (1 – 10)": "आपको मिलाकर कितने लोग आएँगे? (1 – 10)",
        "Please check your details:": "अपनी जानकारी जाँच लीजिए:",
        "Shall I submit this?": "क्या मैं इसे सबमिट कर दूँ?",
        "Okay, cancelled. What else can I help with?": "ठीक है, रद्द कर दिया। और क्या मदद करूँ?",
        "You're welcome! Anything else — stalls, rates, dates, or your registration?": "धन्यवाद! और कुछ — स्टॉल, दरें, तारीख़ या आपका रजिस्ट्रेशन?",
        "Sure — type the 10-digit mobile number you registered with and I'll pull up your exhibitor or visitor registration.": "ज़रूर — जिस 10 अंकों के मोबाइल नंबर से रजिस्टर किया था वह लिखिए, मैं आपका रजिस्ट्रेशन दिखाता हूँ।",
        "Please type the 10-digit mobile number you registered with.": "जिस 10 अंकों के मोबाइल नंबर से रजिस्टर किया था वह लिखिए।",
        "Here's how to reach the ROAR Expo team:": "ROAR Expo टीम से ऐसे संपर्क करें:",
        "Stall rate card (per stall, for all three days):": "स्टॉल रेट कार्ड (प्रति स्टॉल, तीनों दिनों के लिए):",
        "Need the pass again, or want to correct something? Use the buttons below.": "पास दोबारा चाहिए या कुछ सुधारना है? नीचे के बटन इस्तेमाल कीजिए।",
        "Done. Anything else I can help with?": "हो गया। और कुछ मदद चाहिए?",
        "What would you like to change?": "क्या बदलना चाहेंगे?",
    },
}
GREETING = {
    "hin": "Hello! Main ROAR Assistant hoon — ROAR Business Expo Nagpur, {dates}, {venue}. Expo ke baare mein kuch bhi poochiye — main aapko visitor register kar sakta hoon, yahin chat mein stall book kar sakta hoon, mobile number se registration track kar sakta hoon, aur khali stalls, rates aur dates bata sakta hoon. Aap kya karna chahenge?",
    "hi": "नमस्ते! मैं ROAR Assistant हूँ — ROAR Business Expo Nagpur, {dates}, {venue}। एक्सपो के बारे में कुछ भी पूछिए — मैं आपको विज़िटर रजिस्टर कर सकता हूँ, यहीं चैट में स्टॉल बुक कर सकता हूँ, मोबाइल नंबर से रजिस्ट्रेशन ट्रैक कर सकता हूँ, और खाली स्टॉल, दरें और तारीख़ें बता सकता हूँ। आप क्या करना चाहेंगे?",
}
FALLBACK = {
    "hin": "Yeh mujhe samajh nahi aaya. Main visitor registration, exhibitor registration, mobile number se tracking, khali stalls, stall rates, dates/venue aur contact mein madad kar sakta hoon — neeche se chuniye, ya team ko WhatsApp kijiye {phone}.",
    "hi": "यह मुझे समझ नहीं आया। मैं विज़िटर रजिस्ट्रेशन, एग्ज़िबिटर रजिस्ट्रेशन, मोबाइल नंबर से ट्रैकिंग, खाली स्टॉल, स्टॉल रेट, तारीख़/स्थान और संपर्क में मदद कर सकता हूँ — नीचे से चुनिए, या टीम को WhatsApp कीजिए {phone}।",
}


# Hindi / Hinglish words → English keywords, appended to the message before
# intent detection so "स्टॉल के रेट बताइए" or "stall ka daam kya hai" land on the
# same intents as English.
_HINT_WORDS = [
    (r"रेट|दर|कीमत|दाम|शुल्क|daam|kimat|keemat|kitne ka|kitna (hai|hoga|lagega)", "rate"),
    (r"स्टॉल|stall", "stall"),
    (r"खाली|उपलब्ध|khali|available|bacha|bache", "empty available"),
    (r"नक्शा|लेआउट|naksha|layout", "map"),
    (r"तारीख|तारीख़|कब|दिनांक|समय|kab|tareekh|tarikh|samay|time", "date when"),
    (r"कहाँ|कहां|स्थान|पता|जगह|kahan|kaha|jagah|pata|venue", "where venue"),
    (r"रजिस्टर|पंजीकरण|पंजीयन|register|registration", "register"),
    (r"विज़िटर|विजिटर|आगंतुक|दर्शक|visitor|dekhne|ghoomne", "visitor"),
    (r"एग्ज़िबिटर|एग्जिबिटर|प्रदर्शक|exhibitor|stall (lena|book|chahiye|lagana)", "exhibitor stall booking"),
    (r"संपर्क|नंबर|फ़ोन|फोन|ईमेल|sampark|number|phone|email|baat", "contact"),
    (r"स्टेटस|स्थिति|ट्रैक|status|track|check", "status"),
    (r"पास|टिकट|क्यूआर|pass|ticket|qr|id card", "pass"),
    (r"दोबारा|फिर से|वापस|dobara|phir se|wapas|nahi mila|nahi aaya|नहीं मिला|नहीं आया", "resend again"),
    (r"रूबी|महिला|ruby|mahila|women|ladies", "ruby women"),
    (r"स्पॉन्सर|प्रायोजक|sponsor", "sponsor"),
    (r"कॉल|कॉलबैक|call|callback|phone karo", "call back"),
    (r"धन्यवाद|शुक्रिया|dhanyavad|shukriya|thanks", "thanks"),
    (r"रद्द|cancel|band", "cancel"),
    (r"बजट|budget|sasta|sabse sasta|cheap", "budget"),
    (r"बुक|book|booking", "book"),
    (r"कितने लोग|visitors|footfall", "expected visitors"),
]


def normalize_for_intent(message: str) -> str:
    """Returns the message with English hint words appended when it contains
    Hindi / Hinglish vocabulary (the original text is kept for the flows)."""
    low = (message or "").lower()
    if not DEVANAGARI.search(low) and not HINGLISH_WORDS.search(low):
        return message
    hints = [h for pat, h in _HINT_WORDS if re.search(pat, low)]
    return (message + " " + " ".join(hints)) if hints else message


def translate_blocks(blocks: list[dict], lang: str) -> list[dict]:
    if lang not in TR:
        return blocks
    table = TR[lang]
    out = []
    for b in blocks:
        if b.get("type") == "text":
            t = b["text"]
            if t in table:
                b = {"type": "text", "text": table[t]}
            elif t.startswith("Hello! I'm the"):
                b = {"type": "text", "text": GREETING[lang].format(dates=EVENT["eventDatesLabel"], venue=EVENT["venueName"])}
            elif t.startswith("I'm not sure I understood that."):
                b = {"type": "text", "text": FALLBACK[lang].format(phone=BOT["contacts"]["enquiries"]["phone"])}
        out.append(b)
    return out


# ------------------------------------------------------------------ stall codes

_STALL_RE = re.compile(r"\b([A-Za-z]{1,3})\s?-?\s?(\d{1,3})([A-Ba-b])?\b")


def stall_codes_in(message: str) -> list[str]:
    """Candidate stall numbers in free text ("is g2 free", "stall Y 12"). The
    caller verifies them against the stalls collection."""
    out = []
    for m in _STALL_RE.finditer(message or ""):
        code = (m.group(1) + m.group(2) + (m.group(3) or "")).upper()
        if code not in out and not re.fullmatch(r"(AM|PM)\d+", code):
            out.append(code)
    return out[:3]


async def stall_check(db, codes: list[str], low: str):
    from utils.stall_holds import release_expired_holds
    await release_expired_holds(db)
    found = []
    for code in codes:
        s = await db.stalls.find_one({"stallNumber": code})
        if s:
            found.append(s)
    if not found:
        return None
    blocks, quick = [], []
    for s in found:
        p = find_stall_package(s.get("packageCode") or "") or {}
        status = s.get("status")
        owner = None
        if status == "booked" and s.get("bookedBy"):
            e = await db.exhibitors.find_one({"_id": s["bookedBy"]}, {"companyName": 1})
            owner = (e or {}).get("companyName")
        label = {"available": "Available ✅", "held": "Reserved right now (pending confirmation)", "booked": "Booked" + (f" — {owner}" if owner else ""), "blocked": "Not available"}.get(status, status)
        tone = {"available": "ok", "held": "warn", "booked": "muted", "blocked": "muted"}.get(status, "info")
        admin_only = bool(s.get("adminOnly") or p.get("adminOnly"))
        if admin_only and status == "available":
            label = "Available — allotted by the organising team (not booked online)"
            tone = "warn"
        blocks.append(card(f"Stall {s['stallNumber']}", [
            ("Status", label), ("Category", p.get("label")), ("Size", s.get("size") or None), ("Rate", rupees(s.get("rate"))),
            ("Includes", p.get("inclusions")), ("Eligibility", p.get("eligibility")),
        ], tone))
        if status == "available" and not admin_only:
            quick.append((f"Reserve {s['stallNumber']} for 15 min", f"reserve {s['stallNumber']}"))
        elif status == "available" and admin_only:
            c = BOT["contacts"]["ruby"] if (s.get("packageCode") or "").startswith("ruby") or "ruby" in (p.get("label") or "").lower() else BOT["contacts"]["stalls"]
            blocks.append(text(f"{s['stallNumber']} is allotted directly by the organising team. Contact {c['name']} on {c['phone']} to book it."))
            quick.append((f"WhatsApp {c['name'].split()[0]}", f"contact"))
    if any(s.get("status") == "available" and not (s.get("adminOnly") or (find_stall_package(s.get("packageCode") or "") or {}).get("adminOnly")) for s in found):
        blocks.append(text("I can reserve it for 15 minutes while you fill the exhibitor form — tap Reserve and the form opens with the stall already selected."))
    else:
        blocks.append(text("Want me to show the stalls that are still free in that category?"))
        for s in found:
            p = find_stall_package(s.get("packageCode") or "")
            if p:
                quick.append((f"Empty {p['label'].replace(' Stall', '')} stalls", f"which {p['label'].lower().replace(' stall', '')} stalls are available"))
    quick += [("Empty stalls map", "empty stalls"), ("Stall rates", "stall rates")]
    return blocks, qr(*quick)


async def reserve_stall(db, session, code: str):
    from utils.stall_holds import hold_stall, HOLD_MINUTES
    pre = await db.stalls.find_one({"stallNumber": code})
    if pre and (pre.get("adminOnly") or (find_stall_package(pre.get("packageCode") or "") or {}).get("adminOnly")):
        c = BOT["contacts"]["ruby"] if (pre.get("packageCode") or "").startswith("ruby") else BOT["contacts"]["stalls"]
        return [text(f"{code} is allotted by the organising team and can't be reserved online. Contact {c['name']} on {c['phone']}.")], \
               qr(("Contact", "contact"), ("Empty stalls map", "empty stalls"))
    stall, token, expires = await hold_stall(db, code, (session.get("data") or {}).get("holdToken"))
    if not stall:
        s = await db.stalls.find_one({"stallNumber": code})
        if not s:
            return [text(f"I couldn't find a stall numbered {code}. Check the number on the map.")], qr(("Empty stalls map", "empty stalls"))
        return [text(f"Sorry — {code} was just taken by someone else. Pick another available stall.")], qr(("Empty stalls map", "empty stalls"), ("Stall rates", "stall rates"))
    session.setdefault("data", {})["holdToken"] = token
    session["data"]["holdStall"] = code
    p = find_stall_package(stall.get("packageCode") or "") or {}
    until = expires.strftime("%I:%M %p").lstrip("0")
    url = (f"/register/exhibitor?stall={quote(code)}&pkg={quote(stall.get('packageCode') or '')}&hold={quote(token)}"
           f"&exp={quote(expires.isoformat())}&min={HOLD_MINUTES}")
    return ([text(f"{code} is reserved for you for {HOLD_MINUTES} minutes (until {until}). Nobody else can pick it while you complete the form."),
             card("Reserved", [("Stall", code), ("Category", p.get("label")), ("Rate", rupees(stall.get("rate"))), ("Reserved until", until)], "ok"),
             links({"label": f"Continue on the website form with {code}", "to": url}),
             text("If you leave the form unfinished, the stall is released automatically when the timer runs out.")],
            qr(("Book it here in chat", "book a stall in chat"), ("Release the stall", f"release {code}"), ("Stall rates", "stall rates")))


async def release_reserved(db, session, code: str | None):
    from utils.stall_holds import release_hold
    token = (session.get("data") or {}).get("holdToken")
    if not token:
        return [text("You don't have a stall reserved through this chat.")], qr(("Empty stalls map", "empty stalls"))
    ok = await release_hold(db, token)
    session["data"].pop("holdToken", None)
    held = session["data"].pop("holdStall", None)
    return [text(f"{held or 'The stall'} is released and open to others again." if ok else "That reservation had already ended.")], qr(("Empty stalls map", "empty stalls"), ("Stall rates", "stall rates"))


# ------------------------------------------------------------------ budget / industry suggestion

_AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:[.,]\d+)*)\s*(lakhs?|lacs?|lakh|lac|l|k|thousand|hazaar|hazar)?\b", re.I)


def parse_amount(low: str) -> int | None:
    best = None
    for m in _AMOUNT_RE.finditer(low):
        raw = m.group(1).replace(",", "")
        unit = (m.group(2) or "").lower()
        try:
            val = float(raw)
        except ValueError:
            continue
        if unit in ("lakh", "lakhs", "lac", "lacs", "l"):
            val *= 100000
        elif unit in ("k", "thousand", "hazaar", "hazar"):
            val *= 1000
        if val < 1000:  # "2 stalls", "10 days" — not money
            continue
        best = max(best or 0, int(val))
    return best


def industry_in(low: str) -> dict | None:
    for c in EVENT["categories"]:
        words = [w for w in re.split(r"[\s/&]+", c["label"].lower()) if len(w) > 3]
        if any(re.search(r"\b" + re.escape(w), low) for w in words):
            return c
    return None


async def suggest_stalls(db, low: str):
    from utils.bot_engine import available_stalls, map_url
    amount = parse_amount(low)
    ind = industry_in(low)
    free, counts, _ = await available_stalls(db)
    pick = [p for p in EVENT["stallPackages"] if p.get("hasStallPicker") and not p.get("adminOnly")]
    if amount:
        fits = [p for p in pick if p.get("rate") and p["rate"] <= amount]
        if not fits:
            cheapest = min(pick, key=lambda p: p["rate"])
            blocks = [text(f"Stalls start at {rupees(cheapest['rate'])} ({cheapest['label']}" + (", for women entrepreneurs" if cheapest["code"] == "ruby" else "") + f"). A budget of {rupees(amount)} is below that — the team can still advise you on options."),
                      links({"label": "WhatsApp " + BOT["contacts"]["stalls"]["name"].split()[0], "href": wa(BOT["contacts"]["stalls"]["phone"])})]
            return blocks, qr(("Stall rates", "stall rates"), ("Contact", "contact"))
        fits.sort(key=lambda p: -p["rate"])
        rows = []
        for p in fits:
            c = next((x for x in counts if x["code"] == p["code"]), None)
            rows.append({"code": p["code"], "label": p["label"], "rate": rupees(p["rate"]), "count": p.get("stallCount") or "",
                         "available": c["available"] if c else None, "note": p.get("inclusions", "")})
        codes = {p["code"] for p in fits}
        best = fits[0]
        blocks = [text(f"Within {rupees(amount)} you can take " + ", ".join(p["label"] for p in fits) + f". The {best['label']} ({rupees(best['rate'])}) gets you the best location for that budget" + (f" — {ind['label']} exhibitors usually do well with it." if ind else ".")),
                  {"type": "rates", "rows": rows},
                  text("Green dots show the free stalls in those categories:"),
                  {"type": "map", "mapUrl": await map_url(db), "stalls": [s for s in free if s["c"] in codes],
                   "counts": [{"code": c["code"], "label": c["label"], "available": c["available"], "total": c["total"], "numbers": c["numbers"]} for c in counts if c["code"] in codes]},
                  links({"label": "Book a stall", "to": "/register/exhibitor", "primary": True})]
        quick = [(f"Empty {p['label'].replace(' Stall', '')} stalls", f"which {p['label'].lower().replace(' stall', '')} stalls are available") for p in fits[:3]]
        return blocks, qr(*quick, ("Contact", "contact"))
    # industry only / no amount
    blocks = []
    if ind:
        blocks.append(text(f"{ind['label']} is one of the 16 industries at the expo — you choose it on the registration form. For the stall itself, tell me your budget (e.g. \"under 1 lakh\" or \"around 50,000\") and I'll point you to the right category and the stalls still free."))
    else:
        blocks.append(text("Tell me your budget — e.g. \"under 1 lakh\", \"around ₹50,000\" — and I'll suggest the stall category and show which stalls are still free."))
    blocks.append(text("Rate card: " + " · ".join(f"{p['label'].replace(' Stall', '')} {rupees(p['rate'])}" for p in pick)))
    return blocks, qr(("Under ₹60,000", "stall under 60000"), ("Around ₹1 lakh", "stall around 1 lakh"), ("Up to ₹5 lakh", "stall up to 5 lakh"), ("Stall rates", "stall rates"))


# ------------------------------------------------------------------ exhibitor directory

def category_in(low: str) -> dict | None:
    return industry_in(low)


async def directory_search(db, low: str):
    from utils.bot_engine import map_url
    cat = category_in(low)
    name = None
    m = re.search(r"(?:stall of|where is|find|search|company|firm)\s+(.+)$", low)
    if m:
        name = m.group(1).strip(" ?.'\"")
        name = re.sub(r"^(the|a)\s+", "", name)
        name = re.sub(r"\b(stall|booth|company|firm|exhibitor)\b.*$", "", name).strip()
    query = {"status": "confirmed"}
    if cat:
        query["category"] = cat["key"]
    elif name and len(name) >= 3:
        query["companyName"] = {"$regex": re.escape(name), "$options": "i"}
    docs = await db.exhibitors.find(query, {"companyName": 1, "category": 1, "stallNumber": 1, "city": 1, "productsServices": 1}).sort("companyName", 1).to_list(length=40)
    total_confirmed = await db.exhibitors.count_documents({"status": "confirmed"})
    labels = {c["key"]: c["label"] for c in EVENT["categories"]}
    if not docs:
        what = f"in {cat['label']}" if cat else (f"matching “{name}”" if name else "")
        blocks = [text(f"No confirmed exhibitor {what} yet — {total_confirmed} exhibitors are confirmed so far and the list grows every week. " if total_confirmed else "The exhibitor list is being confirmed — check back soon. ")]
        if cat:
            blocks[0]["text"] += "Thinking of exhibiting in this industry yourself?"
            return blocks, qr(("Exhibitor registration", "exhibitor registration"), ("Stall rates", "stall rates"), ("Main menu", "menu"))
        return blocks, qr(("Which industries?", "industries"), ("Live stall map", "empty stalls"), ("Main menu", "menu"))
    blocks = [text((f"Confirmed exhibitors in {cat['label']}" if cat else (f"Exhibitors matching “{name}”" if name else "Confirmed exhibitors")) + f" ({len(docs)}):")]
    for e in docs[:8]:
        blocks.append(card(e.get("companyName", ""), [("Industry", labels.get(e.get("category"), e.get("category"))), ("Stall", e.get("stallNumber") or "To be allotted"),
                                                       ("City", e.get("city")), ("Products", (e.get("productsServices") or "")[:90] or None)], "info"))
    if len(docs) > 8:
        blocks.append(text("… and " + ", ".join(e.get("companyName", "") for e in docs[8:]) + "."))
    nums = [e["stallNumber"] for e in docs if e.get("stallNumber")]
    if nums:
        stalls = await db.stalls.find({"stallNumber": {"$in": nums}}, {"stallNumber": 1, "packageCode": 1, "mapX": 1, "mapY": 1}).to_list(length=None)
        pins = [{"n": s["stallNumber"], "x": round(float(s["mapX"]), 2), "y": round(float(s["mapY"]), 2), "c": s.get("packageCode")} for s in stalls if s.get("mapX") is not None]
        if pins:
            blocks.append({"type": "map", "mapUrl": await map_url(db), "stalls": pins, "counts": [], "label": f"{len(pins)} stall{'s' if len(pins) != 1 else ''} marked"})
    blocks.append(links({"label": "Full stall directory", "to": "/stalls"}))
    return blocks, qr(("Which industries?", "industries"), ("Register as visitor", "register as visitor"), ("Main menu", "menu"))


# ------------------------------------------------------------------ calendar + share

SHARE_TEXT = ("ROAR Business Expo Nagpur 2027 — {dates} at {venue}. 150+ stalls, 16+ industries, free visitor entry. "
              "Register in a minute at www.roarexpo.com (tap “Ask ROAR Anything” at the bottom-right).")


def calendar_blocks():
    share = SHARE_TEXT.format(dates=EVENT["eventDatesLabel"], venue=EVENT["venueName"])
    return [text("Save the dates and bring a friend:"),
            links({"label": "Add to calendar (.ics)", "api": "/public/event.ics", "download": "ROAR-Expo-2027.ics"},
                  {"label": "Directions (Google Maps)", "href": EVENT["venueMapUrl"]},
                  {"label": "Invite a friend on WhatsApp", "href": "https://wa.me/?text=" + quote(share)})]


def event_ics() -> str:
    start = EVENT["eventStartDateISO"].replace("-", "")
    from datetime import date, timedelta
    y, m, d = (int(x) for x in EVENT["eventEndDateISO"].split("-"))
    end = (date(y, m, d) + timedelta(days=1)).strftime("%Y%m%d")  # all-day events end the day after
    desc = f"{EVENT['eventName']} — {BOT['headline']['stalls']} stalls, {BOT['headline']['industries']} industries. {BOT['showTimings']}. www.roarexpo.com"
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ROAR Expo//roarexpo.com//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "BEGIN:VEVENT", f"UID:roar-expo-2027@roarexpo.com", f"DTSTAMP:{utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{start}", f"DTEND;VALUE=DATE:{end}",
        f"SUMMARY:{EVENT['eventName']}", f"LOCATION:{EVENT['venueAddress']}", f"DESCRIPTION:{desc}", f"URL:https://www.roarexpo.com",
        "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", f"DESCRIPTION:{EVENT['eventName']} starts tomorrow", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR", "",
    ])


# ------------------------------------------------------------------ visitor QR pass in the chat

async def qr_pass_blocks(db, visitor: dict):
    try:
        from utils.id_card_image import build_visitor_id_card_png
        idc = await build_visitor_id_card_png(visitor)
    except Exception as err:  # noqa: BLE001
        print("[bot] id card render failed:", err)
        return [text("I couldn't draw your ID card just now — use “Resend my pass” to get it by e-mail, or show your registration ID at the gate: " + visitor.get("registrationCode", ""))], \
               qr(("Resend my pass", "resend my pass"), ("Main menu", "menu"))
    url = idc["public_url"]
    return ([text(f"Here's your entrance pass, {visitor.get('fullName', '').split(' ')[0]} — show this QR at the gate."),
             {"type": "image", "api": url, "alt": f"ROAR Expo ID card {visitor.get('registrationCode')}", "download": f"ROAR-Expo-ID-Card-{visitor.get('registrationCode')}.png"},
             text("Tip: take a screenshot, or tap the card to save it on your phone.")],
            qr(("Resend my pass by e-mail", "resend my pass"), ("Add to calendar", "add to calendar"), ("Main menu", "menu")))


# ------------------------------------------------------------------ exhibitor self-service

async def exhibitor_action(db, exhibitor: dict, action: str):
    from utils.mailer import send_mail
    from utils.email_templates import exhibitor_email_html, exhibitor_approved_email_html
    status = exhibitor.get("status")
    if action == "resend_confirmation":
        try:
            if status == "confirmed":
                await send_mail(to=exhibitor["email"], subject=f"Stall Confirmed — ROAR Expo ({exhibitor['registrationCode']})", html=exhibitor_approved_email_html(exhibitor))
            else:
                await send_mail(to=exhibitor["email"], subject=f"Stall Registration Received — {EVENT['eventName']}", html=exhibitor_email_html(exhibitor))
            await db.exhibitors.update_one({"_id": exhibitor["_id"]}, {"$set": {"emailSent": True, "confirmationResentAt": utcnow()}})
            what = "confirmation" if status == "confirmed" else "registration acknowledgement"
            return [text(f"Done — your {what} e-mail has been sent again to {exhibitor['email']}. Check spam/promotions if it doesn't show up in a few minutes.")], \
                   qr(("Set-up & documents", "setup and documents"), ("E-mail my invoice", "email my invoice"), ("Main menu", "menu"))
        except Exception as err:  # noqa: BLE001
            return [text(f"Sorry — the e-mail could not be sent right now ({err}). Please try again later or WhatsApp {BOT['contacts']['stalls']['name']} on {BOT['contacts']['stalls']['phone']}.")], \
                   qr(("Try again", "resend my confirmation"), ("Main menu", "menu"))
    if action == "invoice":
        if status != "confirmed":
            return [text("Your invoice is issued once the organising team confirms your stall — your registration is still " + ("pending confirmation." if status == "pending" else f"{status}."))], \
                   qr(("Resend my confirmation", "resend my confirmation"), ("Contact", "contact"), ("Main menu", "menu"))
        try:
            from utils.invoice import build_exhibitor_invoice_pdf
            pdf = build_exhibitor_invoice_pdf(exhibitor)
            await send_mail(to=exhibitor["email"], subject=f"Invoice — ROAR Expo stall {exhibitor.get('stallNumber') or ''} ({exhibitor['registrationCode']})".replace("  ", " "),
                            html=f"<p>Dear {exhibitor.get('contactPerson', '')},</p><p>Please find attached the invoice for your stall at {EVENT['eventName']}.</p><p>— ROAR Expo organising team</p>",
                            attachments=[{"filename": f"ROAR-Expo-Invoice-{exhibitor['registrationCode']}.pdf", "content": pdf, "contentType": "application/pdf"}])
            await db.exhibitors.update_one({"_id": exhibitor["_id"]}, {"$set": {"invoiceEmailedAt": utcnow()}})
            return [text(f"Your invoice has been e-mailed to {exhibitor['email']}.")], qr(("Set-up & documents", "setup and documents"), ("Main menu", "menu"))
        except Exception as err:  # noqa: BLE001
            return [text(f"Sorry — the invoice could not be sent right now ({err}). The team can send it: {BOT['contacts']['stalls']['name']} {BOT['contacts']['stalls']['phone']}.")], \
                   qr(("Try again", "email my invoice"), ("Contact", "contact"))
    return None


# ------------------------------------------------------------------ callback request

CALLBACK_TOPICS = [("Stall booking", "stall booking"), ("Sponsorship", "sponsorship"), ("Visitor pass", "visitor pass"), ("Something else", "something else")]


async def callback_flow(db, session, message: str):
    """name → mobile → topic → saved as an enquiry + organisers e-mailed."""
    from utils.bot_engine import _mobile, is_valid_email  # noqa
    data = session.setdefault("data", {})
    step = session.get("step") or "name"
    m = (message or "").strip()
    low = m.lower()
    if step == "name":
        if len(m) < 3 or not re.search(r"[A-Za-z]", m) or re.search(r"\d{5,}", m):
            return [text("Your name, please?")], qr(("Cancel", "cancel")), False
        data["name"] = m.title() if m.islower() or m.isupper() else m
        session["step"] = "mobile"
        return [text("Which number should the team call you on? (10-digit mobile)")], qr(("Cancel", "cancel")), False
    if step == "mobile":
        mob = _mobile(m)
        if not mob:
            return [text("Please type a 10-digit Indian mobile number.")], qr(("Cancel", "cancel")), False
        data["mobile"] = "+91 " + mob[:5] + " " + mob[5:]
        session["step"] = "topic"
        return [text("What is it about?")], qr(*CALLBACK_TOPICS, ("Cancel", "cancel")), False
    if step == "topic":
        if len(m) < 3:
            return [text("A few words about what you need — stall booking, sponsorship, visitor pass, or something else?")], qr(*CALLBACK_TOPICS, ("Cancel", "cancel")), False
        data["topic"] = m
        session["step"] = "when"
        return [text("When is a good time to call?")], qr(("Anytime", "anytime"), ("Morning", "morning 10–1"), ("Afternoon", "afternoon 1–5"), ("Evening", "evening 5–8")), False
    if step == "when":
        data["when"] = m or "anytime"
        from utils.notify import notify_organizers
        details = f"CALLBACK REQUEST via Ask ROAR Anything — topic: {data['topic']}; preferred time: {data['when']}."
        doc = {"name": data["name"], "email": "", "mobile": data["mobile"], "details": details, "status": "new", "handledAt": None,
               "emailSent": False, "emailError": "", "source": "bot-callback", "createdAt": utcnow(), "updatedAt": utcnow()}
        res = await db.enquiries.insert_one(doc)
        doc["_id"] = res.inserted_id
        try:
            await notify_organizers(kind="enquiry", subject=f"Callback request: {data['name']} — {data['topic']}",
                                    html=f"<p><strong>{data['name']}</strong> asked for a call back via the website chat.</p><p>Mobile: {data['mobile']}<br>Topic: {data['topic']}<br>Preferred time: {data['when']}</p>")
            await db.enquiries.update_one({"_id": doc["_id"]}, {"$set": {"emailSent": True}})
        except Exception as err:  # noqa: BLE001
            await db.enquiries.update_one({"_id": doc["_id"]}, {"$set": {"emailError": str(err)}})
        session["flow"], session["step"], session["data"] = None, None, {}
        session["_tag"] = "callback"
        return ([text(f"Noted, {data['name'].split()[0]} — the team will call you on {data['mobile']} ({data['when']}) about {data['topic']}."),
                 card("Callback request", [("Name", data["name"]), ("Mobile", data["mobile"]), ("Topic", data["topic"]), ("Time", data["when"])], "ok"),
                 text(f"Need it sooner? WhatsApp {BOT['contacts']['stalls']['name']} on {BOT['contacts']['stalls']['phone']}.")],
                None, True)
    return None


# ------------------------------------------------------------------ feedback

RATING_QR = qr(("⭐ 1", "rating 1"), ("⭐⭐ 2", "rating 2"), ("⭐⭐⭐ 3", "rating 3"), ("⭐⭐⭐⭐ 4", "rating 4"), ("⭐⭐⭐⭐⭐ 5", "rating 5"), ("Skip", "skip"))


async def feedback_flow(db, session, message: str):
    data = session.setdefault("data", {})
    step = session.get("step") or "rating"
    low = (message or "").strip().lower()
    if low in ("skip", "no", "nahi", "cancel"):
        session["flow"], session["step"], session["data"] = None, None, {}
        return [text("No problem — thanks for chatting with ROAR!")], None, True
    if step == "rating":
        m = re.search(r"[1-5]", low)
        if not m:
            return [text("How would you rate this chat, 1 to 5?")], RATING_QR, False
        data["rating"] = int(m.group())
        session["step"] = "comment"
        return [text("Thank you! Anything we could do better? (type a comment, or Skip)")], qr(("Skip", "skip")), False
    if step == "comment":
        data["comment"] = (message or "").strip()[:500]
        await db.bot_feedback.insert_one({"sessionId": session["sessionId"], "rating": data["rating"], "comment": data["comment"], "lang": session.get("lang", "en"), "createdAt": utcnow()})
        await db.bot_logs.update_one({"sessionId": session["sessionId"]}, {"$set": {"rating": data["rating"], "comment": data["comment"]}}, upsert=True)
        session["flow"], session["step"], session["data"] = None, None, {}
        session["_tag"] = "rated"
        return [text("Thanks — your feedback reached the organising team. See you at the expo!")], None, True
    return None


# ------------------------------------------------------------------ chat logs (for the admin "Chats" tab)

async def log_turn(db, session: dict, user_text: str, blocks: list[dict], tags: list[str] | None = None, unanswered: str | None = None):
    now = utcnow()
    msgs = []
    if user_text:
        msgs.append({"r": "u", "t": user_text[:500], "at": now})
    bot_text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    kinds = [b["type"] for b in blocks if b.get("type") not in ("text",)]
    if bot_text or kinds:
        msgs.append({"r": "b", "t": (bot_text[:700] + (f" [{', '.join(kinds)}]" if kinds else "")).strip(), "at": now})
    update = {
        "$set": {"updatedAt": now, "lang": session.get("lang", "en"), "lastUserText": user_text[:200] if user_text else None, "flow": session.get("flow")},
        "$setOnInsert": {"createdAt": now, "sessionId": session["sessionId"]},
        "$inc": {"count": 1 if user_text else 0},
        "$push": {"messages": {"$each": msgs, "$slice": -300}},
    }
    if tags:
        update["$addToSet"] = {"tags": {"$each": tags}}
    if unanswered:
        update["$push"]["unanswered"] = {"$each": [unanswered[:300]], "$slice": -50}
    try:
        # a page view that only shows the greeting is not a chat yet
        await db.bot_logs.update_one({"sessionId": session["sessionId"]}, update, upsert=bool(user_text))
    except Exception as err:  # noqa: BLE001
        print("[bot] log write failed:", err)
