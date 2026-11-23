import { useState } from "react";
import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Combobox } from "./Combobox";

it("shows other majors when reopening a selected major", async () => {
  function Form() {
    const [value, setValue] = useState("Synthetic Alpha B.S.");
    return <Combobox label="Major" value={value} onChange={setValue} options={["Synthetic Alpha B.S.", "Synthetic Beta B.S."]} />;
  }
  render(<Form />);
  await userEvent.click(screen.getByRole("combobox"));
  await userEvent.click(screen.getByRole("option", { name: "Synthetic Beta B.S." }));
  await userEvent.click(screen.getByRole("combobox"));
  expect(screen.getByRole("option", { name: "Synthetic Alpha B.S." })).toBeVisible();
});
