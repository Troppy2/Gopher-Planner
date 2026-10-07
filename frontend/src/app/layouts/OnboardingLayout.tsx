import { Outlet } from "react-router";
import { Brand } from "@/ui";

export function OnboardingLayout() {
  return (
    <main className="onb">
      <Brand to="/onboarding/coursework" />
      <Outlet />
    </main>
  );
}
