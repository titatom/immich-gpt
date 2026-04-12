import React, { useState, useEffect } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/useAuth";
import { getSetupStatus } from "../services/api";
import BrandLogo from "../components/BrandLogo";
import styles from "./Login.module.css";

export default function Login() {
  const { user, login, loading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getSetupStatus()
      .then(({ setup_required }) => {
        if (setup_required) {
          navigate("/setup", { replace: true });
        }
      })
      .catch(() => {
        // Ignore — if setup status is unreachable just show the login form
      });
  }, [navigate]);

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
        <BrandLogo
          variant="stacked"
          size="auth"
          className={styles.logoRow}
        />

        <h1 className={styles.heading}>Sign in</h1>

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
