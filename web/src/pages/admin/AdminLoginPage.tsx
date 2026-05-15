import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiClientError } from "../../api/client";
import { useAdminAuth } from "../../hooks/useAdminAuth";
import { adminErrorMessage } from "../../utils/adminLabels";

function errorText(error: unknown): string {
  if (error instanceof ApiClientError) {
    return adminErrorMessage(error, "로그인에 실패했습니다.");
  }
  return "로그인에 실패했습니다.";
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
        <p className="admin-eyebrow">현장 관리자</p>
        <h1>관리자 로그인</h1>
        <label className="admin-field">
          이메일
          <input
            autoComplete="username"
            className="admin-input"
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            value={email}
          />
        </label>
        <label className="admin-field">
          비밀번호
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
          {submitting ? "로그인 중" : "로그인"}
        </button>
      </form>
    </main>
  );
}
