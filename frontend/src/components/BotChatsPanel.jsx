import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

// Admin dashboard "Chats (Ask ROAR)" tab — every conversation the website
// assistant had: what was asked, what it answered, which ones registered a
// visitor or asked for a callback, the questions it could not answer (so the
// team can add them to the bot's facts), and the ratings visitors left.
const FILTERS = [
  ["all", "All"],
  ["registered", "Registered via chat"],
  ["stall-booked", "Stalls booked via chat"],
  ["callback", "Callback requests"],
  ["enquiry", "Enquiries"],
  ["unanswered", "Unanswered questions"],
  ["rated", "Rated"],
];

const LANG = { en: "English", hin: "Hinglish", hi: "Hindi" };

// Outcome badges; topic tags ("kb:…") and flow markers stay out of the table.
const TAG_LABEL = {
  registered: "Visitor registered", "stall-booked": "Stall booked", callback: "Callback", enquiry: "Enquiry",
  reserved: "Stall reserved", rated: "Rated", ai: "AI answer",
};
const visibleTags = (tags) => (tags || []).filter((t) => TAG_LABEL[t]);

function fmt(d) {
  if (!d) return "—";
  const t = new Date(d);
  return `${t.toLocaleDateString()} ${t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function Stars({ n }) {
  if (!n) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  return <span title={`${n} / 5`} style={{ color: "var(--gold-600)", letterSpacing: 1 }}>{"★".repeat(n)}<span style={{ color: "var(--border-soft)" }}>{"★".repeat(5 - n)}</span></span>;
}

export default function BotChatsPanel({ token }) {
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(null); // full chat document
  const [busy, setBusy] = useState("");
  const limit = 25;

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const qs = `?search=${encodeURIComponent(search)}&page=${page}&limit=${limit}${filter !== "all" ? `&filter=${filter}` : ""}`;
      const [list, st] = await Promise.all([api.adminBotChats(token, qs), api.adminBotStats(token).catch(() => null)]);
      setRows(list.data || []);
      setTotal(list.total || 0);
      if (st?.data) setStats(st.data);
    } catch (err) {
      alert(err.message || "Failed to load chats");
    } finally {
      setLoading(false);
    }
  }, [token, search, page, filter]);

  useEffect(() => {
    setPage(1);
  }, [search, filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function view(row) {
    setBusy(row.sessionId);
    try {
      const res = await api.adminBotChat(token, row.sessionId);
      setOpen(res.data);
    } catch (err) {
      alert(err.message || "Could not open the chat");
    } finally {
      setBusy("");
    }
  }

  async function remove(row) {
    if (!window.confirm("Delete this chat log? This cannot be undone.")) return;
    setBusy(row.sessionId);
    try {
      await api.adminDeleteBotChat(token, row.sessionId);
      if (open?.sessionId === row.sessionId) setOpen(null);
      await load();
    } catch (err) {
      alert(err.message || "Delete failed");
    } finally {
      setBusy("");
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <>
      {stats && (
        <div className="admin-stats" style={{ marginBottom: 18 }}>
          <div className="card admin-stat-card"><div className="admin-stat-num">{stats.total}</div><div className="admin-stat-label">Chats</div><div className="admin-stat-sub">{stats.today} in the last 24 h{stats.avgRating ? ` · ★ ${stats.avgRating} from ${stats.ratings} rating${stats.ratings === 1 ? "" : "s"}` : ""}</div></div>
          <div className="card admin-stat-card"><div className="admin-stat-num">{stats.registered}</div><div className="admin-stat-label">Visitors registered via chat</div></div>
          <div className="card admin-stat-card"><div className="admin-stat-num">{stats.stallBooked ?? 0}</div><div className="admin-stat-label">Stalls booked via chat</div><div className="admin-stat-sub">in Exhibitors, pending approval</div></div>
          <div className="card admin-stat-card"><div className="admin-stat-num">{(stats.callbacks || 0) + (stats.enquiries || 0)}</div><div className="admin-stat-label">Callbacks & enquiries</div><div className="admin-stat-sub">also in the Enquiries tab</div></div>
          <div className="card admin-stat-card"><div className="admin-stat-num">{stats.unanswered}</div><div className="admin-stat-label">Chats with unanswered questions</div></div>
        </div>
      )}

      <div className="toolbar" style={{ flexWrap: "wrap", gap: 12 }}>
        <input className="search-input" placeholder="Search what visitors asked…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div className="admin-tabs" style={{ margin: 0 }}>
          {FILTERS.map(([value, label]) => (
            <div key={value} className={`admin-tab ${filter === value ? "active" : ""}`} onClick={() => setFilter(value)}>{label}</div>
          ))}
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Last activity</th>
              <th>Messages</th>
              <th>Language</th>
              <th>Last question</th>
              <th>Outcome</th>
              <th>Unanswered</th>
              <th>Rating</th>
              <th className="row-actions-cell">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} style={{ color: "var(--text-muted)" }}>Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={8} style={{ color: "var(--text-muted)" }}>No chats yet.</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.sessionId}>
                  <td style={{ whiteSpace: "nowrap" }}>{fmt(r.updatedAt)}<div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>started {fmt(r.createdAt)}</div></td>
                  <td>{r.count || 0}</td>
                  <td>{LANG[r.lang] || r.lang || "—"}</td>
                  <td style={{ maxWidth: 320 }}>{r.lastUserText || "—"}</td>
                  <td>
                    {visibleTags(r.tags).length === 0 ? <span style={{ color: "var(--text-muted)" }}>—</span> : null}
                    {visibleTags(r.tags).map((t) => (
                      <span key={t} className={`badge ${t === "registered" || t === "stall-booked" ? "badge-green" : t === "callback" || t === "enquiry" ? "badge-gold" : "badge-navy"}`} style={{ marginRight: 4 }}>
                        {TAG_LABEL[t] || t}
                      </span>
                    ))}
                  </td>
                  <td style={{ maxWidth: 260, fontSize: 12.5 }}>{(r.unanswered || []).length ? (r.unanswered || []).slice(-2).map((q, i) => <div key={i}>“{q}”</div>) : <span style={{ color: "var(--text-muted)" }}>—</span>}</td>
                  <td><Stars n={r.rating} />{r.comment ? <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{r.comment}</div> : null}</td>
                  <td className="row-actions-cell">
                    <div className="row-actions">
                      <button className="btn btn-outline" style={{ padding: "6px 12px", fontSize: 12.5 }} disabled={busy === r.sessionId} onClick={() => view(r)}>Transcript</button>
                      <button className="btn btn-outline btn-danger-outline" style={{ padding: "6px 12px", fontSize: 12.5 }} disabled={busy === r.sessionId} onClick={() => remove(r)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="toolbar" style={{ justifyContent: "flex-end", gap: 10 }}>
          <button className="btn btn-outline" style={{ padding: "6px 14px" }} disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹ Prev</button>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Page {page} of {pageCount}</span>
          <button className="btn btn-outline" style={{ padding: "6px 14px" }} disabled={page >= pageCount} onClick={() => setPage((p) => p + 1)}>Next ›</button>
        </div>
      )}

      {open && (
        <div className="modal-overlay" onClick={() => setOpen(null)}>
          <div className="modal-panel card modal-panel-wide" style={{ maxWidth: 680 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 style={{ margin: 0 }}>Chat transcript</h3>
                <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
                  {fmt(open.createdAt)} → {fmt(open.updatedAt)} · {LANG[open.lang] || open.lang || "English"} · {open.count || 0} messages
                  {open.rating ? <> · <Stars n={open.rating} /></> : null}
                </div>
              </div>
              <button type="button" className="btn btn-outline" style={{ padding: "6px 14px" }} onClick={() => setOpen(null)}>Close</button>
            </div>
            <div className="bot-transcript">
              {(open.messages || []).map((m, i) => (
                <div key={i} className={`bot-transcript-row ${m.r === "u" ? "is-user" : "is-bot"}`}>
                  <span className="bot-transcript-who">{m.r === "u" ? "Visitor" : "ROAR"}</span>
                  <span className="bot-transcript-text">{m.t}</span>
                  <span className="bot-transcript-time">{m.at ? new Date(m.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}</span>
                </div>
              ))}
              {(open.unanswered || []).length > 0 && (
                <div className="bot-transcript-unanswered">
                  <strong>Couldn't answer:</strong> {(open.unanswered || []).map((q, i) => <span key={i}>“{q}”{i < open.unanswered.length - 1 ? ", " : ""}</span>)}
                  <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>Add the answer to backend/config/bot_config.py (or set an AI key) so the bot handles it next time.</div>
                </div>
              )}
              {open.comment && <div className="bot-transcript-unanswered"><strong>Feedback:</strong> {open.comment}</div>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
