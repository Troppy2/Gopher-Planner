import type { RequirementProgress } from "@/api/types";
export interface RequirementTree extends RequirementProgress { children: RequirementTree[] }
/** A course rule's code: its label can be an official course name, so prefer the evaluator's evidence. */
export function courseCode(node: RequirementProgress): string {
  const evidence = [node.projectedEvidence, node.completedEvidence];
  return evidence.flatMap((e) => [...e.matchedCodes, ...e.missingCodes])[0] ?? node.label;
}

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
  // The evaluator repeats a rule's notes on every ancestor; keep each note only where it originates.
  const own = (node: RequirementTree): Set<string> => {
    const below = new Set<string>();
    for (const child of node.children) own(child).forEach((detail) => below.add(detail));
    const mine = node.details.filter((detail) => !below.has(detail));
    node.details = mine;
    mine.forEach((detail) => below.add(detail));
    return below;
  };
  const trees = roots.map(flatten);
  trees.forEach(own);
  return trees;
}
