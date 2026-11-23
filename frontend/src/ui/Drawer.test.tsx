import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Drawer } from "./Drawer";

it("keeps the page available when course details use a nonmodal drawer", () => {
  render(<><button>Outside action</button><Drawer open modal={false} title="Synthetic course" onOpenChange={vi.fn()}><p>Details</p></Drawer></>);
  expect(screen.getByRole("button", { name: "Outside action" })).toBeInTheDocument();
  expect(document.body).not.toHaveAttribute("data-scroll-locked");
  expect(screen.getByRole("dialog")).not.toHaveAttribute("aria-modal", "true");
});
