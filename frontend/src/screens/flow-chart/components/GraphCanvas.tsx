import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY } from "d3-force";
import type { Simulation } from "d3-force";
import type { Course, TermId } from "@/api/types";
import { buildGraph, nodeRadius, related } from "../graph/buildGraph";
import type { GraphLink, GraphNode } from "../graph/buildGraph";
import { drawGraph } from "../graph/drawGraph";
import type { View } from "../graph/drawGraph";

export interface GraphControls {
  zoomBy: (f: number) => void;
  fit: () => void;
  reset: () => void;
}

interface Props {
  courses: Course[];
  terms: TermId[];
  selected: string | null;
  onSelect: (code: string) => void;
  reducedMotion: boolean;
}

// Last settled layout, so returning to the screen doesn't re-explode the graph.
const layoutCache = new Map<string, { x: number; y: number }>();
const clampK = (k: number) => Math.min(2.2, Math.max(0.4, k));

export const GraphCanvas = forwardRef<GraphControls, Props>(function GraphCanvas({ courses, terms, selected, onSelect, reducedMotion }, ref) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const st = useRef({
    sim: null as Simulation<GraphNode, GraphLink> | null,
    nodes: [] as GraphNode[],
    links: [] as GraphLink[],
    view: { k: 1, x: 0, y: 0, w: 0, h: 0 } as View,
    dpr: 1,
    hover: null as GraphNode | null,
    dragging: false,
    selected,
    courses,
    raf: 0,
  });

  const draw = () => {
    const s = st.current;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx || !s.view.w) return;
    const focusId = s.hover?.id ?? s.selected;
    drawGraph(ctx, s.dpr, s.view, s.nodes, s.links, focusId ? related(focusId, s.courses) : null, s.hover, s.selected, s.dragging);
  };
  const schedule = () => {
    const s = st.current;
    if (!s.raf) s.raf = requestAnimationFrame(() => ((s.raf = 0), draw()));
  };

  const fit = () => {
    const s = st.current;
    if (!s.nodes.length || !s.view.w) return;
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const n of s.nodes) {
      x0 = Math.min(x0, n.x ?? 0);
      x1 = Math.max(x1, n.x ?? 0);
      y0 = Math.min(y0, n.y ?? 0);
      y1 = Math.max(y1, n.y ?? 0);
    }
    const k = Math.max(0.5, Math.min(1.6, Math.min(s.view.w / (x1 - x0 + 150), s.view.h / (y1 - y0 + 110))));
    Object.assign(s.view, { k, x: -((x0 + x1) / 2) * k, y: -((y0 + y1) / 2) * k });
    schedule();
  };

  const createSim = (fresh: boolean) => {
    const s = st.current;
    s.sim?.stop();
    const { nodes, links } = buildGraph(s.courses, fresh ? undefined : layoutCache);
    s.nodes = nodes;
    s.links = links;
    const futureTerms = terms;
    const termX = (t: TermId | null) => (t ? (futureTerms.indexOf(t) - (futureTerms.length - 1) / 2) * 170 : 0);
    const sim = forceSimulation(nodes)
      .force("link", forceLink<GraphNode, GraphLink>(links).id((d) => d.id).distance(110).strength(0.5))
      .force("charge", forceManyBody().strength(-260))
      .force("collide", forceCollide<GraphNode>((d) => nodeRadius(d) + 18))
      .force("x", forceX<GraphNode>((d) => termX(d.course.term)).strength((d) => (d.course.term ? 0.14 : 0.01)))
      .force("y", forceY(0).strength(0.07))
      .alphaDecay(0.04)
      .stop();
    // Settle most of the layout before the first paint so the graph never explodes on screen.
    sim.tick(fresh || !layoutCache.size ? 260 : 40);
    sim.on("tick", () => {
      for (const n of nodes) layoutCache.set(n.id, { x: n.x ?? 0, y: n.y ?? 0 });
      schedule();
    });
    for (const n of nodes) layoutCache.set(n.id, { x: n.x ?? 0, y: n.y ?? 0 });
    if (!reducedMotion) sim.alpha(0.25).restart();
    s.sim = sim;
  };

  useImperativeHandle(ref, () => ({
    zoomBy: (f) => {
      const v = st.current.view;
      v.k = clampK(v.k * f);
      schedule();
    },
    fit,
    reset: () => {
      st.current.hover = null;
      createSim(true);
      fit();
    },
  }));

  // Build once; keep status changes in place without re-laying out.
  useEffect(() => {
    createSim(false);
    return () => {
      st.current.sim?.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const s = st.current;
    s.courses = courses;
    for (const n of s.nodes) n.course = courses.find((c) => c.code === n.id) ?? n.course;
    schedule();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courses]);

  useEffect(() => {
    st.current.selected = selected;
    schedule();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // Size the canvas to its container at device pixel ratio.
  useEffect(() => {
    const wrap = wrapRef.current!;
    const canvas = canvasRef.current!;
    let first = true;
    const ro = new ResizeObserver(() => {
      const s = st.current;
      s.dpr = window.devicePixelRatio || 1;
      s.view.w = wrap.clientWidth;
      s.view.h = wrap.clientHeight;
      canvas.width = Math.round(s.view.w * s.dpr);
      canvas.height = Math.round(s.view.h * s.dpr);
      if (first && s.view.w) {
        first = false;
        fit();
      }
      draw();
    });
    ro.observe(wrap);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Pointer: hover highlights, click selects, drag pins a node, background drag pans, wheel zooms.
  useEffect(() => {
    const c = canvasRef.current!;
    const s = st.current;
    let down: { x: number; y: number; moved: boolean; node: GraphNode | undefined; vx: number; vy: number } | null = null;
    const pos = (e: PointerEvent | WheelEvent | MouseEvent) => {
      const r = c.getBoundingClientRect();
      return { x: e.clientX - r.left, y: e.clientY - r.top };
    };
    const toWorld = (p: { x: number; y: number }) => ({ x: (p.x - s.view.w / 2 - s.view.x) / s.view.k, y: (p.y - s.view.h / 2 - s.view.y) / s.view.k });
    const nodeAt = (p: { x: number; y: number }) => {
      const w = toWorld(p);
      let best: GraphNode | undefined;
      let bd = Infinity;
      for (const n of s.nodes) {
        const d = Math.hypot((n.x ?? 0) - w.x, (n.y ?? 0) - w.y);
        if (d < nodeRadius(n) + 7 / s.view.k && d < bd) {
          bd = d;
          best = n;
        }
      }
      return best;
    };

    const onDown = (e: PointerEvent) => {
      c.setPointerCapture(e.pointerId);
      const p = pos(e);
      down = { ...p, moved: false, node: nodeAt(p), vx: s.view.x, vy: s.view.y };
      c.classList.add("grabbing");
    };
    const onMove = (e: PointerEvent) => {
      const p = pos(e);
      if (down) {
        if (Math.hypot(p.x - down.x, p.y - down.y) > 3) down.moved = true;
        if (!down.moved) return;
        if (down.node) {
          const w = toWorld(p);
          s.dragging = true;
          down.node.fx = w.x;
          down.node.fy = w.y;
          if (reducedMotion) {
            down.node.x = w.x;
            down.node.y = w.y;
          } else s.sim?.alphaTarget(0.2).restart();
        } else {
          s.view.x = down.vx + (p.x - down.x);
          s.view.y = down.vy + (p.y - down.y);
        }
        schedule();
        return;
      }
      const n = nodeAt(p) ?? null;
      if (n !== s.hover) {
        s.hover = n;
        c.classList.toggle("pointing", !!n);
        schedule();
      }
    };
    const onUp = () => {
      if (!down) return;
      if (down.node && !down.moved) onSelect(down.node.id);
      s.sim?.alphaTarget(0);
      s.dragging = false;
      down = null;
      c.classList.remove("grabbing");
      schedule();
    };
    const onLeave = () => {
      if (!down && s.hover) {
        s.hover = null;
        schedule();
      }
    };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const p = pos(e);
      const before = toWorld(p);
      s.view.k = clampK(s.view.k * (e.deltaY < 0 ? 1.1 : 0.9));
      s.view.x = p.x - s.view.w / 2 - before.x * s.view.k;
      s.view.y = p.y - s.view.h / 2 - before.y * s.view.k;
      schedule();
    };
    const onDbl = (e: MouseEvent) => {
      if (!nodeAt(pos(e))) fit();
    };
    c.addEventListener("pointerdown", onDown);
    c.addEventListener("pointermove", onMove);
    c.addEventListener("pointerup", onUp);
    c.addEventListener("pointercancel", onUp);
    c.addEventListener("pointerleave", onLeave);
    c.addEventListener("wheel", onWheel, { passive: false });
    c.addEventListener("dblclick", onDbl);
    return () => {
      c.removeEventListener("pointerdown", onDown);
      c.removeEventListener("pointermove", onMove);
      c.removeEventListener("pointerup", onUp);
      c.removeEventListener("pointercancel", onUp);
      c.removeEventListener("pointerleave", onLeave);
      c.removeEventListener("wheel", onWheel);
      c.removeEventListener("dblclick", onDbl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSelect, reducedMotion]);

  const linkCount = courses.reduce((a, c) => a + c.prereqs.filter((p) => courses.some((x) => x.code === p)).length, 0);

  return (
    <div className="surf cv" ref={wrapRef}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={`Course graph with ${courses.length} courses and ${linkCount} prerequisite links. The Semesters view has the same information as text.`}
      />
    </div>
  );
});
