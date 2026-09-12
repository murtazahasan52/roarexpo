import { useState } from "react";
import { api } from "../api";
import RecordFrame from "./RecordFrame";

const SHOW = (v) => v || <span className="field-empty">—</span>;

// View / edit one enquiry from the public Enquiry page. `readOnly` shows the
// message without inputs; `asPage` renders as a full page card.
export default function EnquiryEditModal({ enquiry, token, onClose, onSaved, readOnly = false, asPage = false, headerActions = null }) {
  const [form, setForm] = useState({
    name: enquiry.name || "",
    email: enquiry.email || "",
    mobile: enquiry.mobile || "",
    details: enquiry.details || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (readOnly) return;
    setError("");
    setSaving(true);
    try {
      await api.adminUpdateEnquiry(token, enquiry._id, form);
      onSaved();
    } catch (err) {
      setError(err.message || "Failed to update enquiry");
    } finally {
      setSaving(false);
    }
  }

  const field = (label, name, { type = "text", required = false } = {}) => (
    <div key={name} className="field">
      <label>{label}</label>
      {readOnly ? (
        <div className="field-readonly">{SHOW(form[name])}</div>
      ) : (
        <input type={type} required={required} value={form[name]} onChange={(e) => update(name, e.target.value)} />
      )}
    </div>
  );

  return (
    <RecordFrame
      asPage={asPage}
      onClose={onClose}
      title={`${readOnly ? "Enquiry" : "Edit Enquiry"} — ${enquiry.name}`}
      subtitle={`${enquiry.status === "handled" ? "Handled" : "New"} · received ${new Date(enquiry.createdAt).toLocaleString()}${
        enquiry.handledAt ? ` · handled ${new Date(enquiry.handledAt).toLocaleString()}` : ""
      }`}
      error={error}
      actions={headerActions}
    >
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          <div className="form-row">
            {field("Name", "name", { required: true })}
            {field("Mobile", "mobile", { required: true })}
          </div>
          <div className="field">
            <label>Email</label>
            {readOnly ? (
              <div className="field-readonly">
                {form.email ? <a href={`mailto:${form.email}`}>{form.email}</a> : SHOW("")}
              </div>
            ) : (
              <input type="email" required value={form.email} onChange={(e) => update("email", e.target.value)} />
            )}
          </div>
          <div className="field">
            <label>Enquiry Details</label>
            {readOnly ? (
              <div className="field-readonly" style={{ whiteSpace: "pre-wrap" }}>{SHOW(form.details)}</div>
            ) : (
              <textarea required rows={8} value={form.details} onChange={(e) => update("details", e.target.value)} />
            )}
          </div>
          {readOnly && (
            <div className="form-row">
              <div className="field">
                <label>Team notified</label>
                <div className="field-readonly">
                  <span className={`badge ${enquiry.emailSent ? "badge-green" : "badge-gray"}`}>{enquiry.emailSent ? "Email sent" : "Pending"}</span>
                  {enquiry.emailError && <span style={{ color: "var(--rose-500)", marginLeft: 8, fontSize: 12.5 }}>{enquiry.emailError}</span>}
                </div>
              </div>
              <div className="field">
                <label>Auto-reply to sender</label>
                <div className="field-readonly">
                  <span className={`badge ${enquiry.ackSent ? "badge-green" : "badge-gray"}`}>{enquiry.ackSent ? "Sent" : "—"}</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-outline" onClick={onClose}>
            {readOnly ? (asPage ? "Back" : "Close") : "Cancel"}
          </button>
          {!readOnly && (
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
          )}
        </div>
      </form>
    </RecordFrame>
  );
}
