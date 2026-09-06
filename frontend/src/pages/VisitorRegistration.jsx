import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";

const initialState = {
  fullName: "",
  email: "",
  phone: "",
  city: "",
  organization: "",
  designation: "",
  interests: [],
  howDidYouHear: "",
  numberOfGuests: 1,
};

const hearOptions = ["Social Media", "WhatsApp", "Friend / Colleague", "Newspaper", "Organizer Invite", "Other"];

export default function VisitorRegistration() {
  const { config } = useEventConfig();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // Walk-ins scan a QR poster at the entrance, which links here with
  // ?source=onsite — carried through to the backend so the admin dashboard
  // can tell entrance sign-ups apart from ones made ahead of time.
  const isOnsite = searchParams.get("source") === "onsite";
  const [form, setForm] = useState(initialState);
  const [submitting, setSubmitting] = useState(false);
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
    setSubmitting(true);
    try {
      const res = await api.registerVisitor({
        ...form,
        numberOfGuests: Number(form.numberOfGuests) || 1,
        source: isOnsite ? "onsite" : "online",
      });
      navigate(`/register/success?type=visitor&code=${encodeURIComponent(res.data.registrationCode)}`);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 780 }}>
        <div className="eyebrow">{isOnsite ? "Entrance Registration" : "Visitor Registration"}</div>
        <h2>{isOnsite ? `Welcome! Register here at ROAR ${config.eventCity}` : `Get your free invitation to ROAR ${config.eventCity}`}</h2>
        <p className="lead">
          {isOnsite
            ? "Fill this in and you'll instantly get your ID card with a QR code by email (and WhatsApp) — show it at the check-in desk to go straight in."
            : (
              <>
                Register by <strong>{config.registrationDeadlines?.visitor}</strong> and we'll email you an
                ID card with a QR code &mdash; just show it at the entrance for quick check-in.
              </>
            )}
        </p>

        <form className="card form-card" onSubmit={handleSubmit}>
          {error && <div className="alert alert-error">{error}</div>}

          <div className="form-row">
            <div className="field">
              <label>Full Name <span className="required">*</span></label>
              <input required value={form.fullName} onChange={(e) => update("fullName", e.target.value)} />
            </div>
            <div className="field">
              <label>City</label>
              <input value={form.city} onChange={(e) => update("city", e.target.value)} />
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label>Email <span className="required">*</span></label>
              <input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </div>
            <div className="field">
              <label>Phone <span className="required">*</span></label>
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
            <label>Which categories are you interested in?</label>
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

          <div className="form-row">
            <div className="field">
              <label>How did you hear about ROAR?</label>
              <select value={form.howDidYouHear} onChange={(e) => update("howDidYouHear", e.target.value)}>
                <option value="">Select an option</option>
                {hearOptions.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Number of Guests (incl. you)</label>
              <input
                type="number"
                min="1"
                max="10"
                value={form.numberOfGuests}
                onChange={(e) => update("numberOfGuests", e.target.value)}
              />
            </div>
          </div>

          <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
            {submitting ? "Submitting…" : "Get My Invitation"}
          </button>
        </form>
      </div>
    </section>
  );
}
