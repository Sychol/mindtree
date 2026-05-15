import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";

import { useAdminAuth } from "../../hooks/useAdminAuth";

const ADMIN_NAV = [
  ["Dashboard", "dashboard"],
  ["Cards", "cards"],
  ["Replies", "replies"],
  ["Keywords", "keywords"],
  ["Jobs", "jobs"],
  ["Rewards", "rewards"],
  ["Audit Logs", "audit-logs"],
] as const;

export function AdminLayout() {
  const { eventSlug = "fire-expo-2026" } = useParams();
  const navigate = useNavigate();
  const { admin, logout } = useAdminAuth();

  const handleLogout = () => {
    logout();
    navigate("/admin/login", { replace: true });
  };

  return (
    <div className="admin-shell">
      <header className="admin-topbar">
        <div>
          <p className="admin-eyebrow">Field Admin</p>
          <h1>{eventSlug}</h1>
        </div>
        <div className="admin-user">
          <span>{admin?.displayName ?? "Operator"}</span>
          <button className="admin-button admin-button--secondary" type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <div className="admin-layout">
        <nav className="admin-nav" aria-label="Admin sections">
          {ADMIN_NAV.map(([label, path]) => (
            <NavLink
              className={({ isActive }) => `admin-nav__link${isActive ? " is-active" : ""}`}
              key={path}
              to={`/admin/events/${encodeURIComponent(eventSlug)}/${path}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="admin-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
