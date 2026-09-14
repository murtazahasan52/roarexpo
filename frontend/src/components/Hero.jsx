import { Link } from "react-router-dom";
import Icon from "./Icon";
import CountdownTimer from "./CountdownTimer";
import { useEventConfig } from "../hooks/useEventConfig";
import roarWordmark from "../assets/roar-wordmark.png";
import economicAffairsLogo from "../assets/economic-affairs-logo.png";
import dbohraLogo from "../assets/dbohra-logo.png";

export default function Hero() {
  const { config } = useEventConfig();

  return (
    <section className="hero">
      <div className="container hero-inner">
        <div className="hero-tagline fade-up-1">{config.eventTagline}</div>
        <h1 className="hero-title fade-up-2">
          <img src={roarWordmark} alt="ROAR — Rose, Orange and Tiger emblem" className="hero-logo" />
        </h1>
        <div className="hero-subtitle fade-up-3">
          Business Expo &ndash; <span className="hero-city">{config.eventCity}</span>
        </div>
        <div className="hero-managed-by fade-up-3">
          Managed by Dawoodi Bohra Department of Economic Affairs {config.eventCity}
        </div>
        <div className="organizer-logos organizer-logos-hero fade-up-3" data-testid="hero-organizer-logos">
          <div className="organizer-logo-item">
            <span className="organizer-logo-label">Managed By</span>
            <img
              src={economicAffairsLogo}
              alt="Dawoodi Bohra Department of Economic Affairs — Nagpur Jamiyat"
              className="organizer-logo-img organizer-logo-img-tall"
            />
          </div>
          <div className="organizer-logo-divider" aria-hidden="true" />
          <div className="organizer-logo-item">
            <span className="organizer-logo-label">In Association With</span>
            <img src={dbohraLogo} alt="dbohra — A Global Business Network" className="organizer-logo-img organizer-logo-img-wide" />
          </div>
        </div>
        <p className="hero-lead fade-up-4">
          A 3-day business expo bringing together {config.totalStalls} exhibitors across{" "}
          {config.categories?.length || 16}+ industries &mdash; network, explore, collaborate, and
          grow with the region's business community.
        </p>

        <div className="hero-ctas fade-up-5">
          <Link to="/register/exhibitor" className="btn btn-primary">
            <Icon name="store" size={18} /> Register as Exhibitor
          </Link>
          <Link to="/register/visitor" className="btn btn-outline">
            <Icon name="ticket" size={18} /> Register as Visitor
          </Link>
        </div>

        <div className="hero-facts fade-up-6">
          <div className="hero-fact">
            <Icon name="calendar" size={16} /> <strong>{config.eventDatesLabel}</strong>
          </div>
          <div className="hero-fact">
            <Icon name="mapPin" size={16} /> <strong>{config.venueName}</strong>
          </div>
          <div className="hero-fact">
            <Icon name="store" size={16} /> <strong>{config.totalStalls} Stalls</strong>
          </div>
        </div>

        {config.eventStartDateISO && <CountdownTimer targetISO={config.eventStartDateISO} />}
      </div>
    </section>
  );
}
