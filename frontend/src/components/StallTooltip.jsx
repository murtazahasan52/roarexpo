import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const STATUS_LABEL = {
  available: "Available",
  held: "Reserved — pending confirmation",
  booked: "Booked",
  blocked: "Not available",
};

// Hover / tap card for a stall marker, shared by the public Stalls page and
// the exhibitor registration map.
//
// The card is rendered on <body> with position: fixed (a portal), so the
// scrolling map can never clip it — the top row used to lose its card above
// the frame. It flips below the marker near the top of the screen and is
// clamped inside the viewport sideways so long firm names stay readable on a
// phone. Mouse: hover. Touch: tap to open, tap again / tap elsewhere to close.
export function useStallTip() {
  const [hover, setHover] = useState(null); // stallNumber
  const [tip, setTip] = useState(null); // { x, y, below }
  const lastPointer = useRef("mouse"); // what kind of pointer touched a marker last

  function showTip(stallNumber, el) {
    const r = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const half = Math.min(140, Math.max(90, (vw - 32) / 2));
    const x = Math.min(vw - 16 - half, Math.max(16 + half, r.left + r.width / 2));
    const below = r.top < 150;
    setTip({ x, y: below ? r.bottom : r.top, below });
    setHover(stallNumber);
  }
  function hideTip() {
    setHover(null);
    setTip(null);
  }

  useEffect(() => {
    if (!hover) return undefined;
    const off = () => hideTip();
    const outside = (e) => {
      if (!e.target.closest(".map-marker")) hideTip();
    };
    document.addEventListener("pointerdown", outside);
    window.addEventListener("scroll", off, true);
    window.addEventListener("resize", off);
    window.addEventListener("touchmove", off, { passive: true });
    return () => {
      document.removeEventListener("pointerdown", outside);
      window.removeEventListener("scroll", off, true);
      window.removeEventListener("resize", off);
      window.removeEventListener("touchmove", off);
    };
  }, [hover]);

  // Spread onto a marker: hover on mouse, tap-to-toggle on touch, keyboard focus.
  const markerProps = (stallNumber) => ({
    onPointerDown: (e) => {
      lastPointer.current = e.pointerType || "mouse";
    },
    onPointerEnter: (e) => e.pointerType === "mouse" && showTip(stallNumber, e.currentTarget),
    onFocus: (e) => showTip(stallNumber, e.currentTarget),
    onBlur: hideTip,
    "data-tip-target": stallNumber,
  });
  // Call from the marker's onClick (returns true when the click opened the card).
  const toggleTip = (stallNumber, el) => {
    if (hover === stallNumber) {
      hideTip();
      return false;
    }
    showTip(stallNumber, el);
    return true;
  };

  const isTouch = () => lastPointer.current === "touch";

  return { hover, tip, showTip, hideTip, toggleTip, markerProps, isTouch };
}

export function StallTip({ stall, tip, packageLabel, extra }) {
  if (!stall || !tip) return null;
  return createPortal(
    <div className={`map-tooltip is-fixed ${tip.below ? "is-below" : ""}`} style={{ left: tip.x, top: tip.y }} role="tooltip">
      <strong>
        {stall.stallNumber} · {packageLabel(stall.packageCode)}
      </strong>
      {stall.status === "booked" && stall.owner ? (
        <>
          <div>{stall.owner.companyName || "—"}</div>
          {stall.owner.contactPerson && <div className="tip-muted">{stall.owner.contactPerson}</div>}
        </>
      ) : (
        <div className="tip-muted">{STATUS_LABEL[stall.status] || stall.status}</div>
      )}
      {extra && <div className="tip-muted" style={{ marginTop: 4 }}>{extra}</div>}
    </div>,
    document.body
  );
}

export { STATUS_LABEL };
