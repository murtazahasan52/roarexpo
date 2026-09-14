import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import ZoomableMap from "./ZoomableMap";
import RecordFrame from "./RecordFrame";
import Icon from "./Icon";
import { useStallTip, StallTip, STATUS_LABEL } from "./StallTooltip";

const MAX_PRODUCT_IMAGES = 5;

const EMPTY = {
  amount: "",
  numberOfStalls: 1,
  fasciaName: "",
  itsNumber: "",
  contactPerson: "",
  phone: "",
  email: "",
  whatsapp: "",
  designation: "",
  landline: "",
  companyName: "",
  city: "",
  businessAddress: "",
  state: "",
  pincode: "",
  businessEmail: "",
  gstNumber: "",
  website: "",
  linkedin: "",
  instagram: "",
  facebook: "",
  category: "",
  productsServices: "",
  message: "",
};

// Admin-only stall booking. Shows the venue map; clicking any AVAILABLE stall
// opens the SAME form as the public exhibitor registration (the stall is
// already chosen). Books any stall — incl. admin-only Ruby — as a confirmed
// exhibitor with a custom amount, and sends the confirmation email.
export default function StallBookingPanel({ token, onChange }) {
  const { config } = useEventConfig();
  const [mapUrl, setMapUrl] = useState("");
  const [stalls, setStalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [active, setActive] = useState(null); // the stall being booked
  const [form, setForm] = useState(EMPTY);
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [productImageFiles, setProductImageFiles] = useState([]);
  const [productImagePreviews, setProductImagePreviews] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const { hover, tip, hideTip, toggleTip, markerProps } = useStallTip();

  const packages = config.stallPackages || [];
  const packageLabel = (code) => packages.find((p) => p.code === code)?.label || code;
  const formatRate = (n) => (n != null ? `₹${Number(n).toLocaleString("en-IN")}` : "");

  async function load() {
    setLoading(true);
    try {
      const [mapRes, dirRes] = await Promise.all([
        api.getStallMap().catch(() => null),
        api.getStallDirectory().catch(() => null),
      ]);
      setMapUrl(api.fileUrl(mapRes?.data?.url || ""));
      setStalls(dirRes?.data || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const counts = useMemo(() => {
    const c = { total: stalls.length, available: 0, held: 0, booked: 0 };
    stalls.forEach((s) => {
      if (c[s.status] !== undefined) c[s.status] += 1;
    });
    return c;
  }, [stalls]);

  const visible = filter === "all" ? stalls : stalls.filter((s) => s.packageCode === filter);
  const hovered = stalls.find((s) => s.stallNumber === hover);

  function resetForm(stall) {
    setForm({ ...EMPTY, amount: stall.rate != null ? String(stall.rate) : "" });
    setLogoFile(null);
    setLogoPreview("");
    setProductImageFiles([]);
    setProductImagePreviews([]);
    setError("");
  }

  function openBooking(stall) {
    if (stall.status !== "available") {
      alert(`${stall.stallNumber} is ${STATUS_LABEL[stall.status] || stall.status}.`);
      return;
    }
    setActive(stall);
    resetForm(stall);
  }

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleLogoChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
  }

  function handleProductImagesChange(e) {
    const files = Array.from(e.target.files || []);
    setProductImageFiles((prev) => {
      const combined = [...prev, ...files].slice(0, MAX_PRODUCT_IMAGES);
      setProductImagePreviews(combined.map((f) => URL.createObjectURL(f)));
      return combined;
    });
  }

  function removeProductImage(i) {
    setProductImageFiles((prev) => {
      const next = prev.filter((_, idx) => idx !== i);
      setProductImagePreviews(next.map((f) => URL.createObjectURL(f)));
      return next;
    });
  }

  async function submitBooking(e) {
    e.preventDefault();
    setError("");
    if (!form.contactPerson.trim() || !form.companyName.trim() || !form.email.trim() || !form.phone.trim()) {
      setError("Contact name, company name, email and mobile are required.");
      return;
    }
    setSaving(true);
    try {
      const res = await api.adminBookStall(token, {
        ...form,
        stallNumber: active.stallNumber,
        logo: logoFile || undefined,
        productImages: productImageFiles,
      });
      setNotice(res.message || `Stall ${active.stallNumber} booked.`);
      setActive(null);
      await load();
      onChange?.();
    } catch (err) {
      setError(err?.message || "Could not book the stall.");
    } finally {
      setSaving(false);
    }
  }

  const activePackage = active && packages.find((p) => p.code === active.packageCode);

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>Book a Stall</h3>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
            Click any available (green) stall to open the exhibitor form and book it directly — including Ruby stalls and the split L15–L27 halves.
          </p>
        </div>
      </div>

      {notice && (
        <div className="alert alert-success" style={{ marginBottom: 12 }} data-testid="booking-notice">
          {notice}
        </div>
      )}

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading the layout…</p>
      ) : !mapUrl ? (
        <div className="card form-card">
          <p style={{ margin: 0, color: "var(--text-muted)" }}>The venue layout hasn't been published yet.</p>
        </div>
      ) : (
        <>
          <div className="stall-directory-summary" data-testid="booking-summary">
            <span><strong>{counts.total}</strong> stalls</span>
            <span><span className="stall-legend-dot available" style={{ display: "inline-block", marginRight: 6 }} /><strong>{counts.available}</strong> available</span>
            <span><span className="stall-legend-dot held" style={{ display: "inline-block", marginRight: 6 }} /><strong>{counts.held}</strong> reserved</span>
            <span><span className="stall-legend-dot booked" style={{ display: "inline-block", marginRight: 6 }} /><strong>{counts.booked}</strong> booked</span>
          </div>

          <div className="pill-group" style={{ marginBottom: 14 }}>
            <div className={`pill ${filter === "all" ? "selected" : ""}`} onClick={() => setFilter("all")} role="button" tabIndex={0}>
              All categories
            </div>
            {packages
              .filter((p) => p.hasStallPicker && stalls.some((s) => s.packageCode === p.code))
              .map((p) => (
                <div
                  key={p.code}
                  className={`pill ${filter === p.code ? "selected" : ""}`}
                  onClick={() => setFilter(p.code)}
                  role="button"
                  tabIndex={0}
                  data-testid={`booking-filter-${p.code}`}
                >
                  {p.label}
                </div>
              ))}
          </div>

          <ZoomableMap
            src={mapUrl}
            alt="Venue stall layout"
            wrapProps={{ onMouseLeave: hideTip }}
            hint="Zoom in to read stall numbers · click a green stall to book it"
          >
            {visible.map((s) => (
              <div
                key={s.stallNumber}
                className={`map-marker status-${s.status} ${hover === s.stallNumber ? "is-hover" : ""}`}
                style={{ left: `${s.mapX}%`, top: `${s.mapY}%`, cursor: s.status === "available" ? "pointer" : "default" }}
                {...markerProps(s.stallNumber)}
                onClick={(e) => {
                  if (s.status === "available") openBooking(s);
                  else toggleTip(s.stallNumber, e.currentTarget);
                }}
                role="button"
                tabIndex={0}
                data-testid={`book-marker-${s.stallNumber}`}
                aria-label={`${s.stallNumber}, ${packageLabel(s.packageCode)}, ${STATUS_LABEL[s.status] || s.status}`}
              >
                {s.stallNumber}
              </div>
            ))}
          </ZoomableMap>
          <StallTip stall={hovered} tip={tip} packageLabel={packageLabel} />
        </>
      )}

      {active && (
        <RecordFrame
          title={`Book stall ${active.stallNumber}`}
          subtitle={`${packageLabel(active.packageCode)}${activePackage?.eligibility ? " · " + activePackage.eligibility : ""}`}
          error={error}
          onClose={() => setActive(null)}
          wide
        >
          <form onSubmit={submitBooking} className="modal-body" data-testid="booking-form">
            <div className="modal-section-label">Stall &amp; amount</div>
            <div className="form-row">
              <div className="field">
                <label>Stall</label>
                <div className="field-readonly">
                  {active.stallNumber} · {packageLabel(active.packageCode)}
                  {active.rate != null && <span style={{ color: "var(--text-muted)" }}> · list {formatRate(active.rate)}</span>}
                </div>
              </div>
              <div className="field">
                <label>Amount (₹) *</label>
                <input type="number" min={0} value={form.amount} onChange={(e) => update("amount", e.target.value)} placeholder="e.g. 12000" data-testid="booking-amount" />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Number of Stalls</label>
                <input type="number" min={1} value={form.numberOfStalls} onChange={(e) => update("numberOfStalls", Number(e.target.value) || 1)} />
              </div>
              <div className="field">
                <label>Fascia Name on Stall</label>
                <input value={form.fasciaName} onChange={(e) => update("fasciaName", e.target.value)} placeholder="Name to display on the stall board" />
              </div>
            </div>

            <div className="modal-section-label">Contact person</div>
            <div className="form-row">
              <div className="field">
                <label>ITS Number</label>
                <input value={form.itsNumber} onChange={(e) => update("itsNumber", e.target.value)} />
              </div>
              <div className="field">
                <label>Name *</label>
                <input value={form.contactPerson} onChange={(e) => update("contactPerson", e.target.value)} data-testid="booking-contact-person" />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Mobile Number *</label>
                <input inputMode="tel" placeholder="10-digit mobile number" value={form.phone} onChange={(e) => update("phone", e.target.value)} data-testid="booking-phone" />
              </div>
              <div className="field">
                <label>Personal Email *</label>
                <input type="email" placeholder="name@example.com" value={form.email} onChange={(e) => update("email", e.target.value)} data-testid="booking-email" />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>WhatsApp Number</label>
                <input inputMode="tel" placeholder="If different from mobile" value={form.whatsapp} onChange={(e) => update("whatsapp", e.target.value)} />
              </div>
              <div className="field">
                <label>Designation</label>
                <input value={form.designation} onChange={(e) => update("designation", e.target.value)} />
              </div>
            </div>
            <div className="field">
              <label>Landline / Ph. No.</label>
              <input value={form.landline} onChange={(e) => update("landline", e.target.value)} />
            </div>

            <div className="modal-section-label">Business details</div>
            <div className="form-row">
              <div className="field">
                <label>Company / Business Name *</label>
                <input value={form.companyName} onChange={(e) => update("companyName", e.target.value)} data-testid="booking-company" />
              </div>
              <div className="field">
                <label>City</label>
                <input value={form.city} onChange={(e) => update("city", e.target.value)} />
              </div>
            </div>
            <div className="field">
              <label>Business Address</label>
              <input value={form.businessAddress} onChange={(e) => update("businessAddress", e.target.value)} />
            </div>
            <div className="form-row">
              <div className="field">
                <label>State</label>
                <input value={form.state} onChange={(e) => update("state", e.target.value)} />
              </div>
              <div className="field">
                <label>Pin Code</label>
                <input inputMode="numeric" value={form.pincode} onChange={(e) => update("pincode", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Business Email</label>
                <input type="email" value={form.businessEmail} onChange={(e) => update("businessEmail", e.target.value)} />
              </div>
              <div className="field">
                <label>GST Number</label>
                <input value={form.gstNumber} onChange={(e) => update("gstNumber", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Website</label>
                <input placeholder="www.example.com" value={form.website} onChange={(e) => update("website", e.target.value)} />
              </div>
              <div className="field">
                <label>Category</label>
                <select value={form.category} onChange={(e) => update("category", e.target.value)}>
                  <option value="">Select a category</option>
                  {(config.categories || []).map((c) => (
                    <option key={c.key} value={c.label}>{c.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>LinkedIn Page</label>
                <input placeholder="linkedin.com/company/…" value={form.linkedin} onChange={(e) => update("linkedin", e.target.value)} />
              </div>
              <div className="field">
                <label>Instagram Handle</label>
                <input placeholder="@yourbusiness" value={form.instagram} onChange={(e) => update("instagram", e.target.value)} />
              </div>
            </div>
            <div className="field">
              <label>Facebook Page</label>
              <input placeholder="facebook.com/yourbusiness" value={form.facebook} onChange={(e) => update("facebook", e.target.value)} />
            </div>
            <div className="field">
              <label>Company Logo</label>
              <div className="logo-upload-row">
                {logoPreview ? (
                  <img src={logoPreview} alt="Logo preview" className="logo-preview" />
                ) : (
                  <div className="logo-preview logo-preview-empty">
                    <Icon name="monitor" size={22} />
                  </div>
                )}
                <label className="btn btn-outline logo-upload-btn">
                  {logoFile ? "Change Logo" : "Upload Logo"}
                  <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleLogoChange} hidden />
                </label>
              </div>
            </div>

            <div className="modal-section-label">Additional information</div>
            <div className="field">
              <label>Products / Services They'll Showcase</label>
              <textarea value={form.productsServices} onChange={(e) => update("productsServices", e.target.value)} />
            </div>
            <div className="field">
              <label>Product Images <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(up to 5, JPG/PNG/WEBP)</span></label>
              <div className="product-images-grid">
                {productImagePreviews.map((src, i) => (
                  <div className="product-image-thumb" key={i}>
                    <img src={src} alt={`Product ${i + 1}`} />
                    <button type="button" className="product-image-remove" onClick={() => removeProductImage(i)} aria-label="Remove image">
                      <Icon name="x" size={14} />
                    </button>
                  </div>
                ))}
                {productImageFiles.length < MAX_PRODUCT_IMAGES && (
                  <label className="product-image-add">
                    <Icon name="plus" size={20} />
                    <span>Add Image</span>
                    <input type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={handleProductImagesChange} hidden />
                  </label>
                )}
              </div>
            </div>
            <div className="field">
              <label>Anything else we should know?</label>
              <textarea value={form.message} onChange={(e) => update("message", e.target.value)} />
            </div>

            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={() => setActive(null)} disabled={saving}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={saving} data-testid="booking-submit">
                {saving ? "Booking…" : "Confirm Booking"}
              </button>
            </div>
          </form>
        </RecordFrame>
      )}
    </div>
  );
}
