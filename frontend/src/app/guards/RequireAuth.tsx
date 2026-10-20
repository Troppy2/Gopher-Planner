import { Navigate, Outlet, useLocation } from "react-router";
import { useSession } from "@/features/auth/session.store";

export function RequireAuth() {
  const signedIn = useSession((s) => s.signedIn);
  const initialized = useSession((s) => s.initialized);
  const location = useLocation();

  if (!initialized) {
    return <p>Checking your session...</p>;
  }

  if (!signedIn) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
