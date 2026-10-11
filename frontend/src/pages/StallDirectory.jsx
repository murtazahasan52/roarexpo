import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import ZoomableMap from "../components/ZoomableMap";
import { useStallTip, StallTip, STATUS_LABEL } from "../components/StallTooltip";


// Public "Stalls" page: the venue layout with every placed stall. Hovering
// (or tapping, on touch screens) a stall shows its category and status, and
// for booked stalls the firm and the person who booked it.
export default function StallDirectory() {
  const { config } = useEventConfig();
  const [mapUrl, setMapUrl] = useState("");
  const [stalls, setStalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const { hover, tip, hideTip, toggleTip, markerProps } = useStallTip();
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getStallMap().catch(() => null), api.getStallDirectory().catch(() => null)])
      .then(([mapRes, dirRes]) => {
        if (cancelled) return;
        setMapUrl(api.fileUrl(mapRes?.data?.url || ""));
        setStalls(dirRes?.data || []);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const packages = config.stallPackages || [];
  const packageLabel = (code) => packages.find((p) => p.code === code)?.label || code;
  const formatRate = (n) => `₹${Number(n).toLocaleString("en-IN")}`;
  // A stall's own rate wins; otherwise the rate of its category.
  const rateOf = (s) => (s?.rate != null ? s.rate : packages.find((p) => p.code === s?.packageCode)?.rate ?? null);

  // Price list rows: every category with its rate, size and how many of its
  // stalls are still free on the map right now.
  const priceRows = useMemo(
    () =>
      packages.map((p) => {
        const inCat = stalls.filter((s) => s.packageCode === p.code);
        return {
          ...p,
          onMap: inCat.length,
          available: inCat.filter((s) => s.status === "available").length,
        };
      }),
    [packages, stalls]
  );

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
      <div className="container" style={{ maxWidth: 1240 }}>
        <div className="eyebrow">Stalls</div>
        <h2>Venue layout &amp; stall bookings</h2>
        <p className="lead">
          Move your cursor over any stall (or tap it on a phone) to see its price, or who has booked it. Green stalls
          are still available — pick one when you <Link to="/register/exhibitor">register as an exhibitor</Link>.
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

            {packages.filter((p) => p.adminOnly && p.eligibility).map((p) => (
              <div key={p.code} className="admin-only-notice" style={{ marginBottom: 14 }} data-testid={`stall-eligibility-${p.code}`}>
                <span className="admin-only-notice-eligibility" style={{ display: "block", marginBottom: 4 }}>
                  {p.label}: {p.eligibility}
                </span>
                <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
                  Booked via the organizing team — WhatsApp {config.contact?.whatsapp}
                  {config.contact?.email ? ` / ${config.contact.email}` : ""}.
                </span>
              </div>
            ))}

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

            <ZoomableMap
              src={mapUrl}
              alt="Venue stall layout"
              wrapProps={{ onMouseLeave: hideTip }}
              hint="Zoom in to read stall numbers · drag or scroll to move around · hover or tap a stall for details"
            >
              {visible.map((s) => (
                <div
                  key={s.stallNumber}
                  className={`map-marker status-${s.status} ${hover === s.stallNumber ? "is-hover" : ""}`}
                  style={{ left: `${s.mapX}%`, top: `${s.mapY}%`, cursor: "default" }}
                  {...markerProps(s.stallNumber)}
                  onClick={(e) => toggleTip(s.stallNumber, e.currentTarget)}
                  role="button"
                  tabIndex={0}
                  aria-label={`${s.stallNumber}, ${packageLabel(s.packageCode)}, ${STATUS_LABEL[s.status] || s.status}${
                    s.owner ? `, ${s.status === "held" ? "reserved by" : "booked by"} ${s.owner.companyName}` : ""
                  }`}
                >
                  {s.stallNumber}
                </div>
              ))}
            </ZoomableMap>
            <StallTip
              stall={hovered}
              tip={tip}
              packageLabel={packageLabel}
              extra={hovered && packages.find((p) => p.code === hovered.packageCode)?.adminOnly
                ? packages.find((p) => p.code === hovered.packageCode)?.eligibility
                : null}
              price={hovered && hovered.status === "available" && rateOf(hovered) != null ? (
                <>
                  {formatRate(rateOf(hovered))}
                  {packages.find((p) => p.code === hovered.packageCode)?.size && (
                    <small>Stall size {packages.find((p) => p.code === hovered.packageCode).size}</small>
                  )}
                </>
              ) : null}
            />
            <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 10 }}>
              Booking details update live as the organizing team confirms registrations.
            </p>

            {priceRows.length > 0 && (
              <div className="stall-price-section" data-testid="stall-price-list">
                <h3>Stall prices</h3>
                <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginTop: 0 }}>
                  Tap a category to show only its stalls on the layout above.
                </p>
                <div className="table-wrap rate-card-wrap">
                  <table className="rate-card-table stall-price-table">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th>Size</th>
                        <th>Price</th>
                        <th>Available</th>
                      </tr>
                    </thead>
                    <tbody>
                      {priceRows.map((p) => {
                        const pickable = p.hasStallPicker && p.onMap > 0;
                        return (
                          <tr
                            key={p.code}
                            className={filter === p.code ? "selected" : ""}
                            style={pickable ? undefined : { cursor: "default" }}
                            onClick={() => {
                              if (!pickable) return;
                              setFilter(filter === p.code ? "all" : p.code);
                              document.querySelector(".stall-directory-summary")?.scrollIntoView({ behavior: "smooth", block: "start" });
                            }}
                          >
                            <td>
                              {p.icon ? `${p.icon} ` : ""}
                              {p.label}
                              {p.inclusions && (
                                <div style={{ fontSize: 11.5, color: "var(--text-muted)", fontWeight: 400, marginTop: 2 }}>{p.inclusions}</div>
                              )}
                              {p.eligibility && (
                                <div style={{ fontSize: 11.5, color: "var(--text-muted)", fontWeight: 400, marginTop: 2 }}>{p.eligibility}</div>
                              )}
                            </td>
                            <td>{p.size || p.sizeLabel || "—"}</td>
                            <td className="price">{p.rate != null ? formatRate(p.rate) : "On request"}</td>
                            <td>
                              {p.onMap > 0 ? (
                                <span className={`avail-badge ${p.available === 0 ? "none" : ""}`}>
                                  {p.available === 0 ? "Sold out" : `${p.available} of ${p.onMap}`}
                                </span>
                              ) : (
                                <span style={{ color: "var(--text-muted)" }}>—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 8 }}>
                  Ready to book? <Link to="/register/exhibitor">Register as an exhibitor</Link> and pick your stall.
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
