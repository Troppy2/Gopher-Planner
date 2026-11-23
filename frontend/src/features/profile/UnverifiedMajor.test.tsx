import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { UnverifiedMajorNote } from "./profileRules";

const options = { majors: ["Computer Science B.S.", "History B.A."], unverifiedMajors: ["History B.A."] };

describe("UnverifiedMajorNote", () => {
  it("warns for a machine-mapped major", () => {
    render(<UnverifiedMajorNote options={options} major="History B.A." />);
    expect(screen.getByText(/requirements are not verified/i)).toBeTruthy();
  });

  it("stays quiet for a reviewed major or no selection", () => {
    const { container } = render(<UnverifiedMajorNote options={options} major="Computer Science B.S." />);
    render(<UnverifiedMajorNote options={undefined} major="" />);
    expect(container.textContent).toBe("");
    expect(screen.queryByText(/not verified/i)).toBeNull();
  });
});
