import { useEffect, useState } from "react";
import { api, fileUrl } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import RecordFrame from "./RecordFrame";

// Uploaded files are served under the API base (see api.fileUrl).


function fieldsFromExhibitor(exhibitor) {
  return {
    itsNumber: exhibitor.itsNumber || "",
    companyName: exhibitor.companyName || "",
    contactPerson: exhibitor.contactPerson || "",
    designation: exhibitor.designation || "",
    email: exhibitor.email || "",
    phone: exhibitor.phone || "",
    landline: exhibitor.landline || "",
    whatsapp: exhibitor.whatsapp || "",
    businessAddress: exhibitor.businessAddress || "",
    businessEmail: exhibitor.businessEmail || "",
    city: exhibitor.city || "",
    state: exhibitor.state || "",
    pincode: exhibitor.pincode || "",
    website: exhibitor.website || "",
    gstNumber: exhibitor.gstNumber || "",
    linkedin: exhibitor.linkedin || "",
    instagram: exhibitor.instagram || "",
    facebook: exhibitor.facebook || "",
    category: exhibitor.category || "",
    productsServices: exhibitor.productsServices || "",
    message: exhibitor.message || "",
    stallPackage: exhibitor.stallPackage || "",
    numberOfStalls: exhibitor.numberOfStalls || 1,
    stallNumber: exhibitor.stallNumber || "",
    fasciaName: exhibitor.fasciaName || "",
  };
}

const STATUS_LABEL = { pending: "Pending approval", confirmed: "Confirmed", cancelled: "Cancelled" };
const STALL_STATUS_LABEL = { available: "available", held: "pending confirmation", booked: "booked", blocked: "blocked" };

// View / edit an exhibitor registration. `readOnly` shows every field the
// exhibitor submitted (including logo and product images) without inputs —
// used for the "View" button and for admins who can see but not manage
// exhibitors. Otherwise every editable field is a form control, and the
// stall number is picked from the live list of stalls in the chosen
// rate-card category (the exhibitor's current stall stays selectable even
// though it's no longer "available").
export default function ExhibitorEditModal({ exhibitor, token, onClose, onSaved, readOnly = false, asPage = false, headerActions = null }) {
  const { config } = useEventConfig();
  const [form, setForm] = useState(() => fieldsFromExhibitor(exhibitor));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [stalls, setStalls] = useState([]);
  const [stallsLoading, setStallsLoading] = useState(false);

  const selectedPackage = (config.stallPackages || []).find((p) => p.code === form.stallPackage);
  const hasPicker = Boolean(selectedPackage?.hasStallPicker);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  // Load the stalls for whichever category is selected, so the stall number
  // can be chosen from a list rather than typed.
  useEffect(() => {
    if (readOnly || !hasPicker || !form.stallPackage) {
      setStalls([]);
      return;
    }
    let cancelled = false;
    setStallsLoading(true);
    api
      .getStalls(form.stallPackage)
      .then((res) => !cancelled && setStalls(res.data || []))
      .catch(() => !cancelled && setStalls([]))
      .finally(() => !cancelled && setStallsLoading(false));
    return () => {
      cancelled = true;
    };
  }, [form.stallPackage, hasPicker, readOnly]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (readOnly) return;
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

  // Stall options: everything still available in this category, plus the
  // exhibitor's own current stall (which is held/booked by them).
  const stallOptions = stalls.filter((s) => s.status === "available" || s.stallNumber === exhibitor.stallNumber);
  const currentStallKnown = !form.stallNumber || stallOptions.some((s) => s.stallNumber === form.stallNumber);

  // Plain render helper (NOT a nested component — a component defined inside
  // render would remount on every keystroke and drop input focus).
  const field = (label, name, { type = "text", required = false, placeholder = "" } = {}) => (
    <div key={name} className="field">
      <label>{label}</label>
      {readOnly ? (
        <div className="field-readonly">{form[name] || <span className="field-empty">—</span>}</div>
      ) : (
        <input
          type={type}
          required={required}
          placeholder={placeholder}
          value={form[name]}
          onChange={(e) => update(name, e.target.value)}
        />
      )}
    </div>
  );

  return (
    <RecordFrame
      asPage={asPage}
      onClose={onClose}
      title={`${readOnly ? "Exhibitor Details" : "Edit Exhibitor"} — ${exhibitor.registrationCode}`}
      subtitle={`${STATUS_LABEL[exhibitor.status] || exhibitor.status} · registered ${new Date(exhibitor.createdAt).toLocaleString()}`}
      error={error}
      actions={headerActions}
    >
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="modal-section-label">Stall Assignment</div>
            <div className="form-row">
              <div className="field">
                <label>Stall Package</label>
                {readOnly ? (
                  <div className="field-readonly">{selectedPackage?.label || form.stallPackage || "—"}</div>
                ) : (
                  <select
                    value={form.stallPackage}
                    onChange={(e) => {
                      update("stallPackage", e.target.value);
                      // A different category has different stalls — clear the pick.
                      if (e.target.value !== exhibitor.stallPackage) update("stallNumber", "");
                      else update("stallNumber", exhibitor.stallNumber || "");
                    }}
                  >
                    <option value="">Select…</option>
                    {(config.stallPackages || []).map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.label} — {p.rate != null ? `₹${Number(p.rate).toLocaleString("en-IN")}` : p.sizeLabel}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              <div className="field">
                <label>Stall Number</label>
                {readOnly ? (
                  <div className="field-readonly">
                    {form.stallNumber || <span className="field-empty">Not assigned</span>}
                    {exhibitor.stallRate != null && (
                      <span style={{ color: "var(--text-muted)" }}> · ₹{Number(exhibitor.stallRate).toLocaleString("en-IN")}</span>
                    )}
                  </div>
                ) : hasPicker ? (
                  <>
                    <select value={form.stallNumber} onChange={(e) => update("stallNumber", e.target.value)}>
                      <option value="">Not assigned (leave blank to unassign)</option>
                      {!currentStallKnown && <option value={form.stallNumber}>{form.stallNumber}</option>}
                      {stallOptions.map((s) => (
                        <option key={s._id} value={s.stallNumber}>
                          {s.stallNumber}
                          {s.stallNumber === exhibitor.stallNumber
                            ? " — current"
                            : s.status !== "available"
                            ? ` — ${STALL_STATUS_LABEL[s.status] || s.status}`
                            : ""}
                        </option>
                      ))}
                    </select>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                      {stallsLoading
                        ? "Loading stalls…"
                        : `${stallOptions.filter((s) => s.status === "available").length} available in ${selectedPackage?.label || "this category"}`}
                    </div>
                  </>
                ) : (
                  <div className="field-readonly">
                    <span className="field-empty">Not applicable — space allocated by the organizing team</span>
                  </div>
                )}
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Number of Stalls</label>
                {readOnly ? (
                  <div className="field-readonly">{form.numberOfStalls}</div>
                ) : (
                  <input
                    type="number"
                    min={1}
                    value={form.numberOfStalls}
                    onChange={(e) => update("numberOfStalls", Number(e.target.value) || 1)}
                  />
                )}
              </div>
              {field("Fascia Name", "fasciaName")}
            </div>

            <div className="modal-section-label">Contact Person</div>
            <div className="form-row">
              {field("ITS Number", "itsNumber")}
              {field("Name", "contactPerson", { required: true })}
            </div>
            <div className="form-row">
              {field("Designation", "designation")}
              {field("Personal Email", "email", { type: "email", required: true })}
            </div>
            <div className="form-row">
              {field("Mobile", "phone", { required: true })}
              {field("WhatsApp", "whatsapp")}
            </div>
            {field("Landline", "landline")}

            <div className="modal-section-label">Business</div>
            <div className="form-row">
              {field("Company Name", "companyName", { required: true })}
              {field("Business Email", "businessEmail", { type: "email" })}
            </div>
            {field("Business Address", "businessAddress")}
            <div className="form-row">
              {field("City", "city")}
              {field("State", "state")}
            </div>
            <div className="form-row">
              {field("Pincode", "pincode")}
              {field("GST Number", "gstNumber")}
            </div>
            <div className="form-row">
              {field("Website", "website")}
              {field("LinkedIn", "linkedin")}
            </div>
            <div className="form-row">
              {field("Instagram", "instagram")}
              {field("Facebook", "facebook")}
            </div>

            <div className="modal-section-label">Category &amp; Products</div>
            <div className="field">
              <label>Category</label>
              {readOnly ? (
                <div className="field-readonly">{form.category || "—"}</div>
              ) : (
                <select value={form.category} onChange={(e) => update("category", e.target.value)}>
                  <option value="">Select…</option>
                  {(config.categories || []).map((c) => (
                    <option key={c.key} value={c.label}>
                      {c.label}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="field">
              <label>Products / Services</label>
              {readOnly ? (
                <div className="field-readonly" style={{ whiteSpace: "pre-wrap" }}>
                  {form.productsServices || <span className="field-empty">—</span>}
                </div>
              ) : (
                <textarea value={form.productsServices} onChange={(e) => update("productsServices", e.target.value)} />
              )}
            </div>
            <div className="field">
              <label>Message from exhibitor</label>
              {readOnly ? (
                <div className="field-readonly" style={{ whiteSpace: "pre-wrap" }}>
                  {form.message || <span className="field-empty">—</span>}
                </div>
              ) : (
                <textarea value={form.message} onChange={(e) => update("message", e.target.value)} />
              )}
            </div>

            {(exhibitor.logoUrl || (exhibitor.productImages || []).length > 0) && (
              <>
                <div className="modal-section-label">Uploaded Images</div>
                <div className="image-strip">
                  {exhibitor.logoUrl && (
                    <a href={fileUrl(exhibitor.logoUrl)} target="_blank" rel="noreferrer" className="image-thumb" title="Company logo">
                      <img src={fileUrl(exhibitor.logoUrl)} alt="Company logo" />
                      <span>Logo</span>
                    </a>
                  )}
                  {(exhibitor.productImages || []).map((src, i) => (
                    <a key={src} href={fileUrl(src)} target="_blank" rel="noreferrer" className="image-thumb" title={`Product image ${i + 1}`}>
                      <img src={fileUrl(src)} alt={`Product ${i + 1}`} />
                      <span>Product {i + 1}</span>
                    </a>
                  ))}
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
