import { useEffect, useState } from "react";

function getTimeParts(targetDate) {
  const total = Math.max(0, targetDate.getTime() - Date.now());
  const days = Math.floor(total / (1000 * 60 * 60 * 24));
  const hours = Math.floor((total / (1000 * 60 * 60)) % 24);
  const minutes = Math.floor((total / (1000 * 60)) % 60);
  const seconds = Math.floor((total / 1000) % 60);
  return { days, hours, minutes, seconds, done: total <= 0 };
}

export default function CountdownTimer({ targetISO }) {
  const target = new Date(`${targetISO}T00:00:00+05:30`);
  const [time, setTime] = useState(() => getTimeParts(target));

  useEffect(() => {
    const id = setInterval(() => setTime(getTimeParts(target)), 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetISO]);

  if (time.done) return null;

  const items = [
    { label: "Days", value: time.days },
    { label: "Hours", value: time.hours },
    { label: "Minutes", value: time.minutes },
    { label: "Seconds", value: time.seconds },
  ];

  return (
    <div className="countdown" aria-label="Countdown to event">
      {items.map((i) => (
        <div className="countdown-item" key={i.label}>
          <div className="countdown-num">{String(i.value).padStart(2, "0")}</div>
          <div className="countdown-label">{i.label}</div>
        </div>
      ))}
    </div>
  );
}
