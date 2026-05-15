import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";

import { AdminRoutes } from "./routes/AdminRoutes";
import { DisplayRoutes } from "./routes/DisplayRoutes";
import { ParticipantRoutes } from "./routes/ParticipantRoutes";

function LegacyParticipantRedirect() {
  const { eventSlug } = useParams();
  if (!eventSlug || eventSlug === "admin" || eventSlug === "display") {
    return <Navigate to="/e/fire-expo-2026" replace />;
  }
  return <Navigate to={`/e/${encodeURIComponent(eventSlug)}`} replace />;
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin/*" element={<AdminRoutes />} />
        <Route path="/display/:eventSlug/*" element={<DisplayRoutes />} />
        <Route path="/e/:eventSlug/*" element={<ParticipantRoutes />} />
        <Route path="/:eventSlug" element={<LegacyParticipantRedirect />} />
        <Route path="*" element={<Navigate to="/e/fire-expo-2026" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
