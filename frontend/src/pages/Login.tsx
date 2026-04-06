import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/useAuth";
import { Zap } from "lucide-react";
import styles from "./Login.module.css";

export default function Login() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!loading && user) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setError(msg || "Invalid username or password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <div className={styles.logoRow}>
          <Zap size={28} color="var(--accent)" />
          <div>
            <div className={styles.logoTitle}>Immich GPT</div>
            <div className={styles.logoSub}>AI Metadata Enrichment</div>
          </div>
        </div>

        <h1 className={styles.heading}>Sign in</h1>

        <div style={{
          background: "rgba(56,189,248,0.08)",
          border: "1px solid rgba(56,189,248,0.25)",
          borderRadius: 8,
          padding: "10px 12px",
          color: "#7dd3fc",
          fontSize: 12,
          marginBottom: 20,
          lineHeight: 1.5,
        }}>
          Default credentials: <strong>admin</strong> / <strong>admin</strong>.
          You will be asked to set a new password after first login.
        </div>

        <form onSubmit={handleSubmit}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
              autoComplete="username"
              className={styles.input}
              placeholder="admin"
            />
          </div>

          <div className={styles.formGroup} style={{ marginBottom: "24px" }}>
            <label className={styles.label}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className={styles.input}
              placeholder="••••••••"
            />
          </div>

          {error && <div className={styles.errorBox}>{error}</div>}

          <button type="submit" disabled={submitting} className={styles.submitBtn}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <a href="/forgot-password" className={styles.forgotLink}>
          Forgot password?
        </a>
      </div>
    </div>
  );
}
