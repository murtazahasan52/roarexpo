import { useState } from "react";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import RecordFrame from "./RecordFrame";

const hearOptions = ["Social Media", "WhatsApp", "Friend / Colleague", "Newspaper", "Organizer Invite", "Other"];

function fieldsFromVisitor(v) {
  return {
    fullName: v.fullName || "",
    email: v.email || "",
    phone: v.phone || "",
    city: v.city || "",
    organization: v.organization || "",
    designation: v.designation || "",
    interests: v.interests || [],
    howDidYouHear: v.howDidYouHear || "",
    numberOfGuests: v.numberOfGuests || 1,
    source: v.source || "online",
    checkedIn: Boolean(v.checkedIn),
  };
}

const SHOW = (v) => v || <span className="field-empty">—</span>;

// View / edit a visitor registration from the admin dashboard. The
// registration code itself isn't editable — it's what's printed inside the
// visitor's QR. `readOnly` shows the fields without inputs; `asPage` renders
// as a full page card instead of a modal.
export default function VisitorEditModal({ visitor, token, onClose, onSaved, readOnly = false, asPage = false, headerActions = null }) {
  const { config } = useEventConfig();
  const [form, setForm] = useState(() => fieldsFromVisitor(visitor));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function toggleInterest(label) {
    setForm((f) => {
      const has = f.interests.includes(label);
      return { ...f, interests: has ? f.interests.filter((i) => i !== label) : [...f.interests, label] };
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (readOnly) return;
    setError("");
    setSaving(true);
    try {
      await api.adminEditVisitor(token, visitor._id, { ...form, numberOfGuests: Number(form.numberOfGuests) || 1 });
      onSaved();
    } catch (err) {
      setError(err.message || "Failed to update visitor");
    } finally {
      setSaving(false);
    }
  }

  // Plain render helper (not a nested component, so inputs keep focus).
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
      title={`${readOnly ? "Visitor Details" : "Edit Visitor"} — ${visitor.registrationCode}`}
      subtitle={`Registered ${new Date(visitor.createdAt).toLocaleString()}${
        visitor.checkedInAt ? ` · checked in ${new Date(visitor.checkedInAt).toLocaleString()}` : ""
      }`}
      error={error}
      actions={headerActions}
    >
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="modal-section-label">Visitor</div>
            <div className="form-row">
              {field("Full Name", "fullName", { required: true })}
              {field("City", "city")}
            </div>
            <div className="form-row">
              {field("Email", "email", { type: "email", required: true })}
              {field("Phone", "phone", { required: true })}
            </div>
            <div className="form-row">
              {field("Organization / Business", "organization")}
              {field("Designation", "designation")}
            </div>

            <div className="field">
              <label>Interested categories</label>
              {readOnly ? (
                <div className="field-readonly">{SHOW(form.interests.join(", "))}</div>
              ) : (
                <div className="pill-group">
                  {(config.categories || []).map((c) => (
                    <div
                      key={c.key}
                      className={`pill ${form.interests.includes(c.label) ? "selected" : ""}`}
                      onClick={() => toggleInterest(c.label)}
                      role="button"
                      tabIndex={0}
                    >
                      {c.label}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-section-label">Registration</div>
            <div className="form-row">
              <div className="field">
                <label>How did they hear about ROAR?</label>
                {readOnly ? (
                  <div className="field-readonly">{SHOW(form.howDidYouHear)}</div>
                ) : (
                  <select value={form.howDidYouHear} onChange={(e) => update("howDidYouHear", e.target.value)}>
                    <option value="">—</option>
                    {hearOptions.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="field">
                <label>Number of Guests (incl. visitor)</label>
                {readOnly ? (
                  <div className="field-readonly">{form.numberOfGuests}</div>
                ) : (
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={form.numberOfGuests}
                    onChange={(e) => update("numberOfGuests", e.target.value)}
                  />
                )}
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Source</label>
                {readOnly ? (
                  <div className="field-readonly">{form.source === "onsite" ? "Onsite (entrance QR)" : "Online (website)"}</div>
                ) : (
                  <select value={form.source} onChange={(e) => update("source", e.target.value)}>
                    <option value="online">Online (website)</option>
                    <option value="onsite">Onsite (entrance QR)</option>
                  </select>
                )}
              </div>
              <div className="field">
                <label>Check-in status</label>
                {readOnly ? (
                  <div className="field-readonly">
                    <span className={`badge ${form.checkedIn ? "badge-green" : "badge-gray"}`}>{form.checkedIn ? "Checked in" : "Not checked in"}</span>
                  </div>
                ) : (
                  <select value={form.checkedIn ? "yes" : "no"} onChange={(e) => update("checkedIn", e.target.value === "yes")}>
                    <option value="no">Not checked in</option>
                    <option value="yes">Checked in</option>
                  </select>
                )}
              </div>
            </div>
            {readOnly && (
              <>
                <div className="modal-section-label">Delivery</div>
                <div className="form-row">
                  <div className="field">
                    <label>Invitation email</label>
                    <div className="field-readonly">
                      <span className={`badge ${visitor.emailSent ? "badge-green" : "badge-gray"}`}>{visitor.emailSent ? "Sent" : "Pending"}</span>
                      {visitor.emailError && <span style={{ color: "var(--rose-500)", marginLeft: 8, fontSize: 12.5 }}>{visitor.emailError}</span>}
                    </div>
                  </div>
                  <div className="field">
                    <label>WhatsApp</label>
                    <div className="field-readonly">
                      <span className={`badge ${visitor.whatsappSent ? "badge-green" : "badge-gray"}`}>{visitor.whatsappSent ? "Sent" : "—"}</span>
                    </div>
                  </div>
                </div>
              </>
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
