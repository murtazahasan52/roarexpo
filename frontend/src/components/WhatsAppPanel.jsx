import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

const SUB_TABS = [
  { key: "config", label: "Config" },
  { key: "templates", label: "Templates" },
  { key: "broadcast", label: "Broadcast" },
  { key: "logs", label: "Logs" },
];

const AUDIENCES = [
  { key: "all", label: "Everyone (visitors + exhibitors)" },
  { key: "visitors", label: "All visitors" },
  { key: "exhibitors", label: "All exhibitors" },
  { key: "confirmed_exhibitors", label: "Confirmed exhibitors" },
  { key: "pending_exhibitors", label: "Pending exhibitors" },
  { key: "unpaid_exhibitors", label: "Unpaid exhibitors" },
];

function ConfigTab({ token }) {
  const [cfg, setCfg] = useState(null);
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [testPhone, setTestPhone] = useState("");
  const [testMsg, setTestMsg] = useState("");
  const [testOk, setTestOk] = useState(false);

  const load = useCallback(async () => {
    const r = await api.adminWaGetConfig(token);
    setCfg(r.data);
  }, [token]);
  useEffect(() => { load(); }, [load]);

  if (!cfg) return <p style={{ color: "var(--text-muted)" }}>Loading…</p>;

  const set = (k, v) => setCfg((c) => ({ ...c, [k]: v }));

  async function save() {
    setSaving(true); setMsg("");
    try {
      const payload = {
        enabled: cfg.enabled, senderId: cfg.senderId, bhashUser: cfg.bhashUser,
        apiBaseUrl: cfg.apiBaseUrl, priority: cfg.priority, stype: cfg.stype,
      };
      if (password) payload.bhashPassword = password;
      const r = await api.adminWaSaveConfig(token, payload);
      setCfg(r.data); setPassword(""); setMsg("Settings saved.");
    } catch (e) { setMsg(e.message || "Could not save."); }
    finally { setSaving(false); }
  }

  async function sendTest() {
    setTestMsg("");
    try {
      const r = await api.adminWaTest(token, { phone: testPhone });
      setTestOk(!!r.success);
      setTestMsg(r.message || (r.success ? "Sent." : "Failed."));
    } catch (e) { setTestOk(false); setTestMsg(e.message || "Failed."); }
  }

  return (
    <div className="card form-card" style={{ maxWidth: 860 }}>
      <p style={{ marginTop: 0, color: "var(--text-muted)", fontSize: 13.5 }}>
        BhashSMS DLT-approved WhatsApp templates. Messages are sent for registrations, approval, rejection,
        payment status and broadcasts. Turn this on only after your templates are DLT-approved.
      </p>
      <label className="wa-toggle" data-testid="wa-enabled-toggle">
        <input type="checkbox" checked={!!cfg.enabled} onChange={(e) => set("enabled", e.target.checked)} />
        <span>WhatsApp messaging {cfg.enabled ? "enabled" : "disabled"}</span>
      </label>
      <div className="form-row" style={{ marginTop: 14 }}>
        <div className="field">
          <label>Provider</label>
          <div className="field-readonly">BhashSMS (DLT-approved templates)</div>
        </div>
        <div className="field">
          <label>Sender ID (DLT)</label>
          <input value={cfg.senderId || ""} onChange={(e) => set("senderId", e.target.value)} data-testid="wa-sender" />
        </div>
      </div>
      <div className="form-row">
        <div className="field">
          <label>BhashSMS User</label>
          <input value={cfg.bhashUser || ""} onChange={(e) => set("bhashUser", e.target.value)} data-testid="wa-user" autoComplete="off" />
        </div>
        <div className="field">
          <label>BhashSMS Password {cfg.hasPassword && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(set — leave blank to keep)</span>}</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={cfg.hasPassword ? "••••••" : "Enter password"} data-testid="wa-password" autoComplete="new-password" />
        </div>
      </div>
      <div className="field">
        <label>API Base URL</label>
        <input value={cfg.apiBaseUrl || ""} onChange={(e) => set("apiBaseUrl", e.target.value)} data-testid="wa-apiurl" />
      </div>
      <div className="form-row">
        <div className="field">
          <label>Priority</label>
          <input value={cfg.priority || ""} onChange={(e) => set("priority", e.target.value)} data-testid="wa-priority" />
        </div>
        <div className="field">
          <label>stype</label>
          <input value={cfg.stype || ""} onChange={(e) => set("stype", e.target.value)} data-testid="wa-stype" />
        </div>
      </div>
      {msg && <div className="alert alert-success" style={{ marginTop: 8 }}>{msg}</div>}
      <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
        <button className="btn btn-outline" onClick={load} disabled={saving}>Reload</button>
        <button className="btn btn-primary" onClick={save} disabled={saving} data-testid="wa-save-config">{saving ? "Saving…" : "Save Config"}</button>
      </div>

      <div style={{ marginTop: 24, paddingTop: 18, borderTop: "1px solid var(--border-soft, #ece4d6)" }}>
        <strong style={{ fontSize: 14 }}>Send a test message</strong>
        <div style={{ display: "flex", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
          <input className="search-input" placeholder="10-digit mobile number" value={testPhone} onChange={(e) => setTestPhone(e.target.value)} data-testid="wa-test-phone" />
          <button className="btn btn-dark" style={{ padding: "10px 18px" }} onClick={sendTest} data-testid="wa-test-send">Send Test</button>
        </div>
        {testMsg && <div className={`alert ${testOk ? "alert-success" : "alert-error"}`} style={{ marginTop: 10 }} data-testid="wa-test-result">{testMsg}</div>}
      </div>
    </div>
  );
}

function TemplatesTab({ token }) {
  const [rows, setRows] = useState([]);
  const [savingKey, setSavingKey] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const r = await api.adminWaTemplates(token);
    setRows(r.data);
  }, [token]);
  useEffect(() => { load(); }, [load]);

  function edit(key, field, value) {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, [field]: value } : r)));
  }

  async function save(t) {
    setSavingKey(t.key); setMsg("");
    try {
      await api.adminWaSaveTemplate(token, t.key, { body: t.body, enabled: t.enabled, templateName: t.templateName || "" });
      setMsg(`Saved "${t.label}".`);
    } catch (e) { setMsg(e.message || "Could not save."); }
    finally { setSavingKey(""); }
  }

  async function testOne(t) {
    const phone = window.prompt(`Send a test "${t.label}" WhatsApp to which number? (10-digit)`);
    if (!phone) return;
    try {
      const r = await api.adminWaTest(token, { phone: phone.trim(), templateKey: t.key });
      setMsg(r.message || (r.success ? "Test sent." : "Test failed."));
    } catch (e) { setMsg(e.message || "Test failed."); }
  }

  return (
    <div>
      {msg && <div className="alert alert-success" style={{ marginBottom: 12 }}>{msg}</div>}
      <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 0 }}>
        Use {"{{1}}"}, {"{{2}}"} … for variables (in order). No line breaks; keep variable values free of #, $, % for DLT approval.
      </p>
      <div style={{ display: "grid", gap: 16 }}>
        {rows.map((t) => (
          <div className="card" style={{ padding: 18 }} key={t.key} data-testid={`wa-template-${t.key}`}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div>
                <strong>{t.label}</strong>
                <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>{t.description}</div>
              </div>
              <label className="wa-toggle">
                <input type="checkbox" checked={!!t.enabled} onChange={(e) => edit(t.key, "enabled", e.target.checked)} data-testid={`wa-template-enabled-${t.key}`} />
                <span>{t.enabled ? "On" : "Off"}</span>
              </label>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", margin: "8px 0" }}>
              Variables: {t.variables.map((v, i) => `{{${i + 1}}} = ${v}`).join("  ·  ")}
            </div>
            <div className="field" style={{ marginBottom: 10 }}>
              <label style={{ fontSize: 12.5 }}>DLT Template Name <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(the BhashSMS/WhatsApp-approved name — leave blank to send full text)</span></label>
              <input value={t.templateName || ""} onChange={(e) => edit(t.key, "templateName", e.target.value)} placeholder="e.g. roar_visitor_registration" data-testid={`wa-template-name-${t.key}`} autoComplete="off" />
            </div>
            <textarea value={t.body} onChange={(e) => edit(t.key, "body", e.target.value)} rows={3} style={{ width: "100%" }} data-testid={`wa-template-body-${t.key}`} />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
              <button className="btn btn-outline" onClick={() => testOne(t)} data-testid={`wa-template-test-${t.key}`}>Send Test</button>
              <button className="btn btn-primary" onClick={() => save(t)} disabled={savingKey === t.key} data-testid={`wa-template-save-${t.key}`}>
                {savingKey === t.key ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function BroadcastTab({ token }) {
  const [templateKey, setTemplateKey] = useState("reminder");
  const [audience, setAudience] = useState("all");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState("");

  async function send() {
    if (!window.confirm(`Send this WhatsApp ${templateKey === "reminder" ? "reminder" : "information message"} to: ${AUDIENCES.find((a) => a.key === audience)?.label}?`)) return;
    setSending(true); setResult("");
    try {
      const r = await api.adminWaBroadcast(token, { templateKey, audience, message });
      setResult(r.message || "Broadcast finished.");
    } catch (e) { setResult(e.message || "Broadcast failed."); }
    finally { setSending(false); }
  }

  return (
    <div className="card form-card" style={{ maxWidth: 720 }}>
      <div className="field">
        <label>Message type</label>
        <select value={templateKey} onChange={(e) => setTemplateKey(e.target.value)} data-testid="wa-broadcast-template">
          <option value="reminder">Event Reminder</option>
          <option value="info_broadcast">Information Message</option>
        </select>
      </div>
      <div className="field">
        <label>Audience</label>
        <select value={audience} onChange={(e) => setAudience(e.target.value)} data-testid="wa-broadcast-audience">
          {AUDIENCES.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}
        </select>
      </div>
      {templateKey === "info_broadcast" && (
        <div className="field">
          <label>Information message <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(fills the {"{{2}}"} variable)</span></label>
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} placeholder="e.g. Gates open at 10 AM. Please carry your registration ID." data-testid="wa-broadcast-message" />
        </div>
      )}
      <button className="btn btn-primary" onClick={send} disabled={sending} data-testid="wa-broadcast-send">
        {sending ? "Sending…" : "Send Broadcast"}
      </button>
      {result && <div className="alert alert-success" style={{ marginTop: 12 }} data-testid="wa-broadcast-result">{result}</div>}
    </div>
  );
}

function LogsTab({ token }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 30;

  const load = useCallback(async () => {
    const r = await api.adminWaLogs(token, `?page=${page}&limit=${limit}`);
    setRows(r.data); setTotal(r.total);
  }, [token, page]);
  useEffect(() => { load(); }, [load]);

  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <button className="btn btn-outline" onClick={load}>Refresh</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>When</th><th>To</th><th>Template</th><th>Status</th><th>Message</th><th>Reason / Response</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r._id}>
                <td>{new Date(r.createdAt).toLocaleString()}</td>
                <td>{r.to}</td>
                <td>{r.templateKey}</td>
                <td>
                  <span className={`badge ${r.status === "sent" ? "badge-green" : r.status === "failed" ? "badge-navy" : "badge-gray"}`}>{r.status}</span>
                </td>
                <td style={{ maxWidth: 320, fontSize: 12.5 }}>{r.text}</td>
                <td style={{ maxWidth: 220, fontSize: 12, color: "var(--text-muted)" }}>{r.reason || r.providerResponse || "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)" }}>No messages sent yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {pageCount > 1 && (
        <div className="pagination">
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
            <button key={p} className={`admin-tab ${p === page ? "active" : ""}`} style={{ padding: "6px 14px" }} onClick={() => setPage(p)}>{p}</button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WhatsAppPanel({ token }) {
  const [sub, setSub] = useState("config");
  return (
    <div>
      <div className="toolbar" style={{ marginBottom: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>WhatsApp Service</h3>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>BhashSMS (DLT-approved templates)</p>
        </div>
      </div>
      <div className="admin-tabs" style={{ marginBottom: 16 }}>
        {SUB_TABS.map((t) => (
          <div key={t.key} className={`admin-tab ${sub === t.key ? "active" : ""}`} onClick={() => setSub(t.key)} data-testid={`wa-subtab-${t.key}`}>
            {t.label}
          </div>
        ))}
      </div>
      {sub === "config" && <ConfigTab token={token} />}
      {sub === "templates" && <TemplatesTab token={token} />}
      {sub === "broadcast" && <BroadcastTab token={token} />}
      {sub === "logs" && <LogsTab token={token} />}
    </div>
  );
}
