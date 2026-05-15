import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiClientError } from "../../api/client";
import { useAdminAuth } from "../../hooks/useAdminAuth";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.message;
  }
  return "Login failed.";
}

export function AdminLoginPage() {
  const navigate = useNavigate();
  const { login } = useAdminAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/admin/events/fire-expo-2026/dashboard", { replace: true });
    } catch (loginError) {
      setError(errorText(loginError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="admin-login">
      <form className="admin-login__panel" onSubmit={handleSubmit}>
        <p className="admin-eyebrow">Field Admin</p>
        <h1>Operator Login</h1>
        <label className="admin-field">
          Email
          <input
            autoComplete="username"
            className="admin-input"
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            value={email}
          />
        </label>
        <label className="admin-field">
          Password
          <input
            autoComplete="current-password"
            className="admin-input"
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            value={password}
          />
        </label>
        {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
        <button className="admin-button admin-button--primary" disabled={submitting} type="submit">
          {submitting ? "Signing in" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
