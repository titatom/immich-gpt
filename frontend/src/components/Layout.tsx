import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/useAuth";
import { useJobCompletion } from "../hooks/useJobCompletion";
import BrandLogo from "./BrandLogo";
import {
  LayoutDashboard, Settings, Activity, Images, ClipboardList,
  Users, LogOut, Heart, Network, GitBranch,
} from "lucide-react";
import styles from "./Layout.module.css";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard, exact: true },
  { path: "/assets", label: "Assets", icon: Images },
  { path: "/routing", label: "Routing", icon: Network },
  { path: "/routing/plans", label: "Routing plans", icon: GitBranch },
  { path: "/jobs", label: "Jobs", icon: Activity },
  { path: "/logs", label: "Logs", icon: ClipboardList },
  { path: "/settings", label: "Settings", icon: Settings },
];

const DONATE_URL =
  "https://www.paypal.com/donate/?business=P9PZB949MYSD8&no_recurring=0&item_name=Thanks+for+helping+me+continuing+to+develop+this+app+%21&currency_code=CAD";

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  useJobCompletion();

  return (
    <div className={styles.root}>
      <nav className={styles.sidebar}>
        <div className={styles.logo}>
          <BrandLogo size="sidebar" />
        </div>

        <div className={styles.nav}>
          {navItems.map(({ path, label, icon: Icon, exact }) => (
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
          <a
            href={DONATE_URL}
            target="_blank"
            rel="noreferrer"
            className={styles.donateBtn}
          >
            <Heart size={13} className={styles.donateIcon} />
            Donate
          </a>
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
