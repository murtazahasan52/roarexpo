import { Link } from "react-router-dom";
import { useEventConfig } from "../hooks/useEventConfig";
import Icon from "./Icon";

export default function Footer() {
  const { config } = useEventConfig();
  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div>
            <span className="brand-mark" style={{ fontSize: 22 }}>
              ROAR
            </span>
            <p style={{ marginTop: 12, fontSize: 14, maxWidth: 280 }}>
              Business Expo &ndash; {config.eventCity}. Managed by Dawoodi Bohra Department of Economic Affairs
              {config.eventCity}. A stronger business community, for a brighter tomorrow.
            </p>
          </div>

          <div>
            <h4>Explore</h4>
            <ul>
              <li>
                <Link to="/#about">About the Expo</Link>
              </li>
              <li>
                <Link to="/#categories">Expo Categories</Link>
              </li>
              <li>
                <Link to="/contact">Contact</Link>
              </li>
            </ul>
          </div>

          <div>
            <h4>Register</h4>
            <ul>
              <li>
                <Link to="/register/exhibitor">Exhibitor Registration</Link>
              </li>
              <li>
                <Link to="/register/visitor">Visitor Registration</Link>
              </li>
              <li>
                <Link to="/admin/login">Admin Login</Link>
              </li>
            </ul>
          </div>

          <div>
            <h4>Get in Touch</h4>
            <ul>
              <li style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Icon name="mapPin" size={16} /> {config.venueName}
              </li>
              <li style={{ display: "flex", gap: 8, alignItems: "center" }} title={config.contact?.whatsappNote}>
                <Icon name="phone" size={16} /> WhatsApp: {config.contact?.whatsapp}
              </li>
              <li style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Icon name="mail" size={16} /> {config.contact?.email}
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <span>
            &copy; {year} {config.eventName}. All rights reserved.
          </span>
          <span>{config.eventDatesLabel} &middot; {config.venueName}</span>
        </div>
      </div>
    </footer>
  );
}
