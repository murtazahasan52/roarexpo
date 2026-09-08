import { useState } from "react";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";

const initialState = { name: "", email: "", mobile: "", details: "" };

// General enquiry form (reached from the "Enquiry" link in the navbar).
// Submissions are emailed to the organizing team and listed in the admin
// dashboard's Enquiries tab.
export default function Enquiry() {
  const { config } = useEventConfig();
  const [form, setForm] = useState(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (form.details.trim().length < 5) return setError("Please tell us a little about your enquiry.");
    setSubmitting(true);
    try {
      await api.submitEnquiry(form);
      setSent(true);
      setForm(initialState);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 720 }}>
        <div className="eyebrow">Enquiry</div>
        <h2>Have a question about ROAR {config.eventCity}?</h2>
        <p className="lead">
          Send us your enquiry and the organizing team will get back to you. For anything urgent you can
          also WhatsApp us at <strong>{config.contact?.whatsapp}</strong> ({config.contact?.whatsappNote}).
        </p>

        {sent ? (
          <div className="card form-card">
            <div className="alert alert-success">
              Thanks — your enquiry has been sent. Our team will get back to you shortly.
            </div>
            <button className="btn btn-outline" type="button" onClick={() => setSent(false)}>
              Send another enquiry
            </button>
          </div>
        ) : (
          <form className="card form-card" onSubmit={handleSubmit}>
            {error && <div className="alert alert-error">{error}</div>}

            <div className="form-row">
              <div className="field">
                <label>Name <span className="required">*</span></label>
                <input required value={form.name} onChange={(e) => update("name", e.target.value)} />
              </div>
              <div className="field">
                <label>Mobile <span className="required">*</span></label>
                <input required type="tel" value={form.mobile} onChange={(e) => update("mobile", e.target.value)} />
              </div>
            </div>

            <div className="field">
              <label>Email <span className="required">*</span></label>
              <input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </div>

            <div className="field">
              <label>Enquiry Details <span className="required">*</span></label>
              <textarea
                required
                rows={6}
                maxLength={4000}
                placeholder="Tell us what you'd like to know — stall availability, sponsorship, visiting hours, anything at all."
                value={form.details}
                onChange={(e) => update("details", e.target.value)}
              />
            </div>

            <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
              {submitting ? "Sending…" : "Submit Enquiry"}
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
