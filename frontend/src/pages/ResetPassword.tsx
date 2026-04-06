import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { resetPassword } from "../services/api";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (newPassword !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      await resetPassword(token, newPassword);
      navigate("/login", { replace: true, state: { message: "Password reset successfully. Please sign in." } });
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setError(msg || "Reset failed. The token may have expired.");
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
          <div style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9" }}>Immich GPT</div>
        </div>

        <h1 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: "0 0 24px" }}>
          Reset password
        </h1>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>
              Reset token
            </label>
            <input
              type="text"
              value={token}
              onChange={e => setToken(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 8,
                color: "#f1f5f9",
                fontSize: 13,
                outline: "none",
                boxSizing: "border-box",
                fontFamily: "monospace",
              }}
              placeholder="Paste token here"
            />
          </div>

          {[
            { label: "New password", value: newPassword, set: setNewPassword },
            { label: "Confirm password", value: confirm, set: setConfirm },
          ].map(({ label, value, set }) => (
            <div key={label} style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>
                {label}
              </label>
              <input
                type="password"
                value={value}
                onChange={e => set(e.target.value)}
                required
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
                placeholder="••••••••"
              />
            </div>
          ))}

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
            {submitting ? "Resetting…" : "Reset password"}
          </button>

          <div style={{ marginTop: 16, textAlign: "center" }}>
            <a href="/login" style={{ color: "#64748b", fontSize: 13, textDecoration: "none" }}>
              ← Back to login
            </a>
          </div>
        </form>
      </div>
    </div>
  );
}
