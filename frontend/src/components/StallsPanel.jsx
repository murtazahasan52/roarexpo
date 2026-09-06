import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { BASE_URL } from "../api";
import { useEventConfig } from "../hooks/useEventConfig";

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

// Static uploads are served from the backend origin, not the /api base —
// strip the trailing /api to get the file host.
const FILE_ORIGIN = BASE_URL.replace(/\/api\/?$/, "");

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
  const [mapFile, setMapFile] = useState(null);
  const [mapPreview, setMapPreview] = useState("");
  const [mapUploading, setMapUploading] = useState(false);
  const [mapError, setMapError] = useState("");
  const fileInputRef = useRef(null);

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
      if (res?.data?.url) setMapUrl(res.data.url);
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
    setMapPreview(URL.createObjectURL(file));
  }

  async function handleMapUpload() {
    if (!mapFile) return;
    setMapUploading(true);
    setMapError("");
    try {
      const res = await api.adminUploadStallMap(token, mapFile);
      if (res?.data?.url) setMapUrl(res.data.url);
      setMapFile(null);
      setMapPreview("");
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setMapError(err.message || "Failed to upload stall map");
    } finally {
      setMapUploading(false);
    }
  }

  function holderLabel(s) {
    const holder = s.status === "booked" ? s.bookedBy : s.status === "held" ? s.heldBy : null;
    if (!holder) return "—";
    return `${holder.companyName || "—"} (${holder.registrationCode || ""})`;
  }

  const placeableCategories = (config.stallPackages || []).filter((p) => p.hasStallPicker);
  const categoryStallsForPlacement = placeCategory ? stalls.filter((s) => s.packageCode === placeCategory) : [];

  function handlePlaceCategoryChange(code) {
    setPlaceCategory(code);
    setPlaceMsg("");
    const catStalls = stalls.filter((s) => s.packageCode === code);
    const firstUnplaced = catStalls.find((s) => s.mapX == null || s.mapY == null);
    setPlaceStallId(firstUnplaced ? firstUnplaced._id : catStalls[0]?._id || "");
  }

  async function handlePlaceClick(e) {
    if (!placeStallId || !mapUrl || placingCoord) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const xPct = Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100));
    const yPct = Math.min(100, Math.max(0, ((e.clientY - rect.top) / rect.height) * 100));
    const mapX = Number(xPct.toFixed(2));
    const mapY = Number(yPct.toFixed(2));
    const placedStallNumber = categoryStallsForPlacement.find((s) => s._id === placeStallId)?.stallNumber;

    setPlacingCoord(true);
    setPlaceMsg("");
    try {
      await api.adminUpdateStall(token, placeStallId, { mapX, mapY });
      const res = await api.adminListStalls(token);
      setStalls(res.data);
      const catStalls = res.data.filter((s) => s.packageCode === placeCategory);
      const nextUnplaced = catStalls.find((s) => s.mapX == null || s.mapY == null);
      setPlaceStallId(nextUnplaced ? nextUnplaced._id : "");
      setPlaceMsg(
        nextUnplaced
          ? `${placedStallNumber || "Stall"} placed — now click the spot for ${nextUnplaced.stallNumber}.`
          : `${placedStallNumber || "Stall"} placed — every stall in this category now has a spot on the map.`
      );
    } catch (err) {
      setPlaceMsg(err.message || "Failed to place this stall");
    } finally {
      setPlacingCoord(false);
    }
  }

  return (
    <div>
      <div className="card form-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 6 }}>Stall Map</h3>
        <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 16 }}>
          Upload a layout image showing stall numbers and zones — this is shown to exhibitors on the registration
          page.
        </p>
        {mapError && <div className="alert alert-error">{mapError}</div>}
        <div className="logo-upload-row">
          {(mapPreview || mapUrl) && (
            <img
              className="stall-map-preview"
              src={mapPreview || `${FILE_ORIGIN}${mapUrl}`}
              alt="Stall map preview"
              style={{ maxWidth: 220 }}
            />
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg,image/webp"
              onChange={handleMapFileChange}
            />
            <button
              type="button"
              className="btn btn-dark"
              style={{ padding: "8px 18px", alignSelf: "flex-start" }}
              onClick={handleMapUpload}
              disabled={!mapFile || mapUploading}
            >
              {mapUploading ? "Uploading…" : "Upload Map"}
            </button>
          </div>
        </div>
      </div>

      {mapUrl && (
        <div className="card form-card" style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 6 }}>Place Stalls on Map</h3>
          <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 16 }}>
            Pick a numbered category and a stall below, then click that stall's spot on the map. Exhibitors
            pick their stall by tapping the same spot on the registration page — already-placed stalls in
            this category show as green dots, the one you're about to place shows in gold.
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
                {placeableCategories.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.label}
                  </option>
                ))}
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
            <div
              className="map-place-wrap"
              onClick={handlePlaceClick}
              style={{ opacity: placingCoord ? 0.7 : 1, cursor: placeStallId ? "crosshair" : "not-allowed" }}
            >
              <img src={`${FILE_ORIGIN}${mapUrl}`} alt="Stall map for placement" className="map-place-img" />
              {categoryStallsForPlacement
                .filter((s) => s.mapX != null && s.mapY != null)
                .map((s) => (
                  <div
                    key={s._id}
                    className={`map-place-marker ${s._id === placeStallId ? "is-current" : "is-placed"}`}
                    style={{ left: `${s.mapX}%`, top: `${s.mapY}%` }}
                  >
                    {s.stallNumber}
                  </div>
                ))}
            </div>
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
