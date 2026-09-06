// Minimal, dependency-free line-icon set (24x24, stroke = currentColor).
// Avoids pulling in an icon package so the project has fewer install-time
// dependencies to fetch.
const paths = {
  factory:
    "M3 21V10l6 4v-4l6 4v-4l6 4v7H3Z M6 21v-4 M12 21v-4 M18 21v-4",
  robot:
    "M9 7V4h6v3 M5 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z M9 12h.01 M15 12h.01 M9 16h6",
  gear:
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z M19.4 13.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V19.6a2 2 0 0 1-4 0v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H4.4a2 2 0 0 1 0-4h.09a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34H10.5a1.7 1.7 0 0 0 1-1.55V4.4a2 2 0 0 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87V10.5a1.7 1.7 0 0 0 1.55 1h.09a2 2 0 0 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1Z",
  tool:
    "M14.7 6.3a4 4 0 1 0-5.6 5.6L3 18l3 3 6.1-6.1a4 4 0 0 0 5.6-5.6l-2.3 2.3-2-2 2.3-2.3Z",
  building:
    "M4 21V4a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v17 M15 21h5v-9a1 1 0 0 0-1-1h-4 M8 7h1 M8 11h1 M8 15h1 M12 7h1 M12 11h1 M12 15h1",
  gem: "M6 3h12l3 6-9 12L3 9Z M3 9h18 M9 3 8 9l4 12 4-12-1-6",
  monitor: "M3 4h18v12H3z M8 20h8 M12 16v4",
  sun: "M12 4V2 M12 22v-2 M4 12H2 M22 12h-2 M5.6 5.6 4.2 4.2 M19.8 19.8l-1.4-1.4 M5.6 18.4 4.2 19.8 M19.8 4.2l-1.4 1.4 M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z",
  car: "M5 17h14 M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0Z M15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0Z M3 17V11l2-5h10l4 5v6 M3 11h16",
  heart: "M12 21s-7.5-4.6-10-9.3C.4 8.1 2 4.5 5.6 4A5 5 0 0 1 12 7a5 5 0 0 1 6.4-3c3.6.5 5.2 4.1 3.6 7.7C19.5 16.4 12 21 12 21Z",
  cart: "M3 4h2l2.4 12.1a2 2 0 0 0 2 1.6H18a2 2 0 0 0 2-1.6L21 8H6 M9.5 21a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4Z M17 21a1.2 1.2 0 1 0 0-2.4 1.2 1.2 0 0 0 0 2.4Z",
  cup: "M4 4h13v8a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V4Z M17 7h2a3 3 0 0 1 0 6h-2 M6 21h8",
  shirt: "M8 3 5 6l-2 3 3 2v10h12V11l3-2-2-3-3-3-2 2h-2L8 3Z",
  cap: "M22 12 12 8 2 12l10 4 7-2.8V17 M6 13.5V17c0 1.7 2.7 3 6 3s6-1.3 6-3v-3.5",
  bolt: "M13 2 4 14h6l-1 8 9-12h-6l1-8Z",
  plane: "m3 12 18-8-6 18-3-7-7-3Z",
  check: "M20 6 9 17l-5-5",
  mail: "M3 5h18v14H3z M3 6l9 7 9-7",
  phone: "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.8.6 2.7a2 2 0 0 1-.5 2.1L7.9 9.7a16 16 0 0 0 6 6l1.2-1.2a2 2 0 0 1 2.1-.5c.9.3 1.8.5 2.7.6a2 2 0 0 1 1.7 2Z",
  mapPin: "M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z M12 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z",
  menu: "M3 6h18 M3 12h18 M3 18h18",
  close: "M18 6 6 18 M6 6l12 12",
  x: "M18 6 6 18 M6 6l12 12",
  plus: "M12 5v14 M5 12h14",
  users: "M17 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M23 21v-2a4 4 0 0 0-3-3.9 M16 3.1a4 4 0 0 1 0 7.8",
  calendar: "M8 2v4 M16 2v4 M3 9h18 M4 5h16v15H4z",
  ticket: "M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4Z M10 4v16",
  download: "M12 3v12 M7 11l5 5 5-5 M4 21h16",
  store: "M3 9 4 4h16l1 5 M4 9v11h16V9 M4 9h16 M9 20v-6h6v6",
  spark: "M12 2v4 M12 18v4 M4.9 4.9l2.8 2.8 M16.3 16.3l2.8 2.8 M2 12h4 M18 12h4 M4.9 19.1l2.8-2.8 M16.3 7.7l2.8-2.8",
  // Paw print — stands in for the tiger (confidence, leadership, bold steps)
  pawprint:
    "M12 13.5c-2.2 0-4 1.8-4 3.6 0 1.7 1.5 2.9 4 2.9s4-1.2 4-2.9c0-1.8-1.8-3.6-4-3.6Z M7.5 9c-1.1 0-2 1-2 2.2s.9 2.2 2 2.2 2-1 2-2.2-.9-2.2-2-2.2Z M11.3 6.2c-1.1 0-2 1-2 2.2s.9 2.2 2 2.2 2-1 2-2.2-.9-2.2-2-2.2Z M14.9 6.2c-1.1 0-2 1-2 2.2s.9 2.2 2 2.2 2-1 2-2.2-.9-2.2-2-2.2Z M18.5 9c-1.1 0-2 1-2 2.2s.9 2.2 2 2.2 2-1 2-2.2-.9-2.2-2-2.2Z",
  // Orange — stands in for the Orange City (Nagpur): energy, positivity, growth
  citrus:
    "M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z M12 5V2 M12 3c1.4 0 2.4.8 2.8 2",
  // Flower — stands in for the rose (women entrepreneurs' strength & leadership)
  flower:
    "M12 12a2.6 2.6 0 1 0 0-5.2 2.6 2.6 0 0 0 0 5.2Z M12 17.2a2.6 2.6 0 1 0 0-5.2 2.6 2.6 0 0 0 0 5.2Z M6.8 12a2.6 2.6 0 1 0 5.2 0 2.6 2.6 0 0 0-5.2 0Z M12 12a2.6 2.6 0 1 0 5.2 0 2.6 2.6 0 0 0-5.2 0Z M12 12.9a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8Z",
};

export default function Icon({ name, className = "", size = 24 }) {
  const d = paths[name] || paths.spark;
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
