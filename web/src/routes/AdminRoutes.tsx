import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { AdminLayout } from "../components/admin/AdminLayout";
import { getStoredAdminToken } from "../state/adminAuth";
import { AdminAuditLogsPage } from "../pages/admin/AdminAuditLogsPage";
import { AdminCardsPage } from "../pages/admin/AdminCardsPage";
import { AdminDashboardPage } from "../pages/admin/AdminDashboardPage";
import { AdminKeywordJobsPage } from "../pages/admin/AdminKeywordJobsPage";
import { AdminKeywordsPage } from "../pages/admin/AdminKeywordsPage";
import { AdminLoginPage } from "../pages/admin/AdminLoginPage";
import { AdminRepliesPage } from "../pages/admin/AdminRepliesPage";
import { AdminRewardsPage } from "../pages/admin/AdminRewardsPage";

function RequireAdmin({ children }: { children: ReactNode }) {
  if (!getStoredAdminToken()) {
    return <Navigate to="/admin/login" replace />;
  }
  return <>{children}</>;
}

export function AdminRoutes() {
  return (
    <Routes>
      <Route path="login" element={<AdminLoginPage />} />
      <Route
        path="events/:eventSlug"
        element={
          <RequireAdmin>
            <AdminLayout />
          </RequireAdmin>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<AdminDashboardPage />} />
        <Route path="cards" element={<AdminCardsPage />} />
        <Route path="replies" element={<AdminRepliesPage />} />
        <Route path="keywords" element={<AdminKeywordsPage />} />
        <Route path="jobs" element={<AdminKeywordJobsPage />} />
        <Route path="rewards" element={<AdminRewardsPage />} />
        <Route path="audit-logs" element={<AdminAuditLogsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/admin/login" replace />} />
    </Routes>
  );
}
