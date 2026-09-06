import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAdminAuth } from "../hooks/useAdminAuth";

export default function AdminLogin() {
  const { login } = useAdminAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.adminLogin({ email, password });
      login(res.token, res.admin);
      navigate("/admin/dashboard");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <form className="card login-card" onSubmit={handleSubmit}>
        <div className="eyebrow">Admin Access</div>
        <h2 style={{ marginBottom: 24 }}>ROAR Expo Dashboard</h2>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="field">
          <label>Email</label>
          <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label>Password</label>
          <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign In"}
        </button>
      </form>
    </div>
  );
}
