import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "./pages/login/LoginPage";
import { HubPage } from "./pages/hub/HubPage";
import { WorkspacePage } from "./pages/workspace/WorkspacePage";
import { TaskrunnerPage } from "./pages/taskrunner/TaskrunnerPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/v2/login" element={<LoginPage />} />
      <Route path="/v2/hub" element={<HubPage />} />
      <Route path="/v2/hub/:tab/*" element={<HubPage />} />
      <Route path="/v2/workspace" element={<WorkspacePage />} />
      <Route path="/v2/taskrunner" element={<TaskrunnerPage />} />
      <Route path="/v2/taskrunner/:taskId" element={<TaskrunnerPage />} />
      <Route path="/v2" element={<Navigate to="/v2/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
