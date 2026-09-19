import { Link } from "react-router-dom";
import Icon from "../components/Icon";
import Reveal from "../components/Reveal";
import { useEventConfig } from "../hooks/useEventConfig";

// Six reasons — the same points used in the printed brochure ("Why Nagpur?").
const reasons = [
  {
    icon: "compass",
    title: "Geographic centrality",
    desc: "Nagpur sits at the geographic centre of India — the historic Zero Mile Stone marks it — giving businesses from every region a common, convenient meeting point.",
  },
  {
    icon: "plane",
    title: "Connectivity",
    desc: "An international airport, one of India's busiest railway junctions and national highways link Nagpur directly to the country's major cities.",
  },
  {
    icon: "trending",
    title: "Growing ecosystem",
    desc: "Access to Central India's expanding base of industries, traders, retailers, distributors and service businesses.",
  },
  {
    icon: "store",
    title: "Commercial potential",
    desc: "A strong trading tradition and an active entrepreneurial community across manufacturing, trade, retail and services.",
  },
  {
    icon: "building",
    title: "Growing infrastructure",
    desc: "Ongoing investment in logistics, industrial areas, roads and urban infrastructure keeps the city's business base expanding.",
  },
  {
    icon: "road",
    title: "Gateway to Central India",
    desc: "A natural bridge for businesses from the North, South, East and West to meet new customers, suppliers and partners.",
  },
];

const forExhibitors = [
  "Reach buyers, dealers and distributors travelling in from all four regions of India.",
  "One central location keeps travel and logistics simple for your team and your goods.",
  "A dedicated stall, fascia signage and a listing across all expo marketing.",
  "Three full days of footfall from the business community and the public.",
];

const forVisitors = [
  "Easy to reach by air, rail and road from anywhere in the country.",
  "150+ stalls across 16+ industries — machinery to hospitality under one roof.",
  "Meet manufacturers, traders and service providers face to face.",
  "Free entry with a personal invitation card — register online in two minutes.",
];

const reach = [
  {
    icon: "plane",
    title: "By air",
    desc: "Dr. Babasaheb Ambedkar International Airport, Nagpur, with direct flights from India's major cities.",
  },
  {
    icon: "train",
    title: "By rail",
    desc: "Nagpur Junction is a major stop on the country's north–south and east–west trunk rail routes.",
  },
  {
    icon: "road",
    title: "By road",
    desc: "National highways NH-44 (north–south) and NH-53 (east–west) meet at Nagpur.",
  },
];

// Compass-style graphic: Nagpur at the centre, the four regions around it. Bearings are indicative.
function HubGraphic() {
  const cities = [
    { label: "NORTH", city: "Delhi", x: 200, y: 56 },
    { label: "EAST", city: "Kolkata", x: 344, y: 200 },
    { label: "SOUTH", city: "Hyderabad · Chennai", x: 200, y: 344 },
    { label: "WEST", city: "Mumbai", x: 56, y: 200 },
  ];
  return (
    <svg className="why-hub" viewBox="-10 0 420 400" role="img" aria-label="Nagpur at the centre of India, connected to North, South, East and West">
      <defs>
        <radialGradient id="whyHubGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fbe4be" />
          <stop offset="100%" stopColor="#fbe4be" stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle cx="200" cy="200" r="190" fill="url(#whyHubGlow)" />
      {[60, 105, 150].map((r) => (
        <circle key={r} cx="200" cy="200" r={r} fill="none" stroke="#e9c98f" strokeWidth="1.2" strokeDasharray={r === 150 ? "4 6" : undefined} />
      ))}
      {cities.map((c) => (
        <line key={c.label} x1="200" y1="200" x2={c.x} y2={c.y} stroke="#f2a93b" strokeWidth="2" strokeLinecap="round" />
      ))}
      {[45, 135, 225, 315].map((a) => {
        const rad = (a * Math.PI) / 180;
        return <line key={a} x1={200 + Math.cos(rad) * 60} y1={200 + Math.sin(rad) * 60} x2={200 + Math.cos(rad) * 150} y2={200 + Math.sin(rad) * 150} stroke="#e9c98f" strokeWidth="1" strokeDasharray="3 5" />;
      })}
      {cities.map((c) => (
        <g key={c.city}>
          <circle cx={c.x} cy={c.y} r="7" fill="#fff" stroke="#f2a93b" strokeWidth="2.5" />
          <text x={c.x} y={c.y + (c.y < 200 ? -18 : c.y > 200 ? 30 : -14)} textAnchor="middle" fontSize="11" fontWeight="700" letterSpacing="2" fill="#b8740f">
            {c.label}
          </text>
          <text x={c.x} y={c.y + (c.y < 200 ? -5 : c.y > 200 ? 43 : 26)} textAnchor="middle" fontSize="12" fill="#3c4657">
            {c.city}
          </text>
        </g>
      ))}
      <circle cx="200" cy="200" r="34" fill="#0c1a33" />
      <circle cx="200" cy="200" r="40" fill="none" stroke="#f2a93b" strokeWidth="2" />
      <text x="200" y="197" textAnchor="middle" fontSize="11" fontWeight="700" letterSpacing="1.5" fill="#f7c469">
        NAGPUR
      </text>
      <text x="200" y="211" textAnchor="middle" fontSize="8.5" fill="#cfd6e6">
        ZERO MILE
      </text>
    </svg>
  );
}

export default function WhyNagpur() {
  const { config } = useEventConfig();
  const hijri = config.eventDatesHijri || "1st – 3rd Shaban ul Karim 1448H";
  const dates = config.eventDatesLabel || "8 – 10 January 2027";

  return (
    <>
      {/* ---------- Hero ---------- */}
      <section className="why-hero">
        <div className="container why-hero-grid">
          <Reveal>
            <div>
              <div className="eyebrow">Why Nagpur?</div>
              <h1>
                The heart of India. <em>The centre of opportunity.</em>
              </h1>
              <p className="lead">
                ROAR Business Expo is held in Nagpur for a reason: no other city puts manufacturers, traders,
                entrepreneurs and professionals from the North, South, East and West within equal reach.
              </p>
              <div className="why-chips">
                <span className="why-chip">
                  <Icon name="mapPin" /> Zero Mile Stone — centre of India
                </span>
                <span className="why-chip">
                  <Icon name="calendar" /> {dates}
                </span>
                <span className="why-chip">
                  <Icon name="store" /> {config.totalStalls || "150+"} stalls · {config.categories?.length || 16}+ industries
                </span>
              </div>
              <div className="hero-ctas" style={{ justifyContent: "flex-start" }}>
                <Link to="/register/exhibitor" className="btn btn-primary">
                  <Icon name="store" /> Register as Exhibitor
                </Link>
                <Link to="/register/visitor" className="btn btn-outline">
                  <Icon name="ticket" /> Register as Visitor
                </Link>
              </div>
            </div>
          </Reveal>
          <Reveal delay={120}>
            <div className="why-photo">
              <img src="/why-nagpur/zero-mile.jpg" alt="Zero Mile Stone, Nagpur — the historic marker for the centre of India" loading="eager" />
              <div className="why-photo-caption">
                <strong>Zero Mile Stone, Nagpur</strong>
                The historic survey marker for the geographic centre of India.
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ---------- Centre of India ---------- */}
      <section className="section section-alt">
        <div className="container why-hub-grid">
          <Reveal>
            <div>
              <div className="eyebrow">The centre of India</div>
              <h2>Connecting businesses at the centre of the country</h2>
              <p>
                Nagpur sits at the geographic heart of India and is well connected to every region by air, rail
                and highway. For a business expo, that means exhibitors and visitors can reach it easily from
                the North, South, East and West — and a stall here speaks to Central India&rsquo;s growing market
                as well as to buyers travelling in from across the country.
              </p>
              <ul className="why-list">
                {[
                  "Equal reach for businesses from all four regions of India",
                  "One venue, one trip — meet the whole market in three days",
                  "Central India's expanding base of industries, traders and services",
                ].map((t) => (
                  <li key={t}>
                    <Icon name="check" /> {t}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
          <Reveal delay={120}>
            <div>
              <HubGraphic />
              <p style={{ textAlign: "center", fontSize: 12.5, color: "var(--text-muted)", marginTop: 8 }}>
                Bearings indicative · not to scale
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ---------- Six reasons ---------- */}
      <section className="section">
        <div className="container">
          <Reveal>
            <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 36px" }}>
              <div className="eyebrow">Six reasons</div>
              <h2>Why Nagpur works for business</h2>
              <p className="lead" style={{ margin: "0 auto" }}>
                Location is only the start. Here is what makes the city the right host for ROAR.
              </p>
            </div>
          </Reveal>
          <div className="grid grid-3">
            {reasons.map((r, i) => (
              <Reveal key={r.title} delay={i * 80}>
                <div className="card feature-card">
                  <div className="icon-badge icon-badge-lg">
                    <Icon name={r.icon} size={28} />
                  </div>
                  <h3>{r.title}</h3>
                  <p style={{ marginBottom: 0, fontSize: 14.5 }}>{r.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- What it means for you ---------- */}
      <section className="section section-alt">
        <div className="container">
          <Reveal>
            <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 36px" }}>
              <div className="eyebrow">What it means for you</div>
              <h2>Exhibit here. Visit here. Grow from here.</h2>
            </div>
          </Reveal>
          <div className="why-two">
            <Reveal>
              <div className="card feature-card why-side-card">
                <div className="why-side-head">
                  <div className="icon-badge">
                    <Icon name="store" />
                  </div>
                  <h3>For exhibitors</h3>
                </div>
                <ul className="why-list">
                  {forExhibitors.map((t) => (
                    <li key={t}>
                      <Icon name="check" /> {t}
                    </li>
                  ))}
                </ul>
                <Link to="/register/exhibitor" className="btn btn-primary" style={{ marginTop: 22 }}>
                  Book a stall
                </Link>
              </div>
            </Reveal>
            <Reveal delay={100}>
              <div className="card feature-card why-side-card">
                <div className="why-side-head">
                  <div className="icon-badge">
                    <Icon name="ticket" />
                  </div>
                  <h3>For visitors</h3>
                </div>
                <ul className="why-list">
                  {forVisitors.map((t) => (
                    <li key={t}>
                      <Icon name="check" /> {t}
                    </li>
                  ))}
                </ul>
                <Link to="/register/visitor" className="btn btn-outline" style={{ marginTop: 22 }}>
                  Register as a visitor
                </Link>
              </div>
            </Reveal>
          </div>
          <Reveal delay={120}>
            <div className="why-photo-strip">
              <img src="/why-nagpur/expo-hall.jpg" alt="Exhibitors and visitors on the floor at a ROAR Business Expo" loading="lazy" />
              <img src="/why-nagpur/expo-aisle.jpg" alt="Business conversations along an expo aisle" loading="lazy" />
            </div>
          </Reveal>
        </div>
      </section>

      {/* ---------- Getting there ---------- */}
      <section className="section">
        <div className="container">
          <Reveal>
            <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto 36px" }}>
              <div className="eyebrow">Getting there</div>
              <h2>Easy to reach from anywhere in India</h2>
            </div>
          </Reveal>
          <div className="grid grid-3">
            {reach.map((r, i) => (
              <Reveal key={r.title} delay={i * 80}>
                <div className="card feature-card">
                  <div className="icon-badge icon-badge-lg">
                    <Icon name={r.icon} size={28} />
                  </div>
                  <h3>{r.title}</h3>
                  <p style={{ marginBottom: 0, fontSize: 14.5 }}>{r.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={80}>
            <div className="why-venue" style={{ marginTop: 28 }}>
              <div className="card feature-card">
                <div className="eyebrow" style={{ alignItems: "flex-start" }}>The venue</div>
                <h3 style={{ marginBottom: 20 }}>{config.venueName || "MSB School Ground, Nagpur"}</h3>
                <div className="why-venue-facts">
                  <div className="why-fact">
                    <div className="icon-badge">
                      <Icon name="calendar" />
                    </div>
                    <div>
                      <strong>{dates}</strong>
                      {hijri}
                    </div>
                  </div>
                  <div className="why-fact">
                    <div className="icon-badge">
                      <Icon name="clock" />
                    </div>
                    <div>
                      <strong>10 AM – 8 PM</strong>
                      All three days
                    </div>
                  </div>
                  <div className="why-fact">
                    <div className="icon-badge">
                      <Icon name="mapPin" />
                    </div>
                    <div>
                      <strong>{config.venueAddress || "MSB School Ground, Nagpur, Maharashtra, India"}</strong>
                      {config.venueMapUrl && (
                        <a href={config.venueMapUrl} target="_blank" rel="noreferrer">
                          Get directions &rarr;
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="card" style={{ overflow: "hidden", minHeight: 300 }}>
                <iframe
                  title="Venue map — MSB School Ground, Nagpur"
                  src={`https://www.google.com/maps?q=${encodeURIComponent(config.venueName || "MSB School Ground, Nagpur")}&output=embed`}
                  width="100%"
                  height="100%"
                  style={{ border: 0, display: "block", minHeight: 300 }}
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="section section-cta">
        <div className="container" style={{ textAlign: "center" }}>
          <Reveal>
            <div className="eyebrow">Be part of it</div>
            <h2>Meet the whole market — in the middle of the map.</h2>
            <p className="lead" style={{ margin: "0 auto 26px" }}>
              {dates} · {config.venueName || "MSB School Ground, Nagpur"}. Book your stall or register as a visitor
              today.
            </p>
            <div className="hero-ctas" style={{ justifyContent: "center" }}>
              <Link to="/register/exhibitor" className="btn btn-primary">
                <Icon name="store" /> Register as Exhibitor
              </Link>
              <Link to="/register/visitor" className="btn btn-outline">
                <Icon name="ticket" /> Register as Visitor
              </Link>
              <Link to="/enquiry" className="btn btn-outline">
                <Icon name="mail" /> Send an enquiry
              </Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
