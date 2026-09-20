"""
ROAR Expo — Central event content configuration.
Direct port of the old backend's config/eventConfig.js. Edit the values below
to update copy used across the site and in automated emails/PDFs, without
touching any logic code. Keep this a plain dict (not a Pydantic model) so
`EVENT` can be dropped straight into a JSON response body, exactly like the
Express version did with `res.json({ success: true, data: event })`.
"""

EVENT = {
    "eventName": "ROAR — Business Expo Nagpur",
    "eventCity": "Nagpur",
    "eventTagline": "RISE • OPPORTUNITY • AMBITION • REACH",
    "eventDatesLabel": "8th to 10th January 2027",
    "eventStartDateISO": "2027-01-08",
    "eventEndDateISO": "2027-01-10",
    "venueName": "MSB Ground, Nagpur",
    "venueAddress": "MSB Ground, Nagpur, Maharashtra, India",
    # Replace with an exact Google Maps link once available
    "venueMapUrl": "https://www.google.com/maps/search/?api=1&query=MSB+Ground+Nagpur",
    "totalStalls": "150+",
    "organizers": [
        # Shown in the homepage "About" organizer strip (alongside the department's
        # logo). dbohra is shown as a logo partner on the homepage, not listed
        # here as a formal organizer.
        {"name": "Dawoodi Bohra Department of Economic Affairs", "tagline": "Nagpur Jamiyat"},
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
        {"code": "title", "label": "Title Stall", "icon": "🏆", "rate": 1053000, "size": "3m × 8m / 4m × 6m", "stallCount": 2, "hasStallPicker": True, "inclusions": "24 sq m · Prime frontage, maximum branding exposure, premium furnishing package"},
        {"code": "diamond", "label": "Diamond Stall", "icon": "💎", "rate": 753000, "size": "3m × 6m", "stallCount": 2, "hasStallPicker": True, "inclusions": "18 sq m · Prime location, enhanced branding, premium furnishing package"},
        {"code": "gold", "label": "Gold Stall", "icon": "🥇", "rate": 553000, "size": "3m × 5m", "stallCount": 4, "hasStallPicker": True, "inclusions": "15 sq m · High-visibility location, premium furnishing package"},
        {"code": "silver", "label": "Silver Stall", "icon": "🥈", "rate": 353000, "size": "3m × 4m", "stallCount": 4, "hasStallPicker": True, "inclusions": "12 sq m · Good-visibility location, standard furnishing package"},
        {"code": "bronze", "label": "Bronze Stall", "icon": "🥉", "rate": 253000, "size": "3m × 5m", "stallCount": 4, "hasStallPicker": True, "inclusions": "15 sq m · Standard furnishing package, fascia signage"},
        {"code": "premium-corner", "label": "Premium Corner Stall", "icon": "⭐", "rate": 100000, "size": "3m × 4m", "stallCount": 5, "hasStallPicker": True, "inclusions": "12 sq m · Corner location (PP1–PP5), fascia signage"},
        {"code": "premium", "label": "Premium Stall", "icon": "⭐", "rate": 72000, "size": "3m × 4m", "stallCount": 19, "hasStallPicker": True, "inclusions": "12 sq m · 1 table, 2 chairs, power point, fascia signage"},
        {"code": "premium-ruby", "label": "Premium Ruby Stall", "rate": 72000, "size": "3m × 3m", "stallCount": 4, "hasStallPicker": True, "inclusions": "9 sq m · Premium Ruby corner (PR1–PR4), fascia signage"},
        {"code": "premium-corner-15", "label": "Premium Corner Stall (15 sq m)", "icon": "⭐", "rate": 53000, "size": "3m × 5m", "stallCount": 2, "hasStallPicker": True, "inclusions": "15 sq m · Corner location (PP6–PP7), fascia signage"},
        {"code": "premium-ruby-53", "label": "Premium Ruby Stall (Standard)", "rate": 53000, "size": "3m × 3m", "stallCount": 4, "hasStallPicker": True, "inclusions": "9 sq m · Premium Ruby (PR5–PR8), fascia signage"},
        {"code": "regular", "label": "Regular Stall", "rate": 53000, "size": "3m × 3m", "stallCount": 66, "hasStallPicker": True, "inclusions": "9 sq m · 1 table, 2 chairs, power point, fascia signage"},
        {"code": "ruby", "label": "Ruby Stall", "rate": 24000, "size": "3m × 3m", "stallCount": 32, "hasStallPicker": True, "adminOnly": True, "eligibility": "Available only for Women Entrepreneurs of the Dawoodi Bohra Community", "inclusions": "9 sq m · 1 table, 2 chairs, power point, fascia signage"},
        {"code": "food-court", "label": "Food Court", "rate": None, "sizeLabel": "2,000 – 3,000 sq. ft.", "hasStallPicker": False, "inclusions": "Space allocation and pricing discussed directly with the organizing team"},
        {"code": "play-zone", "label": "Play Zone", "rate": None, "sizeLabel": "1,000 sq. ft.", "hasStallPicker": False, "inclusions": "Space allocation and pricing discussed directly with the organizing team"},
    ],
    # Sum of stallCount across the numbered categories above — new 2027 layout:
    # T1–T2 (2), PP1–PP5 (5), PP6–PP7 (2), P1–P19 (19), D1–D2 (2), PR1–PR4 (4),
    # PR5–PR8 (4), G1–G4 (4), R1–R66 (66), S1–S4 (4), B1–B4 (4), RU1–RU32 (32).
    "totalStallsNumbered": 148,
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
