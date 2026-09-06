export default function OrganizerStrip({ organizers }) {
  return (
    <div className="organizer-strip">
      {organizers.map((o) => (
        <div className="organizer-item" key={o.name}>
          <div className="org-name">{o.name}</div>
          <div className="org-tag">{o.tagline}</div>
        </div>
      ))}
    </div>
  );
}
