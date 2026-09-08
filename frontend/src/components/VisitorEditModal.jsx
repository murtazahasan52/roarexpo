import { useState } from "react";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import Icon from "./Icon";

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

// Edit a visitor registration from the admin dashboard. The registration
// code itself isn't editable — it's what's printed inside the visitor's QR.
export default function VisitorEditModal({ visitor, token, onClose, onSaved }) {
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3 style={{ marginBottom: 2 }}>Edit Visitor — {visitor.registrationCode}</h3>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
              Registered {new Date(visitor.createdAt).toLocaleString()}
              {visitor.checkedInAt ? ` · checked in ${new Date(visitor.checkedInAt).toLocaleString()}` : ""}
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="modal-section-label">Visitor</div>
            <div className="form-row">
              <div className="field">
                <label>Full Name</label>
                <input required value={form.fullName} onChange={(e) => update("fullName", e.target.value)} />
              </div>
              <div className="field">
                <label>City</label>
                <input value={form.city} onChange={(e) => update("city", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Email</label>
                <input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
              </div>
              <div className="field">
                <label>Phone</label>
                <input required value={form.phone} onChange={(e) => update("phone", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Organization / Business</label>
                <input value={form.organization} onChange={(e) => update("organization", e.target.value)} />
              </div>
              <div className="field">
                <label>Designation</label>
                <input value={form.designation} onChange={(e) => update("designation", e.target.value)} />
              </div>
            </div>

            <div className="field">
              <label>Interested categories</label>
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
            </div>

            <div className="modal-section-label">Registration</div>
            <div className="form-row">
              <div className="field">
                <label>How did they hear about ROAR?</label>
                <select value={form.howDidYouHear} onChange={(e) => update("howDidYouHear", e.target.value)}>
                  <option value="">—</option>
                  {hearOptions.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Number of Guests (incl. visitor)</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={form.numberOfGuests}
                  onChange={(e) => update("numberOfGuests", e.target.value)}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Source</label>
                <select value={form.source} onChange={(e) => update("source", e.target.value)}>
                  <option value="online">Online (website)</option>
                  <option value="onsite">Onsite (entrance QR)</option>
                </select>
              </div>
              <div className="field">
                <label>Check-in status</label>
                <select value={form.checkedIn ? "yes" : "no"} onChange={(e) => update("checkedIn", e.target.value === "yes")}>
                  <option value="no">Not checked in</option>
                  <option value="yes">Checked in</option>
                </select>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
