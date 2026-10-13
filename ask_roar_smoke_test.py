"""
Ask ROAR Anything — smoke test (read-only, safe on preview AND on the live site).

    python ask_roar_smoke_test.py https://<your-backend-host>        # e.g. https://www.roarexpo.com
    python ask_roar_smoke_test.py http://localhost:8001

It only asks questions and walks the stall booking up to the stall step, then
cancels (the 15-minute hold is released straight away). It never submits a
registration, enquiry or callback, so no e-mails / WhatsApp messages are sent and
no records are created apart from one short chat log in `bot_logs`.
"""
import json
import sys
import uuid

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001").rstrip("/")
API = BASE + "/api"
SID = "smoke" + uuid.uuid4().hex[:20]
ok = fail = 0


def check(cond, label, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print("  PASS", label)
    else:
        fail += 1
        print("  FAIL", label, extra[:200])


def say(msg, action=None):
    r = httpx.post(API + "/bot/chat", json={"sessionId": SID, "message": msg, **({"action": action} if action else {})}, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def text(o):
    return " ".join(b.get("text", "") for b in o["messages"] if b["type"] == "text")


def blob(o):
    return json.dumps(o, ensure_ascii=False)


def chips(o):
    return [q["label"] for q in o["quickReplies"]]


print("Backend:", API)
r = httpx.get(API + "/bot/info", timeout=20)
check(r.status_code == 200 and r.json().get("success"), "GET /api/bot/info", r.text)
print("  AI answers enabled:", r.json().get("data", {}).get("ai") if r.status_code == 200 else "?")
r = httpx.get(API + "/public/event.ics", timeout=20)
check(r.status_code == 200 and "BEGIN:VCALENDAR" in r.text, "GET /api/public/event.ics", r.text)

o = say("", "open")
check("Ask me anything" in text(o) and "Book a stall" in chips(o), "greeting + menu", text(o))
o = say("what does ROAR stand for?")
check("Rise" in text(o), "website topic: ROAR meaning", text(o))
o = say("how do I reach nagpur by train?")
check("Nagpur Junction" in text(o), "website topic: getting there", text(o))
o = say("is entry free?")
check("free" in text(o).lower(), "website topic: entry", text(o))
o = say("stall rates")
check(any(b["type"] == "rates" for b in o["messages"]), "rate card", blob(o))
o = say("empty stalls")
check(any(b["type"] == "map" for b in o["messages"]), "empty-stalls map", blob(o))

o = say("book a stall in chat")
check(o["flow"] == "book" and o["step"] == "package", "chat booking starts at category", blob(o))
cat = next((q["send"] for q in o["quickReplies"] if q["send"].startswith("category ")), None)
check(bool(cat), "a category with free stalls is offered", blob(o))
if cat:
    o = say(cat)
    check(o["step"] == "stall", "stall step shows free stalls", blob(o))
    stall = next((q["send"] for q in o["quickReplies"] if q["send"].startswith("stall ")), None)
    if stall:
        o = say(stall)
        check(o["step"] == "contactPerson" and "reserved" in text(o), "stall held for the booking", text(o))
o = say("cancel")
check(o["flow"] is None and "released" in text(o), "cancel releases the stall", text(o))

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
