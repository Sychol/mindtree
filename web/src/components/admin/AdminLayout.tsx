import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";

import { useAdminAuth } from "../../hooks/useAdminAuth";

const ADMIN_NAV = [
  ["대시보드", "dashboard"],
  ["마음카드", "cards"],
  ["응원 문장", "replies"],
  ["설문 관리", "survey"],
  ["키워드", "keywords"],
  ["작업 상태", "jobs"],
  ["상품 지급", "rewards"],
  ["감사 로그", "audit-logs"],
  ["응답 데이터", "responses"],
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
          <p className="admin-eyebrow">현장 관리자</p>
          <h1>{eventSlug}</h1>
        </div>
        <div className="admin-user">
          <span>{admin?.displayName ?? "운영자"}</span>
          <button className="admin-button admin-button--secondary" type="button" onClick={handleLogout}>
            로그아웃
          </button>
        </div>
      </header>

      <div className="admin-layout">
        <nav className="admin-nav" aria-label="관리자 메뉴">
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
