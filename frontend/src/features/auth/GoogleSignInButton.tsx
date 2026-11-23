import { useEffect, useRef, useState } from "react";

interface GoogleSignInButtonProps {
  onCredential: (credential: string) => void;
}

type Status = "loading" | "ready" | "unavailable" | "unconfigured";

const SCRIPT_TIMEOUT_MS = 8000;
const MIN_WIDTH = 200; // Google's limits for the rendered button
const MAX_WIDTH = 400;

// Google Identity Services warns when initialize runs more than once per page, so it runs once
// and forwards credentials to whichever button is currently mounted.
let initializedFor: string | null = null;
let activeCallback: ((credential: string) => void) | null = null;

export function resetGoogleInitForTests() {
  initializedFor = null;
  activeCallback = null;
}

function ensureInitialized(clientId: string) {
  if (initializedFor === clientId || !window.google) return;
  window.google.accounts.id.initialize({
    client_id: clientId,
    hd: "umn.edu", // only a hint for the account chooser; the server enforces the domain
    callback: (response: google.accounts.id.CredentialResponse) => {
      if (response.credential) activeCallback?.(response.credential);
    },
  });
  initializedFor = clientId;
}

export function GoogleSignInButton({ onCredential }: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onCredential);
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    callbackRef.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setStatus("unconfigured");
      return;
    }

    let done = false;
    const forward = (credential: string) => callbackRef.current(credential);
    const script = document.querySelector<HTMLScriptElement>('script[src="https://accounts.google.com/gsi/client"]');

    const render = () => {
      const element = buttonRef.current;
      if (done || !window.google || !element) return;
      done = true;
      ensureInitialized(clientId);
      activeCallback = forward;
      const available = element.parentElement?.clientWidth || MAX_WIDTH;
      element.replaceChildren();
      window.google.accounts.id.renderButton(element, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        logo_alignment: "left",
        width: Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, available)),
      });
      setStatus("ready");
    };
    const fail = () => {
      if (done) return;
      done = true;
      setStatus("unavailable");
    };

    render();
    script?.addEventListener("load", render);
    script?.addEventListener("error", fail);
    const timer = window.setTimeout(fail, SCRIPT_TIMEOUT_MS);

    return () => {
      done = true;
      window.clearTimeout(timer);
      script?.removeEventListener("load", render);
      script?.removeEventListener("error", fail);
      if (activeCallback === forward) activeCallback = null;
    };
  }, []);

  return (
    <div className="google-signin">
      {status === "loading" && (
        <p role="status" aria-live="polite" className="muted">
          Loading Google sign-in…
        </p>
      )}
      {status === "unavailable" && (
        <p role="alert">
          Google sign-in couldn't load. Check your connection or allow accounts.google.com in your
          content blocker, then reload the page.
        </p>
      )}
      {status === "unconfigured" && (
        <p role="alert">Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID and restart the app.</p>
      )}
      <div ref={buttonRef} hidden={status !== "ready" && status !== "loading"} />
    </div>
  );
}
