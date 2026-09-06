import CountUp from "./CountUp";

export default function StatsBar({ stats }) {
  return (
    <div className="stats-bar">
      {stats.map((s) => (
        <div key={s.label}>
          <div className="stat-num">
            <CountUp value={s.value} />
          </div>
          <div className="stat-label">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
