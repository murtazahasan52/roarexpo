import { Navigate } from "react-router-dom";
import { useAdminAuth } from "../hooks/useAdminAuth";

export default function ProtectedRoute({ children }) {
  const { session, ready } = useAdminAuth();

  if (!ready) return null;
  if (!session?.token) return <Navigate to="/admin/login" replace />;

  return children;
}
