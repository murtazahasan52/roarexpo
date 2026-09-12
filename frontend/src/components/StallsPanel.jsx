import { useCallback, useEffect, useRef, useState } from "react";
import { api, fileUrl } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";
import LayoutApplyModal from "./LayoutApplyModal";
import ZoomableMap from "./ZoomableMap";

const STATUS_LABELS = {
  available: "Available",
  held: "Pending Confirmation",
  booked: "Booked / Confirmed",
  blocked: "Blocked",
};

const STATUS_BADGE = {
  available: "badge-green",
  held: "badge-gold",
  booked: "badge-navy",
  blocked: "badge-gray",
};

// Uploaded files are served under the API base (see api.fileUrl).

const initialForm = { stallNumber: "", packageCode: "", size: "", rate: "" };

export default function StallsPanel({ token }) {
  const { config } = useEventConfig();
  const [stalls, setStalls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState("");

  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [deletingId, setDeletingId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState({ rate: "", status: "available" });
  const [savingId, setSavingId] = useState(null);

  const [mapUrl, setMapUrl] = useState("");
  const [mapInfo, setMapInfo] = useState(null); // { url, uploadedAt, sourceType, series }
  const [mapFile, setMapFile] = useState(null);
  const [mapPreview, setMapPreview] = useState("");
  const [mapUploading, setMapUploading] = useState(false);
  const [mapError, setMapError] = useState("");
  const fileInputRef = useRef(null);

  // ---------- Layout series → category mapping ----------
  // One row per letter series drawn on the layout (e.g. "G" → Gold, "R" →
  // Regular). Saved on the current map; "Generate stalls" turns it into
  // stall records (G1…Gn) at each category's rate-card price.
  const [seriesRows, setSeriesRows] = useState([]);
  const [seriesDirty, setSeriesDirty] = useState(false);
  const [seriesSaving, setSeriesSaving] = useState(false);
  const [seriesMsg, setSeriesMsg] = useState("");
  const [generating, setGenerating] = useState(false);

  // ---------- Auto-detected layout (confirm once, then apply) ----------
  const [detection, setDetection] = useState(null); // opens the confirm dialog when set
  const [detecting, setDetecting] = useState(false); // background job running on the server
  const [pendingDetection, setPendingDetection] = useState(null); // finished, not yet applied
  const [detectError, setDetectError] = useState("");
  const [applyMsg, setApplyMsg] = useState("");
  const pollRef = useRef(null);

  // ---------- Place Stalls on Map ----------
  const [placeCategory, setPlaceCategory] = useState("");
  const [placeStallId, setPlaceStallId] = useState("");
  const [placingCoord, setPlacingCoord] = useState(false);
  const [placeMsg, setPlaceMsg] = useState("");

  const loadStalls = useCallback(async () => {
    setLoading(true);
    setListError("");
    try {
      const res = await api.adminListStalls(token);
      setStalls(res.data);
    } catch (err) {
      setListError(err.message || "Failed to load stalls");
    } finally {
      setLoading(false);
    }
  }, [token]);

  const loadMap = useCallback(async () => {
    try {
      const res = await api.getStallMap();
      if (res?.data?.url) {
        setMapUrl(res.data.url);
        setMapInfo(res.data);
        setSeriesRows((res.data.series || []).map((s) => ({ ...s })));
        setSeriesDirty(false);
      }
    } catch (err) {
      // no map uploaded yet — not an error worth surfacing
    }
  }, []);

  useEffect(() => {
    loadStalls();
    loadMap();
  }, [loadStalls, loadMap]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");
    if (!form.stallNumber.trim() || !form.packageCode.trim() || !form.rate) {
      setFormError("Stall number, package and rate are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.adminCreateStalls(token, [
        {
          stallNumber: form.stallNumber.trim(),
          packageCode: form.packageCode.trim(),
          size: form.size.trim(),
          rate: Number(form.rate),
        },
      ]);
      if (res?.data?.skipped?.length) {
        setFormError(`Stall number "${form.stallNumber}" already exists — not added again.`);
      } else {
        setForm(initialForm);
      }
      loadStalls();
    } catch (err) {
      setFormError(err.message || "Failed to add stall");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this stall? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      await api.adminDeleteStall(token, id);
      loadStalls();
    } catch (err) {
      alert(err.message || "Failed to delete stall");
    } finally {
      setDeletingId(null);
    }
  }

  function startEdit(s) {
    setEditingId(s._id);
    setEditDraft({ rate: String(s.rate), status: s.status });
  }

  async function saveEdit(id) {
    setSavingId(id);
    try {
      await api.adminUpdateStall(token, id, {
        rate: Number(editDraft.rate),
        status: editDraft.status,
      });
      setEditingId(null);
      loadStalls();
    } catch (err) {
      alert(err.message || "Failed to update stall");
    } finally {
      setSavingId(null);
    }
  }

  function handleMapFileChange(e) {
    const file = e.target.files?.[0];
    setMapError("");
    if (!file) return;
    setMapFile(file);
    // A PDF can't be previewed as an <img>; the server renders its first page.
    setMapPreview(file.type === "application/pdf" ? "" : URL.createObjectURL(file));
  }

  async function handleMapUpload() {
    if (!mapFile) return;
    setMapUploading(true);
    setMapError("");
    try {
      const res = await api.adminUploadStallMap(token, mapFile, seriesRows.length ? seriesRows : undefined);
      if (res?.data?.url) {
        setMapUrl(res.data.url);
        setMapInfo(res.data);
        setSeriesRows((res.data.series || []).map((s) => ({ ...s })));
        setSeriesDirty(false);
        // The server is now looking for stall boxes on the new drawing in
        // the background — poll until it's done, then open the one-time
        // confirmation so the admin can apply them.
        setApplyMsg("");
        startPolling();
      }
      setMapFile(null);
      setMapPreview("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setMapError(err.message || "Failed to upload stall map");
    } finally {
      setMapUploading(false);
    }
  }

  // ---- Background detection: poll the server until the job finishes ----
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setDetecting(false);
  }, []);

  const checkDetection = useCallback(
    async (openWhenDone) => {
      try {
        const res = await api.adminDetectionStatus(token);
        const det = res.data?.detection;
        if (!det || det.status === "none") {
          stopPolling();
          return;
        }
        if (det.status === "running") {
          setDetecting(true);
          return;
        }
        stopPolling();
        if (det.status === "error") {
          setDetectError(det.error || "Detection failed");
          setPendingDetection(null);
          return;
        }
        setDetectError("");
        if (det.applied) {
          setPendingDetection(null);
          return;
        }
        setPendingDetection(det);
        if (openWhenDone) setDetection(det);
      } catch (err) {
        stopPolling();
        setDetectError(err.message || "Could not check detection status");
      }
    },
    [token, stopPolling]
  );

  const startPolling = useCallback(() => {
    setDetecting(true);
    setDetectError("");
    setPendingDetection(null);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => checkDetection(true), 2500);
  }, [checkDetection]);

  // On load: is there a finished detection the admin never applied (e.g. the
  // page was closed while it ran)? Offer it again rather than losing it.
  useEffect(() => {
    checkDetection(false);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [checkDetection]);

  const [bundling, setBundling] = useState(false);
  async function handleApplyBundled() {
    if (!window.confirm("Publish the final venue layout bundled with the app and create all its stalls? Existing bookings are kept; sample stalls that are not on the final drawing and are still available will be removed."))
      return;
    setBundling(true);
    setApplyMsg("");
    setDetectError("");
    try {
      const res = await api.adminApplyBundledLayout(token);
      setPendingDetection(null);
      setApplyMsg(res.message || "Final layout published");
      await loadMap();
      await loadStalls();
    } catch (err) {
      setDetectError(err.message || "Could not publish the bundled layout");
    } finally {
      setBundling(false);
    }
  }

  async function handleDetect() {
    setApplyMsg("");
    setDetectError("");
    try {
      await api.adminDetectLayout(token);
      startPolling();
    } catch (err) {
      setDetectError(err.message || "Failed to start detection");
    }
  }

  function handleApplied(message) {
    setDetection(null);
    setPendingDetection(null);
    setApplyMsg(message);
    loadStalls();
    loadMap();
  }

  function updateSeriesRow(index, field, value) {
    setSeriesRows((rows) => rows.map((r, i) => (i === index ? { ...r, [field]: value } : r)));
    setSeriesDirty(true);
    setSeriesMsg("");
  }

  function addSeriesRow() {
    setSeriesRows((rows) => [...rows, { prefix: "", packageCode: "", separator: "" }]);
    setSeriesDirty(true);
  }

  function removeSeriesRow(index) {
    setSeriesRows((rows) => rows.filter((_, i) => i !== index));
    setSeriesDirty(true);
    setSeriesMsg("");
  }

  async function saveSeries() {
    setSeriesSaving(true);
    setSeriesMsg("");
    try {
      const cleaned = seriesRows.filter((r) => r.prefix.trim() && r.packageCode);
      const res = await api.adminSaveMapSeries(token, cleaned);
      setMapInfo(res.data);
      setSeriesRows((res.data.series || []).map((s) => ({ ...s })));
      setSeriesDirty(false);
      setSeriesMsg("Series mapping saved.");
    } catch (err) {
      setSeriesMsg(err.message || "Failed to save series mapping");
    } finally {
      setSeriesSaving(false);
    }
  }

  async function generateStalls() {
    const summary = seriesRows
      .filter((r) => r.prefix && r.packageCode)
      .map((r) => {
        const pkg = (config.stallPackages || []).find((p) => p.code === r.packageCode);
        return `${r.prefix}${r.separator || ""}1 … ${r.prefix}${r.separator || ""}${pkg?.stallCount || "?"} (${pkg?.label || r.packageCode})`;
      })
      .join("\n");
    if (!window.confirm(`Create these stall records (existing numbers are skipped)?\n\n${summary}`)) return;
    setGenerating(true);
    setSeriesMsg("");
    try {
      const res = await api.adminGenerateStallsFromSeries(token);
      setSeriesMsg(res.message || "Stalls generated.");
      loadStalls();
    } catch (err) {
      setSeriesMsg(err.message || "Failed to generate stalls");
    } finally {
      setGenerating(false);
    }
  }

  function seriesForCategory(code) {
    return (mapInfo?.series || []).filter((s) => s.packageCode === code).map((s) => s.prefix).join(", ");
  }

  function holderLabel(s) {
    const holder = s.status === "booked" ? s.bookedBy : s.status === "held" ? s.heldBy : null;
    if (!holder && s.formHold) return "Reserved — exhibitor filling in the form (expires in a few minutes)";
    if (!holder) return "—";
    return `${holder.companyName || "—"} (${holder.registrationCode || ""})`;
  }

  const placeableCategories = (config.stallPackages || []).filter((p) => p.hasStallPicker);
  const categoryStallsForPlacement = placeCategory ? stalls.filter((s) => s.packageCode === placeCategory) : [];
  const unplacedForPlacement = categoryStallsForPlacement.filter((s) => s.mapX == null || s.mapY == null);

  function handlePlaceCategoryChange(code) {
    setPlaceCategory(code);
    setPlaceMsg("");
    const catStalls = stalls.filter((s) => s.packageCode === code);
    const firstUnplaced = catStalls.find((s) => s.mapX == null || s.mapY == null);
    setPlaceStallId(firstUnplaced ? firstUnplaced._id : catStalls[0]?._id || "");
  }

  // Percent position of a pointer/drop point inside the map wrapper.
  function pointToPercent(wrapEl, clientX, clientY) {
    const rect = wrapEl.getBoundingClientRect();
    const xPct = Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100));
    const yPct = Math.min(100, Math.max(0, ((clientY - rect.top) / rect.height) * 100));
    return { mapX: Number(xPct.toFixed(2)), mapY: Number(yPct.toFixed(2)) };
  }

  // Saves a spot for one stall (click-to-place, drag a chip onto the map, or
  // drag a marker to a better spot) and queues the next unplaced stall.
  async function placeStallAt(stallId, { mapX, mapY }) {
    if (!stallId || !mapUrl || placingCoord) return;
    const placedStallNumber = stalls.find((s) => s._id === stallId)?.stallNumber;

    setPlacingCoord(true);
    setPlaceMsg("");
    try {
      await api.adminUpdateStall(token, stallId, { mapX, mapY });
      const res = await api.adminListStalls(token);
      setStalls(res.data);
      const catStalls = res.data.filter((s) => s.packageCode === placeCategory);
      const nextUnplaced = catStalls.find((s) => s.mapX == null || s.mapY == null);
      setPlaceStallId(nextUnplaced ? nextUnplaced._id : "");
      setPlaceMsg(
        nextUnplaced
          ? `${placedStallNumber || "Stall"} placed — now click the spot for ${nextUnplaced.stallNumber}, or drag it from the list.`
          : `${placedStallNumber || "Stall"} placed — every stall in this category now has a spot on the map.`
      );
    } catch (err) {
      setPlaceMsg(err.message || "Failed to place this stall");
    } finally {
      setPlacingCoord(false);
    }
  }

  function handlePlaceClick(e) {
    if (!placeStallId) return;
    placeStallAt(placeStallId, pointToPercent(e.currentTarget, e.clientX, e.clientY));
  }

  // Drag an unplaced stall chip onto the drawing (HTML5 drag & drop).
  function handleMapDragOver(e) {
    if (e.dataTransfer.types.includes("text/stall-id")) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
    }
  }
  function handleMapDrop(e) {
    const id = e.dataTransfer.getData("text/stall-id");
    if (!id) return;
    e.preventDefault();
    placeStallAt(id, pointToPercent(e.currentTarget, e.clientX, e.clientY));
  }

  // Drag a marker that is already on the map to a new spot (pointer events,
  // so it works with a finger too).
  const [dragging, setDragging] = useState(null); // { id, mapX, mapY }
  function handleMarkerPointerDown(e, stall) {
    if (e.button != null && e.button !== 0) return;
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging({ id: stall._id, mapX: stall.mapX, mapY: stall.mapY, startX: e.clientX, startY: e.clientY, moved: false });
  }
  function handleMarkerPointerMove(e) {
    if (!dragging || dragging.id !== e.currentTarget.dataset.id) return;
    const moved = dragging.moved || Math.hypot(e.clientX - dragging.startX, e.clientY - dragging.startY) > 4;
    if (!moved) return;
    const pos = pointToPercent(e.currentTarget.parentElement, e.clientX, e.clientY);
    setDragging((d) => ({ ...d, ...pos, moved: true }));
  }
  function handleMarkerPointerUp(e) {
    if (!dragging || dragging.id !== e.currentTarget.dataset.id) return;
    const d = dragging;
    setDragging(null);
    if (d.moved) placeStallAt(d.id, { mapX: d.mapX, mapY: d.mapY });
    else setPlaceStallId(d.id); // a plain tap selects that stall for re-placing by click
  }

  return (
    <div>
      <div className="card form-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 6 }}>Step 1 — Upload the venue layout</h3>
        <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 16 }}>
          Upload the venue drawing as an image (PNG/JPG/WEBP) or a <strong>PDF</strong> (its first page is converted
          automatically). The stalls drawn on it — and the numbers printed inside them (G1, G2, R1, R2…) — are
          <strong> detected automatically</strong>; you'll be asked once which series is which category, then every
          stall is created with its position and the map goes live for exhibitors and the public Stalls page.
          {mapInfo?.sourceType === "pdf" && " The current map was converted from a PDF."}
        </p>
        {applyMsg && (
          <div className="alert" style={{ background: "#eef6ff", color: "#1c4e8a", border: "1px solid #cfe3fb" }}>
            {applyMsg}
          </div>
        )}
        {mapError && <div className="alert alert-error">{mapError}</div>}
        {detecting && (
          <div className="alert" style={{ background: "#fff8e6", color: "#7a5200", border: "1px solid #f3dfa6" }}>
            <span className="spinner-dot" /> Reading the stall numbers on your layout… this takes about 20–60 seconds.
            The confirmation will open automatically — you can keep working meanwhile.
          </div>
        )}
        {!detecting && detectError && (
          <div className="alert alert-error">
            <strong>Automatic detection didn't work:</strong> {detectError}
            <div style={{ marginTop: 6, fontSize: 12.5 }}>
              You can still add stalls with <strong>Manual option A</strong> (series mapping) and place them with{" "}
              <strong>Manual option B</strong> below, or fix the drawing and click <strong>Detect stalls on this layout</strong>.
            </div>
          </div>
        )}
        {!detecting && !detection && pendingDetection && (
          <div className="alert" style={{ background: "#eefbf1", color: "#1d5a2e", border: "1px solid #bfe6c8", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <span>
              <strong>{pendingDetection.boxes?.filter((b) => b.label && !b.ignored).length || 0} stalls</strong> were detected on the current
              layout but haven't been applied yet.
            </span>
            <button type="button" className="btn btn-primary" style={{ padding: "6px 16px", fontSize: 13 }} onClick={() => setDetection(pendingDetection)}>
              Review &amp; apply
            </button>
          </div>
        )}
        <div className="logo-upload-row">
          {(mapPreview || mapUrl) && (
            <img
              className="stall-map-preview"
              src={mapPreview || fileUrl(mapUrl)}
              alt="Stall map preview"
              style={{ maxWidth: 220 }}
            />
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp,application/pdf"
              onChange={handleMapFileChange}
            />
            <button
              type="button"
              className="btn btn-dark"
              style={{ padding: "8px 18px", alignSelf: "flex-start" }}
              onClick={handleMapUpload}
              disabled={!mapFile || mapUploading}
            >
              {mapUploading ? (mapFile?.type === "application/pdf" ? "Converting PDF…" : "Uploading…") : "Upload Layout"}
            </button>
            {mapFile?.type === "application/pdf" && (
              <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>PDF selected — preview appears after upload.</span>
            )}
            {mapUrl && (
              <button
                type="button"
                className="btn btn-outline"
                style={{ padding: "8px 18px", alignSelf: "flex-start" }}
                onClick={handleDetect}
                disabled={detecting}
                title="Re-run stall detection on the current layout"
              >
                {detecting ? "Detecting…" : "Detect stalls on this layout"}
              </button>
            )}
            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: "8px 18px", alignSelf: "flex-start" }}
              onClick={handleApplyBundled}
              disabled={bundling || detecting}
              title="Publish the final venue drawing shipped with the app, with all its stalls already placed"
            >
              {bundling ? "Publishing…" : "Use the final ROAR layout (143 stalls)"}
            </button>
          </div>
        </div>
      </div>

      {detection && (
        <LayoutApplyModal
          token={token}
          mapUrl={fileUrl(mapUrl)}
          detection={detection}
          onClose={() => setDetection(null)}
          onApplied={handleApplied}
        />
      )}

      {mapUrl && (
        <div className="card form-card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 6 }}>Manual option A — series mapping without detection</h3>
          <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 16 }}>
            Only needed if automatic detection couldn't read your drawing. The layout labels stalls with a letter
            series plus a number (for example <strong>G1, G2</strong> and <strong>R1, R2</strong>). Tell us what each series means — e.g. <strong>G</strong> = Gold,{" "}
            <strong>R</strong> = Regular — and whether the labels use a dash (G-1) or not (G1). Then{" "}
            <strong>Generate stalls</strong> creates one record per stall at that category's rate-card price, named
            exactly as on the drawing, so the online map matches the layout.
          </p>
          {seriesMsg && (
            <div className="alert" style={{ background: "#eef6ff", color: "#1c4e8a", border: "1px solid #cfe3fb" }}>
              {seriesMsg}
            </div>
          )}
          {seriesRows.length === 0 && (
            <p style={{ fontSize: 13, color: "var(--text-muted)" }}>No series defined yet — add one per letter used on the layout.</p>
          )}
          {seriesRows.map((row, i) => {
            const pkg = (config.stallPackages || []).find((p) => p.code === row.packageCode);
            return (
              <div key={i} className="series-row">
                <div className="field">
                  <label>Series on layout</label>
                  <input
                    placeholder="e.g. G"
                    maxLength={4}
                    value={row.prefix}
                    onChange={(e) => updateSeriesRow(i, "prefix", e.target.value.toUpperCase())}
                  />
                </div>
                <div className="field">
                  <label>Means category</label>
                  <select value={row.packageCode} onChange={(e) => updateSeriesRow(i, "packageCode", e.target.value)}>
                    <option value="">Select…</option>
                    {placeableCategories.map((p) => (
                      <option key={p.code} value={p.code}>
                        {p.label} — {p.stallCount} stalls · ₹{Number(p.rate).toLocaleString("en-IN")}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Label style</label>
                  <select value={row.separator || ""} onChange={(e) => updateSeriesRow(i, "separator", e.target.value)}>
                    <option value="">{row.prefix || "G"}1, {row.prefix || "G"}2 …</option>
                    <option value="-">{row.prefix || "G"}-1, {row.prefix || "G"}-2 …</option>
                  </select>
                </div>
                <div className="field series-row-meta">
                  <label>&nbsp;</label>
                  <div style={{ fontSize: 12.5, color: "var(--text-muted)", paddingTop: 10 }}>
                    {pkg ? `${row.prefix || "?"}${row.separator || ""}1 – ${row.prefix || "?"}${row.separator || ""}${pkg.stallCount}` : "—"}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-outline btn-danger-outline series-row-remove"
                  style={{ padding: "6px 12px", fontSize: 12.5 }}
                  onClick={() => removeSeriesRow(i)}
                >
                  Remove
                </button>
              </div>
            );
          })}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
            <button type="button" className="btn btn-outline" style={{ padding: "8px 18px" }} onClick={addSeriesRow}>
              + Add series
            </button>
            <button
              type="button"
              className="btn btn-dark"
              style={{ padding: "8px 18px" }}
              onClick={saveSeries}
              disabled={seriesSaving || !seriesDirty}
            >
              {seriesSaving ? "Saving…" : "Save mapping"}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: "8px 18px" }}
              onClick={generateStalls}
              disabled={generating || seriesDirty || !(mapInfo?.series || []).length}
              title={seriesDirty ? "Save the mapping first" : ""}
            >
              {generating ? "Generating…" : "Generate stalls from layout"}
            </button>
          </div>
        </div>
      )}

      {mapUrl && (
        <div className="card form-card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 6 }}>Manual option B — place or adjust stalls by hand</h3>
          <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 16 }}>
            Use this to nudge a detected stall to a better spot, or to place stalls when detection isn't possible.
            Pick a category; its unplaced stalls appear as chips — drag a chip onto its printed stall on the
            drawing, or click the drawing to place the selected one (the queue advances automatically: G1,
            then G2, …). Drag any green marker to nudge it. That spot becomes the marker exhibitors tap on the
            registration page and the live pin on the public Stalls page.
          </p>
          {placeMsg && (
            <div
              className="alert"
              style={{ background: "#eef6ff", color: "#1c4e8a", border: "1px solid #cfe3fb" }}
            >
              {placeMsg}
            </div>
          )}
          <div className="form-row">
            <div className="field">
              <label>Category</label>
              <select value={placeCategory} onChange={(e) => handlePlaceCategoryChange(e.target.value)}>
                <option value="">Select a category…</option>
                {placeableCategories.map((p) => {
                  const prefixes = seriesForCategory(p.code);
                  const count = stalls.filter((s) => s.packageCode === p.code).length;
                  const placed = stalls.filter((s) => s.packageCode === p.code && s.mapX != null && s.mapY != null).length;
                  return (
                    <option key={p.code} value={p.code}>
                      {p.label}
                      {prefixes ? ` (${prefixes} series)` : ""} — {placed}/{count} placed
                    </option>
                  );
                })}
              </select>
            </div>
            <div className="field">
              <label>Stall</label>
              <select
                value={placeStallId}
                onChange={(e) => setPlaceStallId(e.target.value)}
                disabled={!placeCategory}
              >
                <option value="">Select a stall…</option>
                {categoryStallsForPlacement.map((s) => (
                  <option key={s._id} value={s._id}>
                    {s.stallNumber} — {s.mapX != null && s.mapY != null ? "placed" : "not placed"}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {placeCategory ? (
            <>
              {unplacedForPlacement.length > 0 && (
                <div className="place-chips" aria-label="Stalls not yet on the map">
                  <span className="place-chips-label">Drag onto the map (or click to select):</span>
                  {unplacedForPlacement.map((s) => (
                    <button
                      type="button"
                      key={s._id}
                      className={`place-chip ${s._id === placeStallId ? "is-current" : ""}`}
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData("text/stall-id", s._id);
                        e.dataTransfer.effectAllowed = "move";
                        setPlaceStallId(s._id);
                      }}
                      onClick={() => setPlaceStallId(s._id)}
                    >
                      {s.stallNumber}
                    </button>
                  ))}
                </div>
              )}
              <ZoomableMap
                src={fileUrl(mapUrl)}
                alt="Stall map for placement"
                wrapClassName="map-place-wrap"
                imgClassName="map-place-img"
                hint="Click the drawing to place the selected stall · drag a marker to move it · zoom in for precision"
                wrapProps={{
                  onClick: handlePlaceClick,
                  onDragOver: handleMapDragOver,
                  onDrop: handleMapDrop,
                  style: { opacity: placingCoord ? 0.7 : 1, cursor: placeStallId ? "crosshair" : "default" },
                }}
              >
                {categoryStallsForPlacement
                  .filter((s) => s.mapX != null && s.mapY != null)
                  .map((s) => {
                    const live = dragging && dragging.id === s._id ? dragging : s;
                    return (
                      <div
                        key={s._id}
                        data-id={s._id}
                        data-no-pan
                        className={`map-place-marker ${s._id === placeStallId ? "is-current" : "is-placed"} ${
                          dragging && dragging.id === s._id ? "is-dragging" : ""
                        }`}
                        style={{ left: `${live.mapX}%`, top: `${live.mapY}%` }}
                        onPointerDown={(e) => handleMarkerPointerDown(e, s)}
                        onPointerMove={handleMarkerPointerMove}
                        onPointerUp={handleMarkerPointerUp}
                        onPointerCancel={() => setDragging(null)}
                        onClick={(e) => e.stopPropagation()}
                        title="Drag to move · tap to select"
                      >
                        {s.stallNumber}
                      </div>
                    );
                  })}
              </ZoomableMap>
            </>
          ) : (
            <p style={{ fontSize: 13, color: "var(--text-muted)", margin: 0 }}>
              Choose a category above to start placing stalls on the map.
            </p>
          )}
        </div>
      )}

      <div className="card form-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 18 }}>Add a Stall</h3>
        {formError && <div className="alert alert-error">{formError}</div>}
        <form onSubmit={handleCreate}>
          <div className="form-row">
            <div className="field">
              <label>Stall Number</label>
              <input
                required
                placeholder="e.g. A-12"
                value={form.stallNumber}
                onChange={(e) => update("stallNumber", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Category (Package Code)</label>
              <input
                required
                list="stall-package-codes"
                placeholder="e.g. gold, ruby, food-court"
                value={form.packageCode}
                onChange={(e) => update("packageCode", e.target.value)}
              />
              <datalist id="stall-package-codes">
                {(config.stallPackages || []).map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.label}
                  </option>
                ))}
              </datalist>
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label>Size</label>
              <input
                placeholder="e.g. 10x10 ft"
                value={form.size}
                onChange={(e) => update("size", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Rate (₹)</label>
              <input
                required
                type="number"
                min="0"
                value={form.rate}
                onChange={(e) => update("rate", e.target.value)}
              />
            </div>
          </div>
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Adding…" : "Add Stall"}
          </button>
        </form>
      </div>

      <div className="table-wrap">
        {listError && (
          <div style={{ padding: 16 }}>
            <div className="alert alert-error" style={{ marginBottom: 0 }}>
              {listError}
            </div>
          </div>
        )}
        <table>
          <thead>
            <tr>
              <th>Stall #</th>
              <th>Package</th>
              <th>Size</th>
              <th>Rate</th>
              <th>Status</th>
              <th>Held / Booked By</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {stalls.map((s) => {
              const editing = editingId === s._id;
              return (
                <tr key={s._id}>
                  <td>{s.stallNumber}</td>
                  <td>{s.packageCode}</td>
                  <td>{s.size || "—"}</td>
                  <td>
                    {editing ? (
                      <input
                        type="number"
                        min="0"
                        style={{ width: 90 }}
                        value={editDraft.rate}
                        onChange={(e) => setEditDraft((d) => ({ ...d, rate: e.target.value }))}
                      />
                    ) : (
                      `₹${Number(s.rate).toLocaleString("en-IN")}`
                    )}
                  </td>
                  <td>
                    {editing ? (
                      <select
                        value={editDraft.status}
                        onChange={(e) => setEditDraft((d) => ({ ...d, status: e.target.value }))}
                      >
                        <option value="available">Available</option>
                        <option value="held">Held</option>
                        <option value="booked">Booked</option>
                        <option value="blocked">Blocked</option>
                      </select>
                    ) : (
                      <span className={`badge ${STATUS_BADGE[s.status] || "badge-gray"}`}>
                        {STATUS_LABELS[s.status] || s.status}
                      </span>
                    )}
                  </td>
                  <td>{holderLabel(s)}</td>
                  <td style={{ display: "flex", gap: 8 }}>
                    {editing ? (
                      <>
                        <button
                          className="btn btn-primary"
                          style={{ padding: "6px 14px", fontSize: 12.5 }}
                          onClick={() => saveEdit(s._id)}
                          disabled={savingId === s._id}
                        >
                          {savingId === s._id ? "Saving…" : "Save"}
                        </button>
                        <button
                          className="btn btn-outline"
                          style={{ padding: "6px 14px", fontSize: 12.5 }}
                          onClick={() => setEditingId(null)}
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className="btn btn-outline"
                          style={{ padding: "6px 14px", fontSize: 12.5 }}
                          onClick={() => startEdit(s)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-outline"
                          style={{
                            padding: "6px 14px",
                            fontSize: 12.5,
                            borderColor: "var(--rose-500)",
                            color: "var(--rose-500)",
                          }}
                          onClick={() => handleDelete(s._id)}
                          disabled={deletingId === s._id || s.status === "booked"}
                          title={s.status === "booked" ? "Booked stalls can't be deleted" : ""}
                        >
                          {deletingId === s._id ? "Removing…" : "Delete"}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
            {!loading && stalls.length === 0 && !listError && (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                  No stalls added yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
