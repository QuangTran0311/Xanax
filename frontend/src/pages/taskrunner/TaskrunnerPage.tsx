import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { enqueueToast, type ToastKind } from "../../components/Toast";
import { Tooltip } from "../../components/Tooltip";
import { useTaskrunnerText } from "../../i18n/taskrunner";
import { useTooltipText } from "../../i18n/tooltips";
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
  const tt = useTooltipText();
  const text = useTaskrunnerText();
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams<{ taskId?: string }>();
  const routeTaskId = Number(params.taskId || 0) || null;
  const taskId = taskIdOverride === undefined ? routeTaskId : taskIdOverride;
  const [kind, setKind] = useState<"company" | "automation">(kindOverride || "company");
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [username, setUsername] = useState("—");

  useEffect(() => {
    if (kindOverride) setKind(kindOverride);
  }, [kindOverride]);

  const toast = useCallback((text: string, toastKind: ToastKind = "info") => {
    enqueueToast(text, toastKind);
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

  // Hub giữ cả hai tab runner cùng được mount nên các ID page-wrap, grid-wrap và
  // add-workflow-btn có thể bị trùng. Không truy vấn chúng bằng ID trong đợt này.
  return (
    <div className={`${c("taskrunner-root")} ${embedded ? c("taskrunner-embedded") : ""}`}>
      {!taskId ? (
        <>
          {!embedded ? (
            <div id="topbar">
              <span className={c("logo")}><span className={c("dot")} />Xanax</span>
              <span className={c("page-title")}>{text("kind.company")}</span>
              <span className={c("topbar-user")}>
                {username}
                <Tooltip label={tt("tooltip.taskrunner.logout")}><button onClick={() => void sessionApi.logout().then(() => navigate("/login"))}>
                  {text("common.logout")}
                </button></Tooltip>
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
          initialRunId={Number(new URLSearchParams(location.search).get("attachRun") || 0) || null}
          onBack={goBack}
          onSaved={loadTasks}
          onOpenProject={onOpenProject}
          toast={toast}
        />
      )}

    </div>
  );
}
