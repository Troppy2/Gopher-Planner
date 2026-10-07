import type { Course } from "@/api/types";
import { STATUS_LABEL } from "@/ui";
import { nodeRadius } from "./buildGraph";
import type { GraphLink, GraphNode } from "./buildGraph";

export interface View {
  k: number;
  x: number;
  y: number;
  w: number;
  h: number;
}

const COL = {
  done: "#1E6B4A",
  prog: "#FFCC33",
  progLine: "#8A5F00",
  plan: "#7A0019",
  avail: "#625A5C",
  block: "#A86400",
  blockFill: "#F6E6CC",
  card: "#FBF8F2",
  ink: "#201A1B",
  muted: "#625A5C",
};
const FONT = '"Hanken Grotesk", system-ui, sans-serif';

const statusLine = (c: Course) =>
  c.status === "plan" ? `Planned for ${c.term}` : c.status === "block" ? "Locked: major restriction" : STATUS_LABEL[c.status];

function shape(ctx: CanvasRenderingContext2D, n: GraphNode, alpha: number) {
  const r = nodeRadius(n);
  const x = n.x ?? 0;
  const y = n.y ?? 0;
  ctx.globalAlpha = alpha;
  if (n.course.status === "block") {
    ctx.beginPath();
    ctx.moveTo(x, y - r - 2);
    ctx.lineTo(x + r + 2, y);
    ctx.lineTo(x, y + r + 2);
    ctx.lineTo(x - r - 2, y);
    ctx.closePath();
    ctx.fillStyle = COL.blockFill;
    ctx.fill();
    ctx.strokeStyle = COL.block;
    ctx.lineWidth = 2;
    ctx.stroke();
    return;
  }
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  switch (n.course.status) {
    case "done":
      ctx.fillStyle = COL.done;
      ctx.fill();
      break;
    case "prog":
      ctx.fillStyle = COL.prog;
      ctx.fill();
      ctx.strokeStyle = COL.progLine;
      ctx.lineWidth = 2.2;
      ctx.stroke();
      break;
    case "plan":
      ctx.fillStyle = COL.card;
      ctx.fill();
      ctx.strokeStyle = COL.plan;
      ctx.lineWidth = 2.4;
      ctx.stroke();
      break;
    default:
      ctx.fillStyle = COL.card;
      ctx.fill();
      ctx.strokeStyle = COL.avail;
      ctx.lineWidth = 1.5;
      ctx.stroke();
  }
}

/** Pure draw over a context. `focus` highlights a course's prerequisite and dependent paths. */
export function drawGraph(
  ctx: CanvasRenderingContext2D,
  dpr: number,
  view: View,
  nodes: GraphNode[],
  links: GraphLink[],
  focus: Set<string> | null,
  hover: GraphNode | null,
  selected: string | null,
  dragging: boolean,
) {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, view.w, view.h);
  ctx.save();
  ctx.translate(view.w / 2 + view.x, view.h / 2 + view.y);
  ctx.scale(view.k, view.k);

  for (const l of links) {
    const a = l.source as GraphNode;
    const b = l.target as GraphNode;
    const on = !!focus && focus.has(a.id) && focus.has(b.id);
    ctx.globalAlpha = focus && !on ? 0.12 : 1;
    ctx.beginPath();
    ctx.moveTo(a.x ?? 0, a.y ?? 0);
    ctx.lineTo(b.x ?? 0, b.y ?? 0);
    ctx.strokeStyle = on ? COL.plan : "rgba(32,26,27,.30)";
    ctx.lineWidth = (on ? 1.8 : 1) / Math.max(0.8, view.k * 0.9);
    ctx.stroke();
    if (on) {
      // Arrowheads only on the highlighted path.
      const dx = (b.x ?? 0) - (a.x ?? 0);
      const dy = (b.y ?? 0) - (a.y ?? 0);
      const d = Math.hypot(dx, dy) || 1;
      const ux = dx / d;
      const uy = dy / d;
      const tx = (b.x ?? 0) - ux * (nodeRadius(b) + 4);
      const ty = (b.y ?? 0) - uy * (nodeRadius(b) + 4);
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(tx - ux * 8 - uy * 4, ty - uy * 8 + ux * 4);
      ctx.lineTo(tx - ux * 8 + uy * 4, ty - uy * 8 - ux * 4);
      ctx.closePath();
      ctx.fillStyle = COL.plan;
      ctx.fill();
    }
  }

  for (const n of nodes) {
    const dim = !!focus && !focus.has(n.id);
    if (n.id === selected || n === hover) {
      ctx.globalAlpha = 1;
      ctx.beginPath();
      ctx.arc(n.x ?? 0, n.y ?? 0, nodeRadius(n) + 6, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(122,0,25,.35)";
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    shape(ctx, n, dim ? 0.22 : 1);
    if (n.fx != null) {
      // Pinned marker.
      ctx.globalAlpha = dim ? 0.22 : 1;
      ctx.beginPath();
      ctx.arc(n.x ?? 0, n.y ?? 0, 2, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
    }
  }

  if (view.k > 0.5) {
    ctx.font = `600 ${12 / Math.max(0.75, view.k)}px ${FONT}`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const n of nodes) {
      ctx.globalAlpha = focus && !focus.has(n.id) ? 0.25 : 1;
      ctx.fillStyle = COL.ink;
      ctx.fillText(n.id, n.x ?? 0, (n.y ?? 0) + nodeRadius(n) + 6);
    }
  }
  ctx.restore();
  ctx.globalAlpha = 1;

  if (hover && !dragging) drawTooltip(ctx, view, hover);
}

function drawTooltip(ctx: CanvasRenderingContext2D, view: View, n: GraphNode) {
  const c = n.course;
  const sx = view.w / 2 + view.x + (n.x ?? 0) * view.k;
  const sy = view.h / 2 + view.y + (n.y ?? 0) * view.k - (nodeRadius(n) * view.k + 14);
  const t2 = c.title.length > 34 ? c.title.slice(0, 33) + "…" : c.title;
  const t3 = statusLine(c);
  ctx.font = `400 12px ${FONT}`;
  const w = Math.max(ctx.measureText(t2).width, ctx.measureText(t3).width, 60) + 20;
  const h = 62;
  const bx = Math.min(Math.max(sx - w / 2, 8), view.w - w - 8);
  let by = sy - h;
  if (by < 8) by = sy + nodeRadius(n) * view.k * 2 + 22;
  ctx.fillStyle = "#fff";
  ctx.strokeStyle = "rgba(32,26,27,.2)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(bx, by, w, h, 8);
  ctx.fill();
  ctx.stroke();
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = COL.ink;
  ctx.font = `700 13px ${FONT}`;
  ctx.fillText(c.code, bx + 10, by + 20);
  ctx.font = `400 12px ${FONT}`;
  ctx.fillStyle = COL.muted;
  ctx.fillText(t2, bx + 10, by + 37);
  ctx.fillStyle = COL.ink;
  ctx.font = `600 12px ${FONT}`;
  ctx.fillText(t3, bx + 10, by + 53);
}
