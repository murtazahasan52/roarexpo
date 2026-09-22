import { Link } from "react-router-dom";
import Hero from "../components/Hero";
import ExhibitorMarquee from "../components/ExhibitorMarquee";
import CategoryGrid from "../components/CategoryGrid";
import StatsBar from "../components/StatsBar";
import OrganizerStrip from "../components/OrganizerStrip";
import Icon from "../components/Icon";
import Reveal from "../components/Reveal";
import { useEventConfig } from "../hooks/useEventConfig";
import roseImg from "../assets/roar-rose.png";
import orangeImg from "../assets/roar-orange.png";
import tigerImg from "../assets/roar-tiger.png";

const exhibitBenefits = [
  { icon: "users", title: "Meet Qualified Buyers", desc: "Connect face-to-face with serious buyers, distributors and decision-makers across 16+ industries." },
  { icon: "monitor", title: "Showcase Your Brand", desc: "A dedicated stall, fascia signage and listing across all expo marketing to put your business in front of thousands." },
  { icon: "spark", title: "Generate Real Leads", desc: "Three full days of footfall means real conversations, real leads, and real deals in the room." },
];

const visitBenefits = [
  { icon: "store", title: "150+ Stalls, One Roof", desc: "Explore everything from industrial machinery to jewellery, food, healthcare and travel &mdash; all under one roof." },
  { icon: "ticket", title: "Free Entry Invitation", desc: "Register once and receive a personal invitation card by email &mdash; just show it at the gate." },
  { icon: "users", title: "Network & Learn", desc: "Meet exhibitors, discover new products and services, and connect with Nagpur's business community." },
];

// The story behind the name — straight from the official expo branding,
// illustrated with the actual rose/orange/tiger emblem art from the poster.
const whyRoar = [
  {
    img: roseImg,
    title: "The Rose",
    desc: "Represents women entrepreneurs' strength, creativity, resilience, and the ability to lead.",
  },
  {
    img: orangeImg,
    title: "The Orange",
    desc: "Represents Nagpur, the Orange City, and symbolizes energy, positivity, and growth.",
  },
  {
    img: tigerImg,
    title: "The Tiger",
    desc: "Represents confidence, leadership, and the courage to take bold steps.",
  },
];

function BenefitGrid({ items }) {
  return (
    <div className="grid grid-3">
      {items.map((b, i) => (
        <Reveal key={b.title} delay={i * 90}>
          <div className="card feature-card">
            <div className="icon-badge icon-badge-lg">
              <Icon name={b.icon} size={28} />
            </div>
            <h3>{b.title}</h3>
            <p style={{ marginBottom: 0, fontSize: 14.5 }} dangerouslySetInnerHTML={{ __html: b.desc }} />
          </div>
        </Reveal>
      ))}
    </div>
  );
}

export default function Home() {
  const { config } = useEventConfig();

  const stats = [
    { label: "Stalls", value: "150+" },
    { label: "Show Days", value: "3" },
    { label: "Categories", value: "16+" },
    { label: "Visitors Expected", value: "18000+" },
  ];

  return (
    <>
      <Hero />
      <ExhibitorMarquee />

      <section className="section stats-section">
        <div className="container">
          <div className="stats-panel">
            <StatsBar stats={stats} />
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <Reveal>
            <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto" }}>
              <div className="eyebrow">Why ROAR?</div>
              <h2>Nagpur, Roaring Aloud and Clear: "We Are Ready"</h2>
              <p className="lead" style={{ margin: "0 auto" }}>
                ROAR stands for Rise, Opportunity, Ambition, Reach &mdash; and every part of the
                name carries meaning.
              </p>
            </div>
          </Reveal>

          <Reveal delay={60}>
            <div className="card about-expo-card">
              <div className="eyebrow" style={{ marginBottom: 10 }}>About the Expo</div>
              <p>
                <strong>ROAR Business Expo Nagpur 2027</strong> is envisioned as a platform to bring together
                Dawoodi Bohra businessmen, entrepreneurs, manufacturers, traders, professionals and service
                providers from across India under one roof. The Expo will provide participating businesses with
                an opportunity to showcase their products, services and capabilities to a wider and diverse
                audience, while creating meaningful business connections beyond their existing geographical
                markets.
              </p>
              <p>
                With <strong>150+ stalls</strong> and visitors from all communities, the Expo aims to create
                opportunities for new customers, suppliers, distributors, dealers, business partners and
                collaborations. It will particularly benefit young and emerging entrepreneurs by giving them
                market exposure and an opportunity to interact with established businesses.
              </p>
              <p>
                The Expo will also encourage{" "}
                <strong>
                  business networking, sourcing, procurement, dealership and distribution opportunities,
                  strategic partnerships and long-term commercial relationships
                </strong>
                . With Nagpur&rsquo;s central location and connectivity, the event can serve as a bridge
                connecting businesses from North, South, East, West and Central India.
              </p>
              <p style={{ marginBottom: 0 }}>
                <strong>ROAR Business Expo Nagpur 2027</strong> aims to go beyond a traditional exhibition by
                creating a sustainable business platform that promotes Mumineen businesses, encourages
                entrepreneurship, expands market reach and strengthens the overall business network, while
                opening the doors to a broader customer base from all communities.
              </p>
            </div>
          </Reveal>

          <div className="grid grid-3" style={{ marginTop: 36 }}>
            {whyRoar.map((w, i) => (
              <Reveal key={w.title} delay={i * 110}>
                <div className="card feature-card why-roar-card" style={{ textAlign: "center" }}>
                  <img src={w.img} alt={w.title} className="why-roar-badge" />
                  <h3>{w.title}</h3>
                  <p style={{ marginBottom: 0, fontSize: 14.5 }}>{w.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="about">
        <div className="container">
          <Reveal>
            <div className="eyebrow">About the Expo</div>
            <h2>Network. Explore. Collaborate. Grow.</h2>
            <p className="lead">
              {config.eventName} brings together {config.totalStalls} exhibitors from across{" "}
              {config.eventCity} and beyond for a 3-day business expo at {config.venueName}, from{" "}
              {config.eventDatesLabel}. Whether you're showcasing your business or exploring what's
              new, ROAR is where {config.eventCity}'s business community comes together.
            </p>
            <div style={{ marginTop: 40 }}>
              <OrganizerStrip organizers={config.organizers || []} />
            </div>
          </Reveal>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <Reveal>
            <div className="eyebrow">Why Exhibit</div>
            <h2>Put your business in front of the right people</h2>
          </Reveal>
          <BenefitGrid items={exhibitBenefits} />
          <div style={{ marginTop: 32, textAlign: "center" }}>
            <Link to="/register/exhibitor" className="btn btn-primary">
              Register as Exhibitor
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <Reveal>
            <div className="eyebrow">Why Visit</div>
            <h2>Discover 150+ stalls under one roof</h2>
          </Reveal>
          <BenefitGrid items={visitBenefits} />
          <div style={{ marginTop: 32, textAlign: "center" }}>
            <Link to="/register/visitor" className="btn btn-primary">
              Register as Visitor
            </Link>
          </div>
        </div>
      </section>

      <section className="section section-alt" id="categories">
        <div className="container">
          <Reveal>
            <div className="eyebrow">Expo Categories</div>
            <h2>Something for every industry</h2>
            <p className="lead" style={{ marginBottom: 36 }}>
              From heavy industry to lifestyle &mdash; explore the full range of sectors represented
              at ROAR {config.eventCity}.
            </p>
          </Reveal>
          <CategoryGrid categories={config.categories || []} />
        </div>
      </section>

      <div className="tiger-stripe-band" aria-hidden="true" />

      <section className="section section-cta">
        <div className="container" style={{ textAlign: "center" }}>
          <Reveal>
            <div className="eyebrow">Join Us</div>
            <h2>A stronger business community, for a brighter tomorrow</h2>
            <p className="lead" style={{ margin: "0 auto 32px" }}>
              Spaces are limited &mdash; secure your stall or reserve your visitor invitation today.
            </p>
            <div className="hero-ctas">
              <Link to="/register/exhibitor" className="btn btn-primary">
                Register as Exhibitor
              </Link>
              <Link to="/register/visitor" className="btn btn-outline">
                Register as Visitor
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
