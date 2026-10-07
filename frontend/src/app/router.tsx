import { createBrowserRouter, Link, Navigate, useRouteError } from "react-router";
import type { ComponentType } from "react";
import { PublicLayout } from "./layouts/PublicLayout";
import { OnboardingLayout } from "./layouts/OnboardingLayout";
import { AppShell } from "./layouts/AppShell";
import { RequireAuth } from "./guards/RequireAuth";
import { RequireOnboarded } from "./guards/RequireOnboarded";

const screen = (load: () => Promise<{ default: ComponentType }>) => () => load().then((m) => ({ Component: m.default }));

function RouteError() {
  const error = useRouteError();
  if (import.meta.env.DEV) console.error(error);
  return (
    <div className="page narrow">
      <div className="surf empty">
        <h3>This page didn't load</h3>
        <p>Something went wrong while opening this screen. Reload to try again.</p>
        <button className="btn" onClick={() => location.reload()}>
          Reload
        </button>
      </div>
    </div>
  );
}

function NotFound() {
  return (
    <div className="page narrow">
      <div className="surf empty">
        <h3>Page not found</h3>
        <p>That address doesn't match any screen in Gopher Planner.</p>
        <Link className="btn" to="/dashboard">
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        element: <PublicLayout />,
        children: [{ path: "login", lazy: screen(() => import("@/screens/login/LoginScreen")) }],
      },
      {
        element: <RequireAuth />,
        children: [
          {
            path: "onboarding",
            element: <OnboardingLayout />,
            children: [
              { index: true, element: <Navigate to="coursework" replace /> },
              { path: "coursework", lazy: screen(() => import("@/screens/onboarding/CourseworkScreen")) },
              { path: "profile", lazy: screen(() => import("@/screens/onboarding/ProfileScreen")) },
              { path: "building", lazy: screen(() => import("@/screens/onboarding/BuildingPlanScreen")) },
            ],
          },
          {
            element: <RequireOnboarded />,
            children: [
              {
                element: <AppShell />,
                children: [
                  { path: "dashboard", lazy: screen(() => import("@/screens/dashboard/DashboardScreen")) },
                  { path: "flow-chart", lazy: screen(() => import("@/screens/flow-chart/FlowChartScreen")) },
                  { path: "catalog", lazy: screen(() => import("@/screens/course-catalog/CatalogScreen")) },
                  { path: "settings", lazy: screen(() => import("@/screens/settings/SettingsScreen")) },
                ],
              },
            ],
          },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
