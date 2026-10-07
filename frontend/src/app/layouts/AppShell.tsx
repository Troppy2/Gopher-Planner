import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useMatches, useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import * as Menu from "@radix-ui/react-dropdown-menu";
import { BookOpen, LayoutGrid, LogOut, Search, Settings, Waypoints } from "lucide-react";
import { getProfile } from "@/api/endpoints";
import { queryKeys } from "@/api/queryKeys";
import { initial } from "@/lib/format";
import { useSession } from "@/features/auth/session.store";
import { SearchOverlay } from "@/features/search/SearchOverlay";
import { CourseDrawer } from "@/features/course-detail/CourseDrawer";
import { UnsavedPlanBar } from "@/features/plan/UnsavedPlanBar";
import { useHideOnScroll } from "@/hooks/useHideOnScroll";

const NAV = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutGrid },
  { to: "/flow-chart", label: "Flow chart", Icon: Waypoints },
  { to: "/catalog", label: "Catalog", Icon: BookOpen },
  { to: "/settings", label: "Settings", Icon: Settings },
];
const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/flow-chart": "Flow chart",
  "/catalog": "Course catalog",
  "/settings": "Settings",
};
const PLAN_EDIT_SCREENS = ["/flow-chart", "/catalog"];

export function AppShell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [searchOpen, setSearchOpen] = useState(false);
  const { data: profile } = useQuery({ queryKey: queryKeys.profile, queryFn: getProfile });
  const { email, signOut } = useSession();
  // A route can hide the navigation pill with `handle: { hideNav: true }`.
  const pillHidden = useHideOnScroll();
  const hideNav = useMatches().some((m) => (m.handle as { hideNav?: boolean } | undefined)?.hideNav);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    document.title = TITLES[pathname] ? `${TITLES[pathname]} - Gopher Planner` : "Gopher Planner";
  }, [pathname]);

  return (
    <div className={hideNav ? "shell no-nav" : "shell"}>
      <div className="shell-main">
        <header className="hdr">
          <Link className="hdr-brand" to="/dashboard" aria-label="Gopher Planner, go to dashboard">
            <img src="/favicon.png" alt="" />
            Gopher Planner
          </Link>
          <button className="btn-search" onClick={() => setSearchOpen(true)} aria-label="Search courses, professors, or course codes">
            <Search className="ic" aria-hidden />
            <span>Search courses or professors</span>
            <kbd>Ctrl K</kbd>
          </button>
          <Menu.Root>
            <Menu.Trigger className="avatar" aria-label="Account menu">
              {initial(profile?.name ?? "")}
            </Menu.Trigger>
            <Menu.Portal>
              <Menu.Content className="menu" align="end" sideOffset={8}>
                <div className="menu-head">
                  <b>{profile?.name || "Student"}</b>
                  <span className="muted">{email}</span>
                </div>
                <Menu.Item className="menu-item" onSelect={() => navigate("/settings")}>
                  <Settings className="ic sm" aria-hidden />
                  Settings
                </Menu.Item>
                <Menu.Item
                  className="menu-item"
                  onSelect={() => {
                    signOut();
                    navigate("/login");
                  }}
                >
                  <LogOut className="ic sm" aria-hidden />
                  Sign out
                </Menu.Item>
              </Menu.Content>
            </Menu.Portal>
          </Menu.Root>
        </header>

        <main id="main">
          <Outlet />
        </main>
      </div>

      {!hideNav && (
        <nav className={pillHidden ? "pill-nav away" : "pill-nav"} aria-label="Primary">
          {NAV.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className="pill-link">
              <Icon className="ic" aria-hidden />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      )}
      {PLAN_EDIT_SCREENS.includes(pathname) && <UnsavedPlanBar />}
      <SearchOverlay open={searchOpen} onOpenChange={setSearchOpen} />
      <CourseDrawer />
    </div>
  );
}
