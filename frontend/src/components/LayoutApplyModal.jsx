import { useMemo, useState } from "react";
import { api } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import Icon from "./Icon";
import ZoomableMap from "./ZoomableMap";

// Shown right after a layout is uploaded (or when the admin clicks
// "Detect stalls"). The server has already found every stall box on the
// drawing and read its printed label; this dialog asks the one thing it
// can't know — which category each letter series is — then Save & Apply
// creates every stall with its map position in a single step.
//
// Two modes:
//  • Labels read by OCR (normal): each box already carries "G1", "R12" …
//    The admin confirms the series → category table and can fix any label.
//  • No OCR available: boxes are unlabelled, so each detected ROW gets a
//    series prefix and the numbers are filled in left-to-right.
export default function LayoutApplyModal({ token, mapUrl, detection, onClose, onApplied }) {
  const { config } = useEventConfig();
  const packages = (config.stallPackages || []).filter((p) => p.hasStallPicker);
  const hasOcr = Boolean(detection?.ocrEngine) && (detection?.boxes || []).some((b) => b.label);

  // Working copy of the boxes: label editable, included toggle.
  const [boxes, setBoxes] = useState(() =>
    (detection?.boxes || []).map((b, i) => ({ ...b, id: i, label: b.label || "", included: !b.ignored }))
  );
  // Row-mode helpers (used when OCR gave us nothing): prefix + start number per row.
  const [rowPrefix, setRowPrefix] = useState(() => (detection?.rows || []).map(() => ""));
  const [rowStart, setRowStart] = useState(() => (detection?.rows || []).map(() => 1));
  const [separator, setSeparator] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [hover, setHover] = useState(null);

  // Series → category table, derived from whatever prefixes the boxes carry.
  const prefixesInUse = useMemo(() => {
    const counts = {};
    boxes.forEach((b) => {
      if (!b.included) return;
      const m = b.label.toUpperCase().match(/^([A-Z]{1,4})-?(\d+)$/);
      if (m) counts[m[1]] = (counts[m[1]] || 0) + 1;
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([prefix, count]) => ({ prefix, count }));
  }, [boxes]);

  const [seriesMap, setSeriesMap] = useState(() => {
    const initial = {};
    (detection?.prefixes || []).forEach((p) => {
      initial[p.prefix] = p.suggestedPackageCode || "";
    });
    return initial;
  });

  function suggestFor(prefix) {
    if (seriesMap[prefix] !== undefined) return seriesMap[prefix];
    const exact = packages.find((p) => prefix.length >= 2 && p.code.toUpperCase().startsWith(prefix));
    const first = packages.find((p) => p.code.toUpperCase().startsWith(prefix[0]));
    return (exact || first)?.code || "";
  }

  function setLabel(id, value) {
    setBoxes((list) => list.map((b) => (b.id === id ? { ...b, label: value.toUpperCase().replace(/\s+/g, "") } : b)));
  }

  function toggleIncluded(id) {
    setBoxes((list) => list.map((b) => (b.id === id ? { ...b, included: !b.included } : b)));
  }

  // Row mode: fill labels for one row from its prefix + start number.
  function applyRowNumbering(rowIndex) {
    const row = detection.rows[rowIndex] || [];
    const prefix = (rowPrefix[rowIndex] || "").toUpperCase().trim();
    if (!prefix) return;
    let n = Number(rowStart[rowIndex]) || 1;
    setBoxes((list) =>
      list.map((b) => {
        if (!row.includes(b.id)) return b;
        const next = { ...b, label: `${prefix}${separator}${n}`, included: true };
        n += 1;
        return next;
      })
    );
  }

  const includedBoxes = boxes.filter((b) => b.included);
  const unlabeled = includedBoxes.filter((b) => !b.label).length;
  const duplicates = useMemo(() => {
    const seen = new Set();
    const dup = new Set();
    includedBoxes.forEach((b) => {
      if (!b.label) return;
      if (seen.has(b.label)) dup.add(b.label);
      seen.add(b.label);
    });
    return [...dup];
  }, [includedBoxes]);
  const unmapped = prefixesInUse.filter((p) => !suggestFor(p.prefix));

  async function handleApply() {
    setError("");
    if (!includedBoxes.length) return setError("No stalls selected to apply.");
    if (unlabeled) return setError(`${unlabeled} selected box${unlabeled === 1 ? " has" : "es have"} no stall number yet.`);
    if (duplicates.length) return setError(`Duplicate stall numbers: ${duplicates.join(", ")}`);
    if (unmapped.length) return setError(`Choose a category for series: ${unmapped.map((p) => p.prefix).join(", ")}`);

    const series = prefixesInUse.map((p) => ({ prefix: p.prefix, packageCode: suggestFor(p.prefix), separator }));
    const stalls = includedBoxes.map((b) => {
      const m = b.label.match(/^([A-Z]{1,4})-?(\d+)$/);
      return { stallNumber: b.label, packageCode: suggestFor(m ? m[1] : ""), mapX: b.x, mapY: b.y };
    });

    setSaving(true);
    try {
      const res = await api.adminApplyLayout(token, series, stalls);
      onApplied(res.message || "Layout applied");
    } catch (err) {
      setError(err.message || "Failed to apply layout");
    } finally {
      setSaving(false);
    }
  }

  const noBoxes = !(detection?.boxes || []).length;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-panel card modal-panel-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3 style={{ marginBottom: 2 }}>Apply this layout</h3>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
              {noBoxes
                ? "No stall boxes could be detected on this drawing."
                : `${detection.boxes.length} box${detection.boxes.length === 1 ? "" : "es"} found${
                    hasOcr ? `, ${detection.boxes.filter((b) => b.label).length} labels read` : ", labels not readable — assign a series per row"
                  }`}
            </div>
          </div>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <Icon name="close" />
          </button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="modal-body">
          {noBoxes ? (
            <p style={{ color: "var(--text-muted)" }}>
              {detection?.error && (
                <>
                  <strong style={{ color: "var(--rose-500)" }}>{detection.error}</strong>
                  <br />
                  <br />
                </>
              )}
              Detection works best on a clean drawing where every stall is a closed rectangle with its number
              printed inside. Try a sharper export (PNG/PDF straight from the drawing tool rather than a photo), or
              use <strong>Place each stall</strong> below to position stalls by hand.
            </p>
          ) : (
            <div className="layout-apply-grid">
              {/* Left: the drawing with detected boxes overlaid */}
              <div>
                <ZoomableMap
                  src={mapUrl}
                  alt="Uploaded layout"
                  maxHeight="60vh"
                  wrapProps={{ onMouseLeave: () => setHover(null) }}
                  hint="Zoom in to check the numbers · drag or scroll to move around"
                >
                  {boxes.map((b) => (
                    <div
                      key={b.id}
                      className={`layout-box ${b.included ? "" : "is-excluded"} ${hover === b.id ? "is-hover" : ""}`}
                      style={{ left: `${b.x - b.w / 2}%`, top: `${b.y - b.h / 2}%`, width: `${b.w}%`, height: `${b.h}%` }}
                      onMouseEnter={() => setHover(b.id)}
                      onClick={() => toggleIncluded(b.id)}
                      title={b.included ? "Click to exclude" : "Click to include"}
                    >
                      <span>{b.label || "?"}</span>
                    </div>
                  ))}
                </ZoomableMap>
                <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
                  Green = will be created as a stall. Grey = left out (no stall number was read there — scenery,
                  entrance, stage…). Click a box to toggle it; a box you tick needs a number typed on the right.
                </p>
              </div>

              {/* Right: the one question — series → category */}
              <div>
                <div className="modal-section-label">1. Which series is which category?</div>
                {prefixesInUse.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--text-muted)" }}>
                    Number the rows below first — series will appear here.
                  </p>
                ) : (
                  <table className="series-table">
                    <thead>
                      <tr>
                        <th>Series</th>
                        <th>Stalls</th>
                        <th>Category</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prefixesInUse.map((p) => (
                        <tr key={p.prefix}>
                          <td>
                            <strong>{p.prefix}</strong>
                          </td>
                          <td>{p.count}</td>
                          <td>
                            <select
                              value={suggestFor(p.prefix)}
                              onChange={(e) => setSeriesMap((m) => ({ ...m, [p.prefix]: e.target.value }))}
                            >
                              <option value="">Select…</option>
                              {packages.map((pkg) => (
                                <option key={pkg.code} value={pkg.code}>
                                  {pkg.label} · ₹{Number(pkg.rate).toLocaleString("en-IN")}
                                </option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

                <div className="modal-section-label" style={{ marginTop: 18 }}>
                  2. Stall numbers {hasOcr ? "(read from the drawing — fix any that look wrong)" : "(assign per row)"}
                </div>
                {!hasOcr && (
                  <div className="form-row" style={{ marginBottom: 8 }}>
                    <div className="field">
                      <label>Label style</label>
                      <select value={separator} onChange={(e) => setSeparator(e.target.value)}>
                        <option value="">G1, G2 …</option>
                        <option value="-">G-1, G-2 …</option>
                      </select>
                    </div>
                  </div>
                )}
                <div className="layout-rows">
                  {(detection.rows || []).map((row, ri) => (
                    <div key={ri} className="layout-row">
                      <div className="layout-row-head">
                        <span>Row {ri + 1}</span>
                        {!hasOcr && (
                          <>
                            <input
                              placeholder="Series (e.g. G)"
                              maxLength={4}
                              value={rowPrefix[ri]}
                              onChange={(e) => setRowPrefix((r) => r.map((v, i) => (i === ri ? e.target.value.toUpperCase() : v)))}
                              style={{ width: 110 }}
                            />
                            <input
                              type="number"
                              min={1}
                              value={rowStart[ri]}
                              onChange={(e) => setRowStart((r) => r.map((v, i) => (i === ri ? e.target.value : v)))}
                              style={{ width: 80 }}
                              title="First number in this row"
                            />
                            <button type="button" className="btn btn-outline" style={{ padding: "4px 12px", fontSize: 12 }} onClick={() => applyRowNumbering(ri)}>
                              Number →
                            </button>
                          </>
                        )}
                      </div>
                      <div className="layout-row-boxes">
                        {row.map((id) => {
                          const b = boxes[id];
                          return (
                            <label key={id} className={`layout-chip ${b.included ? "" : "is-excluded"}`} onMouseEnter={() => setHover(id)}>
                              <input type="checkbox" checked={b.included} onChange={() => toggleIncluded(id)} />
                              <input
                                className="layout-chip-input"
                                value={b.label}
                                placeholder="?"
                                onChange={(e) => setLabel(id, e.target.value)}
                                disabled={!b.included}
                              />
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-outline" onClick={onClose}>
            {noBoxes ? "Close" : "Cancel"}
          </button>
          {!noBoxes && (
            <button type="button" className="btn btn-primary" onClick={handleApply} disabled={saving}>
              {saving ? "Applying…" : `Save & Apply ${includedBoxes.length} stall${includedBoxes.length === 1 ? "" : "s"}`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
