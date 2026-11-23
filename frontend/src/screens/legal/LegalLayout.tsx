import type { ReactNode } from "react";
import { Link, NavLink } from "react-router";
import { useSession } from "@/features/auth/session.store";
import "./legal.css";

export const LEGAL_UPDATED = "November 23, 2026";
export const REPO_URL = "https://github.com/Troppy2/Gopher-Planner";
export const ISSUES_URL = `${REPO_URL}/issues`;

/** Shared frame for Privacy, Terms and Contact. Readable signed in or out. */
export function LegalLayout({ title, updated = true, children }: { title: string; updated?: boolean; children: ReactNode }) {
  const signedIn = useSession((s) => s.signedIn);
  return (
    <div className="legal-page">
      <header className="legal-top">
        <Link className="hdr-brand" to={signedIn ? "/dashboard" : "/login"}>
          <img src="/favicon.png" alt="" />
          Gopher Planner
        </Link>
        <nav aria-label="Legal and contact">
          <NavLink to="/privacy">Privacy</NavLink>
          <NavLink to="/terms">Terms</NavLink>
          <NavLink to="/contact">Contact</NavLink>
        </nav>
      </header>
      <main className="legal-body">
        <h1 className="title">{title}</h1>
        {updated && <p className="muted">Last updated {LEGAL_UPDATED}</p>}
        {children}
      </main>
    </div>
  );
}
