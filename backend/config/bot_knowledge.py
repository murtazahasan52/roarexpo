"""
"Ask ROAR Anything" — what the website says, as answers the chat can give.

Every entry is one topic from www.roarexpo.com (home page sections, Why Nagpur,
the stall rate card, registration pages, contact) written as a short chat
answer. The bot matches a visitor's question against `keywords` and replies
with `answer` plus the links and follow-up chips listed. The same text is
also the AI model's only source of facts when an AI key is configured.

Edit the wording freely — no logic lives here. Anything that changes with
the event (dates, venue, rates, deadlines, contacts) is read from
config/event_config.py and config/bot_config.py at answer time, so keep those
two files as the single source and don't repeat figures here.

keywords: phrases matched as whole words, lower case. A multi-word phrase
          scores more than a single word, so put the distinctive phrases first.
"""
import re

from config.bot_config import BOT
from config.event_config import EVENT


def _clean(s: str) -> str:
    # drop editor notes left in the config, e.g. "(Update this policy …)"
    return re.sub(r"\s*\((?:update|todo|placeholder)[^)]*\)", "", s or "", flags=re.I).strip()


def _rupee(n):
    if n is None:
        return "on request"
    s = str(int(n))
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


def _contacts():
    c = BOT["contacts"]
    return c["stalls"], c["ruby"], c["enquiries"], c["emails"]


def entries() -> list[dict]:
    """Built on every call so config edits show up without a restart."""
    stalls_c, ruby_c, help_c, emails = _contacts()
    ins = EVENT.get("exhibitorInstructions", {})
    dates = EVENT["eventDatesLabel"]
    hijri = EVENT.get("eventDatesHijri", "1st – 3rd Shaban ul Karim 1448H")
    venue = EVENT["venueName"]
    deadlines = EVENT.get("registrationDeadlines", {})
    pkgs = [p for p in EVENT["stallPackages"] if p.get("hasStallPicker")]
    sizes = "; ".join(f"{p['label']} {p.get('size', '')} ({_rupee(p.get('rate'))})".replace(" ()", "") for p in pkgs)
    ruby = next((p for p in EVENT["stallPackages"] if p["code"] == "ruby"), {})

    return [
        {
            "id": "roar-meaning",
            "title": "What ROAR stands for",
            "keywords": ["what does roar stand for", "roar stands for", "roar means", "meaning of roar", "full form", "why roar",
                         "rose", "orange", "tiger", "emblem", "logo meaning", "we are ready", "roaring", "rise", "ambition", "reach"],
            "answer": ("ROAR stands for Rise • Opportunity • Ambition • Reach. The emblem tells the story: the Rose represents "
                       "women entrepreneurs' strength, creativity, resilience and the ability to lead; the Orange represents "
                       "Nagpur, the Orange City — energy, positivity and growth; and the Tiger represents confidence, leadership "
                       "and the courage to take bold steps. Our message: Nagpur, roaring aloud and clear — \"We are ready\"."),
            "links": [{"label": "Read on the home page", "to": "/"}],
            "chips": [("About the expo", "about the expo"), ("Why exhibit?", "why should i exhibit"), ("Why visit?", "why should i visit")],
        },
        {
            "id": "about",
            "title": "About the Expo",
            "keywords": ["about the expo", "about roar", "what is roar", "what is this expo", "tell me about", "purpose", "aim",
                         "objective", "vision", "mumineen", "bohra business", "business platform", "overview", "introduction"],
            "answer": ("ROAR Business Expo Nagpur 2027 brings together Dawoodi Bohra businessmen, entrepreneurs, manufacturers, "
                       "traders, professionals and service providers from across India under one roof — " + dates + " at " + venue + ". "
                       "With 150+ stalls and visitors from all communities, it opens doors to new customers, suppliers, "
                       "distributors, dealers and partners, and gives young and emerging entrepreneurs market exposure next to "
                       "established businesses. It is built for networking, sourcing, dealership and distribution, strategic "
                       "partnerships and long-term commercial relationships — and, with Nagpur's central location, a bridge "
                       "between North, South, East, West and Central India."),
            "links": [{"label": "About the Expo", "to": "/#about"}],
            "chips": [("What does ROAR mean?", "what does roar stand for"), ("Who can exhibit?", "who can exhibit"), ("Dates & venue", "dates and venue")],
        },
        {
            "id": "who-can",
            "title": "Who can exhibit or visit",
            "keywords": ["who can exhibit", "who can participate", "who can visit", "who can come", "can anyone", "non bohra",
                         "other community", "all communities", "eligible", "eligibility", "open to all", "only for bohra", "public"],
            "answer": ("Exhibitors: Dawoodi Bohra businessmen, entrepreneurs, manufacturers, traders, professionals and service "
                       "providers from across India — " + (ruby.get("eligibility") or BOT["ruby"]) + " "
                       "Visitors: open to everyone, from all communities — entry is free with an online registration."),
            "links": [{"label": "Register as exhibitor", "to": "/register/exhibitor"}, {"label": "Register as visitor", "to": "/register/visitor"}],
            "chips": [("Book a stall in chat", "book a stall in chat"), ("Register as visitor", "register as visitor")],
        },
        {
            "id": "why-exhibit",
            "title": "Why exhibit",
            "keywords": ["why exhibit", "why should i exhibit", "benefit of exhibiting", "benefits for exhibitors", "why take a stall",
                         "why book a stall", "what will i get", "leads", "buyers", "worth it", "advantage", "roi"],
            "answer": ("Put your business in front of the right people: meet qualified buyers, distributors and decision-makers "
                       "across 16+ industries; showcase your brand with a dedicated stall, fascia signage and a listing across all "
                       "expo marketing; and generate real leads over three full days of footfall. Nagpur's central location brings "
                       "buyers, dealers and distributors in from all four regions, and keeps travel and logistics simple for your "
                       "team and your goods."),
            "links": [{"label": "Register as exhibitor", "to": "/register/exhibitor", "primary": True}],
            "chips": [("Book a stall in chat", "book a stall in chat"), ("Stall rates", "stall rates"), ("Empty stalls map", "empty stalls")],
        },
        {
            "id": "why-visit",
            "title": "Why visit",
            "keywords": ["why visit", "why should i visit", "why should i come", "benefit for visitors", "what is there for visitors",
                         "what can i see", "what will i see", "worth visiting", "things to see"],
            "answer": ("Discover 150+ stalls under one roof — industrial machinery to jewellery, food, healthcare and travel. Meet "
                       "manufacturers, traders and service providers face to face, discover new products and services, and connect "
                       "with Nagpur's business community. Entry is free: register once and your personal invitation card with a QR "
                       "code comes by e-mail — just show it at the gate."),
            "links": [{"label": "Register as visitor", "to": "/register/visitor", "primary": True}],
            "chips": [("Register in chat", "register as visitor"), ("Industries", "industries"), ("Who is exhibiting?", "who is exhibiting")],
        },
        {
            "id": "entry",
            "title": "Entry, pass and ID card",
            "keywords": ["entry fee", "entry free", "is entry free", "ticket price", "ticket cost", "visitor fee", "visitor charges",
                         "pass cost", "pay for entry", "free entry", "entry pass", "id card", "qr code", "invitation card", "gate",
                         "how to enter", "need a pass", "walk in", "on the spot", "spot registration"],
            "answer": ("Visitor entry is free. Register online (or right here in the chat) and you get a personal ID card with a QR "
                       "code by e-mail — and on WhatsApp — to show at the entrance for a quick check-in. Bringing family or "
                       "colleagues? Each person can be registered on the same mobile number. Walk-ins can register at the entrance "
                       "by scanning the Entrance QR. Visitor registration closes on " + deadlines.get("visitor", "the day before the expo") + "."),
            "links": [{"label": "Register as visitor", "to": "/register/visitor"}],
            "chips": [("Register in chat", "register as visitor"), ("Show my QR pass", "show my qr pass"), ("Didn't get my pass", "i did not get my pass")],
        },
        {
            "id": "why-nagpur",
            "title": "Why Nagpur",
            "keywords": ["why nagpur", "why in nagpur", "about nagpur", "zero mile", "centre of india", "center of india", "heart of india",
                         "orange city", "central india", "gateway"],
            "answer": ("Six reasons: geographic centrality (the Zero Mile Stone marks Nagpur as India's centre, a common meeting point "
                       "for every region); connectivity by international airport, a major railway junction and national highways; a "
                       "growing ecosystem of Central India's industries, traders and service businesses; strong commercial potential "
                       "and an active entrepreneurial community; growing infrastructure in logistics, industrial areas and roads; "
                       "and a natural gateway for businesses from the North, South, East and West to meet new markets."),
            "links": [{"label": "Why Nagpur", "to": "/why-nagpur"}],
            "chips": [("How to reach", "how to reach nagpur"), ("Where is the venue?", "venue"), ("Dates", "dates")],
        },
        {
            "id": "getting-there",
            "title": "Getting there",
            "keywords": ["how to reach", "how do i reach", "how to come", "getting there", "airport", "flight", "fly", "train", "railway",
                         "station", "nagpur junction", "bus", "road", "highway", "nh 44", "nh-44", "by car", "travel", "directions", "distance"],
            "answer": ("By air: Dr. Babasaheb Ambedkar International Airport, Nagpur, with direct flights from India's major cities. "
                       "By rail: Nagpur Junction, a major stop on the north–south and east–west trunk routes. By road: national "
                       "highways NH-44 (north–south) and NH-53 (east–west) meet at Nagpur. The venue is " + venue + "."),
            "links": [{"label": "Directions (Google Maps)", "href": EVENT["venueMapUrl"]}, {"label": "Why Nagpur", "to": "/why-nagpur"}],
            "chips": [("Dates & timings", "dates and venue"), ("Add to calendar", "add to calendar")],
        },
        {
            "id": "timings",
            "title": "Show timings",
            "keywords": ["timing", "timings", "what time", "open time", "opening time", "closing time", "hours", "till what time",
                         "how late", "morning", "evening", "schedule"],
            "answer": ("The expo runs " + dates + " (" + hijri + "), " + BOT["showTimings"] + ", at " + venue + ". "
                       "Exhibitor set-up: " + ins.get("setupWindow", "before the opening day") + "; move-out: " + ins.get("moveOutWindow", "after the last day") + "."),
            "links": [{"label": "Add to calendar (.ics)", "api": "/public/event.ics", "download": "ROAR-Expo-2027.ics"}],
            "chips": [("How to reach", "how to reach nagpur"), ("Register as visitor", "register as visitor")],
        },
        {
            "id": "what-to-expect",
            "title": "What to expect",
            "keywords": ["what to expect", "what happens", "programme", "program", "agenda", "events", "keynote", "speaker", "speakers",
                         "workshop", "workshops", "seminar", "session", "networking", "activities", "stage", "inauguration"],
            "answer": ("Three days of exhibition (150+ stalls across 16+ industries), networking with entrepreneurs, traders and industry "
                       "representatives, keynote speakers and business leaders, interactive workshops, plus a Food Court and a Play Zone "
                       "for families. The detailed programme will be announced closer to the dates — follow www.roarexpo.com."),
            "links": [{"label": "Home page", "to": "/"}],
            "chips": [("Industries", "industries"), ("Food court & play zone", "food court and play zone")],
        },
        {
            "id": "food-play",
            "title": "Food Court and Play Zone",
            "keywords": ["food court", "food", "eat", "restaurant", "catering", "snacks", "lunch", "dinner", "food stall", "play zone",
                         "kids", "children", "family", "families", "games"],
            "answer": ("Yes — the venue has a Food Court and a Play Zone for families, both marked on the venue map. Want a space there? "
                       "Food Court (2,000 – 3,000 sq. ft.) and Play Zone (1,000 sq. ft.) spaces are priced and allotted directly by the "
                       "organising team — contact " + stalls_c["name"] + " on " + stalls_c["phone"] + "."),
            "links": [{"label": "Venue map", "to": "/stalls"}],
            "chips": [("Contact", "contact"), ("Request a callback", "call me back")],
        },
        {
            "id": "stall-sizes",
            "title": "Stall sizes and what's included",
            "keywords": ["stall size", "size of stall", "dimension", "dimensions", "sq m", "square", "how big", "what is included",
                         "what's included", "inclusion", "inclusions", "furniture", "table", "chair", "chairs", "power point",
                         "electricity", "light", "fascia", "signage", "carpet", "facilities"],
            "answer": ("Sizes and rates (per stall, all three days): " + sizes + ". Standard stalls include 1 table, 2 chairs, a power "
                       "point and fascia signage with your business name; higher categories add prime locations and premium furnishing. "
                       "Extra electrical load must be requested in advance."),
            "links": [{"label": "Rate card", "to": "/register/exhibitor"}],
            "chips": [("Full rate card", "stall rates"), ("Empty stalls map", "empty stalls"), ("Book a stall in chat", "book a stall in chat")],
        },
        {
            "id": "multiple-stalls",
            "title": "More than one stall",
            "keywords": ["more than one stall", "multiple stalls", "two stalls", "2 stalls", "3 stalls", "adjacent", "combine stalls",
                         "bigger space", "large space", "custom size", "bigger stall"],
            "answer": ("Each online registration books one stall. For two or more stalls side by side, or a larger custom space, the "
                       "organising team books them for you under one name — contact " + stalls_c["name"] + " on " + stalls_c["phone"] + "."),
            "links": [{"label": "WhatsApp " + stalls_c["name"].split()[0], "href": "https://wa.me/" + re.sub(r"\D", "", stalls_c["phone"])}],
            "chips": [("Request a callback", "call me back"), ("Book one stall in chat", "book a stall in chat")],
        },
        {
            "id": "after-booking",
            "title": "What happens after booking",
            "keywords": ["after booking", "after registration", "next step", "next steps", "what next", "approval", "approved", "approve",
                         "pending", "how long", "when will i get confirmation", "confirmation", "process", "booking process"],
            "answer": ("1) Your stall is reserved as soon as you register and shows as pending. 2) You get an e-mail with your registration "
                       "ID and the payment details, plus a WhatsApp message. 3) The organising team reviews and confirms the booking — you get "
                       "a confirmation e-mail. 4) After payment the team marks it paid and the invoice is issued. You can check the "
                       "status here any time with your mobile number."),
            "links": [],
            "chips": [("Track my registration", "track my registration"), ("How to pay", "how to pay for stall")],
        },
        {
            "id": "payment",
            "title": "Paying for a stall",
            "keywords": ["how to pay", "payment", "pay", "bank", "bank details", "account number", "ifsc", "upi", "neft", "rtgs", "cheque",
                         "transfer", "advance", "payment mode", "pay online", "paid"],
            "answer": ("Stall payment is by bank transfer to the organisers' account. The exact amount and the account details are sent "
                       "in your registration e-mail — or type the mobile number you registered with and tap “Payment details” to see "
                       "them here. After paying, share the transaction reference or screenshot with the team so they can mark it paid."),
            "links": [],
            "chips": [("Track my registration", "track my registration"), ("Contact", "contact")],
        },
        {
            "id": "cancellation",
            "title": "Cancellation and refund",
            "keywords": ["cancel my stall", "cancellation", "refund", "money back", "withdraw", "cancel booking", "cancel registration"],
            "answer": _clean(ins.get("cancellationPolicy", "Please contact the organising team about cancellations.")) +
                      " To cancel or change a booking, contact " + stalls_c["name"] + " on " + stalls_c["phone"] + ".",
            "links": [],
            "chips": [("Contact", "contact"), ("Request a callback", "call me back")],
        },
        {
            "id": "documents",
            "title": "Documents and rules for exhibitors",
            "keywords": ["documents", "document", "id proof", "gst", "gst certificate", "agreement", "rules", "guidelines", "badge",
                         "fabrication", "height", "decor", "banner", "fire safety", "loading", "unloading", "machinery"],
            "answer": ("Documents: " + "; ".join(ins.get("documentsRequired", [])) + ". Guidelines: " + " ".join(ins.get("guidelines", []))),
            "links": [],
            "chips": [("Set-up timings", "timings"), ("Contact", "contact")],
        },
        {
            "id": "ruby",
            "title": "Ruby stalls",
            "keywords": ["ruby", "women", "woman", "ladies", "lady", "female", "women entrepreneurs", "mahila", "housewife", "home business"],
            "answer": ((ruby.get("eligibility") or BOT["ruby"]) + " Rate " + _rupee(ruby.get("rate")) + " per stall (" + ruby.get("size", "3m × 3m") + "). "
                       "For Ruby bookings contact " + ruby_c["name"] + " on " + ruby_c["phone"] + "."),
            "links": [{"label": "WhatsApp " + ruby_c["name"].split()[0], "href": "https://wa.me/" + re.sub(r"\D", "", ruby_c["phone"])}],
            "chips": [("Empty Ruby stalls", "which ruby stalls are available"), ("Book a Ruby stall in chat", "book a stall in chat ruby")],
        },
        {
            "id": "organisers",
            "title": "Organisers and sponsors",
            "keywords": ["who organises", "who organizes", "who is behind", "organises", "organizes", "organising", "organizing", "organiser", "organizer", "organised by", "organized by", "managed by", "who is organising", "dbohra", "jamiyat",
                         "economic affairs", "tijaraat", "association", "sponsor", "sponsors", "title sponsor", "perfect buildcom",
                         "quality trading", "aakar"],
            "answer": ("Managed by the " + EVENT["organizers"][0]["name"] + ", " + EVENT["organizers"][0]["tagline"] + ", in association with "
                       + BOT["sponsors"]["collaboration"] + ". Title sponsors: " + " and ".join(BOT["sponsors"]["title"]) + ". Silver sponsor: "
                       + ", ".join(BOT["sponsors"]["silver"]) + ". For sponsorship opportunities, contact " + stalls_c["name"] + " on " + stalls_c["phone"] + "."),
            "links": [{"label": "Home page", "to": "/"}],
            "chips": [("Sponsorship", "sponsorship"), ("Contact", "contact")],
        },
        {
            "id": "venue-map",
            "title": "Venue layout",
            "keywords": ["venue map", "layout", "floor plan", "floorplan", "hall map", "stall map", "where is my stall", "entry gate",
                         "exit", "registration desk", "washroom", "toilet", "conference room", "office"],
            "answer": ("The live venue layout is on the Stalls page — every stall with its number and status (green = available). "
                       "It also marks the entry, stage, Food Court and Play Zone. I can show the empty stalls on the map right here too."),
            "links": [{"label": "Open the stall map", "to": "/stalls"}],
            "chips": [("Empty stalls map", "empty stalls"), ("Is a stall free?", "is G2 free")],
        },
        {
            "id": "unknown-logistics",
            "title": "Parking, stay and other arrangements",
            "keywords": ["hotels near", "hotel near", "place to stay", "where to stay", "parking space", "parking", "park", "hotel", "hotels", "stay", "accommodation", "lodging", "room", "guest house", "pickup",
                         "shuttle", "transport", "wifi", "security", "storage", "wheelchair", "accessibility", "prayer", "namaz", "masjid"],
            "answer": ("These arrangements haven't been published on the website yet — the organising team will share them closer to the "
                       "dates. For now, message the helpdesk on WhatsApp " + help_c["phone"] + " (message only) or leave an enquiry here "
                       "and the team will reply."),
            "links": [{"label": "Send an enquiry", "to": "/enquiry"}],
            "chips": [("Send an enquiry", "send an enquiry"), ("Request a callback", "call me back")],
        },
        {
            "id": "logo-listing",
            "title": "Logo and listing",
            "keywords": ["logo", "my logo", "brand logo", "listing", "valued exhibitors", "slider", "home page logo", "product images",
                         "photos", "brochure listing", "catalogue"],
            "answer": ("Confirmed exhibitors' logos appear in the “Our Valued Exhibitors” slider on the home page and in expo marketing. "
                       "You can upload your logo and up to 5 product images on the exhibitor form — or send them to the team after "
                       "booking and they'll add them for you."),
            "links": [{"label": "Home page", "to": "/"}],
            "chips": [("Who is exhibiting?", "who is exhibiting"), ("Contact", "contact")],
        },
        {
            "id": "pages",
            "title": "Website pages",
            "keywords": ["website", "pages", "menu", "sitemap", "where can i find", "link", "links", "page"],
            "answer": "Everything on www.roarexpo.com:",
            "links": [{"label": "Home", "to": "/"}, {"label": "About", "to": "/#about"}, {"label": "Why Nagpur", "to": "/why-nagpur"},
                      {"label": "Industries", "to": "/#categories"}, {"label": "Stall map", "to": "/stalls"},
                      {"label": "Register as exhibitor", "to": "/register/exhibitor"}, {"label": "Register as visitor", "to": "/register/visitor"},
                      {"label": "Enquiry", "to": "/enquiry"}, {"label": "Contact", "to": "/contact"}, {"label": "Ask ROAR", "to": "/ask"}],
            "chips": [],
        },
        {
            "id": "deadlines",
            "title": "Deadlines",
            "keywords": ["deadline", "last date", "closing date", "till when", "until when", "registration closes", "last day to register"],
            "answer": ("Stall bookings close on " + deadlines.get("stall", "—") + "; visitor registration closes on "
                       + deadlines.get("visitor", "—") + ". Stalls are allotted first come, first served — book early for the best location."),
            "links": [],
            "chips": [("Book a stall in chat", "book a stall in chat"), ("Register as visitor", "register as visitor")],
        },
    ]


def knowledge_text() -> str:
    """All entries as plain text, for the AI model's fact sheet."""
    out = []
    for e in entries():
        out.append(f"[{e['title']}] {e['answer']}")
    return "\n".join(out)
