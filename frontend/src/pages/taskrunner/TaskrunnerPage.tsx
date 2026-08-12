import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { Icon } from "../../components/Icon";
import { sessionApi } from "../../store/session";
import type { ProjectSubtab } from "../hub/types";
import { WorkflowEditor } from "./WorkflowEditor";
import { WorkflowList, type TaskSummary } from "./WorkflowList";
import type { ProjectOption } from "./types";
import { workflowApi } from "./workflowApi";
import styles from "./TaskrunnerPage.module.css";

const c = (name: string) => styles[name] ?? name;

interface TaskrunnerPageProps {
  embedded?: boolean;
  kindOverride?: "company" | "automation";
  taskIdOverride?: number | null;
  basePath?: string;
  onOpenProject?: (projectId: number, subtab: ProjectSubtab) => void;
}

export function TaskrunnerPage({
  embedded = false,
  kindOverride,
  taskIdOverride,
  basePath = "/taskrunner",
  onOpenProject,
}: TaskrunnerPageProps = {}) {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams<{ taskId?: string }>();
  const routeTaskId = Number(params.taskId || 0) || null;
  const taskId = taskIdOverride === undefined ? routeTaskId : taskIdOverride;
  const [kind, setKind] = useState<"company" | "automation">(kindOverride || "company");
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [username, setUsername] = useState("—");
  const [toastState, setToastState] = useState<{
    text: string;
    kind: "success" | "error" | "info";
  } | null>(null);

  useEffect(() => {
    if (kindOverride) setKind(kindOverride);
  }, [kindOverride]);

  const toast = useCallback((text: string, toastKind: "success" | "error" | "info" = "info") => {
    setToastState({ text, kind: toastKind });
    window.setTimeout(() => {
      setToastState((current) => current?.text === text ? null : current);
    }, 3200);
  }, []);

  const loadTasks = useCallback(async () => {
    const data = await workflowApi.tasks(kind);
    const summaries = await Promise.all((data.tasks || []).map(async (task) => {
      try {
        const runs = await workflowApi.runs(task.id, 10000);
        return { ...task, runs: runs.runs || [] };
      } catch {
        return { ...task, runs: [] };
      }
    }));
    setTasks(summaries);
  }, [kind]);

  useEffect(() => {
    void Promise.all([sessionApi.current(), workflowApi.projects()])
      .then(([user, projectData]) => {
        setUsername(user.username);
        setProjects(projectData.projects || []);
      })
      .catch(() => navigate("/login", { replace: true }));
  }, [navigate]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  const openTask = (id: number, run = false) => {
    navigate(`${basePath}/${id}${run ? "?run=1" : ""}`);
  };

  const goBack = () => navigate(basePath);

  // Hub keeps both runner tabs mounted, so #page-wrap, #grid-wrap, and #add-workflow-btn can be duplicated.
  // Do not query these elements by ID; migrating them to classes requires a dedicated phase.
  return (
    <div className={`${c("taskrunner-root")} ${embedded ? c("taskrunner-embedded") : ""}`}>
      {!taskId ? (
        <>
          {!embedded ? (
            <div id="topbar">
              <span className={c("logo")}><span className={c("dot")} />Xanax</span>
              <span className={c("page-title")}>Quy trình</span>
              <span className={c("topbar-user")}>
                {username}
                <button onClick={() => void sessionApi.logout().then(() => navigate("/login"))}>
                  Đăng xuất
                </button>
              </span>
            </div>
          ) : null}
          <div id="page-wrap">
            <WorkflowList
              kind={kind}
              tasks={tasks}
              projects={projects}
              showKindTabs={!embedded}
              onKind={setKind}
              onReload={loadTasks}
              onOpen={openTask}
              onOpenProject={onOpenProject}
              toast={toast}
            />
          </div>
        </>
      ) : (
        <WorkflowEditor
          taskId={taskId}
          runOnOpen={new URLSearchParams(location.search).get("run") === "1"}
          onBack={goBack}
          onSaved={loadTasks}
          onOpenProject={onOpenProject}
          toast={toast}
        />
      )}

      {toastState ? (
        <div className={`${c("react-toast")} ${c(toastState.kind)}`}>
          <Icon name={toastState.kind === "success" ? "check" : toastState.kind === "error" ? "warning" : "info"} />
          {toastState.text}
        </div>
      ) : null}
    </div>
  );
}
