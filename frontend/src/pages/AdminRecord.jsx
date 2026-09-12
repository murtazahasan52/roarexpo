import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAdminAuth } from "../hooks/useAdminAuth";
import ExhibitorEditModal from "../components/ExhibitorEditModal";
import VisitorEditModal from "../components/VisitorEditModal";
import EnquiryEditModal from "../components/EnquiryEditModal";

// A full page for one record — /admin/exhibitors/:id, /admin/visitors/:id,
// /admin/enquiries/:id. Opens in view mode (every field the person
// submitted), switches to edit mode with the Edit button (or ?edit=1 from a
// table's Edit link), and carries the record's own actions in the header:
// approve/reject/invoice/delete for exhibitors, check-in/delete for
// visitors, handled/reopen/delete for enquiries.
const KINDS = {
  exhibitors: {
    label: "Exhibitor",
    tab: "exhibitors",
    fetch: (token, id) => api.adminGetExhibitor(token, id),
    remove: (token, id) => api.adminDeleteExhibitor(token, id),
    describe: (r) => `${r.companyName} (${r.registrationCode})`,
    canEdit: (perms) => hasAny(perms, "exhibitors"),
    canView: (perms) => hasAny(perms, "exhibitors", "invoicing"),
  },
  visitors: {
    label: "Visitor",
    tab: "visitors",
    fetch: (token, id) => api.adminGetVisitor(token, id),
    remove: (token, id) => api.adminDeleteVisitor(token, id),
    describe: (r) => `${r.fullName} (${r.registrationCode})`,
    canEdit: (perms) => hasAny(perms, "visitors"),
    canView: (perms) => hasAny(perms, "visitors"),
  },
  enquiries: {
    label: "Enquiry",
    tab: "enquiries",
    fetch: (token, id) => api.adminGetEnquiry(token, id),
    remove: (token, id) => api.adminDeleteEnquiry(token, id),
    describe: (r) => `the enquiry from ${r.name}`,
    canEdit: (perms) => hasAny(perms, "enquiries"),
    canView: (perms) => hasAny(perms, "enquiries"),
  },
};

function hasAny(permissions, ...names) {
  const list = permissions || [];
  if (list.includes("all")) return true;
  return names.some((n) => list.includes(n));
}

async function openPDF(url, token) {
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error("Could not generate invoice");
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  window.open(objectUrl, "_blank");
  setTimeout(() => URL.revokeObjectURL(objectUrl), 30000);
}

export default function AdminRecord() {
  const { kind, id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { session, logout } = useAdminAuth();
  const token = session?.token;
  const permissions = session?.admin?.permissions || [];
  const spec = KINDS[kind];

  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");
  const editing = searchParams.get("edit") === "1";
  const backTo = `/admin/dashboard?tab=${spec?.tab || "exhibitors"}`;

  const load = useCallback(async () => {
    if (!token || !spec) return;
    setLoading(true);
    setError("");
    try {
      const res = await spec.fetch(token, id);
      setRecord(res.data);
    } catch (err) {
      if (err.message?.toLowerCase().includes("token")) logout();
      setError(err.message || "Could not load this record");
    } finally {
      setLoading(false);
    }
  }, [token, spec, id, logout]);

  useEffect(() => {
    load();
  }, [load]);

  function setEditing(on) {
    const next = new URLSearchParams(searchParams);
    if (on) next.set("edit", "1");
    else next.delete("edit");
    setSearchParams(next, { replace: true });
  }

  async function run(label, fn, { confirm, afterDelete } = {}) {
    if (confirm && !window.confirm(confirm)) return;
    setBusy(label);
    setNotice("");
    try {
      const res = await fn();
      if (afterDelete) {
        navigate(backTo, { replace: true });
        return;
      }
      setNotice(res?.message || `${label} done`);
      await load();
    } catch (err) {
      setNotice(err.message || `${label} failed`);
    } finally {
      setBusy("");
    }
  }

  const canEdit = spec ? spec.canEdit(permissions) : false;
  const canView = spec ? spec.canView(permissions) : false;
  const canInvoice = hasAny(permissions, "exhibitors", "invoicing");

  const actionBtn = (label, onClick, { danger = false, primary = false, title = "" } = {}) => (
    <button
      key={label}
      type="button"
      className={`btn ${primary ? "btn-primary" : "btn-outline"} ${danger ? "btn-danger-outline" : ""}`}
      style={{ padding: "6px 14px", fontSize: 12.5 }}
      onClick={onClick}
      disabled={Boolean(busy)}
      title={title}
    >
      {busy === label ? "…" : label}
    </button>
  );

  function headerActions() {
    if (!record) return null;
    const list = [];
    if (kind === "exhibitors") {
      if (canEdit && record.status === "pending") {
        list.push(
          actionBtn("Approve", () => run("Approve", () => api.adminApproveExhibitor(token, id)), { primary: true }),
          actionBtn("Reject", () => run("Reject", () => api.adminRejectExhibitor(token, id), { confirm: `Reject ${record.companyName}'s registration?` }), { danger: true })
        );
      }
      if (canEdit && record.status === "cancelled") {
        list.push(
          actionBtn("Reopen", () => run("Reopen", () => api.adminReopenExhibitor(token, id), { confirm: `Reopen ${record.companyName}'s registration? It goes back to pending, their stall is reserved again if still free, and they are emailed to review their details.` }), { primary: true })
        );
      }
      if (canInvoice) list.push(actionBtn("Invoice", () => run("Invoice", () => openPDF(api.adminInvoiceUrl(id), token))));
    }
    if (kind === "visitors" && canEdit && !record.checkedIn) {
      list.push(actionBtn("Check in", () => run("Check in", () => api.adminCheckIn(token, record.registrationCode)), { primary: true }));
    }
    if (kind === "enquiries" && canEdit) {
      const handled = record.status === "handled";
      list.push(
        actionBtn(handled ? "Reopen" : "Mark handled", () =>
          run(handled ? "Reopen" : "Mark handled", () => api.adminUpdateEnquiry(token, id, { status: handled ? "new" : "handled" }))
        , { primary: !handled })
      );
    }
    if (canEdit && !editing) list.push(actionBtn("Edit", () => setEditing(true)));
    if (canEdit) {
      list.push(
        actionBtn(
          "Delete",
          () =>
            run("Delete", () => spec.remove(token, id), {
              confirm: `Permanently delete ${spec.describe(record)}? This cannot be undone.`,
              afterDelete: true,
            }),
          { danger: true }
        )
      );
    }
    return list;
  }

  const formProps = {
    token,
    asPage: true,
    readOnly: !editing || !canEdit,
    headerActions: headerActions(),
    onClose: () => (editing ? setEditing(false) : navigate(backTo)),
    onSaved: () => {
      setEditing(false);
      setNotice("Changes saved");
      load();
    },
  };

  return (
    <div className="admin-shell">
      <div className="admin-topbar">
        <div className="container admin-topbar-inner">
          <span className="brand-mark" style={{ fontSize: 20 }}>
            ROAR Admin
          </span>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <Link to={backTo} className="btn btn-outline-light" style={{ padding: "8px 18px" }}>
              ← Dashboard
            </Link>
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

      <div className="container record-page">
        <div className="record-breadcrumb">
          <Link to={backTo}>{spec ? `${spec.label}s` : "Dashboard"}</Link>
          <span>›</span>
          <span>{record ? (kind === "enquiries" ? record.name : record.registrationCode) : "…"}</span>
        </div>

        {notice && (
          <div className="alert" style={{ background: "#eef6ff", color: "#1c4e8a", border: "1px solid #cfe3fb" }}>
            {notice}
          </div>
        )}

        {!spec ? (
          <div className="card form-card">Unknown record type.</div>
        ) : !canView ? (
          <div className="card form-card">Your admin account doesn't have access to {spec.label.toLowerCase()} records.</div>
        ) : loading ? (
          <div className="card form-card" style={{ color: "var(--text-muted)" }}>Loading…</div>
        ) : error || !record ? (
          <div className="card form-card">
            <div className="alert alert-error">{error || "Not found"}</div>
            <Link to={backTo} className="btn btn-outline">Back to {spec.label.toLowerCase()}s</Link>
          </div>
        ) : kind === "exhibitors" ? (
          <ExhibitorEditModal key={`${record.updatedAt}-${editing}`} exhibitor={record} {...formProps} />
        ) : kind === "visitors" ? (
          <VisitorEditModal key={`${record.updatedAt}-${editing}`} visitor={record} {...formProps} />
        ) : (
          <EnquiryEditModal key={`${record.updatedAt}-${editing}`} enquiry={record} {...formProps} />
        )}
      </div>
    </div>
  );
}
