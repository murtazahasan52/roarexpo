import { useEffect, useRef, useState } from "react";

/**
 * Animates a numeric value counting up from 0 the first time it scrolls
 * into view. Accepts numbers or strings with a numeric prefix (e.g. "100+"),
 * and renders any non-numeric suffix as-is once the count finishes.
 */
export default function CountUp({ value }) {
  const match = /^(\d+)(.*)$/.exec(String(value));
  const target = match ? Number(match[1]) : null;
  const suffix = match ? match[2] : "";

  const ref = useRef(null);
  const [display, setDisplay] = useState(target === null ? value : 0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    if (target === null) return; // not a number-led value — nothing to animate
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setDisplay(target);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started) {
          setStarted(true);
          const duration = 1100;
          const startTime = performance.now();
          function tick(now) {
            const progress = Math.min(1, (now - startTime) / duration);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
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
  }, [target]);

  return (
    <span ref={ref}>
      {display}
      {suffix}
    </span>
  );
}
