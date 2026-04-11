import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { UserPlus } from "lucide-react";
import { getSetupStatus, setupCreateAdmin } from "../services/api";
import { useAuth } from "../contexts/useAuth";
import BrandLogo from "../components/BrandLogo";

export default function Setup() {
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const [checking, setChecking] = useState(true);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getSetupStatus()
      .then(({ setup_required }) => {
        if (!setup_required) {
          navigate("/login", { replace: true });
        } else {
          setChecking(false);
        }
      })
      .catch(() => {
        // If status check fails just show the form anyway
        setChecking(false);
      });
  }, [navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setSubmitting(true);
    try {
      await setupCreateAdmin({ email, username, password });
      await refresh();
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : null;
      setError(msg || "Setup failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (checking) {
    return (
      <div style={{
        minHeight: "100vh",
        background: "#0f172a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}>
        <div style={{ color: "#64748b", fontSize: 14 }}>Loading…</div>
      </div>
    );
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
        maxWidth: 420,
      }}>
        <BrandLogo
          variant="stacked"
          size="auth"
          subtitle="AI metadata and album organization for Immich"
          style={{ marginBottom: 32 }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <UserPlus size={18} color="#38bdf8" />
          <h1 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>
            Create admin account
          </h1>
        </div>
        <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 4, marginBottom: 28, lineHeight: 1.6 }}>
          Welcome! No accounts exist yet. Create your administrator account to get started.
        </p>

        <form onSubmit={handleSubmit}>
          {[
            {
              label: "Email",
              type: "email",
              value: email,
              set: setEmail,
              placeholder: "admin@example.com",
              autoComplete: "email",
            },
            {
              label: "Username",
              type: "text",
              value: username,
              set: setUsername,
              placeholder: "admin",
              autoComplete: "username",
            },
            {
              label: "Password",
              type: "password",
              value: password,
              set: setPassword,
              placeholder: "••••••••",
              autoComplete: "new-password",
            },
            {
              label: "Confirm password",
              type: "password",
              value: confirm,
              set: setConfirm,
              placeholder: "••••••••",
              autoComplete: "new-password",
            },
          ].map(({ label, type, value, set, placeholder, autoComplete }, i) => (
            <div key={label} style={{ marginBottom: 16 }}>
              <label style={{ display: "block", fontSize: 13, color: "#94a3b8", marginBottom: 6 }}>
                {label}
              </label>
              <input
                type={type}
                value={value}
                onChange={e => set(e.target.value)}
                required
                autoFocus={i === 0}
                autoComplete={autoComplete}
                placeholder={placeholder}
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
              marginTop: 4,
            }}
          >
            {submitting ? "Creating account…" : "Create admin account"}
          </button>
        </form>
      </div>
    </div>
  );
}
