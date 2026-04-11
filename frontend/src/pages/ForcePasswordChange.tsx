import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/useAuth";
import { changePassword } from "../services/api";
import { Lock } from "lucide-react";
import BrandLogo from "../components/BrandLogo";

export default function ForcePasswordChange() {
  const { refresh } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (newPassword !== confirm) {
      setError("New passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      await refresh();
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setError(msg || "Password change failed");
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
        <BrandLogo
          variant="stacked"
          size="auth"
          subtitle="AI metadata and album organization for Immich"
          style={{ marginBottom: 32 }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <Lock size={18} color="#f59e0b" />
          <h1 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>
            Change your password
          </h1>
        </div>
        <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 4, marginBottom: 28 }}>
          Your account requires a password change before you can continue.
        </p>

        <form onSubmit={handleSubmit}>
          {[
            { label: "Current password", value: currentPassword, set: setCurrentPassword },
            { label: "New password", value: newPassword, set: setNewPassword },
            { label: "Confirm new password", value: confirm, set: setConfirm },
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
            {submitting ? "Saving…" : "Set new password"}
          </button>
        </form>
      </div>
    </div>
  );
}
