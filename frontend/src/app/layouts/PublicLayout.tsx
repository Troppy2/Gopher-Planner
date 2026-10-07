import { Navigate, Outlet } from "react-router";
import { useSession } from "@/features/auth/session.store";

export function PublicLayout() {
  const signedIn = useSession((s) => s.signedIn);
  if (signedIn) return <Navigate to="/dashboard" replace />;
  return (
    <main>
      <Outlet />
    </main>
  );
}
