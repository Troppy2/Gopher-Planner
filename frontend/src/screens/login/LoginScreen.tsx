import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router";
import { Callout, Spinner } from "@/ui";
import { useSession } from "@/features/auth/session.store";
import { GoogleSignInButton } from "@/features/auth/GoogleSignInButton";
import { NotUmnAccountError } from "@/features/auth/google";
import { loginWithGoogle } from "@/features/auth/google";
import "./login.css";

export default function LoginScreen() {
  const signIn = useSession((s) => s.signIn);
  const navigate = useNavigate();

  const [state, setState] = useState<"idle" | "signing" | "rejected" | "error">(
    "idle",
  );
  const [errorMessage, setErrorMessage] = useState("");

  const onCredential = useCallback(
    async (credential: string) => {
      setState("signing");
      setErrorMessage("");

      try {
        const result = await loginWithGoogle(credential);

        signIn(result.user);
        navigate("/dashboard", { replace: true });
      } catch (error) {
        if (error instanceof NotUmnAccountError) {
          setState("rejected");
        } else {
          setState("error");
          setErrorMessage("Something went wrong on our end. Try again in a minute.");
        }
      }
    },
    [signIn, navigate],
  );

  return (
    <div className="login">
      <div className="login-brand">
        <img className="login-mark" src="/favicon.png" alt="" />
        <p className="login-name">Gopher Planner</p>
        <h1 className="slogan">
          Every semester, planned to graduation.
        </h1>
        <p className="login-lede">
          Upload your APAS. Get a four-year plan for your major, at the credit
          load you want.
        </p>
      </div>

      <div>
        <section className="signin surf" aria-labelledby="signin-h">
          <h2 id="signin-h">Sign in</h2>
          <p className="muted">
            Use your University of Minnesota Google account (@umn.edu).
          </p>

          {state === "rejected" && (
            <Callout tone="error" title="That account can't sign in">
              Switch to the Google account that ends in @umn.edu.
            </Callout>
          )}

          {state === "error" && (
            <Callout tone="error" title="Sign-in failed">
              {errorMessage}
            </Callout>
          )}

          {state === "signing" ? (
            <div role="status" aria-live="polite">
              <Spinner />
              Signing in…
            </div>
          ) : (
            <GoogleSignInButton onCredential={onCredential} />
          )}

        </section>

        <nav className="legal" aria-label="Project links">
          <a
            href="https://github.com/Troppy2/Gopher-Planner"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          <Link to="/terms">Terms</Link>
          <Link to="/privacy">Privacy</Link>
          <Link to="/contact">Contact</Link>
        </nav>
      </div>
    </div>
  );
}
