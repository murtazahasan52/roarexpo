import { useEffect, useLayoutEffect, useRef, useState } from "react";

// A venue map you can actually read on a phone.
//
// Wraps the drawing in a scrollable viewport with −/+/Fit zoom controls.
// The drawing is rendered at (zoom × viewport width), so at 2× a stall that
// was a thumbnail becomes a proper box; because every marker is positioned
// in percent it stays glued to its printed stall at any zoom. Panning:
// finger-scroll on touch, mouse-drag or scrollbars on a laptop.
//
// `children` are the markers; `wrapProps` go straight onto the positioned
// wrapper that holds the image (its onClick / onMouseLeave still see the
// same element, so click-to-place maths keep working).
const ZOOM_STEPS = [1, 1.5, 2, 2.5, 3, 4];
const MIN_READABLE_WIDTH = 900; // px — the drawing opens at least this wide so labels are legible

export default function ZoomableMap({ src, alt, imgClassName = "map-picker-img", wrapClassName = "map-picker-wrap", wrapProps = {}, children, maxHeight = "72vh", hint }) {
  const scrollerRef = useRef(null);
  const [zoom, setZoom] = useState(1);
  const [viewportWidth, setViewportWidth] = useState(0);
  const [ready, setReady] = useState(false);
  const drag = useRef(null);

  // Measure the viewport and pick an opening zoom that makes the drawing
  // readable: full width on a laptop, ~2.5× on a phone.
  useLayoutEffect(() => {
    const el = scrollerRef.current;
    if (!el) return undefined;
    const measure = () => {
      const w = el.clientWidth;
      if (!w) return;
      setViewportWidth(w);
      if (!ready) {
        const wanted = MIN_READABLE_WIDTH / w;
        const initial = ZOOM_STEPS.reduce((best, z) => (z >= wanted && best === null ? z : best), null) ?? ZOOM_STEPS[ZOOM_STEPS.length - 1];
        setZoom(w >= MIN_READABLE_WIDTH ? 1 : initial);
        setReady(true);
      }
    };
    measure();
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(measure) : null;
    if (ro) ro.observe(el);
    else window.addEventListener("resize", measure);
    return () => {
      if (ro) ro.disconnect();
      else window.removeEventListener("resize", measure);
    };
  }, [ready]);

  // Keep the point under the middle of the viewport fixed while zooming.
  function changeZoom(next) {
    const el = scrollerRef.current;
    const clamped = Math.min(ZOOM_STEPS[ZOOM_STEPS.length - 1], Math.max(1, next));
    if (!el || clamped === zoom) return;
    const cx = (el.scrollLeft + el.clientWidth / 2) / (viewportWidth * zoom);
    const cy = (el.scrollTop + el.clientHeight / 2) / Math.max(1, el.scrollHeight);
    setZoom(clamped);
    requestAnimationFrame(() => {
      el.scrollLeft = cx * viewportWidth * clamped - el.clientWidth / 2;
      el.scrollTop = cy * el.scrollHeight - el.clientHeight / 2;
    });
  }
  const stepIndex = ZOOM_STEPS.findIndex((z) => z >= zoom);
  const zoomIn = () => changeZoom(ZOOM_STEPS[Math.min(ZOOM_STEPS.length - 1, (stepIndex < 0 ? ZOOM_STEPS.length - 1 : stepIndex) + 1)]);
  const zoomOut = () => changeZoom(ZOOM_STEPS[Math.max(0, (stepIndex < 0 ? ZOOM_STEPS.length : stepIndex) - 1)]);

  // Mouse drag = pan. A drag that actually moved swallows the click that
  // follows it so it can't be mistaken for "place a stall here".
  function onPointerDown(e) {
    if (e.pointerType !== "mouse" || e.button !== 0) return;
    if (e.target.closest("[data-no-pan]")) return;
    const el = scrollerRef.current;
    drag.current = { x: e.clientX, y: e.clientY, left: el.scrollLeft, top: el.scrollTop, moved: false };
  }
  function onPointerMove(e) {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.x;
    const dy = e.clientY - d.y;
    if (!d.moved && Math.hypot(dx, dy) < 5) return;
    d.moved = true;
    const el = scrollerRef.current;
    el.scrollLeft = d.left - dx;
    el.scrollTop = d.top - dy;
  }
  function onPointerUp() {
    const d = drag.current;
    if (d && d.moved) {
      const el = scrollerRef.current;
      const swallow = (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
      };
      el.addEventListener("click", swallow, { capture: true, once: true });
      setTimeout(() => el.removeEventListener("click", swallow, { capture: true }), 0);
    }
    drag.current = null;
  }

  useEffect(() => {
    // Ctrl/⌘ + wheel zooms the map instead of the page.
    const el = scrollerRef.current;
    if (!el) return undefined;
    const onWheel = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      if (e.deltaY < 0) zoomIn();
      else zoomOut();
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  });

  const wrapStyle = { width: viewportWidth ? `${Math.round(viewportWidth * zoom)}px` : "100%", ...(wrapProps.style || {}) };

  return (
    <div className="zoom-map">
      <div className="zoom-map-toolbar">
        <div className="zoom-map-controls" role="group" aria-label="Map zoom">
          <button type="button" onClick={zoomOut} disabled={zoom <= 1} aria-label="Zoom out">
            −
          </button>
          <span className="zoom-map-level">{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={zoomIn} disabled={zoom >= ZOOM_STEPS[ZOOM_STEPS.length - 1]} aria-label="Zoom in">
            +
          </button>
          <button type="button" className="zoom-map-fit" onClick={() => changeZoom(1)} disabled={zoom === 1}>
            Fit
          </button>
        </div>
        <span className="zoom-map-hint">{hint || "Zoom in to read stall numbers · drag or scroll to move around the map"}</span>
      </div>
      <div
        ref={scrollerRef}
        className={`zoom-map-scroller ${zoom > 1 ? "is-zoomed" : ""}`}
        style={{ maxHeight }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div {...wrapProps} className={`${wrapClassName} ${wrapProps.className || ""}`} style={wrapStyle}>
          <img src={src} alt={alt} className={imgClassName} draggable={false} />
          {children}
        </div>
      </div>
    </div>
  );
}
