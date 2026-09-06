import { useState } from "react";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import Icon from "./Icon";

function fieldsFromExhibitor(exhibitor) {
  return {
    companyName: exhibitor.companyName || "",
    contactPerson: exhibitor.contactPerson || "",
    designation: exhibitor.designation || "",
    email: exhibitor.email || "",
    phone: exhibitor.phone || "",
    whatsapp: exhibitor.whatsapp || "",
    businessAddress: exhibitor.businessAddress || "",
    city: exhibitor.city || "",
    state: exhibitor.state || "",
    pincode: exhibitor.pincode || "",
    gstNumber: exhibitor.gstNumber || "",
    category: exhibitor.category || "",
    productsServices: exhibitor.productsServices || "",
    stallPackage: exhibitor.stallPackage || "",
    numberOfStalls: exhibitor.numberOfStalls || 1,
    stallNumber: exhibitor.stallNumber || "",
    fasciaName: exhibitor.fasciaName || "",
  };
}

export default function ExhibitorEditModal({ exhibitor, token, onClose, onSaved }) {
  const { config } = useEventConfig();
  const [form, setForm] = useState(() => fieldsFromExhibitor(exhibitor));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await api.adminEditExhibitor(token, exhibitor._id, form);
      onSaved();
    } catch (err) {
      setError(err.message || "Failed to update exhibitor");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 style={{ marginBottom: 0 }}>Edit Exhibitor — {exhibitor.registrationCode}</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="modal-section-label">Company &amp; Contact</div>
            <div className="form-row">
              <div className="field">
                <label>Company Name</label>
                <input required value={form.companyName} onChange={(e) => update("companyName", e.target.value)} />
              </div>
              <div className="field">
                <label>Contact Person</label>
                <input required value={form.contactPerson} onChange={(e) => update("contactPerson", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Designation</label>
                <input value={form.designation} onChange={(e) => update("designation", e.target.value)} />
              </div>
              <div className="field">
                <label>Email</label>
                <input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Phone</label>
                <input required value={form.phone} onChange={(e) => update("phone", e.target.value)} />
              </div>
              <div className="field">
                <label>WhatsApp</label>
                <input value={form.whatsapp} onChange={(e) => update("whatsapp", e.target.value)} />
              </div>
            </div>

            <div className="modal-section-label">Address</div>
            <div className="field">
              <label>Business Address</label>
              <input value={form.businessAddress} onChange={(e) => update("businessAddress", e.target.value)} />
            </div>
            <div className="form-row">
              <div className="field">
                <label>City</label>
                <input value={form.city} onChange={(e) => update("city", e.target.value)} />
              </div>
              <div className="field">
                <label>State</label>
                <input value={form.state} onChange={(e) => update("state", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Pincode</label>
                <input value={form.pincode} onChange={(e) => update("pincode", e.target.value)} />
              </div>
              <div className="field">
                <label>GST Number</label>
                <input value={form.gstNumber} onChange={(e) => update("gstNumber", e.target.value)} />
              </div>
            </div>

            <div className="modal-section-label">Category &amp; Products</div>
            <div className="field">
              <label>Category</label>
              <select value={form.category} onChange={(e) => update("category", e.target.value)}>
                <option value="">Select…</option>
                {(config.categories || []).map((c) => (
                  <option key={c.key} value={c.label}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Products / Services</label>
              <textarea value={form.productsServices} onChange={(e) => update("productsServices", e.target.value)} />
            </div>

            <div className="modal-section-label">Stall Assignment</div>
            <div className="form-row">
              <div className="field">
                <label>Stall Package</label>
                <select value={form.stallPackage} onChange={(e) => update("stallPackage", e.target.value)}>
                  <option value="">Select…</option>
                  {(config.stallPackages || []).map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.label} — {p.rate != null ? `₹${Number(p.rate).toLocaleString("en-IN")}` : p.sizeLabel}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Number of Stalls</label>
                <input
                  type="number"
                  min={1}
                  value={form.numberOfStalls}
                  onChange={(e) => update("numberOfStalls", Number(e.target.value) || 1)}
                />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Stall Number</label>
                <input
                  placeholder="e.g. G-2, R-14, RU-33 (leave blank to unassign; not applicable for Food Court/Play Zone)"
                  value={form.stallNumber}
                  onChange={(e) => update("stallNumber", e.target.value)}
                />
              </div>
              <div className="field">
                <label>Fascia Name</label>
                <input value={form.fasciaName} onChange={(e) => update("fasciaName", e.target.value)} />
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
