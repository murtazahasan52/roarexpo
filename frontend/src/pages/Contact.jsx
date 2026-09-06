import Icon from "../components/Icon";
import { useEventConfig } from "../hooks/useEventConfig";

export default function Contact() {
  const { config } = useEventConfig();

  return (
    <section className="section">
      <div className="container">
        <div className="eyebrow">Get in Touch</div>
        <h2>Questions about ROAR {config.eventCity}?</h2>
        <p className="lead">
          Reach out to the organizing team for stall availability, sponsorship opportunities, or any
          other queries about the expo.
        </p>

        <div className="grid grid-3" style={{ marginTop: 32 }}>
          <div className="card feature-card">
            <div className="icon-badge icon-badge-lg">
              <Icon name="phone" size={28} />
            </div>
            <h3>WhatsApp Us</h3>
            <p style={{ marginBottom: 4 }}>
              <a
                href={`https://wa.me/${(config.contact?.whatsapp || "").replace(/[^\d]/g, "")}`}
                target="_blank"
                rel="noreferrer"
              >
                {config.contact?.whatsapp}
              </a>
            </p>
            <p style={{ marginBottom: 0, fontSize: 13, color: "var(--text-muted)" }}>
              {config.contact?.whatsappNote || "Message only — no calls"}
            </p>
          </div>
          <div className="card feature-card">
            <div className="icon-badge icon-badge-lg">
              <Icon name="mail" size={28} />
            </div>
            <h3>Email Us</h3>
            <p style={{ marginBottom: 0 }}>
              <a href={`mailto:${config.contact?.email}`}>{config.contact?.email}</a>
            </p>
          </div>
          <div className="card feature-card">
            <div className="icon-badge icon-badge-lg">
              <Icon name="mapPin" size={28} />
            </div>
            <h3>Visit the Venue</h3>
            <p style={{ marginBottom: 6 }}>{config.venueAddress || config.venueName}</p>
            {config.venueMapUrl && (
              <a href={config.venueMapUrl} target="_blank" rel="noreferrer">
                Get directions &rarr;
              </a>
            )}
          </div>
        </div>

        <div className="card" style={{ marginTop: 32, overflow: "hidden" }}>
          <iframe
            title="Venue map"
            src="https://www.google.com/maps?q=MSB+Ground+Nagpur&output=embed"
            width="100%"
            height="360"
            style={{ border: 0, display: "block" }}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        </div>
      </div>
    </section>
  );
}
