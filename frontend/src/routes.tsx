import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

const LoginPage = lazy(() => import("./pages/login/LoginPage").then((module) => ({ default: module.LoginPage })));
const HubPage = lazy(() => import("./pages/hub/HubPage").then((module) => ({ default: module.HubPage })));
const WorkspacePage = lazy(() => import("./pages/workspace/WorkspacePage").then((module) => ({ default: module.WorkspacePage })));
const TaskrunnerPage = lazy(() => import("./pages/taskrunner/TaskrunnerPage").then((module) => ({ default: module.TaskrunnerPage })));

function RouteFallback() {
  return <div role="status" aria-label="Đang tải">…</div>;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/hub" element={<HubPage />} />
        <Route path="/hub/:tab/*" element={<HubPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/taskrunner" element={<TaskrunnerPage />} />
        <Route path="/taskrunner/:taskId" element={<TaskrunnerPage />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  );
}
