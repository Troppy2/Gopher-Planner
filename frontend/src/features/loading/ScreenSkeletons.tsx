import { CourseRowsSkeleton, Skeleton, SkeletonRegion } from "@/ui/Skeleton";

export function FieldsSkeleton({ count = 4 }: { count?: number }) {
  return <div className="skeleton-fields">{Array.from({ length: count }, (_, i) => <div className="skeleton-field" key={i}>
    <Skeleton width="45%" /><Skeleton height={44} />
  </div>)}</div>;
}

export function MetricsSkeleton() {
  return <SkeletonRegion label="progress"><div className="dgrid">
    {["g3", "g4"].map(size => <div className={`card surf skeleton-metric ${size}`} key={size}>
      <Skeleton width="46%" /><Skeleton width="55%" height={40} /><Skeleton height={8} /><Skeleton width="80%" />
    </div>)}
    <div className="card surf skeleton-progress g5"><div className="skeleton-ring" /><div className="skeleton-stack"><Skeleton width={120} /><Skeleton width={150} height={20} /><Skeleton width={180} /></div></div>
  </div></SkeletonRegion>;
}

function SectionSkeleton({ fields = false }: { fields?: boolean }) {
  return <div className="surf skeleton-section"><Skeleton width="40%" height={24} />{fields ? <FieldsSkeleton /> : <CourseRowsSkeleton />}</div>;
}

export function DashboardSkeleton() {
  return <div className="page"><div className="pg-head"><h1 className="title">Dashboard</h1></div>
    <SkeletonRegion label="dashboard"><div className="skeleton-heading"><Skeleton width="55%" height={20} /><Skeleton width={140} height={44} /></div>
      <MetricsSkeleton />
      <div className="dcols"><div className="dcol"><SectionSkeleton /><SectionSkeleton fields /></div><div className="dcol"><SectionSkeleton /><SectionSkeleton /></div></div>
    </SkeletonRegion>
  </div>;
}

export function SettingsSkeleton() {
  return <div className="page narrow"><div className="pg-head"><h1 className="title">Settings</h1></div>
    <SkeletonRegion label="settings">
      {[1, 4, 2].map((count, i) => <div className="sec surf" key={i}><div className="skeleton-heading"><Skeleton width={180} height={28} /></div><FieldsSkeleton count={count} /></div>)}
      <SectionSkeleton />
    </SkeletonRegion>
  </div>;
}

export function PlannerSkeleton({ view }: { view: "sem" | "graph" }) {
  return <SkeletonRegion label="plan">
    {view === "sem" ? <div className="sem">{[0, 1, 2].map(i => <div className="semcard surf skeleton-semester" key={i}>
      <div className="skeleton-heading"><Skeleton width="35%" height={26} /><Skeleton width="22%" /></div>
      <Skeleton height={8} /><CourseRowsSkeleton /><Skeleton width={110} height={32} />
    </div>)}</div> : <>
      <div className="tb surf"><Skeleton width={180} height={32} /><Skeleton width={100} height={32} /></div>
      <div className="surf skeleton-graph">{[0, 1, 2].map(col => <div className="skeleton-graph-column" key={col}>
        {[0, 1, 2].map(row => <div className="skeleton-node" key={row}><Skeleton width="65%" height={16} /><Skeleton /><Skeleton width="40%" /></div>)}
      </div>)}</div>
    </>}
  </SkeletonRegion>;
}

export function CatalogSkeleton() {
  return <SkeletonRegion label="catalog courses" className="skeleton-catalog">
    <div className="chead"><span>Course</span><span>Credits</span><span>Offered</span><span>Status</span><span /></div>
    <ul className="surf clist">{Array.from({ length: 6 }, (_, i) => <li className="citem" key={i}>
      <div className="cm"><Skeleton width="38%" height={16} /><Skeleton width={i % 2 ? "72%" : "90%"} /></div>
      <span className="c-cr"><Skeleton width={28} /></span><span className="c-off"><Skeleton width="70%" /></span>
      <span className="c-st"><Skeleton width={82} height={24} /></span><span className="acts"><Skeleton width={76} height={36} /></span>
    </li>)}</ul>
  </SkeletonRegion>;
}

export function DetailsSkeleton() {
  return <SkeletonRegion label="course details"><div className="skeleton-detail">
    <Skeleton width={110} height={26} />
    <div className="skeleton-detail-facts">{[0, 1, 2, 3].map(i => <div className="skeleton-stack" key={i}><Skeleton width="55%" /><Skeleton width="70%" height={20} /></div>)}</div>
    {[0, 1, 2].map(i => <div className="skeleton-stack" key={i}><Skeleton width="45%" height={20} /><Skeleton /><Skeleton /><Skeleton width="65%" /></div>)}
  </div></SkeletonRegion>;
}

export function WorkspaceSkeleton() {
  return <div className="page skeleton-workspace"><SkeletonRegion label="workspace">
    <div className="skeleton-heading"><Skeleton width={190} height={28} /><Skeleton width={36} height={36} /></div>
    <Skeleton width="45%" height={32} /><SectionSkeleton /><SectionSkeleton />
  </SkeletonRegion></div>;
}
