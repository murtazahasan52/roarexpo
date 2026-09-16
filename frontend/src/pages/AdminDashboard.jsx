import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAdminAuth } from "../hooks/useAdminAuth";
import AdminsPanel from "../components/AdminsPanel";
import StallsPanel from "../components/StallsPanel";
import StallBookingPanel from "../components/StallBookingPanel";
import ScanCheckInPanel from "../components/ScanCheckInPanel";
import EntranceQRPanel from "../components/EntranceQRPanel";
import EnquiriesPanel from "../components/EnquiriesPanel";
import WhatsAppPanel from "../components/WhatsAppPanel";
import CountUp from "../components/CountUp";

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

async function openPDF(url, token) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Could not generate invoice");
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank");
  // Give the new tab time to load the blob before it's revoked.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
}

function StatCard({ label, value, sub }) {
  return (
    <div className="card admin-stat-card">
      <div className="admin-stat-num">
        <CountUp value={value} />
      </div>
      <div className="admin-stat-label">{label}</div>
      {sub && <div className="admin-stat-sub">{sub}</div>}
    </div>
  );
}

const TAB_LABELS = {
  exhibitors: "Exhibitors",
  book: "Book a Stall",
  stalls: "Stalls & Map",
  visitors: "Visitors",
  scan: "Scan & Check In",
  "entrance-qr": "Entrance QR",
  enquiries: "Enquiries",
  whatsapp: "WhatsApp",
  admins: "Admins",
};

// True if `permissions` (an array on the admin's session) holds "all" or
// any of the given permission names.
function hasAny(permissions, ...names) {
  const list = permissions || [];
  if (list.includes("all")) return true;
  return names.some((n) => list.includes(n));
}

function tabsForPermissions(permissions) {
  const tabs = [];
  if (hasAny(permissions, "exhibitors", "invoicing")) tabs.push("exhibitors");
  if (hasAny(permissions, "exhibitors")) tabs.push("book");
  if (hasAny(permissions, "stall-inventory")) tabs.push("stalls");
  if (hasAny(permissions, "visitors")) tabs.push("visitors");
  if (hasAny(permissions, "visitors", "scanning")) tabs.push("scan");
  if (hasAny(permissions, "visitors")) tabs.push("entrance-qr");
  if (hasAny(permissions, "enquiries")) tabs.push("enquiries");
  if (hasAny(permissions, "all")) tabs.push("whatsapp");
  if (hasAny(permissions, "all")) tabs.push("admins");
  return tabs;
}

export default function AdminDashboard() {
  const { session, logout } = useAdminAuth();
  const navigate = useNavigate();
  const token = session?.token;
  const permissions = session?.admin?.permissions || [];
  const availableTabs = tabsForPermissions(permissions);

  // Full exhibitor management (edit/approve/reject) vs. read-only access
  // (an "invoicing"-only admin can see the list to know who to invoice, but
  // can't act on registrations).
  const canManageExhibitors = hasAny(permissions, "exhibitors");
  const canSeeInvoice = hasAny(permissions, "exhibitors", "invoicing");
  const canSeeExhibitorsList = hasAny(permissions, "exhibitors", "invoicing");
  const canSeeVisitors = hasAny(permissions, "visitors");
  const canSeeCheckedInStat = hasAny(permissions, "visitors", "scanning");
  const canSeeEnquiries = hasAny(permissions, "enquiries");

  // The active tab lives in the URL (?tab=visitors) so a record page's
  // "← Dashboard" link — and the browser's Back button — return here.
  const [searchParams, setSearchParams] = useSearchParams();
  const urlTab = searchParams.get("tab");
  const tab = availableTabs.includes(urlTab) ? urlTab : availableTabs[0];
  const setTab = (t) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", t);
    setSearchParams(next);
  };
  const [stats, setStats] = useState({ exhibitorCount: 0, approvedExhibitorCount: 0, pendingExhibitorCount: 0, visitorCount: 0, checkedInCount: 0, newEnquiryCount: 0 });
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkInCode, setCheckInCode] = useState("");
  const [checkInMsg, setCheckInMsg] = useState("");
  const [exporting, setExporting] = useState(false);
  const [invoicingId, setInvoicingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const limit = 20;

  const [pkgSize, setPkgSize] = useState({});
  useEffect(() => {
    api.getConfig().then((r) => {
      const map = {};
      (r.data?.stallPackages || []).forEach((p) => { map[p.code] = p.size || p.sizeLabel || ""; });
      setPkgSize(map);
    }).catch(() => {});
  }, []);

  async function handleExport() {
    setExporting(true);
    try {
      await downloadCSV(api.exportUrl(tab), token, `roar-expo-${tab}.csv`);
    } catch (err) {
      alert(err.message || "Export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleInvoice(id) {
    setInvoicingId(id);
    try {
      await openPDF(api.adminInvoiceUrl(id), token);
    } catch (err) {
      alert(err.message || "Failed to generate invoice");
    } finally {
      setInvoicingId(null);
    }
  }

  const loadStats = useCallback(async () => {
    if (!token) return;
    try {
      const res = await api.adminStats(token);
      setStats(res.data);
    } catch (err) {
      if (err.message?.toLowerCase().includes("token")) logout();
    }
  }, [token, logout]);

  const loadRows = useCallback(async () => {
    if (!token || tab === "admins" || tab === "book" || tab === "stalls" || tab === "scan" || tab === "entrance-qr" || tab === "enquiries") return;
    setLoading(true);
    try {
      const qs = `?search=${encodeURIComponent(search)}&page=${page}&limit=${limit}`;
      const res = tab === "exhibitors" ? await api.adminExhibitors(token, qs) : await api.adminVisitors(token, qs);
      setRows(res.data);
      setTotal(res.total);
    } catch (err) {
      if (err.message?.toLowerCase().includes("token")) logout();
    } finally {
      setLoading(false);
    }
  }, [token, tab, search, page, logout]);

  useEffect(() => {
    if (!token) {
      navigate("/admin/login");
      return;
    }
    loadStats();
  }, [token, navigate, loadStats]);

  useEffect(() => {
    setPage(1);
  }, [tab, search]);

  useEffect(() => {
    loadRows();
  }, [loadRows]);

  const [decidingId, setDecidingId] = useState(null);
  const [pwModal, setPwModal] = useState(false);
  const [pwForm, setPwForm] = useState({ currentPassword: "", newPassword: "", confirmPassword: "" });
  const [pwSaving, setPwSaving] = useState(false);
  const [pwError, setPwError] = useState("");

  async function handleReopen(r) {
    if (!window.confirm(`Reopen ${r.companyName}'s registration? It goes back to pending, their stall is reserved again if still free, and they are emailed to review their details.`)) return;
    setDecidingId(r._id);
    try {
      const res = await api.adminReopenExhibitor(token, r._id);
      alert(res.message || "Registration reopened");
      loadRows();
      loadStats();
    } catch (err) {
      alert(err.message || "Failed to reopen");
    } finally {
      setDecidingId(null);
    }
  }

  async function handleApprove(id) {
    const paid = window.confirm(
      "Approve this exhibitor's stall booking.\n\nHas the payment been received?\n\nClick OK = mark PAID\nClick Cancel = mark UNPAID"
    );
    setDecidingId(id);
    try {
      await api.adminApproveExhibitor(token, id, paid ? "paid" : "unpaid");
      loadRows();
      loadStats();
    } catch (err) {
      alert(err.message || "Failed to approve exhibitor");
    } finally {
      setDecidingId(null);
    }
  }

  async function handleTogglePayment(r) {
    const next = r.paymentStatus === "paid" ? "unpaid" : "paid";
    try {
      await api.adminSetPayment(token, r._id, next);
      loadRows();
    } catch (err) {
      alert(err.message || "Failed to update payment status");
    }
  }

  async function handleReject(id) {
    if (!window.confirm("Reject this exhibitor's registration? Their stall (if any) will be released.")) return;
    setDecidingId(id);
    try {
      await api.adminRejectExhibitor(token, id);
      loadRows();
      loadStats();
    } catch (err) {
      alert(err.message || "Failed to reject exhibitor");
    } finally {
      setDecidingId(null);
    }
  }

  async function handleDeleteExhibitor(r) {
    if (
      !window.confirm(
        `Permanently delete the registration for ${r.companyName} (${r.registrationCode})? ` +
          "Their stall (if any) will be released. This cannot be undone."
      )
    )
      return;
    setDeletingId(r._id);
    try {
      await api.adminDeleteExhibitor(token, r._id);
      loadRows();
      loadStats();
    } catch (err) {
      alert(err.message || "Failed to delete exhibitor");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleDeleteVisitor(r) {
    if (!window.confirm(`Permanently delete the visitor registration for ${r.fullName} (${r.registrationCode})? This cannot be undone.`))
      return;
    setDeletingId(r._id);
    try {
      await api.adminDeleteVisitor(token, r._id);
      loadRows();
      loadStats();
    } catch (err) {
      alert(err.message || "Failed to delete visitor");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleCheckIn(e) {
    e.preventDefault();
    setCheckInMsg("");
    try {
      const res = await api.adminCheckIn(token, checkInCode);
      setCheckInMsg(res.alreadyCheckedIn ? "Already checked in earlier." : "Checked in successfully!");
      setCheckInCode("");
      loadRows();
      loadStats();
    } catch (err) {
      setCheckInMsg(err.message || "Check-in failed");
    }
  }

  const pageCount = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="admin-shell">
      <div className="admin-topbar">
        <div className="container admin-topbar-inner">
          <span className="brand-mark" style={{ fontSize: 20 }}>
            ROAR Admin
          </span>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              className="btn btn-outline-light"
              style={{ padding: "8px 18px" }}
              onClick={() => { setPwForm({ currentPassword: "", newPassword: "", confirmPassword: "" }); setPwError(""); setPwModal(true); }}
              data-testid="change-password-btn"
            >
              Change Password
            </button>
            <button
              className="btn btn-outline-light"
              style={{ padding: "8px 18px" }}
              onClick={() => {
                logout();
                navigate("/admin/login");
              }}
            >
              Log Out
            </button>
          </div>
        </div>
      </div>

      {pwModal && (
        <div className="modal-overlay" onClick={() => setPwModal(false)}>
          <div className="modal-panel" style={{ maxWidth: 420 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 style={{ margin: 0 }}>Change Password</h3>
              <button className="modal-close" onClick={() => setPwModal(false)} aria-label="Close">×</button>
            </div>
            <form
              className="modal-body"
              onSubmit={async (e) => {
                e.preventDefault();
                setPwError("");
                if (pwForm.newPassword !== pwForm.confirmPassword) { setPwError("New passwords do not match."); return; }
                if (pwForm.newPassword.length < 8) { setPwError("New password must be at least 8 characters."); return; }
                setPwSaving(true);
                try {
                  await api.adminChangePassword(token, pwForm);
                  setPwModal(false);
                  alert("Password changed successfully.");
                } catch (err) {
                  setPwError(err.message || "Could not change password.");
                } finally {
                  setPwSaving(false);
                }
              }}
            >
              {pwError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{pwError}</div>}
              <div className="field">
                <label>Current Password</label>
                <input type="password" value={pwForm.currentPassword} onChange={(e) => setPwForm((f) => ({ ...f, currentPassword: e.target.value }))} data-testid="pw-current" required />
              </div>
              <div className="field">
                <label>New Password</label>
                <input type="password" value={pwForm.newPassword} onChange={(e) => setPwForm((f) => ({ ...f, newPassword: e.target.value }))} data-testid="pw-new" minLength={8} required />
              </div>
              <div className="field">
                <label>Confirm New Password</label>
                <input type="password" value={pwForm.confirmPassword} onChange={(e) => setPwForm((f) => ({ ...f, confirmPassword: e.target.value }))} data-testid="pw-confirm" minLength={8} required />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setPwModal(false)} disabled={pwSaving}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={pwSaving} data-testid="pw-submit">{pwSaving ? "Saving…" : "Change Password"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="container" style={{ paddingTop: 32, paddingBottom: 60 }}>
        <div className="admin-stats">
          {canSeeExhibitorsList && (
            <StatCard
              label="Approved Exhibitors"
              value={stats.approvedExhibitorCount || 0}
              sub={`${stats.pendingExhibitorCount || 0} pending approval · ${stats.exhibitorCount || 0} total`}
            />
          )}
          {canSeeVisitors && <StatCard label="Visitor Registrations" value={stats.visitorCount} />}
          {canSeeCheckedInStat && <StatCard label="Visitors Checked In" value={stats.checkedInCount} />}
          {canSeeEnquiries && <StatCard label="New Enquiries" value={stats.newEnquiryCount || 0} />}
        </div>

        {tab === "visitors" && (
          <form className="card" style={{ padding: 20, marginBottom: 24, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }} onSubmit={handleCheckIn}>
            <strong style={{ fontSize: 14 }}>Check in visitor:</strong>
            <input
              className="search-input"
              placeholder="Enter registration code (e.g. RE-VIS-8F3K2Q)"
              value={checkInCode}
              onChange={(e) => setCheckInCode(e.target.value)}
            />
            <button className="btn btn-dark" type="submit" style={{ padding: "10px 20px" }}>
              Check In
            </button>
            {checkInMsg && <span style={{ fontSize: 13.5, color: "var(--text-muted)" }}>{checkInMsg}</span>}
          </form>
        )}

        {availableTabs.length > 1 && (
          <div className="admin-tabs">
            {availableTabs.map((t) => (
              <div key={t} className={`admin-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
                {TAB_LABELS[t]}
              </div>
            ))}
          </div>
        )}

        {tab === "admins" ? (
          <AdminsPanel token={token} />
        ) : tab === "book" ? (
          <StallBookingPanel token={token} onChange={loadStats} />
        ) : tab === "stalls" ? (
          <StallsPanel token={token} />
        ) : tab === "scan" ? (
          <ScanCheckInPanel token={token} />
        ) : tab === "entrance-qr" ? (
          <EntranceQRPanel token={token} />
        ) : tab === "enquiries" ? (
          <EnquiriesPanel token={token} onChange={loadStats} />
        ) : tab === "whatsapp" ? (
          <WhatsAppPanel token={token} />
        ) : (
          <>
            <div className="toolbar">
              <input
                className="search-input"
                placeholder={`Search ${tab}…`}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button className="btn btn-dark" style={{ padding: "10px 20px" }} onClick={handleExport} disabled={exporting}>
                {exporting ? "Exporting…" : "Export CSV"}
              </button>
            </div>

            <div className="table-wrap">
              {tab === "exhibitors" ? (
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Company</th>
                      <th className="exh-stall-col">Stall · Status · Actions</th>
                      <th>Size</th>
                      <th>Contact</th>
                      <th>Email</th>
                      <th>Phone</th>
                      <th>Category</th>
                      <th>Email Sent</th>
                      <th>WhatsApp</th>
                      <th>Registered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r._id}>
                        <td>{r.registrationCode}</td>
                        <td>{r.companyName}</td>
                        <td className="exh-stall-cell">
                          <div className="exh-stall-head">
                            {r.stallNumber ? (
                              <>
                                <strong>{r.stallNumber}</strong>
                                <span className="exh-muted">{r.stallPackage}</span>
                              </>
                            ) : (
                              <span>{r.stallPackage}</span>
                            )}
                          </div>
                          {r.fasciaName && <div className="exh-muted">Fascia: {r.fasciaName}</div>}
                          <div className="exh-badges">
                            <span
                              className={`badge ${
                                r.status === "confirmed"
                                  ? "badge-green"
                                  : r.status === "cancelled"
                                  ? "badge-gray"
                                  : "badge-navy"
                              }`}
                              data-testid={`status-badge-${r._id}`}
                            >
                              {r.status === "confirmed" ? "Confirmed" : r.status === "cancelled" ? "Cancelled" : "Pending"}
                            </span>
                            {r.status === "confirmed" && (
                              <span
                                className={`badge ${r.paymentStatus === "paid" ? "badge-green" : "badge-navy"}`}
                                data-testid={`payment-badge-${r._id}`}
                              >
                                {r.paymentStatus === "paid" ? "Paid" : "Unpaid"}
                              </span>
                            )}
                          </div>
                          {r.status === "confirmed" && (r.approvedByName || r.approvedBy?.name) && (
                            <div className="exh-muted">Approved by {r.approvedByName || r.approvedBy?.name}</div>
                          )}
                          <div className="exh-actions">
                            {canManageExhibitors && r.status === "pending" && (
                              <>
                                <button className="btn-mini btn-mini-green" onClick={() => handleApprove(r._id)} disabled={decidingId === r._id} data-testid={`approve-${r._id}`}>
                                  {decidingId === r._id ? "…" : "Approve"}
                                </button>
                                <button className="btn-mini btn-mini-red" onClick={() => handleReject(r._id)} disabled={decidingId === r._id} data-testid={`reject-${r._id}`}>
                                  Reject
                                </button>
                              </>
                            )}
                            {canManageExhibitors && r.status === "cancelled" && (
                              <button className="btn-mini" onClick={() => handleReopen(r)} disabled={decidingId === r._id} data-testid={`reopen-${r._id}`}>
                                {decidingId === r._id ? "…" : "Reopen"}
                              </button>
                            )}
                            {canManageExhibitors && r.status === "confirmed" && (
                              <button
                                className={`btn-mini ${r.paymentStatus === "paid" ? "btn-mini-amber" : "btn-mini-green"}`}
                                onClick={() => handleTogglePayment(r)}
                                data-testid={`payment-toggle-${r._id}`}
                              >
                                Mark {r.paymentStatus === "paid" ? "Unpaid" : "Paid"}
                              </button>
                            )}
                            <Link to={`/admin/exhibitors/${r._id}`} className="btn-mini" data-testid={`view-${r._id}`}>View</Link>
                            {canManageExhibitors && (
                              <Link to={`/admin/exhibitors/${r._id}?edit=1`} className="btn-mini">Edit</Link>
                            )}
                            {canSeeInvoice && (
                              <button className="btn-mini" onClick={() => handleInvoice(r._id)} disabled={invoicingId === r._id}>
                                {invoicingId === r._id ? "…" : "Invoice"}
                              </button>
                            )}
                            {canManageExhibitors && (
                              <button className="btn-mini btn-mini-red" onClick={() => handleDeleteExhibitor(r)} disabled={deletingId === r._id}>
                                {deletingId === r._id ? "…" : "Delete"}
                              </button>
                            )}
                          </div>
                        </td>
                        <td>{r.stallSize || pkgSize[r.stallPackage] || "—"}</td>
                        <td>{r.contactPerson}</td>
                        <td>{r.email}</td>
                        <td>{r.phone}</td>
                        <td>{r.category}</td>
                        <td>
                          <span className={`badge ${r.emailSent ? "badge-green" : "badge-gray"}`}>
                            {r.emailSent ? "Sent" : "Pending"}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${r.whatsappSent ? "badge-green" : "badge-gray"}`}>
                            {r.whatsappSent ? "Sent" : "—"}
                          </span>
                        </td>
                        <td>{new Date(r.createdAt).toLocaleString()}</td>
                      </tr>
                    ))}
                    {!loading && rows.length === 0 && (
                      <tr>
                        <td colSpan={11} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                          No exhibitor registrations yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Phone</th>
                      <th>Organization</th>
                      <th>Guests</th>
                      <th>Source</th>
                      <th>Checked In</th>
                      <th>Email Sent</th>
                      <th>WhatsApp</th>
                      <th>Registered</th>
                      <th className="row-actions-cell">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r._id}>
                        <td>{r.registrationCode}</td>
                        <td>{r.fullName}</td>
                        <td>{r.email}</td>
                        <td>{r.phone}</td>
                        <td>{r.organization}</td>
                        <td>{r.numberOfGuests}</td>
                        <td>
                          <span className={`badge ${r.source === "onsite" ? "badge-navy" : "badge-gray"}`}>
                            {r.source === "onsite" ? "Onsite" : "Online"}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${r.checkedIn ? "badge-green" : "badge-gray"}`}>
                            {r.checkedIn ? "Checked In" : "Not Yet"}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${r.emailSent ? "badge-green" : "badge-gray"}`}>
                            {r.emailSent ? "Sent" : "Pending"}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${r.whatsappSent ? "badge-green" : "badge-gray"}`}>
                            {r.whatsappSent ? "Sent" : "—"}
                          </span>
                        </td>
                        <td>{new Date(r.createdAt).toLocaleString()}</td>
                        <td className="row-actions-cell">
                          <div className="row-actions">
                          <Link to={`/admin/visitors/${r._id}`} className="btn btn-outline" style={{ padding: "6px 14px", fontSize: 12.5 }}>
                            View
                          </Link>
                          <Link to={`/admin/visitors/${r._id}?edit=1`} className="btn btn-outline" style={{ padding: "6px 14px", fontSize: 12.5 }}>
                            Edit
                          </Link>
                          <button
                            className="btn btn-outline btn-danger-outline"
                            style={{ padding: "6px 14px", fontSize: 12.5 }}
                            onClick={() => handleDeleteVisitor(r)}
                            disabled={deletingId === r._id}
                          >
                            {deletingId === r._id ? "…" : "Delete"}
                          </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!loading && rows.length === 0 && (
                      <tr>
                        <td colSpan={12} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                          No visitor registrations yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>

            {pageCount > 1 && (
              <div className="pagination">
                {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    className={`admin-tab ${p === page ? "active" : ""}`}
                    style={{ padding: "6px 14px" }}
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>

    </div>
  );
}
