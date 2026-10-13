import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api";
import Icon from "./Icon";
import tiger from "../assets/roar-tiger.png";

// "Ask ROAR Anything" — the floating website assistant.
//
// Everything it knows comes from the backend (POST /api/bot/chat): the server
// decides the reply as a list of typed blocks (text / card / links / rates /
// map) plus quick-reply chips, and keeps the conversation state (visitor
// registration steps, status lookups) in its own session store. This
// component only renders blocks and sends what the visitor types or taps.

const STORAGE_KEY = "roar-bot-session";

function newSessionId() {
  const rnd = (typeof crypto !== "undefined" && crypto.randomUUID) ? crypto.randomUUID().replace(/-/g, "") : Math.random().toString(36).slice(2) + Date.now().toString(36);
  return rnd.slice(0, 32);
}

function loadSessionId() {
  try {
    const v = sessionStorage.getItem(STORAGE_KEY);
    if (v && /^[A-Za-z0-9_-]{8,64}$/.test(v)) return v;
  } catch (e) {
    // storage blocked — a fresh id per page load is fine
  }
  const id = newSessionId();
  try {
    sessionStorage.setItem(STORAGE_KEY, id);
  } catch (e) {
    // ignore
  }
  return id;
}

// Turns a plain reply into text with tappable links for URLs, e-mails and
// Indian mobile numbers — the server never sends HTML.
function linkify(text) {
  const re = /((?:https?:\/\/|www\.)[^\s,)]+|[\w.+-]+@[\w-]+\.[\w.]+|\+91[\s-]?\d{5}[\s-]?\d{5})/g;
  const parts = [];
  let last = 0;
  let m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const t = m[0];
    if (t.includes("@")) parts.push(<a key={m.index} href={`mailto:${t}`}>{t}</a>);
    else if (t.startsWith("+91")) parts.push(<a key={m.index} href={`https://wa.me/${t.replace(/\D/g, "")}`} target="_blank" rel="noreferrer">{t}</a>);
    else parts.push(<a key={m.index} href={t.startsWith("http") ? t : `https://${t}`} target="_blank" rel="noreferrer">{t}</a>);
    last = m.index + t.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

const CATEGORY_COLORS = {
  title: "#5b6b8c", diamond: "#9ccc65", gold: "#f0be4a", silver: "#c4cbd4", bronze: "#e48fb0", premium: "#3a9bd9", "premium-corner": "#1f7fc4",
  "premium-ruby": "#c86ad0", "premium-corner-15": "#2b6cb0", "premium-ruby-53": "#b259c4", regular: "#8fd3ff", ruby: "#f08a8a",
};

function MiniMap({ block, onNavigate }) {
  const [open, setOpen] = useState(null);
  const src = api.fileUrl(block.mapUrl);
  const counts = block.counts || [];
  const totalFree = counts.reduce((n, c) => n + c.available, 0);
  const shown = open ? (block.stalls || []).filter((s) => s.c === open) : block.stalls || [];
  const current = counts.find((c) => c.code === open);
  return (
    <div className="bot-map">
      {src ? (
        <div className="bot-map-frame">
          <img src={src} alt="Venue layout" draggable={false} />
          {shown.map((s) => (
            <span key={s.n} className="bot-map-dot" style={{ left: `${s.x}%`, top: `${s.y}%`, background: CATEGORY_COLORS[s.c] || "#2e9e5b" }} title={s.n} />
          ))}
          <span className="bot-map-count">{block.label ? block.label : open && current ? `${current.available} ${current.label.replace(" Stall", "")} free` : `${totalFree} stalls free`}</span>
        </div>
      ) : (
        <p className="bot-muted">The venue map hasn't been published yet.</p>
      )}
      <div className="bot-map-legend">
        {counts.map((c) => (
          <button key={c.code} type="button" className={`bot-chip ${open === c.code ? "is-on" : ""}`} onClick={() => setOpen(open === c.code ? null : c.code)}>
            <i style={{ background: CATEGORY_COLORS[c.code] || "#2e9e5b" }} />
            {c.label.replace(" Stall", "")} <b>{c.available}</b>/{c.total}
          </button>
        ))}
      </div>
      {open && current && (
        <div className="bot-map-numbers">
          {current.numbers.length ? current.numbers.join(" · ") : "No stalls left in this category."}
        </div>
      )}
      <Link to="/stalls" className="bot-map-link" onClick={onNavigate}>Open the full-screen map →</Link>
    </div>
  );
}

function Block({ block, onNavigate }) {
  if (block.type === "text") return <p className="bot-text">{linkify(block.text)}</p>;
  if (block.type === "card") {
    return (
      <div className={`bot-card tone-${block.tone || "info"}`}>
        <div className="bot-card-title">{block.title}</div>
        {block.rows.map(([k, v]) => (
          <div className="bot-card-row" key={k}>
            <span>{k}</span>
            <strong>{v}</strong>
          </div>
        ))}
      </div>
    );
  }
  if (block.type === "links") {
    return (
      <div className="bot-links">
        {block.items.map((it) =>
          it.to ? (
            <Link key={it.label} to={it.to} className={`bot-link ${it.primary ? "is-primary" : ""}`} onClick={onNavigate}>{it.label}</Link>
          ) : it.api ? (
            <a key={it.label} href={api.fileUrl(it.api)} download={it.download || true} className={`bot-link ${it.primary ? "is-primary" : ""}`}>{it.label}</a>
          ) : (
            <a key={it.label} href={it.href} target="_blank" rel="noreferrer" className={`bot-link ${it.primary ? "is-primary" : ""}`}>{it.label}</a>
          )
        )}
      </div>
    );
  }
  if (block.type === "rates") {
    return (
      <div className="bot-rates">
        {block.rows.map((r) => (
          <div className="bot-rate" key={r.code}>
            <div className="bot-rate-head">
              <span>{r.label}</span>
              <strong>{r.rate}</strong>
            </div>
            <div className="bot-rate-meta">
              {r.count ? <span>{typeof r.count === "number" ? `${r.count} stalls` : r.count}</span> : null}
              {r.available !== null && r.available !== undefined ? <span className={r.available ? "is-free" : "is-full"}>{r.available ? `${r.available} available` : "sold out"}</span> : null}
            </div>
            {r.note ? <div className="bot-rate-note">{r.note}</div> : null}
          </div>
        ))}
      </div>
    );
  }
  if (block.type === "map") return <MiniMap block={block} onNavigate={onNavigate} />;
  if (block.type === "image") {
    const src = block.api ? api.fileUrl(block.api) : block.url;
    return (
      <a className="bot-image" href={src} download={block.download || true} target="_blank" rel="noreferrer">
        <img src={src} alt={block.alt || ""} />
        <span className="bot-image-caption">Tap to save</span>
      </a>
    );
  }
  return null;
}

// `embedded` renders the chat inline (the full-page /ask route) instead of the
// floating launcher; `initialQuestion` is asked right after the greeting
// (www.roarexpo.com/ask?q=stall%20rates). Any page can push a question in with
// window.dispatchEvent(new CustomEvent("roar-bot:ask", { detail: "stall rates" })).
export default function RoarBot({ embedded = false, initialQuestion = "" }) {
  const location = useLocation();
  const [open, setOpen] = useState(embedded);
  const [messages, setMessages] = useState([]); // {id, role: "bot"|"user", blocks|text}
  const [quick, setQuick] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [started, setStarted] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const sessionId = useRef(null);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const idSeq = useRef(0);

  const bootRef = useRef(false);
  // The floating launcher hides on admin pages and on /ask (which has the chat built in).
  const hidden = !embedded && (location.pathname.startsWith("/admin") || location.pathname.replace(/\/+$/, "") === "/ask");

  // Little "Ask ROAR Anything" hint beside the launcher after a few seconds on the first visit.
  useEffect(() => {
    if (hidden) return undefined;
    let seen = false;
    try {
      seen = sessionStorage.getItem(`${STORAGE_KEY}-hint`) === "1";
    } catch (e) {
      // ignore
    }
    if (seen) return undefined;
    const t = setTimeout(() => setShowHint(true), 4000);
    return () => clearTimeout(t);
  }, [hidden]);

  // Footer link (and anything else) can open the chat: window.dispatchEvent(new CustomEvent("roar-bot:open"))
  useEffect(() => {
    if (hidden) return undefined;
    const onOpen = () => openPanel();
    const onAsk = (e) => {
      const q = typeof e.detail === "string" ? e.detail : "";
      if (!q) return;
      if (!started) {
        setStarted(true);
        setOpen(true);
        ask("", "open").then(() => ask(q));
      } else {
        setOpen(true);
        ask(q);
      }
    };
    window.addEventListener("roar-bot:open", onOpen);
    window.addEventListener("roar-bot:ask", onAsk);
    return () => {
      window.removeEventListener("roar-bot:open", onOpen);
      window.removeEventListener("roar-bot:ask", onAsk);
    };
  });

  // Full-page mode starts the conversation by itself (once, even under StrictMode).
  useEffect(() => {
    if (!embedded || bootRef.current) return;
    bootRef.current = true;
    setStarted(true);
    (async () => {
      await ask("", "open");
      if (initialQuestion) await ask(initialQuestion);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [embedded]);

  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, busy, open]);

  const push = (role, payload) => {
    idSeq.current += 1;
    setMessages((m) => [...m, { id: idSeq.current, role, ...payload }]);
  };

  async function ask(text, action) {
    if (!sessionId.current) sessionId.current = loadSessionId();
    if (text) push("user", { text });
    setQuick([]);
    setBusy(true);
    try {
      const res = await api.botChat({ sessionId: sessionId.current, message: text || "", action });
      const data = res?.data || {};
      if (data.sessionId && data.sessionId !== sessionId.current) {
        sessionId.current = data.sessionId;
        try {
          sessionStorage.setItem(STORAGE_KEY, data.sessionId);
        } catch (e) {
          // ignore
        }
      }
      push("bot", { blocks: data.messages || [] });
      setQuick(data.quickReplies || []);
    } catch (err) {
      push("bot", { blocks: [{ type: "text", text: `Sorry, I couldn't reach the ROAR server (${err.message}). Please try again in a moment, or message the team on WhatsApp +91 92841 82675.` }] });
      setQuick([{ label: "Try again", send: text || "hi" }]);
    } finally {
      setBusy(false);
    }
  }

  function openPanel() {
    setOpen(true);
    setShowHint(false);
    try {
      sessionStorage.setItem(`${STORAGE_KEY}-hint`, "1");
    } catch (e) {
      // ignore
    }
    if (!started) {
      setStarted(true);
      ask("", "open");
    }
    setTimeout(() => inputRef.current && inputRef.current.focus(), 50);
  }

  function restart() {
    sessionId.current = newSessionId();
    try {
      sessionStorage.setItem(STORAGE_KEY, sessionId.current);
    } catch (e) {
      // ignore
    }
    setMessages([]);
    ask("", "open");
  }

  function submit(e) {
    e.preventDefault();
    const t = input.trim();
    if (!t || busy) return;
    setInput("");
    ask(t);
  }

  // Tapping a page link inside the chat closes the panel on phones so the page is visible.
  const onNavigate = () => {
    if (!embedded && typeof window !== "undefined" && window.innerWidth < 640) setOpen(false);
  };

  const rendered = useMemo(
    () =>
      messages.map((m) =>
        m.role === "user" ? (
          <div key={m.id} className="bot-msg is-user"><p className="bot-text">{m.text}</p></div>
        ) : (
          <div key={m.id} className="bot-msg is-bot">
            <img src={tiger} alt="" className="bot-avatar" />
            <div className="bot-bubbles">
              {m.blocks.map((b, i) => (
                <div key={i} className={`bot-bubble kind-${b.type}`}>
                  <Block block={b} onNavigate={onNavigate} />
                </div>
              ))}
            </div>
          </div>
        )
      ),
    [messages]
  );

  if (hidden) return null;

  return (
    <>
      {!open && !embedded && (
        <div className="bot-launcher-wrap">
          {showHint && (
            <div className="bot-hint" role="status">
              Ask anything about the expo — register, book a stall or track your booking, right here.
              <button type="button" aria-label="Dismiss" onClick={() => setShowHint(false)}><Icon name="close" size={14} /></button>
            </div>
          )}
          <button type="button" className="bot-launcher" onClick={openPanel} aria-label="Ask ROAR Anything">
            <img src={tiger} alt="" />
            <span className="bot-launcher-label">Ask ROAR <em>Anything</em></span>
          </button>
        </div>
      )}

      {open && (
        <section className={`bot-panel ${embedded ? "is-embedded" : ""}`} role={embedded ? "region" : "dialog"} aria-label="Ask ROAR Anything">
          <header className="bot-head">
            <img src={tiger} alt="" />
            <div>
              <div className="bot-head-title">Ask ROAR Anything</div>
              <div className="bot-head-sub"><i /> {embedded ? "ROAR Assistant · replies instantly" : "Replies instantly"}</div>
            </div>
            <button type="button" className="bot-icon-btn" onClick={restart} title="Start over" aria-label="Start over"><Icon name="spark" size={18} /></button>
            {!embedded && (
              <Link to="/ask" className="bot-icon-btn" title="Open full page" aria-label="Open the chat as a full page" onClick={() => setOpen(false)}>
                <Icon name="expand" size={17} />
              </Link>
            )}
            {!embedded && (
              <button type="button" className="bot-icon-btn" onClick={() => setOpen(false)} aria-label="Close chat"><Icon name="close" size={20} /></button>
            )}
          </header>

          <div className="bot-list" ref={listRef}>
            {rendered}
            {busy && (
              <div className="bot-msg is-bot">
                <img src={tiger} alt="" className="bot-avatar" />
                <div className="bot-bubbles"><div className="bot-bubble bot-typing"><span /><span /><span /></div></div>
              </div>
            )}
          </div>

          {quick.length > 0 && !busy && (
            <div className="bot-quick">
              {quick.map((q) => (
                <button type="button" key={q.label} className={`bot-chip ${q.primary ? "is-primary" : ""}`} onClick={() => ask(q.send || q.label)}>{q.label}</button>
              ))}
            </div>
          )}

          <form className="bot-input" onSubmit={submit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a question or your mobile number…"
              maxLength={500}
              autoComplete="off"
              aria-label="Message"
            />
            <button type="submit" disabled={!input.trim() || busy} aria-label="Send"><Icon name="plane" size={18} /></button>
          </form>
          <div className="bot-foot">Ask anything · visitor registration · book a stall · track by mobile · www.roarexpo.com/ask</div>
        </section>
      )}
    </>
  );
}
