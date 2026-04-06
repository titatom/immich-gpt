import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getReviewCount } from "../services/api";
import { useAuth } from "../contexts/useAuth";
import {
  LayoutDashboard, Eye, FolderKanban, MessageSquare,
  Settings, Activity, Zap, Images, ClipboardList, Users, LogOut,
} from "lucide-react";
import styles from "./Layout.module.css";

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
    <div className={styles.root}>
      <nav className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoRow}>
            <Zap size={22} color="var(--accent)" />
            <span className={styles.logoTitle}>Immich GPT</span>
          </div>
          <div className={styles.logoSub}>AI Metadata Enrichment</div>
        </div>

        <div className={styles.nav}>
          {navItems.map(({ path, label, icon: Icon, badge, exact }) => (
            <NavLink
              key={path}
              to={path}
              end={exact}
              className={({ isActive }) =>
                [styles.navLink, isActive ? styles.navLinkActive : ""].join(" ")
              }
            >
              <Icon size={16} />
              <span className={styles.navLabel}>{label}</span>
              {badge && countData && countData.count > 0 && (
                <span className={styles.navBadge}>{countData.count}</span>
              )}
            </NavLink>
          ))}

          {isAdmin && (
            <div className={styles.navAdmin}>
              <NavLink
                to="/admin/users"
                className={({ isActive }) =>
                  [styles.navLink, styles.navAdminLink, isActive ? styles.navAdminLinkActive : ""].join(" ")
                }
              >
                <Users size={16} />
                <span>Users</span>
              </NavLink>
            </div>
          )}
        </div>

        <div className={styles.userFooter}>
          {user && (
            <div className={styles.userInfo}>
              <div className={styles.userName}>{user.username}</div>
              <div className={styles.userEmail}>{user.email}</div>
            </div>
          )}
          <button onClick={logout} className={styles.signOutBtn}>
            <LogOut size={13} />
            Sign out
          </button>
        </div>
      </nav>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
