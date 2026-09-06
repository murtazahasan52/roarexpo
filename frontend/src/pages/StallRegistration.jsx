import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import Icon from "../components/Icon";

const MAX_PRODUCT_IMAGES = 5;

const initialState = {
  // Personal details
  itsNumber: "",
  contactPerson: "",
  designation: "",
  email: "",
  phone: "",
  landline: "",
  whatsapp: "",
  // Business details
  companyName: "",
  businessAddress: "",
  businessEmail: "",
  city: "",
  state: "",
  pincode: "",
  website: "",
  gstNumber: "",
  linkedin: "",
  instagram: "",
  facebook: "",
  // Category & stall
  category: "",
  stallPackage: "",
  stallNumber: "",
  numberOfStalls: 1,
  fasciaName: "",
  // Additional info
  productsServices: "",
  message: "",
  agreedToTerms: false,
};

export default function StallRegistration() {
  const { config } = useEventConfig();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialState);
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [productImageFiles, setProductImageFiles] = useState([]);
  const [productImagePreviews, setProductImagePreviews] = useState([]);
  const [stallMapUrl, setStallMapUrl] = useState("");
  const [categoryStalls, setCategoryStalls] = useState([]);
  const [stallsLoading, setStallsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  // Load the venue stall map once, if the organizers have uploaded one.
  useEffect(() => {
    api
      .getStallMap()
      .then((res) => setStallMapUrl(res.data?.url || ""))
      .catch(() => setStallMapUrl(""));
  }, []);

  // Whenever a numbered-stall category is chosen, fetch every stall of that
  // category (any status) so the exhibitor can see a live, color-coded map:
  // available stalls are selectable, held/booked/blocked ones are shown but
  // disabled. Food Court / Play Zone have no numbered stalls at all — those
  // are sq.ft-based spaces the organizing team allocates directly — so this
  // fetch is skipped entirely for them.
  useEffect(() => {
    const pkg = (config.stallPackages || []).find((p) => p.code === form.stallPackage);
    if (!form.stallPackage || !pkg?.hasStallPicker) {
      setCategoryStalls([]);
      return;
    }
    setStallsLoading(true);
    update("stallNumber", "");
    api
      .getStalls(form.stallPackage)
      .then((res) => setCategoryStalls(res.data || []))
      .catch(() => setCategoryStalls([]))
      .finally(() => setStallsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.stallPackage]);

  function handleLogoChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    setLogoPreview(URL.createObjectURL(file));
  }

  function handleProductImagesChange(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setProductImageFiles((prev) => {
      const combined = [...prev, ...files].slice(0, MAX_PRODUCT_IMAGES);
      setProductImagePreviews(combined.map((f) => URL.createObjectURL(f)));
      return combined;
    });
    e.target.value = "";
  }

  function removeProductImage(index) {
    setProductImageFiles((prev) => {
      const combined = prev.filter((_, i) => i !== index);
      setProductImagePreviews(combined.map((f) => URL.createObjectURL(f)));
      return combined;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!form.itsNumber.trim()) return setError("Please enter your ITS number.");
    if (!form.businessAddress.trim()) return setError("Please enter your business address.");
    if (!form.category) return setError("Please select a category.");
    if (!form.stallPackage) return setError("Please select a stall category.");
    if (!form.fasciaName.trim()) return setError("Please enter the fascia name to be displayed on your stall.");
    if (!form.agreedToTerms) return setError("Please agree to the terms & conditions to continue.");

    setSubmitting(true);
    try {
      const res = await api.registerExhibitor({
        ...form,
        numberOfStalls: Number(form.numberOfStalls) || 1,
        logo: logoFile || undefined,
        productImages: productImageFiles,
      });
      navigate(`/register/success?type=exhibitor&code=${encodeURIComponent(res.data.registrationCode)}`);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
      // If the stall was taken in the race window, refresh the list so the
      // exhibitor can immediately pick another one.
      if (err.message && /stall was just taken/i.test(err.message) && form.stallPackage) {
        api.getStalls(form.stallPackage).then((r) => setCategoryStalls(r.data || [])).catch(() => {});
      }
    } finally {
      setSubmitting(false);
    }
  }

  const selectedPackage = (config.stallPackages || []).find((p) => p.code === form.stallPackage);
  const selectedStall = categoryStalls.find((s) => s.stallNumber === form.stallNumber);
  const placeableStalls = categoryStalls.filter((s) => s.mapX != null && s.mapY != null);

  function formatRate(n) {
    return `₹${Number(n).toLocaleString("en-IN")}`;
  }

  function stallStatusLabel(stall) {
    if (stall.status === "available") return formatRate(stall.rate);
    if (stall.status === "held") return "Pending confirmation";
    if (stall.status === "booked") return "Booked";
    return "Unavailable";
  }

  const personalDone = Boolean(form.itsNumber && form.contactPerson && form.phone && form.email);
  const businessDone = Boolean(form.companyName && form.businessAddress);
  const stallDone = Boolean(form.category && form.stallPackage);
  const termsDone = form.agreedToTerms;

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 1080 }}>
        <div className="eyebrow">Exhibitor Registration</div>
        <h2>Reserve your stall at ROAR {config.eventCity}</h2>
        <p className="lead">
          Registration deadline: <strong>{config.registrationDeadlines?.stall}</strong>. You'll
          receive a confirmation email right after you submit, and our team will review and confirm
          your stall shortly after.
        </p>

        <div className="registration-layout">
          <form className="card form-card" onSubmit={handleSubmit} encType="multipart/form-data">
            {error && <div className="alert alert-error">{error}</div>}

            <div className="form-section-head">
              <span className="form-section-num">01</span>
              <h3>Personal Details</h3>
            </div>
            <div className="form-row">
              <div className="field">
                <label>ITS Number <span className="required">*</span></label>
                <input
                  required
                  inputMode="numeric"
                  placeholder="e.g. 20123456"
                  value={form.itsNumber}
                  onChange={(e) => update("itsNumber", e.target.value)}
                />
              </div>
              <div className="field">
                <label>Name <span className="required">*</span></label>
                <input required value={form.contactPerson} onChange={(e) => update("contactPerson", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Mobile Number <span className="required">*</span></label>
                <input required value={form.phone} onChange={(e) => update("phone", e.target.value)} />
              </div>
              <div className="field">
                <label>Personal Email <span className="required">*</span></label>
                <input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>WhatsApp Number</label>
                <input value={form.whatsapp} onChange={(e) => update("whatsapp", e.target.value)} />
              </div>
              <div className="field">
                <label>Designation</label>
                <input value={form.designation} onChange={(e) => update("designation", e.target.value)} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Landline / Ph. No.</label>
                <input value={form.landline} onChange={(e) => update("landline", e.target.value)} />
              </div>
            </div>

            <div className="form-section-head">
              <span className="form-section-num">02</span>
              <h3>Business Details</h3>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Company / Business Name <span className="required">*</span></label>
                <input required value={form.companyName} onChange={(e) => update("companyName", e.target.value)} />
              </div>
              <div className="field">
                <label>City</label>
                <input value={form.city} onChange={(e) => update("city", e.target.value)} />
              </div>
            </div>
            <div className="field">
              <label>Business Address <span className="required">*</span></label>
              <input required value={form.businessAddress} onChange={(e) => update("businessAddress", e.target.value)} />
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
            <div className="form-row">
              <div className="field">
                <label>Facebook Page</label>
                <input placeholder="facebook.com/yourbusiness" value={form.facebook} onChange={(e) => update("facebook", e.target.value)} />
              </div>
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

            <div className="form-section-head">
              <span className="form-section-num">03</span>
              <h3>Choose Your Category &amp; Stall</h3>
            </div>
            <div className="field">
              <label>Category <span className="required">*</span></label>
              <select required value={form.category} onChange={(e) => update("category", e.target.value)}>
                <option value="">Select a category</option>
                {(config.categories || []).map((c) => (
                  <option key={c.key} value={c.label}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field">
              <label>Stall Category <span className="required">*</span></label>
              <div className="table-wrap rate-card-wrap">
                <table className="rate-card-table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Amount / Size</th>
                      <th>Stalls</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(config.stallPackages || []).map((p) => (
                      <tr
                        key={p.code}
                        className={form.stallPackage === p.code ? "selected" : ""}
                        onClick={() => update("stallPackage", p.code)}
                      >
                        <td>{p.icon ? `${p.icon} ` : ""}{p.label}</td>
                        <td>{p.rate != null ? formatRate(p.rate) : p.sizeLabel}</td>
                        <td>{p.stallCount || "—"}</td>
                        <td>
                          <span
                            className={`rate-card-radio ${form.stallPackage === p.code ? "checked" : ""}`}
                            aria-hidden="true"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="rate-card-total">Total Stalls: {config.totalStallsNumbered || 103}</p>
              {selectedPackage && (
                <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4, marginBottom: 0 }}>
                  Includes: {selectedPackage.inclusions}
                </p>
              )}
            </div>

            {stallMapUrl && (
              <div className="field">
                <label>Venue Stall Map {stallsLoading && "(loading stalls…)"}</label>
                {form.stallPackage && selectedPackage?.hasStallPicker ? (
                  placeableStalls.length > 0 ? (
                    <>
                      <div className="stall-legend">
                        <span className="stall-legend-item">
                          <span className="stall-legend-dot available" /> Available
                        </span>
                        <span className="stall-legend-item">
                          <span className="stall-legend-dot held" /> Pending confirmation
                        </span>
                        <span className="stall-legend-item">
                          <span className="stall-legend-dot booked" /> Booked
                        </span>
                        <span className="stall-legend-item">
                          <span className="stall-legend-dot blocked" /> Unavailable
                        </span>
                      </div>
                      <div className="map-picker-wrap">
                        <img src={stallMapUrl} alt="Venue stall map" className="map-picker-img" />
                        {placeableStalls.map((s) => {
                          const selectable = s.status === "available";
                          return (
                            <div
                              key={s.stallNumber}
                              className={`map-marker status-${s.status} ${
                                form.stallNumber === s.stallNumber ? "selected" : ""
                              }`}
                              style={{ left: `${s.mapX}%`, top: `${s.mapY}%` }}
                              onClick={() => selectable && update("stallNumber", s.stallNumber)}
                              role="button"
                              tabIndex={selectable ? 0 : -1}
                              aria-disabled={!selectable}
                              title={`${s.stallNumber} · ${stallStatusLabel(s)}`}
                            >
                              {s.stallNumber}
                            </div>
                          );
                        })}
                      </div>
                      <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 8 }}>
                        Tap a marker on the map to pick that stall. (Sample layout — the organizing team may
                        update this closer to the event.)
                      </p>
                    </>
                  ) : (
                    !stallsLoading && (
                      <>
                        <img src={stallMapUrl} alt="Venue stall map" className="stall-map-preview" />
                        <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 8, marginBottom: 0 }}>
                          No specific stalls have been placed on the map yet for this category — register
                          anyway and our team will assign your stall and confirm the rate directly.
                        </p>
                      </>
                    )
                  )
                ) : (
                  <>
                    <a href={stallMapUrl} target="_blank" rel="noreferrer">
                      <img src={stallMapUrl} alt="Venue stall map" className="stall-map-preview" />
                    </a>
                    <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 6 }}>
                      Reference layout of the venue — tap to view full size. (Sample layout — the organizing
                      team may update this closer to the event.)
                    </p>
                  </>
                )}
              </div>
            )}

            {!stallMapUrl && form.stallPackage && selectedPackage?.hasStallPicker && (
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 20px" }}>
                The venue map hasn't been uploaded yet — register anyway and our team will assign your stall
                and confirm the rate directly.
              </p>
            )}

            {form.stallPackage && selectedPackage && !selectedPackage.hasStallPicker && (
              <p style={{ fontSize: 13, color: "var(--text-muted)", margin: "0 0 20px" }}>
                {selectedPackage.label} space is allocated directly by our team rather than picked online —
                submit your registration and we'll reach out to confirm the size, position and pricing.
              </p>
            )}

            <div className="form-row">
              <div className="field">
                <label>Number of Stalls</label>
                <input
                  type="number"
                  min="1"
                  value={form.numberOfStalls}
                  onChange={(e) => update("numberOfStalls", e.target.value)}
                />
              </div>
              <div className="field">
                <label>Fascia Name on Stall <span className="required">*</span></label>
                <input
                  required
                  placeholder="Name to display on your stall board"
                  value={form.fasciaName}
                  onChange={(e) => update("fasciaName", e.target.value)}
                />
              </div>
            </div>

            <div className="form-section-head">
              <span className="form-section-num">04</span>
              <h3>Additional Information</h3>
            </div>
            <div className="field">
              <label>Products / Services You'll Showcase <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(~150 words)</span></label>
              <textarea value={form.productsServices} onChange={(e) => update("productsServices", e.target.value)} />
            </div>
            <div className="field">
              <label>Product Images <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(4–5 HD images, JPG/PNG/WEBP only)</span></label>
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
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      multiple
                      onChange={handleProductImagesChange}
                      hidden
                    />
                  </label>
                )}
              </div>
            </div>
            <div className="field">
              <label>Anything else we should know?</label>
              <textarea value={form.message} onChange={(e) => update("message", e.target.value)} />
            </div>

            <div className="field">
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.agreedToTerms}
                  onChange={(e) => update("agreedToTerms", e.target.checked)}
                />
                <span>
                  I agree to the exhibitor terms &amp; conditions and confirm the details above are
                  accurate.
                </span>
              </label>
            </div>

            <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
              {submitting ? "Submitting…" : "Submit Registration"}
            </button>
          </form>

          <aside className="card registration-summary">
            <div className="summary-title">Your Registration Summary</div>
            <div className="summary-sub">Updates live as you fill in the form</div>

            <div className="summary-row">
              <span className="summary-row-label">Name</span>
              <span className={`summary-row-value ${form.contactPerson ? "" : "muted"}`}>
                {form.contactPerson || "Not entered yet"}
              </span>
            </div>
            <div className="summary-row">
              <span className="summary-row-label">Company</span>
              <span className={`summary-row-value ${form.companyName ? "" : "muted"}`}>
                {form.companyName || "Not entered yet"}
              </span>
            </div>
            <div className="summary-row">
              <span className="summary-row-label">Category</span>
              <span className={`summary-row-value ${form.category ? "" : "muted"}`}>
                {form.category || "Not selected yet"}
              </span>
            </div>
            <div className="summary-row">
              <span className="summary-row-label">Stall Category</span>
              <span className={`summary-row-value ${selectedPackage ? "" : "muted"}`}>
                {selectedPackage
                  ? `${selectedPackage.label} · ${selectedPackage.rate != null ? formatRate(selectedPackage.rate) : selectedPackage.sizeLabel}`
                  : "Not selected yet"}
              </span>
            </div>
            <div className="summary-row">
              <span className="summary-row-label">Stall</span>
              <span className={`summary-row-value ${selectedStall ? "" : "muted"}`}>
                {selectedStall
                  ? `${selectedStall.stallNumber} · ${formatRate(selectedStall.rate)}`
                  : selectedPackage && !selectedPackage.hasStallPicker
                  ? "Allocated by organizers"
                  : "Auto-assigned later"}
              </span>
            </div>

            <div className="summary-checklist">
              <div className={`summary-check ${personalDone ? "done" : ""}`}>
                <span className="summary-check-dot">{personalDone && <Icon name="check" size={12} />}</span>
                Personal details
              </div>
              <div className={`summary-check ${businessDone ? "done" : ""}`}>
                <span className="summary-check-dot">{businessDone && <Icon name="check" size={12} />}</span>
                Business details
              </div>
              <div className={`summary-check ${stallDone ? "done" : ""}`}>
                <span className="summary-check-dot">{stallDone && <Icon name="check" size={12} />}</span>
                Category &amp; stall
              </div>
              <div className={`summary-check ${termsDone ? "done" : ""}`}>
                <span className="summary-check-dot">{termsDone && <Icon name="check" size={12} />}</span>
                Terms agreed
              </div>
            </div>

            <div className="summary-deadline">
              Registration deadline: <strong>{config.registrationDeadlines?.stall}</strong>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
