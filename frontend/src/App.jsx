import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";

import { EventConfigContext } from "./hooks/useEventConfig";
import { AdminAuthContext, useAdminAuthProviderValue } from "./hooks/useAdminAuth";
import { fallbackConfig } from "./eventConfigFallback";
import { api } from "./api";

import PublicLayout from "./layouts/PublicLayout";
import Home from "./pages/Home";
import Contact from "./pages/Contact";
import Enquiry from "./pages/Enquiry";
import StallDirectory from "./pages/StallDirectory";
import StallRegistration from "./pages/StallRegistration";
import VisitorRegistration from "./pages/VisitorRegistration";
import RegistrationSuccess from "./pages/RegistrationSuccess";
import AdminLogin from "./pages/AdminLogin";
import AdminDashboard from "./pages/AdminDashboard";
import ProtectedRoute from "./components/ProtectedRoute";
import NotFound from "./pages/NotFound";

export default function App() {
  const [config, setConfig] = useState(fallbackConfig);
  const [loading, setLoading] = useState(true);
  const adminAuth = useAdminAuthProviderValue();

  useEffect(() => {
    let cancelled = false;
    api
      .getConfig()
      .then((res) => {
        if (!cancelled && res?.data) setConfig(res.data);
      })
      .catch(() => {
        // API unreachable — fall back to bundled config so the site still renders
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <EventConfigContext.Provider value={{ config, loading }}>
      <AdminAuthContext.Provider value={adminAuth}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route path="/" element={<Home />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/enquiry" element={<Enquiry />} />
            <Route path="/stalls" element={<StallDirectory />} />
            <Route path="/register/exhibitor" element={<StallRegistration />} />
            <Route path="/register/visitor" element={<VisitorRegistration />} />
            <Route path="/register/success" element={<RegistrationSuccess />} />
            <Route path="*" element={<NotFound />} />
          </Route>

          <Route path="/admin/login" element={<AdminLogin />} />
          <Route
            path="/admin/dashboard"
            element={
              <ProtectedRoute>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AdminAuthContext.Provider>
    </EventConfigContext.Provider>
  );
}
