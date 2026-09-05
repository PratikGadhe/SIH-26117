import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { LockKeyhole, ShieldCheck } from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { ApiError } from "../services/api";
import "./Login.css";

function Login() {
  const { authenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (authenticated) return <Navigate to="/" replace />;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;

    setSubmitting(true);
    setError("");
    try {
      await login(username.trim(), password);
      const destination = location.state?.from || "/";
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Sign-in could not be completed.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="login-logo"><ShieldCheck size={26} /></span>
          <div>
            <strong>ASTRA</strong>
            <span>Cognivault local workbench</span>
          </div>
        </div>

        <div className="login-heading">
          <span><LockKeyhole size={17} /> AUTHENTICATED ACCESS</span>
          <h1>Sign in</h1>
          <p>Use an account provisioned in the local Cognivault backend.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label>
            Username
            <input
              autoComplete="username"
              maxLength={64}
              onChange={(event) => setUsername(event.target.value)}
              required
              value={username}
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              maxLength={256}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error && <div className="login-error" role="alert">{error}</div>}

          <button disabled={submitting} type="submit">
            {submitting ? "Signing in…" : "Sign in to ASTRA"}
          </button>
        </form>

        <p className="login-note">
          The access token is kept only for this browser tab session. Public
          registration creates the basic <code>user</code> role, which cannot
          execute agent tasks.
        </p>
      </section>
    </main>
  );
}

export default Login;
