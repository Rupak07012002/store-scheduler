import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function PrivateRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-6 text-slate-500">Loading...</p>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
