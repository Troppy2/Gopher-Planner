import type { SimulationLinkDatum, SimulationNodeDatum } from "d3-force";
import type { Course } from "@/api/types";

export interface GraphNode extends SimulationNodeDatum {
  id: string;
  course: Course;
}
export type GraphLink = SimulationLinkDatum<GraphNode> & { source: GraphNode | string; target: GraphNode | string };

export const nodeRadius = (n: GraphNode) => 5.5 + n.course.credits * 1.2;

/** Pure: courses to nodes and prerequisite links. Positions come from `cache` when available. */
export function buildGraph(courses: Course[], cache?: Map<string, { x: number; y: number }>) {
  const ids = new Set(courses.map((c) => c.code));
  let seed = 11;
  const rnd = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const nodes: GraphNode[] = courses.map((c) => {
    const p = cache?.get(c.code);
    return { id: c.code, course: c, x: p?.x ?? (rnd() - 0.5) * 320, y: p?.y ?? (rnd() - 0.5) * 320 };
  });
  const links: GraphLink[] = [];
  for (const c of courses) for (const p of c.prereqs) if (ids.has(p)) links.push({ source: p, target: c.code });
  return { nodes, links };
}

/** Every course upstream (prerequisites) and downstream (dependents) of `code`. */
export function related(code: string, courses: Course[]) {
  const out = new Set([code]);
  const up = (c: string) => {
    for (const p of courses.find((x) => x.code === c)?.prereqs ?? []) {
      if (!out.has(p) && courses.some((x) => x.code === p)) {
        out.add(p);
        up(p);
      }
    }
  };
  const down = (c: string) => {
    for (const x of courses) {
      if (x.prereqs.includes(c) && !out.has(x.code)) {
        out.add(x.code);
        down(x.code);
      }
    }
  };
  up(code);
  down(code);
  return out;
}
