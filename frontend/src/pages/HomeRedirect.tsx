import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "employee") return <Navigate to="/my-shifts" replace />;
  return <Navigate to="/stores" replace />;
}
