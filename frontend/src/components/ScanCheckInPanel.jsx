import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { api } from "../api";
import Icon from "./Icon";

const READER_ID = "roar-qr-reader";

export default function ScanCheckInPanel({ token }) {
  const scannerRef = useRef(null);
  const busyRef = useRef(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [starting, setStarting] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [manualCode, setManualCode] = useState("");
  const [result, setResult] = useState(null); // { kind: "success" | "already" | "error", message, visitor }
  const [sessionCount, setSessionCount] = useState(0);

  async function handleDecoded(decodedText) {
    if (busyRef.current) return;
    busyRef.current = true;
    const code = decodedText.trim().toUpperCase();
    try {
      const res = await api.adminCheckIn(token, code);
      const visitor = res.data;
      if (res.alreadyCheckedIn) {
        setResult({ kind: "already", message: "Already checked in earlier.", visitor });
      } else {
        setResult({ kind: "success", message: "Checked in successfully!", visitor });
        setSessionCount((n) => n + 1);
      }
    } catch (err) {
      setResult({ kind: "error", message: err.message || "Check-in failed.", visitor: null });
    } finally {
      // Pause briefly so the same QR still in frame doesn't immediately
      // re-trigger — the admin taps "Scan Next" to resume.
      if (scannerRef.current) {
        try {
          scannerRef.current.pause(true);
        } catch (e) {
          // ignore — scanner may have already stopped
        }
      }
    }
  }

  async function startScanner() {
    setCameraError("");
    setStarting(true);
    try {
      if (!scannerRef.current) {
        scannerRef.current = new Html5Qrcode(READER_ID);
      }
      await scannerRef.current.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 260, height: 260 } },
        (decodedText) => {
          handleDecoded(decodedText);
        },
        () => {
          // per-frame "no QR found" — expected constantly while aiming, ignore
        }
      );
      setCameraOn(true);
    } catch (err) {
      setCameraError(
        "Couldn't access the camera. Check your browser's camera permission for this page, or use the manual code entry below."
      );
    } finally {
      setStarting(false);
    }
  }

  async function stopScanner() {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop();
        scannerRef.current.clear();
      } catch (e) {
        // ignore
      }
    }
    setCameraOn(false);
    setResult(null);
  }

  function scanNext() {
    setResult(null);
    busyRef.current = false;
    if (scannerRef.current) {
      try {
        scannerRef.current.resume();
      } catch (e) {
        // ignore
      }
    }
  }

  useEffect(() => {
    return () => {
      if (scannerRef.current) {
        scannerRef.current.stop().then(() => scannerRef.current.clear()).catch(() => {});
      }
    };
  }, []);

  async function handleManualSubmit(e) {
    e.preventDefault();
    if (!manualCode.trim()) return;
    busyRef.current = false;
    await handleDecoded(manualCode.trim());
    setManualCode("");
  }

  return (
    <div>
      <div className="card form-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 6 }}>Scan &amp; Check In</h3>
        <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 20 }}>
          Point the camera at a visitor's ID card QR code (from their email or WhatsApp) to mark them
          checked in instantly. Checked in this session: <strong>{sessionCount}</strong>
        </p>

        {cameraError && <div className="alert alert-error">{cameraError}</div>}

        <div
          id={READER_ID}
          style={{
            maxWidth: 360,
            margin: "0 auto",
            borderRadius: 12,
            overflow: "hidden",
            background: cameraOn ? "transparent" : "#f4f5f8",
            minHeight: cameraOn ? "auto" : 220,
            display: cameraOn ? "block" : "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "1.5px solid var(--border-soft)",
          }}
        >
          {!cameraOn && (
            <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 20 }}>
              <Icon name="monitor" size={28} />
              <div style={{ fontSize: 13, marginTop: 8 }}>Camera preview will appear here</div>
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 18 }}>
          {!cameraOn ? (
            <button className="btn btn-primary" type="button" onClick={startScanner} disabled={starting}>
              {starting ? "Starting Camera…" : "Start Scanning"}
            </button>
          ) : (
            <button className="btn btn-outline" type="button" onClick={stopScanner}>
              Stop Camera
            </button>
          )}
        </div>

        {result && (
          <div
            className="card"
            style={{
              maxWidth: 420,
              margin: "20px auto 0",
              padding: 20,
              textAlign: "center",
              borderTop: `3px solid ${result.kind === "error" ? "var(--rose-500)" : "var(--gold-500)"}`,
            }}
          >
            <div
              style={{
                fontWeight: 700,
                fontSize: 15,
                color: result.kind === "error" ? "var(--rose-500)" : "var(--text-heading)",
                marginBottom: 6,
              }}
            >
              {result.message}
            </div>
            {result.visitor && (
              <div style={{ fontSize: 13.5, color: "var(--text-muted)" }}>
                {result.visitor.fullName} &middot; {result.visitor.registrationCode}
              </div>
            )}
            {cameraOn && (
              <button className="btn btn-dark" type="button" style={{ marginTop: 14, padding: "8px 20px" }} onClick={scanNext}>
                Scan Next Visitor
              </button>
            )}
          </div>
        )}
      </div>

      <div className="card form-card">
        <h3 style={{ marginBottom: 6 }}>Manual Code Entry</h3>
        <p style={{ fontSize: 13.5, color: "var(--text-muted)", marginBottom: 16 }}>
          No camera handy? Type or paste the registration code instead.
        </p>
        <form style={{ display: "flex", gap: 12, flexWrap: "wrap" }} onSubmit={handleManualSubmit}>
          <input
            className="search-input"
            style={{ flex: 1, minWidth: 220 }}
            placeholder="e.g. RE-VIS-8F3K2Q"
            value={manualCode}
            onChange={(e) => setManualCode(e.target.value)}
          />
          <button className="btn btn-dark" type="submit" style={{ padding: "10px 20px" }}>
            Check In
          </button>
        </form>
      </div>
    </div>
  );
}
