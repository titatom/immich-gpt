import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getReviewCount } from "../services/api";
import { useAuth } from "../contexts/useAuth";
import {
  LayoutDashboard,
  Eye,
  FolderKanban,
  MessageSquare,
  Settings,
  Activity,
  Zap,
  Images,
  ClipboardList,
  Users,
  LogOut,
} from "lucide-react";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { path: "/review", label: "Review", icon: Eye, badge: true },
  { path: "/assets", label: "Assets", icon: Images },
  { path: "/buckets", label: "Buckets", icon: FolderKanban },
  { path: "/prompts", label: "Prompts", icon: MessageSquare },
  { path: "/jobs", label: "Jobs", icon: Activity },
  { path: "/logs", label: "Audit Logs", icon: ClipboardList },
  { path: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const { data: countData } = useQuery<{ count: number }>({
    queryKey: ["review-count"],
    queryFn: () => getReviewCount("pending_review"),
    refetchInterval: 15_000,
  });

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a" }}>
      {/* Sidebar */}
      <nav style={{
        width: 220,
        background: "#1e293b",
        borderRight: "1px solid #334155",
        display: "flex",
        flexDirection: "column",
        padding: "24px 0",
        flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ padding: "0 20px 24px", borderBottom: "1px solid #334155" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Zap size={22} color="#38bdf8" />
            <span style={{ fontSize: 16, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.3px" }}>
              Immich GPT
            </span>
          </div>
          <div style={{ fontSize: 11, color: "#64748b", marginTop: 4, paddingLeft: 32 }}>
            AI Metadata Enrichment
          </div>
        </div>

        {/* Nav links */}
        <div style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
          {navItems.map(({ path, label, icon: Icon, badge, exact }) => (
            <NavLink
              key={path}
              to={path}
              end={exact}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 12px",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? "#38bdf8" : "#94a3b8",
                background: isActive ? "rgba(56,189,248,0.1)" : "transparent",
                transition: "all 0.15s",
              })}
            >
              <Icon size={16} />
              <span style={{ flex: 1 }}>{label}</span>
              {badge && countData && countData.count > 0 && (
                <span style={{
                  background: "#ef4444",
                  color: "white",
                  borderRadius: 10,
                  padding: "1px 7px",
                  fontSize: 11,
                  fontWeight: 700,
                  minWidth: 20,
                  textAlign: "center",
                }}>
                  {countData.count}
                </span>
              )}
            </NavLink>
          ))}

          {isAdmin && (
            <NavLink
              to="/admin/users"
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "9px 12px",
                borderRadius: 8,
                textDecoration: "none",
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? "#a78bfa" : "#94a3b8",
                background: isActive ? "rgba(139,92,246,0.1)" : "transparent",
                transition: "all 0.15s",
                marginTop: 8,
                borderTop: "1px solid #334155",
                paddingTop: "9px",
              })}
            >
              <Users size={16} />
              <span>Users</span>
            </NavLink>
          )}
        </div>

        {/* User footer */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid #334155" }}>
          {user && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500, marginBottom: 2 }}>
                {user.username}
              </div>
              <div style={{ fontSize: 11, color: "#64748b" }}>{user.email}</div>
            </div>
          )}
          <button
            onClick={logout}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              width: "100%",
              padding: "7px 8px",
              background: "transparent",
              border: "1px solid #334155",
              borderRadius: 6,
              color: "#94a3b8",
              fontSize: 12,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <LogOut size={13} />
            Sign out
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, overflow: "auto", padding: 0 }}>
        <Outlet />
      </main>
    </div>
  );
}
