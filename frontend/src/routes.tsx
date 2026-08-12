import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "./pages/login/LoginPage";
import { WorkspacePage } from "./pages/workspace/WorkspacePage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/v2/login" element={<LoginPage />} />
      <Route path="/v2/workspace" element={<WorkspacePage />} />
      <Route path="/v2" element={<Navigate to="/v2/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
