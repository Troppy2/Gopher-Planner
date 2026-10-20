import { useEffect, useRef } from "react";

interface GoogleSignInButtonProps {
  onCredential: (credential: string) => void;
}

export function GoogleSignInButton({ onCredential }: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onCredential);

  useEffect(() => {
    callbackRef.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    let cancelled = false;

    const renderButton = () => {
      if (cancelled || !window.google || !buttonRef.current) {
        return;
      }

      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

      if (!clientId) {
        console.error("Missing VITE_GOOGLE_CLIENT_ID");
        return;
      }

      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          const credential = response.credential;

          if (credential) {
            callbackRef.current(credential);
          }
        },
      });

      buttonRef.current.replaceChildren();

      window.google.accounts.id.renderButton(buttonRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: 320,
      });
    };

    const script = document.querySelector<HTMLScriptElement>(
      'script[src="https://accounts.google.com/gsi/client"]',
    );

    if (window.google) {
      renderButton();
    } else if (script) {
      script.addEventListener("load", renderButton);
    }

    return () => {
      cancelled = true;
      script?.removeEventListener("load", renderButton);
    };
  }, []);

  return <div ref={buttonRef} />;
}
