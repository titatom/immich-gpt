import React, { useState } from "react";
import { Zap } from "lucide-react";
import { forgotPassword } from "../services/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [result, setResult] = useState<{ message: string; token?: string } | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const data = await forgotPassword(email);
      setResult(data);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0f172a",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 24,
    }}>
      <div style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: 12,
        padding: 40,
        width: "100%",
        maxWidth: 400,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 32 }}>
          <Zap size={28} color="#38bdf8" />
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9" }}>Immich GPT</div>
          </div>
        </div>

        <h1 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: "0 0 8px" }}>
          Forgot password
        </h1>
        <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 0, marginBottom: 24 }}>
          Enter your email address. If the account exists, a reset token will be generated.
        </p>

        {result ? (
          <div>
            <div style={{
              background: "rgba(34,197,94,0.1)",
              border: "1px solid rgba(34,197,94,0.3)",
              borderRadius: 8,
              padding: "12px 16px",
              color: "#4ade80",
              fontSize: 13,
              marginBottom: 16,
            }}>
              {result.message}
            </div>
            {result.token && (
              <div style={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
                padding: "12px 16px",
                marginBottom: 16,
              }}>
                <div style={{ color: "#94a3b8", fontSize: 12, marginBottom: 6 }}>Reset token (valid 1 hour):</div>
                <code style={{ color: "#38bdf8", fontSize: 13, wordBreak: "break-all" }}>{result.token}</code>
              </div>
            )}
            <a href="/reset-password" style={{ color: "#38bdf8", fontSize: 13 }}>
              Use this token to reset your password →
            </a>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: 8,
                  color: "#f1f5f9",
                  fontSize: 14,
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>

            {error && (
              <div style={{
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 8,
                padding: "10px 12px",
                color: "#f87171",
                fontSize: 13,
                marginBottom: 16,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              style={{
                width: "100%",
                padding: "11px 16px",
                background: submitting ? "#1e3a5f" : "#0ea5e9",
                color: "white",
                border: "none",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
                cursor: submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Sending…" : "Get reset token"}
            </button>

            <div style={{ marginTop: 16, textAlign: "center" }}>
              <a href="/login" style={{ color: "#64748b", fontSize: 13, textDecoration: "none" }}>
                ← Back to login
              </a>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
