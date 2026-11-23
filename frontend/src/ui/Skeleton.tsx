import type { CSSProperties, ReactNode } from "react";
import "./skeleton.css";

/** Decorative blocks never expose fake values or interactive controls. */
export function Skeleton({ width = "100%", height = 12, className = "" }: { width?: CSSProperties["width"]; height?: CSSProperties["height"]; className?: string }) {
  return <span aria-hidden="true" className={`skeleton ${className}`} style={{ width, height }} />;
}

export function SkeletonRegion({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return <div role="status" aria-label={`Loading ${label}`} className={className}>
    <span className="vh">Loading {label}…</span>
    <div aria-hidden="true" aria-busy="true">{children}</div>
  </div>;
}

export function CourseRowsSkeleton({ rows = 3 }: { rows?: number }) {
  return <div className="skeleton-course-list">{Array.from({ length: rows }, (_, index) => <div className="skeleton-course-row" key={index}>
    <div className="skeleton-stack"><Skeleton width="38%" height={16} /><Skeleton width={index % 2 ? "70%" : "90%"} /></div>
    <Skeleton width={52} height={20} />
  </div>)}</div>;
}
