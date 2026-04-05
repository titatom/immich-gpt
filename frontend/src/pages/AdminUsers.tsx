import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  adminListUsers,
  adminCreateUser,
  adminUpdateUser,
  adminResetPassword,
  adminDeleteUser,
} from "../services/api";
import { UserPlus, RefreshCw, Trash2, ShieldCheck, UserX, User, Key } from "lucide-react";

interface AdminUser {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  force_password_change: boolean;
  created_at: string;
}

export default function AdminUsers() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ email: "", username: "", password: "", role: "user", force_password_change: true });
  const [createError, setCreateError] = useState("");
  const [resetResult, setResetResult] = useState<{ userId: string; token?: string } | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: adminListUsers,
  });

  const createMutation = useMutation({
    mutationFn: adminCreateUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setShowCreate(false);
      setCreateForm({ email: "", username: "", password: "", role: "user", force_password_change: true });
      setCreateError("");
    },
    onError: (err: unknown) => {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to create user";
      setCreateError(msg || "Failed to create user");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...data }: { id: string; is_active?: boolean; force_password_change?: boolean }) =>
      adminUpdateUser(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const resetMutation = useMutation({
    mutationFn: (userId: string) => adminResetPassword(userId),
    onSuccess: (data, userId) => setResetResult({ userId, token: data.token }),
  });

  const deleteMutation = useMutation({
    mutationFn: adminDeleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  return (
    <div style={{ padding: "32px 40px", maxWidth: 900 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>User Management</h1>
          <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>
            Admin view — account lifecycle only. No user content visible.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "9px 16px",
            background: "#0ea5e9",
            color: "white",
            border: "none",
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          <UserPlus size={15} /> New user
        </button>
      </div>

      {showCreate && (
        <div style={{
          background: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 10,
          padding: 24,
          marginBottom: 24,
        }}>
          <h3 style={{ color: "#f1f5f9", fontSize: 15, fontWeight: 600, margin: "0 0 16px" }}>Create user</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
            {(["email", "username", "password"] as const).map(field => (
              <div key={field}>
                <label style={{ display: "block", fontSize: 12, color: "#94a3b8", marginBottom: 4, textTransform: "capitalize" }}>
                  {field}
                </label>
                <input
                  type={field === "password" ? "password" : "text"}
                  value={createForm[field]}
                  onChange={e => setCreateForm(f => ({ ...f, [field]: e.target.value }))}
                  style={{
                    width: "100%",
                    padding: "8px 10px",
                    background: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: 6,
                    color: "#f1f5f9",
                    fontSize: 13,
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>
            ))}
            <div>
              <label style={{ display: "block", fontSize: 12, color: "#94a3b8", marginBottom: 4 }}>Role</label>
              <select
                value={createForm.role}
                onChange={e => setCreateForm(f => ({ ...f, role: e.target.value }))}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: 6,
                  color: "#f1f5f9",
                  fontSize: 13,
                  outline: "none",
                }}
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </div>
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, color: "#94a3b8", fontSize: 13, marginBottom: 16, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={createForm.force_password_change}
              onChange={e => setCreateForm(f => ({ ...f, force_password_change: e.target.checked }))}
            />
            Require password change on first login
          </label>
          {createError && (
            <div style={{ color: "#f87171", fontSize: 13, marginBottom: 12 }}>{createError}</div>
          )}
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => createMutation.mutate(createForm)}
              disabled={createMutation.isPending}
              style={{
                padding: "8px 16px",
                background: "#0ea5e9",
                color: "white",
                border: "none",
                borderRadius: 6,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {createMutation.isPending ? "Creating…" : "Create"}
            </button>
            <button
              onClick={() => { setShowCreate(false); setCreateError(""); }}
              style={{
                padding: "8px 16px",
                background: "transparent",
                color: "#94a3b8",
                border: "1px solid #334155",
                borderRadius: 6,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {resetResult?.token && (
        <div style={{
          background: "rgba(34,197,94,0.1)",
          border: "1px solid rgba(34,197,94,0.3)",
          borderRadius: 8,
          padding: "12px 16px",
          marginBottom: 20,
        }}>
          <div style={{ color: "#4ade80", fontSize: 13, marginBottom: 6 }}>Reset token (valid 1 hour — share securely):</div>
          <code style={{ color: "#38bdf8", fontSize: 12, wordBreak: "break-all" }}>{resetResult.token}</code>
          <button
            onClick={() => setResetResult(null)}
            style={{ display: "block", marginTop: 8, color: "#94a3b8", fontSize: 12, background: "none", border: "none", cursor: "pointer" }}
          >
            Dismiss
          </button>
        </div>
      )}

      {isLoading ? (
        <div style={{ color: "#64748b", fontSize: 14 }}>Loading users…</div>
      ) : (
        <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155" }}>
                {["User", "Role", "Status", "Actions"].map(h => (
                  <th key={h} style={{
                    padding: "12px 16px",
                    textAlign: "left",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "#64748b",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(users as AdminUser[]).map((u, idx) => (
                <tr key={u.id} style={{
                  borderBottom: idx < users.length - 1 ? "1px solid #1e293b" : "none",
                  background: idx % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
                }}>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <User size={14} color="#64748b" />
                      <div>
                        <div style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 500 }}>{u.username}</div>
                        <div style={{ color: "#64748b", fontSize: 12 }}>{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <span style={{
                      background: u.role === "admin" ? "rgba(139,92,246,0.15)" : "rgba(56,189,248,0.1)",
                      color: u.role === "admin" ? "#a78bfa" : "#38bdf8",
                      borderRadius: 6,
                      padding: "2px 8px",
                      fontSize: 12,
                      fontWeight: 500,
                    }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                      <span style={{
                        background: u.is_active ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                        color: u.is_active ? "#4ade80" : "#f87171",
                        borderRadius: 6,
                        padding: "2px 8px",
                        fontSize: 12,
                      }}>
                        {u.is_active ? "active" : "disabled"}
                      </span>
                      {u.force_password_change && (
                        <span style={{
                          background: "rgba(245,158,11,0.1)",
                          color: "#fbbf24",
                          borderRadius: 6,
                          padding: "2px 8px",
                          fontSize: 11,
                        }}>
                          pw change required
                        </span>
                      )}
                    </div>
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <ActionBtn
                        title={u.is_active ? "Disable" : "Enable"}
                        icon={u.is_active ? <UserX size={13} /> : <ShieldCheck size={13} />}
                        onClick={() => updateMutation.mutate({ id: u.id, is_active: !u.is_active })}
                        color={u.is_active ? "#f87171" : "#4ade80"}
                      />
                      <ActionBtn
                        title="Reset password"
                        icon={<Key size={13} />}
                        onClick={() => resetMutation.mutate(u.id)}
                        color="#f59e0b"
                      />
                      <ActionBtn
                        title="Require password change"
                        icon={<RefreshCw size={13} />}
                        onClick={() => updateMutation.mutate({ id: u.id, force_password_change: true })}
                        color="#94a3b8"
                      />
                      <ActionBtn
                        title="Delete user"
                        icon={<Trash2 size={13} />}
                        onClick={() => {
                          if (window.confirm(`Delete user ${u.username}? This cannot be undone.`)) {
                            deleteMutation.mutate(u.id);
                          }
                        }}
                        color="#ef4444"
                      />
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ padding: 32, textAlign: "center", color: "#475569", fontSize: 14 }}>
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ActionBtn({ title, icon, onClick, color }: {
  title: string;
  icon: React.ReactNode;
  onClick: () => void;
  color: string;
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 28,
        height: 28,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid #334155",
        borderRadius: 6,
        color,
        cursor: "pointer",
        transition: "background 0.15s",
      }}
    >
      {icon}
    </button>
  );
}
