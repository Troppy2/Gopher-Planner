import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet } from "react-router";
import { getProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";

export function RequireOnboarded() {
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  if (isLoading) return null;
  if (isError || !data) {
    return (
      <div className="page narrow">
        <div className="surf empty">
          <h3>We couldn't load your profile</h3>
          <p>Your planner needs your profile to open. Check your connection and try again.</p>
          <button className="btn" onClick={() => refetch()}>
            Try again
          </button>
        </div>
      </div>
    );
  }
  if (!data.onboarded) return <Navigate to="/onboarding/coursework" replace />;
  return <Outlet />;
}
