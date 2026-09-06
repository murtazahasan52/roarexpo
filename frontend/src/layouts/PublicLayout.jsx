import { Outlet, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import WhatsAppButton from "../components/WhatsAppButton";

export default function PublicLayout() {
  const location = useLocation();

  useEffect(() => {
    if (location.hash) {
      // Wait a tick for the target route/section to render before scrolling.
      const id = location.hash.slice(1);
      const raf = requestAnimationFrame(() => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
      return () => cancelAnimationFrame(raf);
    }
    window.scrollTo(0, 0);
  }, [location.pathname, location.hash]);

  return (
    <>
      <Navbar />
      <main>
        <Outlet />
      </main>
      <Footer />
      <WhatsAppButton />
    </>
  );
}
