import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

const PERMISSION_OPTIONS = [
  { value: "all", label: "Full Access", hint: "Everything, plus managing other admins" },
  { value: "exhibitors", label: "Exhibitors", hint: "View, edit, approve/reject registrations" },
  { value: "stall-inventory", label: "Stalls & Map", hint: "Stall inventory + venue map upload" },
  { value: "visitors", label: "Visitors", hint: "List, search, export, and check in visitors" },
  { value: "scanning", label: "Scanning Only", hint: "Gate check-in only — no visitor list/export" },
  { value: "invoicing", label: "Invoicing", hint: "Generate stall booking-summary invoices" },
  { value: "enquiries", label: "Enquiries", hint: "Read and handle enquiries from the public Enquiry page" },
];

const PERMISSION_LABELS = Object.fromEntries(PERMISSION_OPTIONS.map((p) => [p.value, p.label]));

const initialForm = { name: "", email: "", password: "", permissions: ["exhibitors"] };

function PermissionBadges({ permissions = [] }) {
  if (permissions.includes("all")) {
    return <span className="badge badge-green">Full Access</span>;
  }
  if (permissions.length === 0) {
    return <span className="badge badge-gray">No access</span>;
  }
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {permissions.map((p) => (
        <span key={p} className="badge badge-navy">
          {PERMISSION_LABELS[p] || p}
        </span>
      ))}
    </div>
  );
}

export default function AdminsPanel({ token }) {
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [form, setForm] = useState(initialForm);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const loadAdmins = useCallback(async () => {
    setLoading(true);
    setListError("");
    try {
      const res = await api.adminListAdmins(token);
      setAdmins(res.data);
    } catch (err) {
      setListError(err.message || "Failed to load admins");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadAdmins();
  }, [loadAdmins]);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function togglePermission(value) {
    setForm((f) => {
      if (value === "all") {
        // "all" is exclusive — selecting it clears every other checkbox.
        return { ...f, permissions: f.permissions.includes("all") ? [] : ["all"] };
      }
      const withoutAll = f.permissions.filter((p) => p !== "all");
      const next = withoutAll.includes(value) ? withoutAll.filter((p) => p !== value) : [...withoutAll, value];
      return { ...f, permissions: next };
    });
  }

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");
    if (form.permissions.length === 0) {
      setFormError("Select at least one permission.");
      return;
    }
    setSubmitting(true);
    try {
      await api.adminCreateAdmin(token, form);
      setForm(initialForm);
      loadAdmins();
    } catch (err) {
      setFormError(err.message || "Failed to create admin");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Remove this admin's access? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      await api.adminDeleteAdmin(token, id);
      loadAdmins();
    } catch (err) {
      alert(err.message || "Failed to remove admin");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleResetPassword(a) {
    const pw = window.prompt(`Set a new password for ${a.name || a.email} (min 8 characters):`);
    if (pw === null) return;
    if (pw.length < 8) { alert("Password must be at least 8 characters."); return; }
    try {
      await api.adminResetAdminPassword(token, a._id, { newPassword: pw, confirmPassword: pw });
      alert(`Password reset for ${a.name || a.email}. They can now log in with the new password.`);
    } catch (err) {
      alert(err.message || "Failed to reset password");
    }
  }

  return (
    <div>
      <div className="card form-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 18 }}>Add an Admin</h3>
        {formError && <div className="alert alert-error">{formError}</div>}
        <form onSubmit={handleCreate}>
          <div className="form-row">
            <div className="field">
              <label>Name</label>
              <input required value={form.name} onChange={(e) => update("name", e.target.value)} />
            </div>
            <div className="field">
              <label>Email</label>
              <input required type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
            </div>
          </div>
          <div className="field">
            <label>Password</label>
            <input
              required
              type="password"
              minLength={8}
              placeholder="At least 8 characters"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
            />
          </div>

          <div className="field">
            <label>Permissions</label>
            <div className="permission-grid">
              {PERMISSION_OPTIONS.map((opt) => {
                const checked = form.permissions.includes(opt.value);
                const disabled = opt.value !== "all" && form.permissions.includes("all");
                return (
                  <label
                    key={opt.value}
                    className={`permission-option ${checked ? "checked" : ""} ${disabled ? "disabled" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={disabled}
                      onChange={() => togglePermission(opt.value)}
                    />
                    <span>
                      <strong>{opt.label}</strong>
                      <span className="permission-hint">{opt.hint}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <button className="btn btn-primary" type="submit" disabled={submitting} style={{ marginTop: 6 }}>
            {submitting ? "Creating…" : "Create Admin"}
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
              <th>Name</th>
              <th>Email</th>
              <th>Permissions</th>
              <th>Added</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {admins.map((a) => (
              <tr key={a._id}>
                <td>{a.name}</td>
                <td>{a.email}</td>
                <td>
                  <PermissionBadges permissions={a.permissions} />
                </td>
                <td>{new Date(a.createdAt).toLocaleDateString()}</td>
                <td style={{ display: "flex", gap: 8 }}>
                  <button
                    className="btn btn-outline"
                    style={{ padding: "6px 14px", fontSize: 12.5 }}
                    onClick={() => handleResetPassword(a)}
                    data-testid={`reset-pw-${a._id}`}
                  >
                    Reset Password
                  </button>
                  <button
                    className="btn btn-outline"
                    style={{
                      padding: "6px 14px",
                      fontSize: 12.5,
                      borderColor: "var(--rose-500)",
                      color: "var(--rose-500)",
                    }}
                    onClick={() => handleDelete(a._id)}
                    disabled={deletingId === a._id}
                  >
                    {deletingId === a._id ? "Removing…" : "Remove"}
                  </button>
                </td>
              </tr>
            ))}
            {!loading && admins.length === 0 && !listError && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>
                  No admins found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
