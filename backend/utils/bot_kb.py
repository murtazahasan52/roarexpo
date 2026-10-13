"""Matches a free-text question to a website topic (config/bot_knowledge.py)
and turns it into chat blocks. No AI needed: it scores whole-word keyword
hits, longer phrases counting more, so "how do I reach Nagpur by train"
lands on Getting there and "what does the tiger mean" on What ROAR stands for.
"""
from __future__ import annotations

import re

from config.bot_knowledge import entries

_STOP = {"the", "a", "an", "is", "are", "to", "for", "of", "in", "on", "at", "i", "me", "my", "we", "you", "it", "do", "does",
         "can", "and", "or", "what", "how", "when", "where", "which", "who", "will", "be", "there", "this", "that", "please", "pls",
         "tell", "about", "any", "with", "from", "have", "has", "get", "want", "need", "should"}

STRONG = 2.0   # beats a generic intent (e.g. "where" → venue) when the question is specific
WEAK = 1.0     # enough to answer when nothing else matched


def _norm(s: str) -> str:
    s = (s or "").lower().replace("’", "'")
    s = re.sub(r"[^\w\s'&-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def score(entry: dict, text: str) -> float:
    total = 0.0
    hit_words = set()
    for kw in entry["keywords"]:
        k = _norm(kw)
        if not k:
            continue
        if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", text):
            words = [w for w in k.split() if w not in _STOP]
            if not words:
                continue
            if set(words) <= hit_words:
                continue  # already counted inside a longer phrase
            hit_words.update(words)
            total += 1.0 + 1.25 * (len(words) - 1)
    return total


def best(message: str, k: int = 3) -> list[tuple[float, dict]]:
    text = _norm(message)
    if not text:
        return []
    scored = [(score(e, text), e) for e in entries()]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def blocks_for(entry: dict) -> tuple[list[dict], list[dict]]:
    blocks = [{"type": "text", "text": entry["answer"]}]
    if entry.get("links"):
        blocks.append({"type": "links", "items": entry["links"]})
    quick = [{"label": a, "send": b} for a, b in entry.get("chips", [])]
    quick.append({"label": "Main menu", "send": "menu"})
    return blocks, quick


def suggestions(message: str) -> list[dict]:
    """'Did you mean' chips — the closest topics even when the score is low."""
    return [{"label": e["title"], "send": e["keywords"][0]} for _, e in best(message, 3)]
