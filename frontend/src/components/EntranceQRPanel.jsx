import { useEffect, useState } from "react";
import { api } from "../api";

export default function EntranceQRPanel({ token }) {
  const [qr, setQr] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .adminEntranceQR(token)
      .then((res) => {
        if (!cancelled) setQr(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load the entrance QR code");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="card form-card">
      <h3 style={{ marginBottom: 6 }}>Entrance QR — Walk-in Registration</h3>
      <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 20, maxWidth: 560 }}>
        Print this and display it at the main entrance. Visitors who haven't pre-registered can scan
        it with their own phone camera to open the registration form; the moment they submit, their
        ID card with a QR code is emailed (and sent on WhatsApp, once configured) to them — ready to
        be scanned back in at Scan &amp; Check In.
      </p>

      {error && <div className="alert alert-error">{error}</div>}
      {loading && <p style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading…</p>}

      {qr && (
        <div id="entrance-qr-poster">
          <div
            style={{
              maxWidth: 420,
              margin: "0 auto",
              textAlign: "center",
              padding: "36px 28px",
              border: "1.5px solid var(--border-soft)",
              borderRadius: 16,
              background: "#fff",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontWeight: 800,
                fontSize: 26,
                letterSpacing: 3,
                color: "var(--navy-900)",
                marginBottom: 4,
              }}
            >
              ROAR
            </div>
            <div style={{ fontSize: 12, letterSpacing: 1.5, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 20 }}>
              Business Expo &ndash; Nagpur
            </div>
            <img
              src={qr.qrDataUrl}
              alt="Scan to register at the entrance"
              style={{ width: 260, height: 260, margin: "0 auto", display: "block" }}
            />
            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text-heading)", marginTop: 20 }}>
              Scan to Register &amp; Get Your Entry Pass
            </div>
            <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 6, wordBreak: "break-all" }}>{qr.url}</div>
          </div>
        </div>
      )}

      {qr && (
        <div style={{ textAlign: "center", marginTop: 20 }}>
          <button className="btn btn-dark" type="button" style={{ padding: "10px 22px" }} onClick={() => window.print()}>
            Print Poster
          </button>
        </div>
      )}
    </div>
  );
}
