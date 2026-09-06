import { Link, useSearchParams } from "react-router-dom";
import Icon from "../components/Icon";

export default function RegistrationSuccess() {
  const [params] = useSearchParams();
  const type = params.get("type") === "exhibitor" ? "exhibitor" : "visitor";
  const code = params.get("code") || "";

  const isExhibitor = type === "exhibitor";

  return (
    <section className="section">
      <div className="container">
        <div className="card success-box">
          <Icon name="check" className="success-icon" />
          <h2>You're all set!</h2>
          <p style={{ color: "var(--text-muted)" }}>
            {isExhibitor
              ? "Your stall registration has been received. We've emailed your confirmation, event details, and exhibitor instructions to the email address you provided."
              : "Your visitor registration is confirmed. We've emailed your ID card with a QR code (also sent on WhatsApp, where enabled) — bring it along or show it on your phone at the entrance for quick, scan-and-go check-in."}
          </p>
          {code && <div className="reg-code">{code}</div>}

          <div style={{ marginTop: 32, display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link to="/" className="btn btn-dark">
              Back to Home
            </Link>
            <Link to="/contact" className="btn btn-outline" style={{ borderColor: "var(--navy-800)", color: "var(--navy-900)" }}>
              Contact the Team
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
