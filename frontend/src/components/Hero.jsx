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
        <div className="hero-crest fade-up-2">
          <div className="organizer-logo-item hero-crest-side">
            <span className="organizer-logo-label">Managed By</span>
            <img
              src={economicAffairsLogo}
              alt="Dawoodi Bohra Department of Economic Affairs — Nagpur Jamiyat"
              className="organizer-logo-img organizer-logo-img-tall"
            />
          </div>
          <h1 className="hero-title">
            <img src={roarWordmark} alt="ROAR — Rose, Orange and Tiger emblem" className="hero-logo" />
          </h1>
          <div className="organizer-logo-item hero-crest-side">
            <span className="organizer-logo-label">In Association With</span>
            <img src={dbohraLogo} alt="dbohra — A Global Business Network" className="organizer-logo-img organizer-logo-img-wide" />
          </div>
        </div>
        <div className="hero-subtitle fade-up-3">
          Business Expo &ndash; <span className="hero-city">{config.eventCity}</span>
        </div>
        <div className="hero-managed-by fade-up-3">
          Managed by Dawoodi Bohra Department of Economic Affairs {config.eventCity}
        </div>
        <div className="sponsor-logos fade-up-3" data-testid="hero-sponsor-logos">
          <span className="sponsor-logos-label">Title Sponsor</span>
          <div className="sponsor-logos-row">
            <img src={perfectBuildcomLogo} alt="Perfect Buildcom — Title Sponsor" className="sponsor-logo-img sponsor-logo-dark" data-testid="sponsor-logo-perfect" />
            <img src={qualityTradingLogo} alt="Quality Trading Company, Nagpur — Title Sponsor" className="sponsor-logo-img sponsor-logo-light" data-testid="sponsor-logo-quality" />
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
