import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";

const STATUS_LABEL = {
  available: "Available",
  held: "Reserved — pending confirmation",
  booked: "Booked",
  blocked: "Not available",
};

// Public "Stalls" page: the venue layout with every placed stall. Hovering
// (or tapping, on touch screens) a stall shows its category and status, and
// for booked stalls the firm and the person who booked it.
export default function StallDirectory() {
  const { config } = useEventConfig();
  const [mapUrl, setMapUrl] = useState("");
  const [stalls, setStalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hover, setHover] = useState(null); // stallNumber currently hovered/tapped
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getStallMap().catch(() => null), api.getStallDirectory().catch(() => null)])
      .then(([mapRes, dirRes]) => {
        if (cancelled) return;
        setMapUrl(mapRes?.data?.url || "");
        setStalls(dirRes?.data || []);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const packages = config.stallPackages || [];
  const packageLabel = (code) => packages.find((p) => p.code === code)?.label || code;

  const counts = useMemo(() => {
    const c = { total: stalls.length, available: 0, held: 0, booked: 0 };
    stalls.forEach((s) => {
      if (c[s.status] !== undefined) c[s.status] += 1;
    });
    return c;
  }, [stalls]);

  const visible = filter === "all" ? stalls : stalls.filter((s) => s.packageCode === filter);
  const hovered = stalls.find((s) => s.stallNumber === hover);

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 1080 }}>
        <div className="eyebrow">Stalls</div>
        <h2>Venue layout &amp; stall bookings</h2>
        <p className="lead">
          Move your cursor over any stall (or tap it on a phone) to see who has booked it. Green stalls are still
          available — pick one when you <Link to="/register/exhibitor">register as an exhibitor</Link>.
        </p>

        {loading ? (
          <p style={{ color: "var(--text-muted)" }}>Loading the layout…</p>
        ) : !mapUrl ? (
          <div className="card form-card">
            <p style={{ margin: 0, color: "var(--text-muted)" }}>
              The venue layout hasn't been published yet — check back soon.
            </p>
          </div>
        ) : (
          <>
            <div className="stall-directory-summary">
              <span><strong>{counts.total}</strong> stalls on the map</span>
              <span><span className="stall-legend-dot available" style={{ display: "inline-block", marginRight: 6 }} /><strong>{counts.available}</strong> available</span>
              <span><span className="stall-legend-dot held" style={{ display: "inline-block", marginRight: 6 }} /><strong>{counts.held}</strong> reserved</span>
              <span><span className="stall-legend-dot booked" style={{ display: "inline-block", marginRight: 6 }} /><strong>{counts.booked}</strong> booked</span>
            </div>

            <div className="pill-group" style={{ marginBottom: 14 }}>
              <div className={`pill ${filter === "all" ? "selected" : ""}`} onClick={() => setFilter("all")} role="button" tabIndex={0}>
                All categories
              </div>
              {packages
                .filter((p) => p.hasStallPicker && stalls.some((s) => s.packageCode === p.code))
                .map((p) => (
                  <div
                    key={p.code}
                    className={`pill ${filter === p.code ? "selected" : ""}`}
                    onClick={() => setFilter(p.code)}
                    role="button"
                    tabIndex={0}
                  >
                    {p.label}
                  </div>
                ))}
            </div>

            <div className="map-picker-wrap" onMouseLeave={() => setHover(null)}>
              <img src={mapUrl} alt="Venue stall layout" className="map-picker-img" />
              {visible.map((s) => (
                <div
                  key={s.stallNumber}
                  className={`map-marker status-${s.status} ${hover === s.stallNumber ? "is-hover" : ""}`}
                  style={{ left: `${s.mapX}%`, top: `${s.mapY}%`, cursor: "default" }}
                  onMouseEnter={() => setHover(s.stallNumber)}
                  onClick={() => setHover((h) => (h === s.stallNumber ? null : s.stallNumber))}
                  role="button"
                  tabIndex={0}
                  onFocus={() => setHover(s.stallNumber)}
                  aria-label={`${s.stallNumber}, ${packageLabel(s.packageCode)}, ${STATUS_LABEL[s.status] || s.status}${
                    s.owner ? `, booked by ${s.owner.companyName}` : ""
                  }`}
                >
                  {s.stallNumber}
                </div>
              ))}
              {hovered && (
                <div className="map-tooltip" style={{ left: `${hovered.mapX}%`, top: `${hovered.mapY}%` }}>
                  <strong>
                    {hovered.stallNumber} · {packageLabel(hovered.packageCode)}
                  </strong>
                  {hovered.status === "booked" && hovered.owner ? (
                    <>
                      <div>{hovered.owner.companyName || "—"}</div>
                      {hovered.owner.contactPerson && <div className="tip-muted">{hovered.owner.contactPerson}</div>}
                    </>
                  ) : (
                    <div className="tip-muted">{STATUS_LABEL[hovered.status] || hovered.status}</div>
                  )}
                </div>
              )}
            </div>
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 10 }}>
              Booking details update live as the organizing team confirms registrations.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
