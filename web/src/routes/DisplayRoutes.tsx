import { Route, Routes } from "react-router-dom";

import { DisplayPage } from "../pages/display/DisplayPage";

export function DisplayRoutes() {
  return (
    <Routes>
      <Route index element={<DisplayPage />} />
      <Route path="*" element={<DisplayPage />} />
    </Routes>
  );
}
