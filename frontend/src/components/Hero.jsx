import { Link } from "react-router-dom";
import Icon from "./Icon";
import CountdownTimer from "./CountdownTimer";
import { useEventConfig } from "../hooks/useEventConfig";
import roarWordmark from "../assets/roar-wordmark.png";
import economicAffairsLogo from "../assets/economic-affairs-logo.png";
import dbohraLogo from "../assets/dbohra-logo.png";
import perfectBuildcomLogo from "../assets/perfect-buildcom-logo.jpg";
import qualityTradingLogo from "../assets/quality-trading-logo.png";

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
        <div className="brand-logo-row fade-up-3" data-testid="hero-organizer-logos">
          <figure className="brand-logo-tile">
            <figcaption className="brand-logo-label">Managed By</figcaption>
            <img
              src={economicAffairsLogo}
              alt="Dawoodi Bohra Department of Economic Affairs — Nagpur Jamiyat"
              className="brand-logo-img"
            />
          </figure>
          <figure className="brand-logo-tile">
            <figcaption className="brand-logo-label">In Association With</figcaption>
            <img src={dbohraLogo} alt="dbohra — A Global Business Network" className="brand-logo-img" />
          </figure>
        </div>
        <div className="brand-logo-row fade-up-3" data-testid="hero-sponsor-logos">
          <figure className="brand-logo-tile">
            <figcaption className="brand-logo-label brand-logo-label-title">Title Sponsor</figcaption>
            <img src={perfectBuildcomLogo} alt="Perfect Buildcom — Title Sponsor" className="brand-logo-img brand-logo-img-dark" data-testid="sponsor-logo-perfect" />
          </figure>
          <figure className="brand-logo-tile">
            <figcaption className="brand-logo-label brand-logo-label-title">Title Sponsor</figcaption>
            <img src={qualityTradingLogo} alt="Quality Trading Company, Nagpur — Title Sponsor" className="brand-logo-img" data-testid="sponsor-logo-quality" />
          </figure>
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
