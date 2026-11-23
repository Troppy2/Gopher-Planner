import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GoogleSignInButton, resetGoogleInitForTests } from "./GoogleSignInButton";

function fakeGoogle() {
  const initialize = vi.fn();
  const renderButton = vi.fn((element: HTMLElement, _options: google.accounts.id.GsiButtonConfiguration) => {
    element.append(Object.assign(document.createElement("div"), { textContent: "Google button" }));
  });
  window.google = { accounts: { id: { initialize, renderButton } } } as unknown as typeof google;
  return { initialize, renderButton };
}

describe("GoogleSignInButton", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "synthetic-client.apps.googleusercontent.com");
    resetGoogleInitForTests();
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.useRealTimers();
    (window as { google?: unknown }).google = undefined;
  });

  it("renders Google's button, hints the umn.edu domain and initializes once across remounts", () => {
    const { initialize, renderButton } = fakeGoogle();
    const first = render(<GoogleSignInButton onCredential={() => {}} />);
    expect(screen.getByText("Google button")).toBeInTheDocument();
    first.unmount();
    render(<GoogleSignInButton onCredential={() => {}} />);
    expect(initialize).toHaveBeenCalledTimes(1);
    expect(initialize.mock.calls[0][0]).toMatchObject({ hd: "umn.edu" });
    expect(renderButton).toHaveBeenCalledTimes(2);
    const width = renderButton.mock.calls[0]?.[1].width ?? 0;
    expect(width).toBeGreaterThanOrEqual(200);
    expect(width).toBeLessThanOrEqual(400);
  });

  it("routes the credential to the latest callback", () => {
    const { initialize } = fakeGoogle();
    const first = vi.fn();
    const second = vi.fn();
    const view = render(<GoogleSignInButton onCredential={first} />);
    view.rerender(<GoogleSignInButton onCredential={second} />);
    act(() => initialize.mock.calls[0][0].callback({ credential: "synthetic-token" }));
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledWith("synthetic-token");
  });

  it("shows a loading state, then explains when Google's script never arrives", () => {
    vi.useFakeTimers();
    render(<GoogleSignInButton onCredential={() => {}} />);
    expect(screen.getByRole("status")).toHaveTextContent(/loading google sign-in/i);
    act(() => vi.advanceTimersByTime(10_000));
    expect(screen.getByRole("alert")).toHaveTextContent(/couldn't load/i);
  });

  it("explains a missing client ID instead of rendering nothing", () => {
    vi.stubEnv("VITE_GOOGLE_CLIENT_ID", "");
    fakeGoogle();
    render(<GoogleSignInButton onCredential={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/unavailable right now/i);
  });
});
