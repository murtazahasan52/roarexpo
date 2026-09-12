import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { Link } from "react-router-dom";

async function downloadCSV(url, token, filename) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

// Admin dashboard "Enquiries" tab — lists messages from the public Enquiry
// page, newest first, with a New / Handled filter, search, CSV export, and a
// per-row toggle to mark an enquiry handled (or reopen it).
export default function EnquiriesPanel({ token, onChange }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [newCount, setNewCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const limit = 20;

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const statusQs = statusFilter === "all" ? "" : `&status=${statusFilter}`;
      const qs = `?search=${encodeURIComponent(search)}&page=${page}&limit=${limit}${statusQs}`;
      const res = await api.adminEnquiries(token, qs);
      setRows(res.data || []);
      setTotal(res.total || 0);
      setNewCount(res.newCount || 0);
    } catch (err) {
      alert(err.message || "Failed to load enquiries");
    } finally {
      setLoading(false);
    }
  }, [token, search, page, statusFilter]);

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleStatus(row) {
    const next = row.status === "handled" ? "new" : "handled";
    setBusyId(row._id);
    try {
      await api.adminUpdateEnquiry(token, row._id, { status: next });
      await load();
      if (onChange) onChange();
    } catch (err) {
      alert(err.message || "Failed to update enquiry");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(row) {
    if (!window.confirm(`Delete the enquiry from ${row.name}? This cannot be undone.`)) return;
    setBusyId(row._id);
    try {
      await api.adminDeleteEnquiry(token, row._id);
      await load();
      if (onChange) onChange();
    } catch (err) {
      alert(err.message || "Failed to delete enquiry");
    } finally {
      setBusyId(null);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      await downloadCSV(api.exportUrl("enquiries"), token, "roar-expo-enquiries.csv");
    } catch (err) {
      alert(err.message || "Export failed");
    } finally {
      setExporting(false);
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <>
      <div className="toolbar" style={{ flexWrap: "wrap", gap: 12 }}>
        <input
          className="search-input"
          placeholder="Search enquiries by name, email, mobile or text…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="admin-tabs" style={{ margin: 0 }}>
          {[
            ["all", "All"],
            ["new", `New${newCount ? ` (${newCount})` : ""}`],
            ["handled", "Handled"],
          ].map(([value, label]) => (
            <div
              key={value}
              className={`admin-tab ${statusFilter === value ? "active" : ""}`}
              onClick={() => setStatusFilter(value)}
            >
              {label}
            </div>
          ))}
        </div>
        <button className="btn btn-dark" style={{ padding: "10px 20px" }} onClick={handleExport} disabled={exporting}>
          {exporting ? "Exporting…" : "Export CSV"}
        </button>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Received</th>
              <th>Name</th>
              <th>Email</th>
              <th>Mobile</th>
              <th>Enquiry</th>
              <th>Status</th>
              <th className="row-actions-cell">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: 32 }}>Loading…</td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: 32, color: "var(--text-muted)" }}>
                  No enquiries {statusFilter !== "all" ? `marked "${statusFilter}"` : "yet"}.
                </td>
              </tr>
            ) : (
              rows.map((r) => {
                const expanded = expandedId === r._id;
                const long = (r.details || "").length > 140;
                return (
                  <tr key={r._id}>
                    <td style={{ whiteSpace: "nowrap" }}>{new Date(r.createdAt).toLocaleString()}</td>
                    <td><strong>{r.name}</strong></td>
                    <td><a href={`mailto:${r.email}`}>{r.email}</a></td>
                    <td style={{ whiteSpace: "nowrap" }}>{r.mobile}</td>
                    <td style={{ maxWidth: 420, whiteSpace: "pre-wrap" }}>
                      {expanded || !long ? r.details : `${r.details.slice(0, 140)}…`}
                      {long && (
                        <button
                          type="button"
                          className="link-button"
                          style={{ display: "block", marginTop: 4 }}
                          onClick={() => setExpandedId(expanded ? null : r._id)}
                        >
                          {expanded ? "Show less" : "Read more"}
                        </button>
                      )}
                    </td>
                    <td>
                      <span className={`badge ${r.status === "handled" ? "badge-navy" : "badge-gold"}`}>
                        {r.status === "handled" ? "Handled" : "New"}
                      </span>
                    </td>
                    <td className="row-actions-cell">
                      <div className="row-actions">
                      <Link to={`/admin/enquiries/${r._id}`} className="btn btn-outline" style={{ padding: "6px 14px", fontSize: 13 }}>
                        View
                      </Link>
                      <button
                        className={`btn ${r.status === "handled" ? "btn-outline" : "btn-primary"}`}
                        style={{ padding: "6px 14px", fontSize: 13 }}
                        onClick={() => toggleStatus(r)}
                        disabled={busyId === r._id}
                      >
                        {busyId === r._id ? "…" : r.status === "handled" ? "Reopen" : "Mark Handled"}
                      </button>
                      <Link to={`/admin/enquiries/${r._id}?edit=1`} className="btn btn-outline" style={{ padding: "6px 14px", fontSize: 13 }}>
                        Edit
                      </Link>
                      <button
                        className="btn btn-outline btn-danger-outline"
                        style={{ padding: "6px 14px", fontSize: 13 }}
                        onClick={() => handleDelete(r)}
                        disabled={busyId === r._id}
                      >
                        Delete
                      </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {pageCount > 1 && (
        <div className="admin-tabs" style={{ marginTop: 16 }}>
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
            <div key={p} className={`admin-tab ${p === page ? "active" : ""}`} onClick={() => setPage(p)}>
              {p}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
