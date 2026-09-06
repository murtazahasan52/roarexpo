"""
ROAR Expo — Central event content configuration.
Direct port of the old backend's config/eventConfig.js. Edit the values below
to update copy used across the site and in automated emails/PDFs, without
touching any logic code. Keep this a plain dict (not a Pydantic model) so
`EVENT` can be dropped straight into a JSON response body, exactly like the
Express version did with `res.json({ success: true, data: event })`.
"""

EVENT = {
    "eventName": "ROAR — Saifee Burhani Business Expo",
    "eventCity": "Nagpur",
    "eventTagline": "RISE • OPPORTUNITY • AMBITION • REACH",
    "eventDatesLabel": "8 – 10 January 2027",
    "eventStartDateISO": "2027-01-08",
    "eventEndDateISO": "2027-01-10",
    "venueName": "MSB Ground, Nagpur",
    "venueAddress": "MSB Ground, Nagpur, Maharashtra, India",
    # Replace with an exact Google Maps link once available
    "venueMapUrl": "https://www.google.com/maps/search/?api=1&query=MSB+Ground+Nagpur",
    "totalStalls": "100+",
    "organizers": [
        # Confirmed exact spelling/wording per the organizer's own site.
        # dbohra is shown as a logo partner on the homepage, not listed here as
        # a formal organizer — Tijaraat is the sole organizer per instruction.
        {"name": "Idaarah al-Tijaarat al-Raabehah", "tagline": "Economic Affairs Committee"},
    ],
    "contact": {
        # Per the official expo poster: WhatsApp message only, no calls.
        "whatsapp": "+91 92841 82675",
        "whatsappNote": "WhatsApp Message Only — No Calls",
        "email": "mkt@roarexpo.com",
    },
    "registrationDeadlines": {
        "stall": "20 December 2026",
        "visitor": "6 January 2027",
    },
    # Stall rate card — the official ROAR Expo stall chart. Categories with
    # hasStallPicker=True have a fixed count of individually numbered stalls
    # (seeded via seed/stall_seed.py) that exhibitors can pick online in real
    # time on the registration form; the other two are sq.ft-based spaces
    # with no fixed stall count, so no online stall number picker is shown
    # for them — pricing/allocation is handled directly by the organizing
    # team. stallCount is informational (matches the official chart's
    # "No. of Stalls" column) and totals to totalStallsNumbered.
    "stallPackages": [
        {"code": "title", "label": "Title Stall", "icon": "🏆", "rate": 2100000, "stallCount": 1, "hasStallPicker": True, "inclusions": "Prime frontage location, maximum branding exposure, premium furnishing package"},
        {"code": "diamond", "label": "Diamond Stall", "icon": "💎", "rate": 753000, "stallCount": 2, "hasStallPicker": True, "inclusions": "Prime location, enhanced branding, premium furnishing package"},
        {"code": "gold", "label": "Gold Stall", "icon": "🥇", "rate": 453000, "stallCount": 3, "hasStallPicker": True, "inclusions": "High-visibility location, premium furnishing package"},
        {"code": "silver", "label": "Silver Stall", "icon": "🥈", "rate": 353000, "stallCount": 4, "hasStallPicker": True, "inclusions": "Good-visibility location, standard furnishing package"},
        {"code": "bronze", "label": "Bronze Stall", "icon": "🥉", "rate": 153000, "stallCount": 5, "hasStallPicker": True, "inclusions": "Standard furnishing package, fascia signage"},
        {"code": "premium", "label": "Premium Stall", "icon": "⭐", "rate": 72000, "stallCount": 11, "hasStallPicker": True, "inclusions": "1 table, 2 chairs, power point, fascia signage"},
        {"code": "regular", "label": "Regular Stall", "rate": 53000, "stallCount": 27, "hasStallPicker": True, "inclusions": "1 table, 2 chairs, power point, fascia signage"},
        {"code": "ruby", "label": "Ruby Stall", "rate": 24000, "stallCount": 50, "hasStallPicker": True, "inclusions": "1 table, 2 chairs, power point, fascia signage"},
        {"code": "food-court", "label": "Food Court", "rate": None, "sizeLabel": "2,000 – 3,000 sq. ft.", "hasStallPicker": False, "inclusions": "Space allocation and pricing discussed directly with the organizing team"},
        {"code": "play-zone", "label": "Play Zone", "rate": None, "sizeLabel": "1,000 sq. ft.", "hasStallPicker": False, "inclusions": "Space allocation and pricing discussed directly with the organizing team"},
    ],
    # Sum of stallCount across the 8 individually-numbered categories above —
    # matches the official chart's "Total Stalls: 103". Food Court and Play
    # Zone are sq.ft-based and excluded from this figure.
    "totalStallsNumbered": 103,
    "categories": [
        {"key": "industrial-machinery", "label": "Industrial Machinery"},
        {"key": "robotics-automation", "label": "Robotics & Automation"},
        {"key": "manufacturing", "label": "Manufacturing"},
        {"key": "plywood-hardware-tools", "label": "Plywood / Hardware & Tools"},
        {"key": "construction-real-estate", "label": "Construction & Real Estate"},
        {"key": "jewellery-luxury", "label": "Jewellery & Luxury"},
        {"key": "it-technology", "label": "IT & Technology"},
        {"key": "renewable-energy-solar", "label": "Renewable Energy & Solar"},
        {"key": "automotive-ev", "label": "Automotive & EV"},
        {"key": "healthcare-medical", "label": "Healthcare & Medical"},
        {"key": "fmcg-consumer-goods", "label": "FMCG & Consumer Goods"},
        {"key": "food-beverage", "label": "Food & Beverage"},
        {"key": "textiles-apparel", "label": "Textiles & Apparel"},
        {"key": "education-skills", "label": "Education & Skills"},
        {"key": "electrical-electronics", "label": "Electrical & Electronics"},
        {"key": "travel-hospitality", "label": "Travel & Hospitality"},
    ],
    # Exhibitor move-in / move-out & general instructions (placeholders — edit freely)
    "exhibitorInstructions": {
        "setupWindow": "6 – 7 January 2027, 10:00 AM – 8:00 PM",
        "moveOutWindow": "10 January 2027, 7:00 PM – 11:00 PM",
        "dailyShowTiming": "10:00 AM – 8:00 PM (all 3 days)",
        "documentsRequired": [
            "Valid government photo ID for all staff manning the stall",
            "GST certificate / business registration proof (for invoicing)",
            "Signed exhibitor agreement (sent along with this email)",
        ],
        "guidelines": [
            "Stall fabrication must stay within your allotted footprint and height limit (2.5m unless approved otherwise).",
            "Electrical load beyond the standard power point must be requested in advance.",
            "Exhibitor badges must be worn at all times inside the expo hall.",
            "Loading/unloading of heavy machinery is only permitted during the move-in window at the designated gate.",
            "All stall decor and banners must be fire-safety compliant.",
        ],
        "cancellationPolicy": (
            "Cancellations made before the registration deadline are eligible for a full refund of any advance "
            "paid. Cancellations after the deadline are non-refundable. (Update this policy to match your final terms.)"
        ),
    },
}


def find_stall_package(code: str) -> dict | None:
    return next((p for p in EVENT["stallPackages"] if p["code"] == code), None)


def numbered_packages() -> list[dict]:
    """Rate-card categories that have an online, individually-numbered stall picker."""
    return [p for p in EVENT["stallPackages"] if p.get("hasStallPicker")]
