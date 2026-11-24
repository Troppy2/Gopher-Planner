import { describe, expect, it } from "vitest";
import type { RequirementProgress } from "@/api/types";
import { buildTree } from "./buildTree";
export const node = (id: string, type = "group", parentId: string | null = null): RequirementProgress => ({
  id, type, parentId, label: id, category: "Major core", completedStatus: "unsatisfied", projectedStatus: "unsatisfied",
  completedEvidence: { matchedCodes: [], missingCodes: [], appliedAdjustments: [] },
  projectedEvidence: { matchedCodes: [], missingCodes: [], appliedAdjustments: [] }, details: [],
});
describe("buildTree", () => {
  it("rebuilds nesting in source order and ignores orphans", () => {
    const tree = buildTree([node("g"), node("a", "all", "g"), node("x", "course", "a"), node("y", "course", "a"), node("orphan", "course", "missing")]);
    expect(tree.map(n => n.id)).toEqual(["g"]);
    expect(tree[0].children[0].children.map(n => n.id)).toEqual(["x", "y"]);
  });
  it("flattens only same-kind single-child wrappers", () => {
    const tree = buildTree([node("g"), node("a", "all", "g"), node("b", "all", "a"), node("c", "any", "b"), node("x", "course", "c")]);
    expect(tree[0].children[0].id).toBe("b");
    expect(tree[0].children[0].children[0].id).toBe("c");
  });
});

describe("buildTree notes", () => {
  it("keeps each evaluator note only on the node it comes from", () => {
    const withDetails = (n: RequirementProgress, details: string[]) => ({ ...n, details });
    const tree = buildTree([
      withDetails(node("g"), ["Group note", "Leaf note"]),
      withDetails(node("a", "all", "g"), ["Leaf note"]),
      withDetails(node("x", "course", "a"), ["Leaf note"]),
    ]);
    expect(tree[0].details).toEqual(["Group note"]);
    expect(tree[0].children[0].details).toEqual([]);
    expect(tree[0].children[0].children[0].details).toEqual(["Leaf note"]);
  });
});
