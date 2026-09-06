import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="section">
      <div className="container" style={{ textAlign: "center" }}>
        <h2>Page not found</h2>
        <p className="lead" style={{ margin: "0 auto 24px" }}>
          The page you're looking for doesn't exist or may have moved.
        </p>
        <Link to="/" className="btn btn-primary">
          Back to Home
        </Link>
      </div>
    </section>
  );
}
