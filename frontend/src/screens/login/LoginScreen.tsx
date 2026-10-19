import { useCallback, useState } from "react";
import { useNavigate } from "react-router";
import { Callout, Spinner } from "@/ui";
import { useSession } from "@/features/auth/session.store";
import { GoogleSignInButton } from "@/features/auth/GoogleSignInButton";
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
        const message =
          error instanceof Error ? error.message : "Unable to sign in";

        if (message.includes("@umn.edu")) {
          setState("rejected");
        } else {
          setState("error");
          setErrorMessage(message);
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
          Tired of Looking?
          <br />
          Try Gopher Planner!
        </h1>
        <p className="login-lede">
          A four-year course plan for University of Minnesota students, built
          from your APAS, your major, and the credit load you want.
        </p>
      </div>

      <div>
        <section className="signin surf" aria-labelledby="signin-h">
          <h2 id="signin-h">Sign in</h2>
          <p className="muted">
            Use your University of Minnesota Google account.
          </p>

          {state === "rejected" && (
            <Callout tone="error" title="That account can't sign in">
              Use your University of Minnesota Google account, the one ending in
              @umn.edu.
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

          <p className="hint">
            Only University of Minnesota accounts (@umn.edu) can sign in.
          </p>
        </section>

        <nav className="legal" aria-label="Project links">
          <a
            href="https://github.com/Troppy2/Gopher-Planner"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          <a href="#terms">Terms</a>
          <a href="#privacy">Privacy</a>
        </nav>
      </div>
    </div>
  );
}
