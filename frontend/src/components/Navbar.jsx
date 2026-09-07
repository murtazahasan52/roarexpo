import { useState } from "react";
import { NavLink } from "react-router-dom";
import Icon from "./Icon";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/#about", label: "About" },
  { to: "/#categories", label: "Categories" },
  { to: "/contact", label: "Contact" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <NavLink to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark">ROAR</span>
          <span className="brand-sub">Business Expo – Nagpur</span>
        </NavLink>

        <nav className={`nav-links ${open ? "open" : ""}`}>
          {links.map((l) => (
            <NavLink
              key={l.label}
              to={l.to}
              end={l.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              {l.label}
            </NavLink>
          ))}
          <div className="mobile-only-ctas">
            <NavLink to="/register/exhibitor" className="btn btn-primary" onClick={() => setOpen(false)}>
              Exhibit
            </NavLink>
            <NavLink to="/register/visitor" className="btn btn-outline" onClick={() => setOpen(false)}>
              Visit
            </NavLink>
          </div>
        </nav>

        <div className="nav-cta">
          <NavLink to="/register/visitor" className="btn btn-outline">
            Register as Visitor
          </NavLink>
          <NavLink to="/register/exhibitor" className="btn btn-primary">
            Register as Exhibitor
          </NavLink>
        </div>

        <button className="nav-toggle" onClick={() => setOpen((v) => !v)} aria-label="Toggle menu">
          <Icon name={open ? "close" : "menu"} />
        </button>
      </div>
    </header>
  );
}
