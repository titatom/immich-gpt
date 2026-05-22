import React, { useState } from "react";
import BrandLogo from "../components/BrandLogo";
import { forgotPassword } from "../services/api";
import { formatApiError } from "../utils/apiError";
import { copySecretToClipboard } from "../utils/clipboard";
import styles from "./Login.module.css";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<{ message: string; token?: string } | null>(null);
  const [error, setError] = useState("");
  const [copyStatus, setCopyStatus] = useState<"copied" | "manual" | "failed" | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setCopyStatus(null);
    setSubmitting(true);
    try {
      const data = await forgotPassword(email);
      setResult({ message: data.message });
      if (data.token) {
        const copied = await copySecretToClipboard(data.token);
        setCopyStatus(copied ? "copied" : "manual");
      }
    } catch (err: unknown) {
      setError(formatApiError(err, "Something went wrong. Please try again."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <BrandLogo className={styles.logoRow} size="auth" showSubtitle={false} />

        <h1 className={styles.heading} style={{ marginBottom: 8 }}>Forgot password</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-base)", marginTop: 0, marginBottom: 24 }}>
          Admin accounts only — enter the user's email to generate a reset token.
        </p>

        {result ? (
          <div>
            <div style={{
              background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)",
              borderRadius: 8, padding: "12px 16px", color: "#4ade80",
              fontSize: "var(--text-base)", marginBottom: 16,
            }}>
              {result.message}
            </div>
            {copyStatus && (
              <div style={{
                background: "var(--bg-raised)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "12px 16px", marginBottom: 16,
              }}>
                <div style={{ color: "var(--text-secondary)", fontSize: "var(--text-sm)", marginBottom: 6 }}>
                  Reset token generated
                </div>
                <div style={{ color: "var(--text-primary)", fontSize: "var(--text-base)" }}>
                  {copyStatus === "copied"
                    ? "The one-time token was copied to your clipboard. It is not displayed here."
                    : "The one-time token could not be copied automatically, so use the admin user-management screen or server logs to issue a new token through a secure channel."}
                </div>
              </div>
            )}
            <a href="/reset-password" style={{ color: "var(--accent)", fontSize: "var(--text-base)" }}>
              Use this token to reset the password →
            </a>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className={styles.formGroup}>
              <label className={styles.label}>Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
                className={styles.input}
              />
            </div>

            {error && <div className={styles.errorBox}>{error}</div>}

            <button type="submit" disabled={submitting} className={styles.submitBtn}>
              {submitting ? "Generating…" : "Generate reset token"}
            </button>

            <div style={{ marginTop: 16, textAlign: "center" }}>
              <a href="/login" style={{ color: "var(--text-muted)", fontSize: "var(--text-base)", textDecoration: "none" }}>
                ← Back to login
              </a>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
