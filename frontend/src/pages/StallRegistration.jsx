import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import Icon from "../components/Icon";
import ZoomableMap from "../components/ZoomableMap";
import { useStallTip, StallTip } from "../components/StallTooltip";

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
  fasciaName: "",
  // Additional info
  productsServices: "",
  message: "",
  agreedToTerms: false,
};

export default function StallRegistration() {
  const { config } = useEventConfig();
  const navigate = useNavigate();
  const submittedRef = useRef(false);
  // Auto-saved draft: the form (no files) plus the reserved stall, so a
  // refresh or an accidental back-swipe doesn't lose anything.
  const DRAFT_KEY = "roar_exhibitor_draft_v1";
  const loadDraft = () => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      if (!raw) return null;
      const d = JSON.parse(raw);
      if (!d || !d.form || Date.now() - (d.savedAt || 0) > 24 * 3600 * 1000) return null;
      if (d.hold && new Date(d.hold.expiresAt).getTime() <= Date.now()) d.hold = null;
      if (!d.hold) d.form.stallNumber = "";
      return d;
    } catch (_) {
      return null;
    }
  };
  const draftRef = useRef(loadDraft());
  const restoringRef = useRef(Boolean(draftRef.current?.form?.stallPackage));
  const [form, setForm] = useState(() => (draftRef.current ? { ...initialState, ...draftRef.current.form } : initialState));
  const [draftRestored, setDraftRestored] = useState(Boolean(draftRef.current));
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setLogoPreview] = useState("");
  const [productImageFiles, setProductImageFiles] = useState([]);
  const [productImagePreviews, setProductImagePreviews] = useState([]);
  const [stallMapUrl, setStallMapUrl] = useState("");
  const [categoryStalls, setCategoryStalls] = useState([]);
  const [allStalls, setAllStalls] = useState([]); // every placed stall, all categories — drawn as the full layout
  const [stallsLoading, setStallsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  // Every problem that stops a submit is also shown in a popup, each line
  // clickable to jump to the field — nothing is hidden off-screen any more.
  const [errorPopup, setErrorPopup] = useState(null); // { title, items: [{ field, message }] }
  const FIELD_LABELS = {
    itsNumber: "ITS Number", contactPerson: "Name", phone: "Mobile Number", email: "Personal Email", whatsapp: "WhatsApp Number",
    companyName: "Company / Business Name", businessAddress: "Business Address", businessEmail: "Business Email", pincode: "Pin Code",
    gstNumber: "GST Number", website: "Website", category: "Category", stallPackage: "Stall Category", stallNumber: "Stall",
    fasciaName: "Fascia Name", agreedToTerms: "Terms & conditions", productImages: "Product images", logo: "Logo",
  };
  function jumpToField(name) {
    const el = document.querySelector(`[data-field="${name}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    const input = el.querySelector("input, select, textarea");
    if (input) setTimeout(() => input.focus({ preventScroll: true }), 350);
  }
  // Server-side validation comes back as { message, errors: [{ msg, param | loc }] }
  function popupFromServerError(err) {
    const details = err?.details || {};
    const items = (details.errors || []).map((e) => {
      const field = e.param || (Array.isArray(e.loc) ? String(e.loc[e.loc.length - 1]) : "");
      return { field, message: `${FIELD_LABELS[field] || field || "Form"}: ${e.msg || "invalid"}` };
    });
    const tech = err?.network ? "No response from the server" : err?.status ? `Server answered HTTP ${err.status}` : "";
    return {
      title: items.length ? "Please correct these before submitting" : "We couldn't submit your registration",
      items: items.length ? items : [{ field: "", message: err?.message || "Something went wrong. Please try again." }],
      technical: items.length ? "" : [tech, `POST ${api.baseUrl}/exhibitors/register`].filter(Boolean).join(" · "),
    };
  }

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
    setFieldErrors((e) => {
      if (touched[field] && RULES[field]) return { ...e, [field]: RULES[field](value) || undefined };
      return e[field] ? { ...e, [field]: undefined } : e;
    });
  }

  // Load the venue stall map once, if the organizers have uploaded one.
  useEffect(() => {
    api
      .getStallMap()
      .then((res) => setStallMapUrl(api.fileUrl(res.data?.url || "")))
      .catch(() => setStallMapUrl(""));
    // The whole venue is drawn (every category's placed stalls) so the map
    // reads like the printed layout; only the chosen category is selectable.
    // The public directory also carries the firm name for booked stalls, so
    // hovering any marker can say who has taken it.
    api
      .getStallDirectory()
      .then((res) => setAllStalls((res.data || []).filter((s) => s.mapX != null && s.mapY != null)))
      .catch(() => setAllStalls([]));
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
    if (restoringRef.current) {
      restoringRef.current = false; // first run after restoring a draft: keep the reserved stall
    } else {
      update("stallNumber", "");
      if (holdRef.current && holdRef.current.stallNumber !== form.stallNumber) releaseCurrentHold();
    }
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

  // ---- Validation: every problem is shown right under its own field (and
  // the page scrolls to the first one) instead of a single message at the
  // bottom or the browser's floating bubble on an off-screen input.
  const [fieldErrors, setFieldErrors] = useState({});
  const [touched, setTouched] = useState({});

  // One rule per field, used both while typing (after the field has been
  // visited) and on submit, so the message is the same everywhere.
  const digits = (v) => String(v || "").replace(/\D/g, "");
  const RULES = {
    itsNumber: (v) => (digits(v).length === 8 && String(v).trim() === digits(v) ? "" : "ITS number must be exactly 8 digits (e.g. 20123456)."),
    contactPerson: (v) => (String(v || "").trim().length >= 2 ? "" : "Enter the contact person's full name."),
    phone: (v) => (/^(\+?91[\s-]?)?[6-9]\d{9}$/.test(String(v || "").replace(/[\s()-]/g, "")) ? "" : "Enter a valid 10-digit mobile number (starts with 6–9)."),
    whatsapp: (v) => (!String(v || "").trim() || /^(\+?91[\s-]?)?[6-9]\d{9}$/.test(String(v).replace(/[\s()-]/g, "")) ? "" : "WhatsApp number must be 10 digits."),
    email: (v) => (/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(String(v || "").trim()) ? "" : "Enter a valid email address, e.g. name@example.com (must contain @ and a domain like .com)."),
    businessEmail: (v) => (!String(v || "").trim() || /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(String(v).trim()) ? "" : "Enter a valid business email, e.g. info@company.com."),
    companyName: (v) => (String(v || "").trim() ? "" : "Enter your company / business name."),
    businessAddress: (v) => (String(v || "").trim() ? "" : "Enter your business address."),
    pincode: (v) => (!String(v || "").trim() || /^\d{6}$/.test(String(v).trim()) ? "" : "Pincode must be 6 digits."),
    gstNumber: (v) => (!String(v || "").trim() || /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/i.test(String(v).trim()) ? "" : "GST number should be 15 characters, e.g. 27AABCU9603R1ZM."),
    website: (v) => (!String(v || "").trim() || /^(https?:\/\/)?([\w-]+\.)+[a-z]{2,}(\/\S*)?$/i.test(String(v).trim()) ? "" : "Enter a valid website, e.g. www.company.com."),
    category: (v) => (v ? "" : "Select the category your business belongs to."),
    stallPackage: (v) => (v ? "" : "Pick a stall category from the rate card."),
    fasciaName: (v) => (String(v || "").trim() ? "" : "Enter the name to be printed on your stall board."),
    agreedToTerms: (v) => (v ? "" : "Please agree to the terms & conditions to continue."),
  };
  function validateField(name, value) {
    const rule = RULES[name];
    return rule ? rule(value) : "";
  }
  function validate() {
    const errs = {};
    Object.keys(RULES).forEach((name) => {
      const msg = validateField(name, form[name]);
      if (msg) errs[name] = msg;
    });
    return errs;
  }
  // Check a field when the exhibitor leaves it — and from then on, live.
  function touch(name) {
    setTouched((t) => ({ ...t, [name]: true }));
    const msg = validateField(name, form[name]);
    setFieldErrors((e) => ({ ...e, [name]: msg || undefined }));
  }
  function showFieldErrors(errs) {
    setFieldErrors(errs);
    setTouched((t) => ({ ...t, ...Object.fromEntries(Object.keys(errs).map((k) => [k, true])) }));
    const first = Object.keys(errs)[0];
    const el = first && document.querySelector(`[data-field="${first}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      const input = el.querySelector("input, select, textarea");
      if (input) setTimeout(() => input.focus({ preventScroll: true }), 350);
    }
  }
  const fieldError = (name) => (fieldErrors[name] ? <div className="field-error" role="alert">{fieldErrors[name]}</div> : null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const errs = validate();
    if (Object.keys(errs).length) {
      showFieldErrors(errs);
      setError(`Please fix the ${Object.keys(errs).length === 1 ? "highlighted field" : `${Object.keys(errs).length} highlighted fields`} above.`);
      setErrorPopup({
        title: "Please correct these before submitting",
        items: Object.entries(errs).map(([field, message]) => ({ field, message: `${FIELD_LABELS[field] || field}: ${message}` })),
      });
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.registerExhibitor({
        ...form,
        holdToken: hold?.token || "",
        numberOfStalls: 1, // one stall per registration — the count is no longer asked on the form
        logo: logoFile || undefined,
        productImages: productImageFiles,
      });
      submittedRef.current = true;
      try {
        localStorage.removeItem(DRAFT_KEY);
      } catch (_) {
        /* ignore */
      }
      navigate(`/register/success?type=exhibitor&code=${encodeURIComponent(res.data.registrationCode)}`);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
      const popup = popupFromServerError(err);
      setErrorPopup(popup);
      // mirror server field errors inline too
      const inline = {};
      popup.items.forEach((it) => {
        if (it.field) inline[it.field] = it.message.replace(/^[^:]+:\s*/, "");
      });
      if (Object.keys(inline).length) showFieldErrors(inline);
      // If the stall was taken in the race window, refresh the list so the
      // exhibitor can immediately pick another one.
      if (err.message && /stall was just taken|reservation.*expired|pick an available stall/i.test(err.message) && form.stallPackage) {
        setHold(null);
        update("stallNumber", "");
        api.getStalls(form.stallPackage).then((r) => setCategoryStalls(r.data || [])).catch(() => {});
      }
    } finally {
      setSubmitting(false);
    }
  }

  const { hover, tip, hideTip, toggleTip, markerProps, isTouch } = useStallTip();

  // ---- Temporary hold on the picked stall while the form is filled in ----
  // Clicking an available stall asks "reserve it?"; the server then holds it
  // for a few minutes (nobody else can pick it) and hands back a token the
  // form submits. A countdown shows how long is left; on expiry the pick is
  // cleared and the stall is free again.
  const [holdPrompt, setHoldPrompt] = useState(null); // stall being confirmed
  const [hold, setHold] = useState(() => draftRef.current?.hold || null); // { token, stallNumber, expiresAt, minutes }
  const [holdInfo, setHoldInfo] = useState("");
  const [holdBusy, setHoldBusy] = useState(false);
  const [holdNotice, setHoldNotice] = useState("");
  const [now, setNow] = useState(Date.now());
  const holdRef = useRef(null);
  holdRef.current = hold;

  useEffect(() => {
    if (!hold) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [hold]);

  useEffect(() => {
    if (submittedRef.current) return undefined;
    const t = setTimeout(() => {
      try {
        const { agreedToTerms, ...rest } = form; // eslint-disable-line no-unused-vars
        const filled = Object.values(rest).some((v) => (typeof v === "string" ? v.trim() : v));
        if (filled) localStorage.setItem(DRAFT_KEY, JSON.stringify({ form: rest, hold, savedAt: Date.now() }));
        else localStorage.removeItem(DRAFT_KEY);
      } catch (_) {
        /* storage unavailable */
      }
    }, 400);
    return () => clearTimeout(t);
  }, [form, hold]);

  function startOver() {
    releaseCurrentHold();
    try {
      localStorage.removeItem(DRAFT_KEY);
    } catch (_) {
      /* ignore */
    }
    setForm(initialState);
    setFieldErrors({});
    setTouched({});
    setDraftRestored(false);
    setHoldInfo("");
    setHoldNotice("");
  }

  const holdSecondsLeft = hold ? Math.max(0, Math.round((new Date(hold.expiresAt).getTime() - now) / 1000)) : 0;

  useEffect(() => {
    if (hold && holdSecondsLeft === 0) {
      setHold(null);
      update("stallNumber", "");
      setHoldNotice(`Your reservation on ${hold.stallNumber} has expired — it is open to others again. Pick a stall to reserve it once more.`);
      if (form.stallPackage) api.getStalls(form.stallPackage).then((r) => setCategoryStalls(r.data || [])).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [holdSecondsLeft, hold]);

  // Leaving the page does NOT release the hold: the draft (with the reserved
  // stall) is restored on return, and an abandoned hold expires by itself.

  async function confirmHold(stall) {
    setHoldBusy(true);
    setHoldNotice("");
    setHoldInfo("");
    const previous = hold?.stallNumber;
    try {
      const res = await api.holdStall(stall.stallNumber, hold?.token); // the server releases the previous one
      setHold({ token: res.data.holdToken, stallNumber: stall.stallNumber, expiresAt: res.data.expiresAt, minutes: res.data.holdMinutes });
      update("stallNumber", stall.stallNumber);
      setHoldPrompt(null);
      setFieldErrors((e) => ({ ...e, stallNumber: undefined }));
      if (previous && previous !== stall.stallNumber) setHoldInfo(`Switched to ${stall.stallNumber} — ${previous} has been released for others.`);
      if (form.stallPackage) api.getStalls(form.stallPackage).then((r) => setCategoryStalls(r.data || [])).catch(() => {});
    } catch (err) {
      setHoldPrompt(null);
      setHoldNotice(err.message || "That stall could not be reserved. Please pick another.");
      if (form.stallPackage) api.getStalls(form.stallPackage).then((r) => setCategoryStalls(r.data || [])).catch(() => {});
    } finally {
      setHoldBusy(false);
    }
  }

  async function releaseCurrentHold() {
    const h = holdRef.current;
    setHold(null);
    if (h) api.releaseStallHold(h.token).catch(() => {});
  }

  function formatCountdown(sec) {
    const m = Math.floor(sec / 60);
    const s2 = sec % 60;
    return `${m}:${String(s2).padStart(2, "0")}`;
  }
  const ownerOf = (stallNumber) => allStalls.find((s) => s.stallNumber === stallNumber)?.owner || null;
  const selectedPackage = (config.stallPackages || []).find((p) => p.code === form.stallPackage);
  const selectedStall = categoryStalls.find((s) => s.stallNumber === form.stallNumber);
  const placeableStalls = categoryStalls.filter((s) => s.mapX != null && s.mapY != null);
  const otherCategoryStalls = allStalls.filter((s) => s.packageCode !== form.stallPackage);
  const availableInCategory = placeableStalls.filter((s) => s.status === "available");

  function formatRate(n) {
    return `₹${Number(n).toLocaleString("en-IN")}`;
  }

  function packageLabel(code) {
    return (config.stallPackages || []).find((p) => p.code === code)?.label || code;
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
          <form className="card form-card" onSubmit={handleSubmit} encType="multipart/form-data" noValidate>
            {draftRestored && (
              <div className="alert" style={{ background: "#eef6ff", color: "#1c4e8a", border: "1px solid #cfe3fb", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                <span>
                  We restored your unfinished form{hold ? ` — stall ${hold.stallNumber} is still reserved for you` : ""}.
                </span>
                <button type="button" className="link-button" onClick={startOver}>
                  Start over
                </button>
              </div>
            )}
            {error && <div className="alert alert-error">{error}</div>}

            <div className="form-section-head">
              <span className="form-section-num">01</span>
              <h3>Personal Details</h3>
            </div>
            <div className="form-row">
              <div className="field" data-field="itsNumber">
                <label>ITS Number <span className="required">*</span></label>
                <input
                  required
                  inputMode="numeric"
                  maxLength={8}
                  placeholder="8-digit ITS number, e.g. 20123456"
                  value={form.itsNumber}
                  onChange={(e) => update("itsNumber", e.target.value)} onBlur={() => touch("itsNumber")}
                />
                {fieldError("itsNumber")}
              </div>
              <div className="field" data-field="contactPerson">
                <label>Name <span className="required">*</span></label>
                <input required value={form.contactPerson} onChange={(e) => update("contactPerson", e.target.value)} onBlur={() => touch("contactPerson")} />
                {fieldError("contactPerson")}
              </div>
            </div>
            <div className="form-row">
              <div className="field" data-field="phone">
                <label>Mobile Number <span className="required">*</span></label>
                <input required inputMode="tel" placeholder="10-digit mobile number" value={form.phone} onChange={(e) => update("phone", e.target.value)} onBlur={() => touch("phone")} />
                {fieldError("phone")}
              </div>
              <div className="field" data-field="email">
                <label>Personal Email <span className="required">*</span></label>
                <input required type="email" placeholder="name@example.com" value={form.email} onChange={(e) => update("email", e.target.value)} onBlur={() => touch("email")} />
                {fieldError("email")}
              </div>
            </div>
            <div className="form-row">
              <div className="field" data-field="whatsapp">
                <label>WhatsApp Number</label>
                <input inputMode="tel" placeholder="10-digit number (if different)" value={form.whatsapp} onChange={(e) => update("whatsapp", e.target.value)} onBlur={() => touch("whatsapp")} />
                {fieldError("whatsapp")}
              </div>
              <div className="field">
                <label>Designation</label>
                <input value={form.designation} onChange={(e) => update("designation", e.target.value)} onBlur={() => touch("designation")} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Landline / Ph. No.</label>
                <input value={form.landline} onChange={(e) => update("landline", e.target.value)} onBlur={() => touch("landline")} />
              </div>
            </div>

            <div className="form-section-head">
              <span className="form-section-num">02</span>
              <h3>Business Details</h3>
            </div>
            <div className="form-row">
              <div className="field" data-field="companyName">
                <label>Company / Business Name <span className="required">*</span></label>
                <input required value={form.companyName} onChange={(e) => update("companyName", e.target.value)} onBlur={() => touch("companyName")} />
                {fieldError("companyName")}
              </div>
              <div className="field">
                <label>City</label>
                <input value={form.city} onChange={(e) => update("city", e.target.value)} onBlur={() => touch("city")} />
              </div>
            </div>
            <div className="field" data-field="businessAddress">
              <label>Business Address <span className="required">*</span></label>
              <input required value={form.businessAddress} onChange={(e) => update("businessAddress", e.target.value)} onBlur={() => touch("businessAddress")} />
                {fieldError("businessAddress")}
            </div>
            <div className="form-row">
              <div className="field">
                <label>State</label>
                <input value={form.state} onChange={(e) => update("state", e.target.value)} onBlur={() => touch("state")} />
              </div>
              <div className="field" data-field="pincode">
                <label>Pin Code</label>
                <input inputMode="numeric" value={form.pincode} onChange={(e) => update("pincode", e.target.value)} onBlur={() => touch("pincode")} />
                {fieldError("pincode")}
              </div>
            </div>
            <div className="form-row">
              <div className="field" data-field="businessEmail">
                <label>Business Email</label>
                <input type="email" value={form.businessEmail} onChange={(e) => update("businessEmail", e.target.value)} onBlur={() => touch("businessEmail")} />
                {fieldError("businessEmail")}
              </div>
              <div className="field" data-field="gstNumber">
                <label>GST Number</label>
                <input value={form.gstNumber} onChange={(e) => update("gstNumber", e.target.value)} onBlur={() => touch("gstNumber")} />
                {fieldError("gstNumber")}
              </div>
            </div>
            <div className="form-row">
              <div className="field" data-field="website">
                <label>Website</label>
                <input placeholder="www.example.com" value={form.website} onChange={(e) => update("website", e.target.value)} onBlur={() => touch("website")} />
                {fieldError("website")}
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>LinkedIn Page</label>
                <input placeholder="linkedin.com/company/…" value={form.linkedin} onChange={(e) => update("linkedin", e.target.value)} onBlur={() => touch("linkedin")} />
              </div>
              <div className="field">
                <label>Instagram Handle</label>
                <input placeholder="@yourbusiness" value={form.instagram} onChange={(e) => update("instagram", e.target.value)} onBlur={() => touch("instagram")} />
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label>Facebook Page</label>
                <input placeholder="facebook.com/yourbusiness" value={form.facebook} onChange={(e) => update("facebook", e.target.value)} onBlur={() => touch("facebook")} />
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
            <div className="field" data-field="category">
              <label>Category <span className="required">*</span></label>
              <select required value={form.category} onChange={(e) => update("category", e.target.value)} onBlur={() => touch("category")}>
                <option value="">Select a category</option>
                {(config.categories || []).map((c) => (
                  <option key={c.key} value={c.label}>
                    {c.label}
                  </option>
                ))}
              </select>
                {fieldError("category")}
            </div>

            <div className="field" data-field="stallPackage">
              <label>Stall Category <span className="required">*</span></label>
              {fieldError("stallPackage")}
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
              <p className="rate-card-total">Total Stalls: {config.totalStallsNumbered || 141}</p>
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
                        <span className="stall-legend-item">
                          <span className="stall-legend-dot other" /> Other categories
                        </span>
                      </div>
                      <p style={{ fontSize: 13, color: "var(--text-heading)", margin: "0 0 8px" }}>
                        <strong>{availableInCategory.length}</strong> {selectedPackage.label.replace(/ Stall$/, "")} stall
                        {availableInCategory.length === 1 ? "" : "s"} available — tap a green one to select it.
                      </p>
                      <ZoomableMap src={stallMapUrl} alt="Venue stall map" wrapProps={{ onMouseLeave: hideTip }}>
                        {otherCategoryStalls.map((s) => (
                          <div
                            key={`other-${s.stallNumber}`}
                            className={`map-marker other-category ${hover === s.stallNumber ? "is-hover" : ""}`}
                            style={{ left: `${s.mapX}%`, top: `${s.mapY}%` }}
                            {...markerProps(s.stallNumber)}
                            onClick={(e) => isTouch() && toggleTip(s.stallNumber, e.currentTarget)}
                            aria-disabled
                          >
                            {s.stallNumber}
                          </div>
                        ))}
                        {placeableStalls.map((s) => {
                          const selectable = s.status === "available" || (hold && hold.stallNumber === s.stallNumber);
                          return (
                            <div
                              key={s.stallNumber}
                              className={`map-marker status-${s.status} ${
                                form.stallNumber === s.stallNumber ? "selected" : ""
                              } ${hover === s.stallNumber ? "is-hover" : ""}`}
                              style={{ left: `${s.mapX}%`, top: `${s.mapY}%` }}
                              {...markerProps(s.stallNumber)}
                              onClick={(e) => {
                                // On a phone the first tap shows the card, the second selects;
                                // with a mouse the card is already showing, so one click selects.
                                const mine = hold && hold.stallNumber === s.stallNumber;
                                // One stall at a time: the first pick asks to reserve; picking another
                                // afterwards just switches (the previous one is released automatically).
                                const pick = () => (hold ? confirmHold(s) : setHoldPrompt(s));
                                if (isTouch()) {
                                  const opened = toggleTip(s.stallNumber, e.currentTarget);
                                  if (selectable && !opened && !mine) pick();
                                } else if (selectable && !mine) {
                                  pick();
                                }
                              }}
                              role="button"
                              tabIndex={selectable ? 0 : -1}
                              aria-disabled={!selectable}
                              aria-label={`${s.stallNumber} · ${stallStatusLabel(s)}`}
                            >
                              {s.stallNumber}
                            </div>
                          );
                        })}
                      </ZoomableMap>
                      <StallTip
                        stall={
                          hover
                            ? (() => {
                                const own = placeableStalls.find((s) => s.stallNumber === hover);
                                const other = otherCategoryStalls.find((s) => s.stallNumber === hover);
                                const st = own || other;
                                return st ? { ...st, owner: st.owner || ownerOf(st.stallNumber) } : null;
                              })()
                            : null
                        }
                        tip={tip}
                        packageLabel={packageLabel}
                        extra={
                          hover && placeableStalls.some((s) => s.stallNumber === hover)
                            ? (() => {
                                const st = placeableStalls.find((s) => s.stallNumber === hover);
                                return st.status === "available" ? `${formatRate(st.rate)} — tap to select` : null;
                              })()
                            : hover
                            ? "Choose this category on the rate card to book it"
                            : null
                        }
                      />
                      {holdNotice && <div className="alert alert-error" style={{ marginTop: 10 }}>{holdNotice}</div>}
                      {holdInfo && <div className="alert" style={{ marginTop: 10, background: "#eef6ff", color: "#1c4e8a", border: "1px solid #cfe3fb" }}>{holdInfo}</div>}
                      {hold && (
                        <div className="alert alert-success" style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                          <span>
                            <strong>{hold.stallNumber}</strong> is reserved for you for {formatCountdown(holdSecondsLeft)} more — submit the form before then to keep it.
                          </span>
                          <button type="button" className="link-button" onClick={() => { releaseCurrentHold(); update("stallNumber", ""); }}>
                            Release &amp; pick another
                          </button>
                        </div>
                      )}
                      <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 8 }}>
                        Tap a marker on the map to pick that stall. Use + to zoom in and scroll around if the numbers are small. (Sample layout — the organizing team may
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

            <div className="field" data-field="fasciaName">
              <label>Fascia Name on Stall <span className="required">*</span></label>
              <input
                required
                placeholder="Name to display on your stall board"
                value={form.fasciaName}
                onChange={(e) => update("fasciaName", e.target.value)} onBlur={() => touch("fasciaName")}
              />
                {fieldError("fasciaName")}
            </div>

            <div className="form-section-head">
              <span className="form-section-num">04</span>
              <h3>Additional Information</h3>
            </div>
            <div className="field">
              <label>Products / Services You'll Showcase <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>(~150 words)</span></label>
              <textarea value={form.productsServices} onChange={(e) => update("productsServices", e.target.value)} onBlur={() => touch("productsServices")} />
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
              <textarea value={form.message} onChange={(e) => update("message", e.target.value)} onBlur={() => touch("message")} />
            </div>

            <div className="field" data-field="agreedToTerms">
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={form.agreedToTerms}
                  onChange={(e) => update("agreedToTerms", e.target.checked)} onBlur={() => touch("agreedToTerms")}
                />
                <span>
                  I agree to the exhibitor terms &amp; conditions and confirm the details above are
                  accurate.
                </span>
              </label>
              {fieldError("agreedToTerms")}
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
            {hold && (
              <div className={`summary-hold ${holdSecondsLeft <= 120 ? "is-urgent" : ""}`}>
                <Icon name="clock" size={14} />
                <span>
                  <strong>{hold.stallNumber}</strong> reserved for you — <strong>{formatCountdown(holdSecondsLeft)}</strong> left to submit
                </span>
              </div>
            )}

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
      {errorPopup && (
        <div className="modal-overlay" onClick={() => setErrorPopup(null)}>
          <div className="modal-panel card" style={{ maxWidth: 520 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ marginBottom: 0, color: "var(--rose-500)" }}>{errorPopup.title}</h3>
            </div>
            <div className="modal-body">
              <ul className="error-list">
                {errorPopup.items.map((it, i) => (
                  <li key={i}>
                    {it.field ? (
                      <button type="button" className="link-button" onClick={() => { setErrorPopup(null); jumpToField(it.field); }}>
                        {it.message}
                      </button>
                    ) : (
                      it.message
                    )}
                  </li>
                ))}
              </ul>
              {errorPopup.items.some((it) => it.field) && (
                <p style={{ fontSize: 12.5, color: "var(--text-muted)", margin: "10px 0 0" }}>Click a line to go to that field.</p>
              )}
              {errorPopup.technical && (
                <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "10px 0 0", wordBreak: "break-all" }}>
                  Technical details (for the organizers): {errorPopup.technical}
                </p>
              )}
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-primary" onClick={() => { const f = errorPopup.items.find((it) => it.field); setErrorPopup(null); if (f) jumpToField(f.field); }}>
                {errorPopup.items.some((it) => it.field) ? "Fix now" : "OK"}
              </button>
            </div>
          </div>
        </div>
      )}
      {holdPrompt && (
        <div className="modal-overlay" onClick={() => !holdBusy && setHoldPrompt(null)}>
          <div className="modal-panel card" style={{ maxWidth: 440 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ marginBottom: 0 }}>Reserve stall {holdPrompt.stallNumber}?</h3>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: 10 }}>
                <strong>{holdPrompt.stallNumber}</strong> · {packageLabel(holdPrompt.packageCode)} · {formatRate(holdPrompt.rate)}
              </p>
              <p style={{ color: "var(--text-muted)", fontSize: 14, marginBottom: 0 }}>
                We'll hold this stall for you for <strong>{hold?.minutes || 15} minutes</strong> while you complete the form, so nobody
                else can take it. Submit before the timer runs out; if it expires, the stall opens up again and you can reserve it
                once more. Your booking is confirmed once the organizing team approves your registration.
              </p>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={() => setHoldPrompt(null)} disabled={holdBusy}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={() => confirmHold(holdPrompt)} disabled={holdBusy}>
                {holdBusy ? "Reserving…" : `Reserve ${holdPrompt.stallNumber}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
