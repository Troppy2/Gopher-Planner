import type { RequirementProgress } from "@/api/types";
export interface RequirementTree extends RequirementProgress { children: RequirementTree[] }
export function buildTree(nodes: RequirementProgress[]): RequirementTree[] {
  const map = new Map(nodes.map(node => [node.id, { ...node, children: [] } as RequirementTree]));
  const roots: RequirementTree[] = [];
  for (const node of map.values()) {
    if (node.parentId === null) roots.push(node);
    else map.get(node.parentId)?.children.push(node);
  }
  const flatten = (node: RequirementTree): RequirementTree => {
    const children = node.children.map(flatten);
    const child = children[0];
    if ((node.type === "all" || node.type === "any") && children.length === 1 && child.type === node.type && !node.details.length && !node.projectedEvidence.appliedAdjustments.length) return child;
    return { ...node, children };
  };
  return roots.map(flatten);
}
