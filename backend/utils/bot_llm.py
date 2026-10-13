"""Optional AI answer for free-text questions the guided bot can't match.

Returns None whenever no key is configured or the provider fails, so the
caller always has a safe fallback. The model only ever sees the event facts
we hand it (system prompt built from event_config + bot_config) and the
visitor's question — never database records."""
import asyncio

import httpx

from config.bot_config import BOT, llm_settings
from config.event_config import EVENT

TIMEOUT = 20.0


def _fmt_rate(rate):
    if rate is None:
        return "on request"
    return "₹" + f"{int(rate):,}".replace(",", ",")


def knowledge_text() -> str:
    """Plain-text fact sheet given to the model as its only source."""
    lines = [
        f"Event: {EVENT['eventName']} ({BOT['tagline']}). Brand: ROAR Expo. Website: www.roarexpo.com",
        f"Dates: {EVENT['eventDatesLabel']} ({EVENT.get('eventDatesHijri', '1st – 3rd Shaban ul Karim 1448H')}). Timings: {BOT['showTimings']}.",
        f"Venue: {EVENT['venueName']}. Address: {EVENT['venueAddress']}. Map: {EVENT['venueMapUrl']}",
        f"Managed by: {EVENT['organizers'][0]['name']}, {EVENT['organizers'][0]['tagline']}. In collaboration with {BOT['sponsors']['collaboration']}.",
        f"Title sponsors: {', '.join(BOT['sponsors']['title'])}. Silver sponsor: {', '.join(BOT['sponsors']['silver'])}.",
        f"Headline figures: {BOT['headline']['stalls']} stalls, {BOT['headline']['industries']} industries, {BOT['headline']['visitors']} expected visitors, {BOT['headline']['days']} days.",
        "About: " + BOT["about"],
        "What to expect: " + "; ".join(BOT["whatToExpect"]),
        BOT["ruby"],
        "Stall rate card (per stall, all three days):",
    ]
    for p in EVENT["stallPackages"]:
        extra = f", {p['stallCount']} stalls" if p.get("stallCount") else (f", {p.get('sizeLabel')}" if p.get("sizeLabel") else "")
        lines.append(f"  - {p['label']}: {_fmt_rate(p.get('rate'))}{extra}. Includes: {p.get('inclusions', '')}")
    lines.append("Industry categories: " + ", ".join(c["label"] for c in EVENT["categories"]))
    d = EVENT["registrationDeadlines"]
    lines.append(f"Registration deadlines: stall booking {d['stall']}, visitor registration {d['visitor']}.")
    ins = EVENT["exhibitorInstructions"]
    lines.append(f"Exhibitor set-up: {ins['setupWindow']}. Move-out: {ins['moveOutWindow']}. Daily show timing: {ins['dailyShowTiming']}.")
    lines.append("Exhibitor guidelines: " + " ".join(ins["guidelines"]))
    lines.append("Cancellation policy: " + ins["cancellationPolicy"])
    c = BOT["contacts"]
    lines.append(f"Contact for stalls/partnerships/sponsorship: {c['stalls']['name']} {c['stalls']['phone']} ({c['stalls']['for']}).")
    lines.append(f"Contact for Ruby stalls: {c['ruby']['name']} {c['ruby']['phone']}.")
    lines.append(f"General enquiries: WhatsApp {c['enquiries']['phone']} ({c['enquiries']['for']}). Emails: {', '.join(c['emails'])}.")
    lines.append("Website pages: /register/visitor (free visitor registration, ID card with QR by e-mail), "
                 "/register/exhibitor (book a stall online, pick the stall on the live map), /stalls (live stall map), "
                 "/why-nagpur, /contact, /enquiry, /ask (this assistant). Stalls can also be booked inside this chat (tap 'Book a stall').")
    from config.bot_knowledge import knowledge_text as _website
    lines.append("WEBSITE TOPICS:")
    lines.append(_website())
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are ROAR Assistant, the friendly helpdesk of ROAR Business Expo Nagpur 2027 on www.roarexpo.com. "
    "Answer ONLY from the fact sheet below. If the answer is not in it, say you don't have that detail and point "
    "the visitor to the enquiry WhatsApp number or e-mail. Reply in the visitor's language (English, Hindi or "
    "Hinglish). Be warm and brief: at most 4 short sentences, plain text only — no markdown, no asterisks, no "
    "bullet symbols. Never invent prices, dates, names or stall availability. For live stall availability or a "
    "registration status, tell the visitor to use the chat buttons 'Empty stalls' or 'Track my registration'.\n\n"
    "FACT SHEET\n"
)


async def ai_answer(question: str, history: list[dict] | None = None) -> str | None:
    s = llm_settings()
    if not s["enabled"] or not question.strip():
        return None
    system = SYSTEM_PROMPT + knowledge_text()
    msgs = []
    for h in (history or [])[-6:]:
        if h.get("role") in ("user", "assistant") and h.get("text"):
            msgs.append({"role": h["role"], "content": h["text"][:800]})
    msgs.append({"role": "user", "content": question.strip()[:1000]})
    try:
        if s["emergent_key"]:
            return await asyncio.wait_for(_emergent(s, system, msgs), TIMEOUT + 5)
        if s["openai_key"]:
            return await asyncio.wait_for(_openai(s, system, msgs), TIMEOUT + 5)
        if s["anthropic_key"]:
            return await asyncio.wait_for(_anthropic(s, system, msgs), TIMEOUT + 5)
    except Exception as err:  # noqa: BLE001 — the guided answer takes over
        print("[bot] AI fallback failed:", repr(err))
    return None


async def _emergent(s, system, msgs):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage  # type: ignore
    except Exception:  # noqa: BLE001 — package only exists on Emergent
        return await _openai_compatible(s["emergent_key"], "https://api.openai.com/v1", s["model"] or "gpt-4o-mini", system, msgs)
    model = s["model"] or "gpt-4o-mini"
    chat = LlmChat(api_key=s["emergent_key"], session_id="roar-bot", system_message=system).with_model("openai", model)
    # Earlier turns are folded into the question so the stateless helper keeps context.
    context = "\n".join(f"{m['role']}: {m['content']}" for m in msgs[:-1])
    text = (f"Earlier in this chat:\n{context}\n\nVisitor now asks: " if context else "") + msgs[-1]["content"]
    reply = await chat.send_message(UserMessage(text=text))
    return _clean(str(reply))


async def _openai(s, system, msgs):
    return await _openai_compatible(s["openai_key"], "https://api.openai.com/v1", s["model"] or "gpt-4o-mini", system, msgs)


async def _openai_compatible(key, base, model, system, msgs):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "temperature": 0.3, "max_tokens": 350,
                  "messages": [{"role": "system", "content": system}] + msgs},
        )
        r.raise_for_status()
        return _clean(r.json()["choices"][0]["message"]["content"])


async def _anthropic(s, system, msgs):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": s["anthropic_key"], "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": s["model"] or "claude-3-5-haiku-latest", "max_tokens": 350, "temperature": 0.3,
                  "system": system, "messages": msgs},
        )
        r.raise_for_status()
        parts = r.json().get("content") or []
        return _clean("".join(p.get("text", "") for p in parts if p.get("type") == "text"))


def _clean(text: str) -> str | None:
    text = (text or "").replace("**", "").replace("##", "").strip()
    return text or None
