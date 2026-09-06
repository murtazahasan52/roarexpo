import { Link } from "react-router-dom";
import Icon from "./Icon";
import CountdownTimer from "./CountdownTimer";
import { useEventConfig } from "../hooks/useEventConfig";
import roarWordmark from "../assets/roar-wordmark.png";

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
          Saifee Burhani Business Expo &middot; <span className="hero-city">{config.eventCity}</span>
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
