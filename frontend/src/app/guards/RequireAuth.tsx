import { Navigate, Outlet, useLocation } from "react-router";
import { useSession } from "@/features/auth/session.store";

export function RequireAuth() {
  const signedIn = useSession((s) => s.signedIn);
  const location = useLocation();
  if (!signedIn) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <Outlet />;
}
