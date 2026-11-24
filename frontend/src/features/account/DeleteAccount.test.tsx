import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { useSession } from "@/features/auth/session.store";
import { DeleteAccount } from "./DeleteAccount";

const signedIn = () => useSession.setState({ signedIn: true, initialized: true, email: "synthetic@umn.edu", user: null });

it("deletes the account only after typed confirmation, then signs out", async () => {
  signedIn();
  let body: unknown = null;
  server.use(http.delete(api("/auth/account"), async ({ request }) => {
    body = await request.json();
    return HttpResponse.json({ message: "Account deleted" });
  }));
  const { client } = renderWithProviders(<DeleteAccount />);
  client.setQueryData(["profile"], { name: "Synthetic" });

  await userEvent.click(screen.getByRole("button", { name: "Delete account" }));
  const dialog = await screen.findByRole("dialog", { name: "Delete your account?" });
  const confirm = dialog.querySelector("button[type=submit]") as HTMLButtonElement;
  expect(confirm).toBeDisabled();

  await userEvent.type(screen.getByLabelText(/to confirm/), "delete");
  expect(confirm).toBeEnabled();
  await userEvent.click(confirm);

  expect(await screen.findByText("Navigated away")).toBeInTheDocument();
  expect(body).toEqual({ confirm: true });
  expect(useSession.getState().signedIn).toBe(false);
  expect(client.getQueryData(["profile"])).toBeUndefined();
});

it("keeps the user signed in and explains a failed deletion", async () => {
  signedIn();
  server.use(http.delete(api("/auth/account"), () => HttpResponse.json({ error: "Unavailable" }, { status: 503 })));
  renderWithProviders(<DeleteAccount />);

  await userEvent.click(screen.getByRole("button", { name: "Delete account" }));
  await userEvent.type(await screen.findByLabelText(/to confirm/), "DELETE");
  await userEvent.click(screen.getByRole("dialog").querySelector("button[type=submit]") as HTMLButtonElement);

  expect(await screen.findByText("Couldn't delete your account.")).toBeVisible();
  await waitFor(() => expect(useSession.getState().signedIn).toBe(true));
});
