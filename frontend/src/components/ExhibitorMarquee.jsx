import { useEffect, useState } from "react";
import { api, fileUrl } from "../api";

export default function ExhibitorMarquee() {
  const [logos, setLogos] = useState([]);

  useEffect(() => {
    let alive = true;
    api
      .getExhibitorLogos()
      .then((res) => {
        if (alive) setLogos((res && res.data) || []);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  if (!logos.length) return null;

  // Duplicate the list so the marquee can loop seamlessly.
  const track = [...logos, ...logos];

  return (
    <section className="exhibitor-marquee" data-testid="exhibitor-marquee">
      <div className="container">
        <h2 className="exhibitor-marquee-title">Our Valued Exhibitors</h2>
        <div className="exhibitor-marquee-viewport">
          <div className="exhibitor-marquee-track" style={{ "--logo-count": logos.length }}>
            {track.map((e, i) => (
              <div className="exhibitor-marquee-item" key={`${e.id}-${i}`} title={e.companyName} aria-hidden={i >= logos.length}>
                <img
                  src={fileUrl(e.logoUrl)}
                  alt={e.companyName}
                  className="exhibitor-marquee-logo"
                  loading="lazy"
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
