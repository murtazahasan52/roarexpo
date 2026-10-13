"""
"Ask ROAR Anything" — facts the website chat bot answers from.

Everything event-related (dates, venue, rate card, categories, deadlines,
exhibitor instructions) comes from config/event_config.py so the bot never
drifts from the site. This file only holds the extra, bot-specific facts —
people to contact, headline figures and sponsors — plus the optional AI
settings. Edit the values; no logic lives here.
"""
import os

BOT = {
    "name": "ROAR Assistant",
    "title": "Ask ROAR Anything",
    "tagline": "The Road to New Milestones in Business",
    "showTimings": "10:00 AM – 8:00 PM, all three days",
    "headline": {
        "stalls": "150+",  # headline figure shown on the site; live counts come from the stalls collection
        "industries": "16+",
        "visitors": "18,000+",
        "days": "3",
    },
    "contacts": {
        "stalls": {
            "name": "Yusuf Bhai Kanchwala",
            "phone": "+91 99228 02852",
            "for": "stall bookings, partnerships and sponsorship (WhatsApp or call)",
        },
        "ruby": {
            "name": "Rashida ben Fidvi",
            "phone": "+91 93737 83531",
            "for": "Ruby stalls (reserved for women entrepreneurs)",
        },
        "enquiries": {
            "name": "ROAR Expo helpdesk",
            "phone": "+91 92841 82675",
            "for": "general enquiries (WhatsApp message only — no calls)",
        },
        "emails": ["mkt@roarexpo.com", "admin@roarexpo.com"],
    },
    "sponsors": {
        "title": ["Perfect Buildcom", "Quality Trading Company (QTC), Nagpur"],
        "silver": ["Aakar Constructions Group, Nagpur"],
        "collaboration": "dbohra — A Global Business Network",
    },
    "about": (
        "ROAR Business Expo Nagpur 2027 brings Dawoodi Bohra businessmen, entrepreneurs, manufacturers, "
        "traders, professionals and service providers from across India together under one roof — three days "
        "to showcase products and services, meet new customers, suppliers, dealers and partners, and build "
        "lasting business relationships. R.O.A.R. stands for Rise • Opportunity • Ambition • Reach."
    ),
    "whatToExpect": [
        "Exhibition — 150+ stalls across 16+ industries",
        "Networking with entrepreneurs, traders and industry representatives",
        "Keynote speakers and business leaders",
        "Interactive workshops",
        "Food Court and a Play Zone for families",
    ],
    "ruby": "Ruby stalls (RU1 – RU32) are reserved for women entrepreneurs of the Dawoodi Bohra community.",
}


def llm_settings() -> dict:
    """Optional AI fallback for free-text questions. The bot works fully
    without any key (guided flows + facts above); set ONE of these to let it
    also answer open questions in natural language:
        EMERGENT_LLM_KEY   — Emergent's universal key (uses emergentintegrations)
        OPENAI_API_KEY     — OpenAI directly (model: BOT_LLM_MODEL, default gpt-4o-mini)
        ANTHROPIC_API_KEY  — Anthropic directly (model: BOT_LLM_MODEL, default claude-3-5-haiku-latest)
    BOT_AI=false switches the AI fallback off even when a key is present."""
    enabled = (os.environ.get("BOT_AI") or "true").strip().lower() not in ("0", "false", "no", "off")
    return {
        "enabled": enabled,
        "emergent_key": (os.environ.get("EMERGENT_LLM_KEY") or "").strip(),
        "openai_key": (os.environ.get("OPENAI_API_KEY") or "").strip(),
        "anthropic_key": (os.environ.get("ANTHROPIC_API_KEY") or "").strip(),
        "model": (os.environ.get("BOT_LLM_MODEL") or "").strip(),
    }
