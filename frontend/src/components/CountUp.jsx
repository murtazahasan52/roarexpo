import { useEffect, useRef, useState } from "react";

/**
 * Animates a numeric value counting up from 0 the first time it scrolls
 * into view. Accepts numbers or strings with a numeric prefix (e.g. "100+"),
 * and renders any non-numeric suffix as-is. If the value changes later (e.g.
 * dashboard stats loading in after mount), the displayed number updates.
 */
export default function CountUp({ value }) {
  const match = /^(\d+)(.*)$/.exec(String(value));
  const target = match ? Number(match[1]) : null;
  const suffix = match ? match[2] : "";

  const ref = useRef(null);
  const revealedRef = useRef(false);
  const [display, setDisplay] = useState(target === null ? value : 0);

  useEffect(() => {
    if (target === null) {
      setDisplay(value);
      return;
    }
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setDisplay(target);
      return;
    }
    // Already revealed once — reflect any later value change immediately.
    if (revealedRef.current) {
      setDisplay(target);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !revealedRef.current) {
          revealedRef.current = true;
          const duration = 1100;
          const startTime = performance.now();
          function tick(now) {
            const progress = Math.min(1, (now - startTime) / duration);
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplay(Math.round(eased * target));
            if (progress < 1) requestAnimationFrame(tick);
          }
          requestAnimationFrame(tick);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );

    observer.observe(el);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, value]);

  // Safety net: whatever the animation/observer does, always reflect the
  // latest numeric value shortly after it changes (fixes stat cards that load
  // their value asynchronously after mount).
  useEffect(() => {
    if (target === null) return;
    const t = setTimeout(() => setDisplay(target), 1300);
    return () => clearTimeout(t);
  }, [target]);

  return (
    <span ref={ref}>
      {display}
      {suffix}
    </span>
  );
}
