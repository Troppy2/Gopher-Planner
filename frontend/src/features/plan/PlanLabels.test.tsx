import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ElectiveNote, SlotTag } from "./PlanLabels";

describe("plan labels", () => {
  it("shows gen ed labels and remaining free elective credits", () => {
    render(<><SlotTag slot="Synthetic arts" /><ElectiveNote credits={7} /></>);
    expect(screen.getByText("Gen ed: Synthetic arts")).toBeInTheDocument();
    expect(screen.getByText("7 free elective credits still needed")).toBeInTheDocument();
  });
  it("omits empty labels and a zero elective balance", () => {
    const { container } = render(<><SlotTag /><ElectiveNote credits={0} /></>);
    expect(container).toBeEmptyDOMElement();
  });
});
