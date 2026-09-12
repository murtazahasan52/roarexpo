import Icon from "./Icon";

// One chrome for every "record" form (exhibitor, visitor, enquiry).
//
// `asPage` renders it as a full-width card on its own page — the admin
// record pages at /admin/<kind>/<id> — with no overlay and no close button
// (the page has its own Back link). Without it, the same markup pops up as
// a modal over the dashboard (kept for places that still want a quick edit).
export default function RecordFrame({ asPage = false, onClose, title, subtitle, error, actions, children, wide = false }) {
  const inner = (
    <>
      <div className="modal-header">
        <div>
          <h3 style={{ marginBottom: 2 }}>{title}</h3>
          {subtitle && <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>{subtitle}</div>}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
          {actions}
          {!asPage && (
            <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
              <Icon name="close" />
            </button>
          )}
        </div>
      </div>
      {error && <div className="alert alert-error" style={{ margin: "16px 24px 0" }}>{error}</div>}
      {children}
    </>
  );

  if (asPage) return <div className={`card record-card ${wide ? "record-card-wide" : ""}`}>{inner}</div>;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal-panel card ${wide ? "modal-panel-wide" : ""}`} onClick={(e) => e.stopPropagation()}>
        {inner}
      </div>
    </div>
  );
}
