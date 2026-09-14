import { useEffect, useState } from "react";
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
  const [installEvent, setInstallEvent] = useState(null);
  const [installed, setInstalled] = useState(
    typeof window !== "undefined" && window.matchMedia?.("(display-mode: standalone)").matches
  );

  useEffect(() => {
    function onPrompt(e) {
      e.preventDefault();
      setInstallEvent(e);
    }
    function onInstalled() {
      setInstalled(true);
      setInstallEvent(null);
    }
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  async function handleInstall() {
    if (!installEvent) {
      alert(
        "To install this admin app:\n\n• iPhone/iPad (Safari): tap the Share icon → \"Add to Home Screen\".\n• Android/Chrome: open the browser menu (⋮) → \"Install app\" / \"Add to Home screen\".\n\nOnce installed, it stays signed in on this device until you log out."
      );
      return;
    }
    installEvent.prompt();
    try { await installEvent.userChoice; } catch { /* ignore */ }
    setInstallEvent(null);
  }

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

        {!installed && (
          <button
            type="button"
            className="btn btn-outline btn-block"
            style={{ marginTop: 12 }}
            onClick={handleInstall}
            data-testid="install-admin-app-btn"
          >
            Install Admin App on this device
          </button>
        )}
        <p style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center", marginTop: 10, marginBottom: 0 }}>
          {installed ? "Installed — stays signed in until you log out." : "Install it once — it stays signed in on this device until you log out."}
        </p>
      </form>
    </div>
  );
}
